import os
import tarfile
import sqlite3
import shutil
import subprocess
import re
import tkinter.messagebox as msgbox
import reporte_excel

RUTA_7Z = "7z"

def verificar_dependencias():
    faltantes = []
    for comando, nombre in [("adb", "ADB"), (RUTA_7Z, "7-Zip (7z)")]:
        try:
            subprocess.run([comando], stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
        except FileNotFoundError:
            faltantes.append(nombre)

    if faltantes:
        msg = "❗ Las siguientes dependencias no están disponibles en las variables de entorno:\n\n"
        msg += "\n".join(f"• {dep}" for dep in faltantes)
        msg += "\n\nPor favor agrégalas al PATH antes de continuar."
        msgbox.showerror("Dependencias faltantes", msg)
        raise SystemExit("Faltan dependencias: " + ", ".join(faltantes))

def obtener_numero_serie():
    try:
        devices_output = subprocess.check_output(['adb', 'devices'], stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW).decode('utf-8').strip().splitlines()
        if len(devices_output) > 1:
            return devices_output[1].split()[0]
        return None
    except subprocess.CalledProcessError as e:
        return f"Error al obtener el número de serie: {str(e)}"

def sanitize_name(name):
    return name.replace(":", "_").replace("(", "_").replace(")", "_")

def contar_archivos_en_directorio(raiz):
    total = 0
    for ruta, carpetas, archivos in os.walk(raiz):
        total += len(archivos)
    return total

def contar_archivos_en_dmc():
    try:
        result = subprocess.check_output([
    "adb", "shell", "find /storage/emulated/0/Android/data/sv.gob.bcr.odk.encf/files/projects -type f | wc -l"
    ], stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)

        return int(result.decode().strip())
    except subprocess.CalledProcessError as e:
        print(f"[INFO] No se pudo contar archivos en DMC: {e.output.decode().strip()}")
        return 0
    except Exception as e:
        print(f"[ERROR] al contar archivos en el DMC: {e}")
        return 0


def delete_db_journal_files_on_device(update_callback=None):
    if update_callback:
        update_callback(10)
    delete_cmd = "find /storage/emulated/0/Android/data/sv.gob.bcr.odk.encf/files/projects -name '*.db-journal' -exec rm -f {} +"
    try:
        subprocess.run(["adb", "shell", delete_cmd], check=True, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
    except subprocess.CalledProcessError as e:
        print("[INFO] No existe la carpeta 'projects', se omite limpieza de .db-journal.")
    if update_callback:
        update_callback(20)


def compress_projects_and_pull(local_destination_folder, update_callback=None):
    verificar_dependencias()
    os.makedirs(local_destination_folder, exist_ok=True)

    #Verificar si la carpeta 'projects' existe en el dispositivo
    check_cmd = ["adb", "shell", "ls /storage/emulated/0/Android/data/sv.gob.bcr.odk.encf/files/projects"]
    result = subprocess.run(check_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    
    if "No such file" in result.stderr:
        print("[INFO] No existe la carpeta 'projects', se omite compresión y extracción de técnico.")
        return False  # Se omite el backup técnico

    #Si existe, continúa normalmente
    try:
        delete_db_journal_files_on_device()
    except Exception as e:
        print(f"[INFO] No se pudo eliminar archivos .db-journal: {e}")

    remote_tar_path = "/storage/emulated/0/Android/data/sv.gob.bcr.odk.encf/files/projects.tar.gz"
    compress_cmd = f"toybox tar -czf {remote_tar_path} -C /storage/emulated/0/Android/data/sv.gob.bcr.odk.encf/files projects"

    try:
        subprocess.run(["adb", "shell", compress_cmd], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        subprocess.run(["adb", "pull", remote_tar_path, local_destination_folder], check=True, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] No se pudo crear o extraer el tar.gz: {e}")
        return False

    if update_callback:
        update_callback(40)
    return True


def decompress_projects(local_destination_folder, update_callback=None):
    tar_gz_path = os.path.join(local_destination_folder, "projects.tar.gz")
    
    if not os.path.exists(tar_gz_path):
        print("[INFO] No se encontró el archivo projects.tar.gz, se omite descompresión.")
        return None

    extracted_folder = os.path.join(local_destination_folder, "projects_extracted")
    os.makedirs(extracted_folder, exist_ok=True)

    with tarfile.open(tar_gz_path, "r:gz") as tar_ref:
        total_files = len(tar_ref.getmembers())
        for i, member in enumerate(tar_ref.getmembers()):
            member.name = sanitize_name(member.name)
            tar_ref.extract(member, path=extracted_folder)
            if update_callback:
                progress = int(((i + 1) / total_files) * 100)
                update_callback(progress)

    return extracted_folder


def obtener_nombre_unico(base_path, nombre_base):
    nombre_final = nombre_base
    contador = 2
    while os.path.exists(os.path.join(base_path, nombre_final)):
        nombre_final = f"{nombre_base}-{contador}"
        contador += 1
    return nombre_final

def create_folders_with_project_archive(extracted_folder, output_folder, update_callback=None):
    archivos_dmc = contar_archivos_en_dmc()
    projects_root = os.path.join(extracted_folder, "projects")
    if not os.path.isdir(projects_root):
        print(f"No existe la carpeta: {projects_root}")
        return

    archivos_extraidos = contar_archivos_en_directorio(projects_root)
    subfolders = [f for f in os.listdir(projects_root) if os.path.isdir(os.path.join(projects_root, f))]
    registros_excel = []
    comprimidos_exitosos = 0

    for i, folder_name in enumerate(subfolders):
        subfolder_path = os.path.join(projects_root, folder_name)
        metadata_dir = os.path.join(subfolder_path, "metadata")
        db_file = os.path.join(metadata_dir, "user_logs.db")

        if not os.path.isfile(db_file):
            continue

        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT codConsultor, idSegmento FROM user_logs;")
            rows = cursor.fetchall()
            conn.close()
        except sqlite3.Error as e:
            print(f"Error al leer la base de datos '{db_file}': {e}")
            continue

        for cod_consultor, id_segmento in rows:
            if not id_segmento:
                continue

            segmento_folder = os.path.join(output_folder, str(id_segmento))
            os.makedirs(segmento_folder, exist_ok=True)

            nombre_consultor_final = obtener_nombre_unico(segmento_folder, cod_consultor)
            consultor_folder = os.path.join(segmento_folder, nombre_consultor_final)
            os.makedirs(consultor_folder, exist_ok=True)

            seven_zip_path = os.path.join(consultor_folder, "projects.7z")
            source_path = os.path.join(extracted_folder, "projects")

            try:
                subprocess.run(
                    [RUTA_7Z, "a", "-t7z", seven_zip_path, f"{source_path}\\*"],
                    shell=True,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True, creationflags=subprocess.CREATE_NO_WINDOW
                )
                registros_excel.append((cod_consultor, id_segmento, consultor_folder))
                comprimidos_exitosos += 1
            except subprocess.CalledProcessError as e:
                print(f"[ERROR] Falló la compresión con 7z: {e.stderr or e.stdout}")
                continue

        if update_callback:
            progress = int(((i + 1) / len(subfolders)) * 100)
            update_callback(progress)

    for cod_consultor, id_segmento, ruta in registros_excel:
        try:
            reporte_excel.registrar_actividad_en_excel(output_folder, cod_consultor, id_segmento)
        except Exception as ex:
            print(f"[ERROR] Al registrar en Excel: {ex}")

    mensaje = (
        f"📁 Archivos detectados en DMC: {archivos_dmc}\n"
        f"📂 Archivos extraídos en laptop: {archivos_extraidos}\n"
        f"🧾 Respaldos generados (consultores): {len(registros_excel)}\n"
        f"✅ Archivos comprimidos exitosamente (.7z): {comprimidos_exitosos}\n"
        f"🔍 Comparación extracción: {archivos_extraidos} / {archivos_dmc}"
    )
    try:
        msgbox.showinfo("Resumen del Backup", mensaje)
    except:
        print(mensaje)

def procesar_db_especialista(db_path_local, xml_path_local, output_folder):
    try:
        if not os.path.isfile(db_path_local) or not os.path.isfile(xml_path_local):
            raise ValueError("Ambos archivos (DB y XML) deben existir.")

        # Limpieza de nombres de archivo
        db_name = re.sub(r"\[\d+\]", "", os.path.basename(db_path_local))
        xml_name = re.sub(r"\[\d+\]", "", os.path.basename(xml_path_local))

        # 1) Consultar pares (segmentoId, codConsultorSuper) y quedarnos con codConsultorSuper únicos
        conn = sqlite3.connect(db_path_local)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT s.segmentoId, s.codConsultorSuper
            FROM SupervisionEntity s
            JOIN BrigadeEntity b ON s.especialistaId = b.idSupervisor
            JOIN ConsultantEntity ce ON ce.idConsultores = b.idSupervisor
            WHERE ce.codConsultor = s.codConsultorSuper
        """)
        resultados = cursor.fetchall()
        conn.close()

        print(f"[INFO] Resultado consulta (segmentoId, codConsultorSuper): {resultados}")

        def obtener_nombre_unico_raiz(output_folder, cod_consultor):
            nombre_base = cod_consultor
            contador = 1
            nombre_final = nombre_base
            while os.path.exists(os.path.join(output_folder, nombre_final)):
                contador += 1
                nombre_final = f"{nombre_base}-{contador}"
            return nombre_final

        # 2) Crear carpetas en la RAÍZ por cada codConsultorSuper y copiar DB/XML ahí
        consultores_procesados = set()
        for _, codConsultorSuper in resultados:
            if not codConsultorSuper or codConsultorSuper in consultores_procesados:
                continue
            consultores_procesados.add(codConsultorSuper)

            nombre_final = obtener_nombre_unico_raiz(output_folder, codConsultorSuper)
            carpeta_consultor = os.path.join(output_folder, nombre_final)
            os.makedirs(carpeta_consultor, exist_ok=True)

            shutil.copy2(db_path_local, os.path.join(carpeta_consultor, db_name))
            shutil.copy2(xml_path_local, os.path.join(carpeta_consultor, xml_name))
            print(f"[OK] Copiados DB y XML en: {carpeta_consultor}")

        print("[OK] Procesamiento completado: DB y XML copiados en carpetas por consultor (raíz).")

    except Exception as e:
        print(f"[ERROR] procesar_db_especialista: {e}")


def obtener_nombre_unico_raiz(output_folder, cod_consultor):
    nombre_base = cod_consultor
    contador = 1
    nombre_final = nombre_base
    while os.path.exists(os.path.join(output_folder, nombre_final)):
        contador += 1
        nombre_final = f"{nombre_base}-{contador}"
    return nombre_final

def clean_up(local_destination_folder):
    tar_gz_path = os.path.join(local_destination_folder, "projects.tar.gz")
    extracted_folder = os.path.join(local_destination_folder, "projects_extracted")
    try:
        if os.path.exists(tar_gz_path):
            os.remove(tar_gz_path)
        if os.path.exists(extracted_folder):
            shutil.rmtree(extracted_folder)
        print("Limpieza completada.")
    except Exception as e:
        print(f"[ERROR] durante clean_up(): {e}")
