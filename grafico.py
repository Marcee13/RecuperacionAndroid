#Logos obtenidos de: https://www.flaticon.es/

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, filedialog
import os
import recuperar
import threading
import subprocess
import sys
from PIL import Image, ImageTk

# Ruta por defecto (modificable)
DEFAULT_PATH = os.path.expanduser("~/Downloads/BackUp_CensoAgropecuario")

# Función para verificar y obtener el número de serie de los dispositivos conectados
def obtener_numero_serie():
    try:
        result = subprocess.Popen(
            ['adb', 'devices'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW # Se evita la creacion de ventana CMD por cada ejecucion de la funcion
        )
        output, error = result.communicate()  # Captura la salida del comando
        output = output.decode('utf-8')
        
        lines = output.splitlines()
        devices = [line.split()[0] for line in lines if line.endswith("\tdevice")]

        if devices:
            return devices[0]
        else:
            return None
    except FileNotFoundError:
        print("ADB no está instalado.")
        return None

# Función para actualizar el mensaje del dispositivo conectado
def mostrar_info_dispositivo():
    serial = obtener_numero_serie()
    if serial:
        label_info_dispositivo.config(text=f"Dispositivo conectado: {serial}")
    else:
        label_info_dispositivo.config(text="No hay dispositivos conectados.")
    
    ventana.after(1000, mostrar_info_dispositivo)

# Función que actualiza la barra de progreso
def update_progress(progress):
    progress_bar['value'] = progress
    ventana.update_idletasks()

# Función para actualizar el mensaje en la interfaz
def update_message(message):
    label_resultado.config(text=message)
    ventana.update_idletasks()

# Función para seleccionar y cambiar la ruta de destino
def cambiar_ruta():
    carpeta = filedialog.askdirectory(title="Selecciona la carpeta de destino")
    if carpeta:
        label_ruta.config(text=f"Ruta de destino: {carpeta}")

# Función que ejecuta el proceso en segundo plano usando hilos
def ejecutar_script():
    folder_name = folder_entry.get()
    if not folder_name:
        messagebox.showerror("Error", "Debes ingresar el nombre de la carpeta.")
        return

    ruta_destino = label_ruta.cget("text").replace("Ruta de destino: ", "")
    if not os.path.exists(ruta_destino):
        try:
            # Crear la ruta si no existe
            os.makedirs(ruta_destino)
            messagebox.showinfo("Éxito", f"Se creó la ruta: {ruta_destino}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo crear la ruta. Error: {e}")
            return

    btn_recuperar.config(state=tk.DISABLED)
    update_message("Ejecutando proceso...")
    update_progress(0)

    def hilo_recuperar():
        try:
            final_output_folder = os.path.join(ruta_destino, folder_name)

            recuperar.compress_projects_and_pull(final_output_folder, update_callback=update_progress)
            update_message("Compresión y transferencia completadas...")
            
            extracted_folder = recuperar.decompress_projects(final_output_folder, update_callback=update_progress)
            update_message("Descompresión completada...")
            
            recuperar.create_folders_with_project_archive(extracted_folder, final_output_folder, update_callback=update_progress)
            update_message("Archivos organizados correctamente...")
            
            recuperar.clean_up(final_output_folder)
            update_message("Limpieza completada...")

            ventana.after(0, mostrar_resultado, f"Proceso completado con éxito en: {final_output_folder}")
        except Exception as e:
            ventana.after(0, mostrar_error, f"Error: {e}")
        finally:
            ventana.after(0, habilitar_boton)

    thread = threading.Thread(target=hilo_recuperar)
    thread.start()

def mostrar_resultado(resultado):
    label_resultado.config(text=resultado)

def mostrar_error(mensaje):
    messagebox.showerror("Error", mensaje)

def habilitar_boton():
    btn_recuperar.config(state=tk.NORMAL)

def cerrar_ventana():
    ventana.destroy()

# Detectar si estamos en un archivo .exe
if getattr(sys, 'frozen', False):
    # Si estamos en un .exe, obtener la ruta de los archivos extraídos
    application_path = sys._MEIPASS
else:
    # Si estamos ejecutando desde un script, usar la ruta del script
    application_path = os.path.dirname(os.path.abspath(__file__))

# Ruta completa a las imágenes
logo_path = os.path.join(application_path, 'imagenes/logo.png')
cerrar_path = os.path.join(application_path, 'imagenes/cerrar.png')
respaldo_path = os.path.join(application_path, 'imagenes/respaldo.png')
carpeta_path = os.path.join(application_path, 'imagenes/carpeta.png')

# Ventana principal de la aplicación se define el tamaño y otras caracteristicas.
ventana = tk.Tk()
ventana.title("Backup y Compresión de Información")
ventana.geometry("500x400")
ventana.resizable(False,False)

# Se aplica el logo de la aplicación
try:
    icono = tk.PhotoImage(file=logo_path)
    ventana.iconphoto(False, icono)
except Exception as e:
    print(f"Error al cargar el icono: {e}")

# Carga de imagen para los botones
try:
    image_salir = Image.open(cerrar_path)
    image_salir = image_salir.resize((18, 18))
    iconSalir = ImageTk.PhotoImage(image_salir)
except Exception as e:
    print(f"Error al cargar la imagen 'cerrar.png': {e}")

try:
    image_inicio = Image.open(respaldo_path)
    image_inicio = image_inicio.resize((18, 18))
    iconInicio = ImageTk.PhotoImage(image_inicio)
except Exception as e:
    print(f"Error al cargar la imagen 'respaldo.png': {e}")

try:
    image_carpeta = Image.open(carpeta_path)
    image_carpeta = image_carpeta.resize((18, 18))
    iconCarpeta = ImageTk.PhotoImage(image_carpeta)
except Exception as e:
    print(f"Error al cargar la imagen 'carpeta.png': {e}")

# Etiqueta para mostrar el número de serie del dispositivo
label_info_dispositivo = tk.Label(
    ventana,
    text="Cargando información del dispositivo...",
    wraplength=450
)
label_info_dispositivo.pack(pady=10)

# Funcion para comprobar dispositivos conectados
mostrar_info_dispositivo()

# Frame para etiqueta y entrada
frame_folder = tk.Frame(ventana)
frame_folder.pack(pady=5)

label_folder = tk.Label(
    frame_folder,
    text="Nombre de la carpeta:"
)
label_folder.pack(side=tk.LEFT, padx=5, pady=20)

folder_entry = tk.Entry(frame_folder, width=40)
folder_entry.pack(side=tk.LEFT, padx=5)

# Frame para contener la ruta y el botón de cambiar
frame_ruta = tk.Frame(ventana)
frame_ruta.pack(pady=10)

# Mostrar la ruta de destino
label_ruta = tk.Label(
    frame_ruta,
    text=f"Ruta de destino: {DEFAULT_PATH}",
    anchor="w",
    bg="lightgray",
    wraplength=350,
    justify="left"
)
label_ruta.pack(side=tk.LEFT, padx=5, fill="x")

# Botón para cambiar la ruta
btn_cambiar_ruta = tk.Button(
    frame_ruta,
    text="Cambiar ruta",
    image=iconCarpeta,
    compound="left",
    padx=5,
    command=cambiar_ruta
)
btn_cambiar_ruta.pack(side=tk.LEFT, padx=5)

# Frame para la barra de progreso y su etiqueta
frame_progreso = tk.Frame(ventana)
frame_progreso.pack(pady=5)

label_progress = tk.Label(frame_progreso, text="Progreso:")
label_progress.pack(side=tk.LEFT, padx=5)

progress_bar = ttk.Progressbar(
    frame_progreso,
    length=300,
    orient='horizontal',
    mode='determinate',
    maximum=100
)
progress_bar.pack(side=tk.LEFT, padx=5)

# Mostrar los resultados
label_resultado = tk.Label(
    ventana,
    text="Aquí aparecerán los resultados",
    wraplength=450
)
label_resultado.pack(pady=10)

# Frame para los botones
frame_botones = tk.Frame(ventana)
frame_botones.pack(pady=20)

btn_recuperar = tk.Button(
    frame_botones,
    text="Iniciar Proceso",
    image=iconInicio,
    compound="left",
    anchor="w",
    padx=10,
    command=ejecutar_script,
    width=115
)
btn_recuperar.pack(side=tk.LEFT, padx=10)

btn_salir = tk.Button(
    frame_botones,
    text="Salir",
    image=iconSalir,
    compound="left",
    anchor="w",
    padx=10,
    command=cerrar_ventana,
    width="70"
)
btn_salir.pack(side=tk.LEFT, padx=10)

ventana.mainloop()

