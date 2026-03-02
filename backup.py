# Logos obtenidos de: https://www.flaticon.es/

import os
import sys
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import recuperar

DEFAULT_PATH = os.path.expanduser("~/Downloads/BackUp_CensoAgropecuario")
DEFAULT_DB_PATH = "Download/censo_agro_esp_db.db"
DEFAULT_XML_PATH = "Download/archivo.xml"
APP_TITLE = "Backup y Compresión de Información"
APP_SIZE = "800x600"

final_output_folder = ""

def obtener_numero_serie():
    try:
        result = subprocess.run(['adb', 'devices'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
        devices = [line.split()[0] for line in result.stdout.decode().splitlines() if line.endswith("\tdevice")]
        return devices[0] if devices else None
    except FileNotFoundError:
        print("ADB no está instalado.")
        return None

def mostrar_info_dispositivo():
    serial = obtener_numero_serie()
    label_info_dispositivo.config(text=f"Dispositivo conectado: {serial}" if serial else "No hay dispositivos conectados.")
    ventana.after(1000, mostrar_info_dispositivo)

def update_progress(progress):
    progress_bar['value'] = progress
    ventana.update_idletasks()

def update_message(message):
    label_resultado.config(text=message)
    ventana.update_idletasks()

def cambiar_ruta():
    carpeta = filedialog.askdirectory(title="Selecciona la carpeta de SEDE")
    if carpeta:
        label_ruta.config(text=f"Ruta de SEDE: {carpeta}")

def cambiar_db():
    archivo = filedialog.askopenfilename(title="Selecciona la base de datos del especialista", filetypes=[("SQLite DB", "*.db")])
    if archivo:
        label_db.config(text=f"Backup de especialista: {archivo}")

def cambiar_xml():
    archivo = filedialog.askopenfilename(title="Selecciona el archivo XML del especialista", filetypes=[("Archivo XML", "*.xml")])
    if archivo:
        label_xml.config(text=f"Archivo XML: {archivo}")

def abrir_excel():
    try:
        ruta_completa = os.path.join(final_output_folder, "registro_backup.xlsx")
        if os.path.exists(ruta_completa):
            os.startfile(ruta_completa)
        else:
            messagebox.showwarning("Archivo no encontrado", f"No se encontró:\n{ruta_completa}")
    except Exception as e:
        messagebox.showerror("Error inesperado", str(e))

def ejecutar_especialista():
    db_path = label_db.cget("text").replace("Backup de especialista: ", "").strip()
    xml_path = label_xml.cget("text").replace("Archivo XML: ", "").strip()
    folder_name = folder_entry.get()

    if not folder_name:
        return messagebox.showerror("Error", "Debes ingresar el nombre de la carpeta.")

    ruta_sede = label_ruta.cget("text").replace("Ruta de SEDE: ", "").strip()
    if not ruta_sede:
        return messagebox.showerror("Error", "Debes seleccionar una carpeta de SEDE.")

    if not os.path.isfile(db_path) or not os.path.isfile(xml_path):
        return messagebox.showerror("Error", "Debes seleccionar tanto el archivo .db como el archivo .xml")

    os.makedirs(ruta_sede, exist_ok=True)
    global final_output_folder
    final_output_folder = os.path.join(ruta_sede, folder_name)

    btn_completo.config(state=tk.DISABLED)
    update_progress(0)
    update_message("Procesando backup de especialista...")

    def hilo_especialista():
        try:
            recuperar.procesar_db_especialista(db_path, xml_path, final_output_folder)

            ventana.after(0, lambda: update_message("Backup de especialista completado."))
            ventana.after(0, lambda: messagebox.showinfo("Éxito", f"Backup completado en:\n{final_output_folder}"))

        except Exception as e:
            ventana.after(0, lambda: messagebox.showerror("Error", str(e)))

        finally:
            ventana.after(0, lambda: btn_completo.config(state=tk.NORMAL))
            ventana.after(0, lambda: update_progress(0))

    threading.Thread(target=hilo_especialista).start()



def ejecutar_script(usar_db_esp=False):
    folder_name = folder_entry.get()
    if not folder_name:
        return messagebox.showerror("Error", "Debes ingresar el nombre de la carpeta.")

    ruta_sede = label_ruta.cget("text").replace("Ruta de SEDE: ", "").strip()
    if not ruta_sede:
        return messagebox.showerror("Error", "Debes seleccionar una carpeta de SEDE.")

    os.makedirs(ruta_sede, exist_ok=True)
    global final_output_folder
    final_output_folder = os.path.join(ruta_sede, folder_name)

    if usar_db_esp:
        db_path = label_db.cget("text").replace("Backup de especialista: ", "").strip()
        xml_path = label_xml.cget("text").replace("Archivo XML: ", "").strip()
        if not os.path.isfile(db_path) or not os.path.isfile(xml_path):
            return messagebox.showerror("Error", "Debes seleccionar tanto el archivo .db como el archivo .xml")
    else:
        db_path = xml_path = None

    btn_recuperar.config(state=tk.DISABLED)
    btn_completo.config(state=tk.DISABLED)
    update_message("Ejecutando proceso...")
    update_progress(0)

    def hilo():
        try:
            if usar_db_esp:
                recuperar.procesar_db_especialista(db_path, xml_path, final_output_folder)

            recuperar.clean_up(final_output_folder)
            update_message("Limpieza completada.")

            if recuperar.compress_projects_and_pull(final_output_folder, update_callback=update_progress):
                update_message("Transferencia completada...")
                extracted = recuperar.decompress_projects(final_output_folder, update_callback=update_progress)
                if extracted is not None:
                    update_message("Descompresión completada...")
                    recuperar.create_folders_with_project_archive(extracted, final_output_folder, update_callback=update_progress)
                    update_message("Organización completada...")
                    recuperar.clean_up(final_output_folder)

            update_progress(0)
            ventana.after(0, lambda: messagebox.showinfo("Éxito", f"Proceso completado en:\n{final_output_folder}"))

        except Exception as e:
            ventana.after(0, lambda err=e: messagebox.showerror("Error", str(err)))
        finally:
            ventana.after(0, lambda: btn_recuperar.config(state=tk.NORMAL))
            ventana.after(0, lambda: btn_completo.config(state=tk.NORMAL))

    threading.Thread(target=hilo).start()

def mostrar_ayuda():
    messagebox.showinfo("Ayuda", (
        "*** Cómo usar el programa ***\n\n"
        "- Ingresa el nombre de la carpeta (código del Especialista).\n"
        "- Puedes cambiar la carpeta de destino.\n"
        "- Selecciona el archivo .db y el archivo .xml del especialista.\n"
        "- Presiona 'DMC TÉCNICO' para extraer datos del dispositivo.\n"
        "- Presiona 'DMC ESPECIALISTA' para ejecutar ambos procesos.\n"
        "- Presiona 'Abrir Registro de Actividades' para ver el Excel generado."
    ))

def mostrar_tooltip(event):
    tooltip = tk.Toplevel(ventana)
    tooltip.wm_overrideredirect(True)
    tooltip.geometry(f"+{event.x_root + 10}+{event.y_root + 25}")
    tk.Label(tooltip, text="Ayuda", bg="#DDDDDD", padx=5, pady=2).pack()
    tooltip.after(800, tooltip.destroy)

def cargar_icono(path, size=(18, 18)):
    try:
        return ImageTk.PhotoImage(Image.open(path).resize(size))
    except Exception as e:
        print(f"Error cargando {path}: {e}")
        return None

def cerrar_ventana():
    ventana.destroy()

# Interfaz
ventana = tk.Tk()
ventana.title(APP_TITLE)
ventana.geometry(APP_SIZE)
ventana.resizable(False, False)

base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
img_path = lambda name: os.path.join(base_path, 'imagenes', name)

iconos = {
    "logo": cargar_icono(img_path("logo.png")),
    "cerrar": cargar_icono(img_path("cerrar.png")),
    "respaldo": cargar_icono(img_path("respaldo.png")),
    "carpeta": cargar_icono(img_path("carpeta.png")),
    "info": cargar_icono(img_path("informacion.png")),
    "excel": cargar_icono(img_path("excel.png"))
}
if iconos["logo"]:
    ventana.iconphoto(False, iconos["logo"])

label_info_dispositivo = tk.Label(ventana, text="Cargando información del dispositivo...", wraplength=450)
label_info_dispositivo.pack(pady=10)
mostrar_info_dispositivo()

frame_folder = tk.Frame(ventana)
frame_folder.pack(pady=5)
tk.Label(frame_folder, text="Usuario de Especialista:").pack(side=tk.LEFT, padx=5)
folder_entry = tk.Entry(frame_folder, width=40)
folder_entry.pack(side=tk.LEFT, padx=5)

frame_ruta = tk.Frame(ventana)
frame_ruta.pack(pady=5)
label_ruta = tk.Label(frame_ruta, text=f"Ruta de SEDE: {DEFAULT_PATH}", anchor="w", bg="lightgray", wraplength=350)
label_ruta.pack(side=tk.LEFT, padx=5)
tk.Button(frame_ruta, text="Cambiar SEDE", image=iconos["carpeta"], compound="left", command=cambiar_ruta).pack(side=tk.LEFT, padx=5)

frame_db = tk.Frame(ventana)
frame_db.pack(pady=5)
label_db = tk.Label(frame_db, text=f"Backup de especialista: {DEFAULT_DB_PATH}", anchor="w", bg="lightgray", wraplength=350)
label_db.pack(side=tk.LEFT, padx=5)
tk.Button(frame_db, text="Cambiar ruta de BD", image=iconos["carpeta"], compound="left", command=cambiar_db).pack(side=tk.LEFT, padx=5)

frame_xml = tk.Frame(ventana)
frame_xml.pack(pady=5)
label_xml = tk.Label(frame_xml, text=f"Archivo XML: {DEFAULT_XML_PATH}", anchor="w", bg="lightgray", wraplength=350)
label_xml.pack(side=tk.LEFT, padx=5)
tk.Button(frame_xml, text="Cambiar ruta de preferencias", image=iconos["carpeta"], compound="left", command=cambiar_xml).pack(side=tk.LEFT, padx=5)

frame_progreso = tk.Frame(ventana)
frame_progreso.pack(pady=5)
tk.Label(frame_progreso, text="Progreso:").pack(side=tk.LEFT, padx=5)
progress_bar = ttk.Progressbar(frame_progreso, length=300, orient='horizontal', mode='determinate', maximum=100)
progress_bar.pack(side=tk.LEFT, padx=5)

label_resultado = tk.Label(ventana, text="Aquí aparecerán los resultados", wraplength=450)
label_resultado.pack(pady=10)

frame_botones = tk.Frame(ventana)
frame_botones.pack(pady=20)

btn_recuperar = tk.Button(frame_botones, text="DMC DE TÉCNICO", image=iconos["respaldo"], compound="left", command=lambda: ejecutar_script(False), width=115)
btn_recuperar.pack(side=tk.LEFT, padx=10)

btn_completo = tk.Button(frame_botones, text="DMC DE ESPECIALISTA", image=iconos["respaldo"], compound="left", command=ejecutar_especialista, width=115)
btn_completo.pack(side=tk.LEFT, padx=10)

tk.Button(frame_botones, text="Salir", image=iconos["cerrar"], compound="left", command=cerrar_ventana, width=70).pack(side=tk.LEFT, padx=10)
tk.Button(frame_botones, text="Abrir Registro de Actividades", image=iconos["excel"], compound="left", command=abrir_excel).pack(side=tk.LEFT, padx=10)

btn_ayuda = tk.Button(ventana, image=iconos["info"], command=mostrar_ayuda)
btn_ayuda.pack(side=tk.RIGHT, padx=20)
btn_ayuda.bind("<Enter>", mostrar_tooltip)

ventana.mainloop()
