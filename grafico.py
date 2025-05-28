#Logos obtenidos de: https://www.flaticon.es/

import os
import sys
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import recuperar

DEFAULT_PATH = os.path.expanduser("~/Downloads/BackUp_CensoAgropecuario")
APP_TITLE = "Backup y Compresión de Información"
APP_SIZE = "500x350"

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
    carpeta = filedialog.askdirectory(title="Selecciona la carpeta de destino")
    if carpeta:
        label_ruta.config(text=f"Ruta de destino: {carpeta}")

def abrir_excel():
    try:
        ruta_completa = os.path.join(final_output_folder, "registro_backup.xlsx")
        if os.path.exists(ruta_completa):
            os.startfile(ruta_completa)
        else:
            messagebox.showwarning("Archivo no encontrado", f"No se encontró:\n{ruta_completa}")
    except Exception as e:
        messagebox.showerror("Error inesperado", str(e))

def ejecutar_script():
    folder_name = folder_entry.get()
    if not folder_name:
        return messagebox.showerror("Error", "Debes ingresar el nombre de la carpeta.")
    
    ruta_destino = label_ruta.cget("text").replace("Ruta de destino: ", "")
    os.makedirs(ruta_destino, exist_ok=True)

    btn_recuperar.config(state=tk.DISABLED)
    update_message("Ejecutando proceso...")
    update_progress(0)

    def hilo():
        global final_output_folder
        final_output_folder = os.path.join(ruta_destino, folder_name)
        try:
            recuperar.compress_projects_and_pull(final_output_folder, update_callback=update_progress)
            update_message("Transferencia completada...")
            extracted = recuperar.decompress_projects(final_output_folder, update_callback=update_progress)
            update_message("Descompresión completada...")
            recuperar.create_folders_with_project_archive(extracted, final_output_folder, update_callback=update_progress)
            update_message("Organización completada...")
            recuperar.clean_up(final_output_folder)
            update_message("Limpieza completada.")
            messagebox.showinfo("Éxito", f"Proceso completado en:\n{final_output_folder}")
        except Exception as e:
            ventana.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            update_progress(0)
            ventana.after(0, lambda: btn_recuperar.config(state=tk.NORMAL))

    threading.Thread(target=hilo).start()

def mostrar_ayuda():
    messagebox.showinfo("Ayuda", (
        "*** Cómo usar el programa ***\n\n"
        "- Ingresa el nombre de la carpeta (código del Especialista).\n"
        "- Puedes cambiar la carpeta de destino.\n"
        "- Presiona 'Iniciar Proceso' para extraer datos del dispositivo.\n"
        "- No cambies el nombre de la carpeta durante una brigada.\n"
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

ventana = tk.Tk()
ventana.title(APP_TITLE)
ventana.geometry(APP_SIZE)
ventana.resizable(False, False)

# Detectar si se ejecuta desde .exe o script
base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
img_path = lambda name: os.path.join(base_path, 'imagenes', name)

# Cargar íconos
iconos = {
    "logo": cargar_icono(img_path("logo.png")),
    "cerrar": cargar_icono(img_path("cerrar.png")),
    "respaldo": cargar_icono(img_path("respaldo.png")),
    "carpeta": cargar_icono(img_path("carpeta.png")),
    "info": cargar_icono(img_path("informacion.png")),
    "excel": cargar_icono(img_path("excel.png"))
}
if iconos["logo"]: ventana.iconphoto(False, iconos["logo"])

label_info_dispositivo = tk.Label(ventana, text="Cargando información del dispositivo...", wraplength=450)
label_info_dispositivo.pack(pady=10)
mostrar_info_dispositivo()

frame_folder = tk.Frame(ventana)
frame_folder.pack(pady=5)
tk.Label(frame_folder, text="Nombre de la carpeta:").pack(side=tk.LEFT, padx=5)
folder_entry = tk.Entry(frame_folder, width=40)
folder_entry.pack(side=tk.LEFT, padx=5)

frame_ruta = tk.Frame(ventana)
frame_ruta.pack(pady=10)
label_ruta = tk.Label(frame_ruta, text=f"Ruta de destino: {DEFAULT_PATH}", anchor="w", bg="lightgray", wraplength=350)
label_ruta.pack(side=tk.LEFT, padx=5)
tk.Button(frame_ruta, text="Cambiar ruta", image=iconos["carpeta"], compound="left", command=cambiar_ruta).pack(side=tk.LEFT, padx=5)

frame_progreso = tk.Frame(ventana)
frame_progreso.pack(pady=5)
tk.Label(frame_progreso, text="Progreso:").pack(side=tk.LEFT, padx=5)
progress_bar = ttk.Progressbar(frame_progreso, length=300, orient='horizontal', mode='determinate', maximum=100)
progress_bar.pack(side=tk.LEFT, padx=5)

label_resultado = tk.Label(ventana, text="Aquí aparecerán los resultados", wraplength=450)
label_resultado.pack(pady=10)

frame_botones = tk.Frame(ventana)
frame_botones.pack(pady=20)

btn_recuperar = tk.Button(
    frame_botones,
    text="Iniciar Proceso",
    image=iconos["respaldo"],
    compound="left",
    command=ejecutar_script,
    width=115
)
btn_recuperar.pack(side=tk.LEFT, padx=10)

tk.Button(frame_botones, text="Salir", image=iconos["cerrar"], compound="left", command=cerrar_ventana, width=70).pack(side=tk.LEFT, padx=10)
tk.Button(frame_botones, text="Abrir Registro de Actividades", image=iconos["excel"], compound="left", command=abrir_excel).pack(side=tk.LEFT, padx=10)

btn_ayuda = tk.Button(ventana, image=iconos["info"], command=mostrar_ayuda)
btn_ayuda.pack(side=tk.RIGHT, padx=20)
btn_ayuda.bind("<Enter>", mostrar_tooltip)

ventana.mainloop()