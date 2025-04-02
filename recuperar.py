import subprocess
import os
import tarfile
import sqlite3
import shutil
import reporte_excel

def obtener_numero_serie():
    try:
        devices_output = subprocess.check_output(['adb', 'devices']).decode('utf-8').strip().splitlines()
        
        if len(devices_output) > 1:
            dispositivo_serie = devices_output[1].split()[0]
            return dispositivo_serie  # Devuelve el número de serie del dispositivo
        else:
            return None  # Retorna None si no hay dispositivos conectados

    except subprocess.CalledProcessError as e:
        return f"Error al obtener el número de serie: {str(e)}"
        
def verificar_dispositivo_conectado():
    try:
        devices_output = subprocess.check_output(['adb', 'devices']).decode('utf-8').strip().splitlines()
        return len(devices_output) > 1
    except subprocess.CalledProcessError:
        return False

def sanitize_name(name):
    """Reemplaza los caracteres problemáticos para nombres de archivos."""
    name = name.replace(":", "_").replace("(", "_").replace(")", "_")
    return name

def delete_db_journal_files_on_device(update_callback=None):
    if update_callback:
        update_callback(10)
    #Se crean rutas diferentes dependiendo de la version del aplicativo. Se debe modificar segun sea la direccion a la carpeta.    
    #delete_cmd = "find /storage/emulated/0/Android/data/org.odk.collect.android/files/projects -name '*.db-journal' -exec rm -f {} +"
    delete_cmd = "find /storage/emulated/0/Android/data/sv.gob.bcr.odk.surveys/files/projects -name '*.db-journal' -exec rm -f {} +"
    subprocess.run(["adb", "shell", delete_cmd], check=True, creationflags=subprocess.CREATE_NO_WINDOW) #Se crea una flag para evitar la aparicion de ventanas CMD
    if update_callback:
        update_callback(20)

def compress_projects_and_pull(local_destination_folder, update_callback=None):
    """Comprime la carpeta 'projects' en el dispositivo y la transfiere a la PC."""
    os.makedirs(local_destination_folder, exist_ok=True)
    delete_db_journal_files_on_device()
    
    #Se crean rutas diferentes dependiendo de la version del aplicativo. Se debe modificar segun sea la direccion a la carpeta.
    #remote_tar_path = "/storage/emulated/0/Android/data/org.odk.collect.android/files/projects.tar.gz"
    #compress_cmd = f"toybox tar -czf {remote_tar_path} -C /storage/emulated/0/Android/data/org.odk.collect.android/files projects"

    remote_tar_path = "/storage/emulated/0/Android/data/sv.gob.bcr.odk.surveys/files/projects.tar.gz"
    compress_cmd = f"toybox tar -czf {remote_tar_path} -C /storage/emulated/0/Android/data/sv.gob.bcr.odk.surveys/files projects"

    subprocess.run(["adb", "shell", compress_cmd], check=True, creationflags=subprocess.CREATE_NO_WINDOW)

    subprocess.run(["adb", "pull", remote_tar_path, local_destination_folder], check=True, creationflags=subprocess.CREATE_NO_WINDOW) #Se crea una flag para evitar la aparicion de ventanas CMD

    if update_callback:
        update_callback(40)

def decompress_projects(local_destination_folder, update_callback=None):
    """Descomprime el archivo 'projects.tar.gz' en una carpeta local."""
    tar_gz_path = os.path.join(local_destination_folder, "projects.tar.gz")
    extracted_folder = os.path.join(local_destination_folder, "projects_extracted")
    
    os.makedirs(extracted_folder, exist_ok=True)
    with tarfile.open(tar_gz_path, "r:gz") as tar_ref:
        total_files = len(tar_ref.getmembers())
        for i, member in enumerate(tar_ref.getmembers()):
            member.name = sanitize_name(member.name)
            tar_ref.extract(member, path=extracted_folder)
            
            # Actualizar el progreso
            if update_callback:
                progress = int(((i + 1) / total_files) * 100)
                update_callback(progress)  # Llamar al callback con el progreso
            
    return extracted_folder


def create_folders_with_project_archive(extracted_folder, output_folder, update_callback=None):
    """Organiza los datos extraídos y crea archivos comprimidos en subcarpetas."""
    projects_root = os.path.join(extracted_folder, "projects")
    if not os.path.isdir(projects_root):
        print(f"No existe la carpeta: {projects_root}")
        return

    subfolders = [f for f in os.listdir(projects_root) if os.path.isdir(os.path.join(projects_root, f))]
    total_subfolders = len(subfolders)
    
    # Recorremos cada subcarpeta
    for i, folder_name in enumerate(subfolders):
        subfolder_path = os.path.join(projects_root, folder_name)
        if not os.path.isdir(subfolder_path):
            continue

        metadata_dir = os.path.join(subfolder_path, "metadata")
        if not os.path.isdir(metadata_dir):
            continue
        
        for file_name in os.listdir(metadata_dir):
            if file_name.lower().endswith(".db"):
                db_path = os.path.join(metadata_dir, file_name)
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT DISTINCT codConsultor, idSegmento FROM user_logs;")
                    rows = cursor.fetchall()

                    os.makedirs(output_folder, exist_ok=True)
                    for row in rows:
                        cod_consultor, id_segmento = row
                        if not id_segmento:
                            continue

                        segmento_folder = os.path.join(output_folder, str(id_segmento))
                        os.makedirs(segmento_folder, exist_ok=True)
                        
                        consultor_folder = os.path.join(segmento_folder, cod_consultor)
                        os.makedirs(consultor_folder, exist_ok=True)
                        
                        tar_gz_path = os.path.join(consultor_folder, "projects.tar.gz")
                        with tarfile.open(tar_gz_path, "w:gz") as tar:
                            tar.add(extracted_folder, arcname="projects")

                        #Se capturan los datos para generar el Excel
                        reporte_excel.registrar_actividad_en_excel(output_folder, cod_consultor, id_segmento)

                    conn.close()
                except sqlite3.Error as e:
                    print(f"Error al leer la base de datos '{db_path}': {e}")
                finally:
                    conn.close()

        # Actualiza el progreso
        if update_callback:
            progress = int(((i + 1) / total_subfolders) * 100)
            update_callback(progress)        

def clean_up(local_destination_folder):
    """Elimina los archivos temporales generados durante el proceso."""
    tar_gz_path = os.path.join(local_destination_folder, "projects.tar.gz")
    extracted_folder = os.path.join(local_destination_folder, "projects_extracted")

    if os.path.exists(tar_gz_path):
        os.remove(tar_gz_path)
    
    if os.path.exists(extracted_folder):
        shutil.rmtree(extracted_folder)
