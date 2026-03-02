import os
import pandas as pd
from datetime import datetime

def registrar_actividad_en_excel(output_folder, cod_consultor, id_segmento):
    # Ruta del archivo Excel
    excel_file = os.path.join(output_folder, "registro_backup.xlsx")

    # Datos a registrar
    actividad = {
        "CodConsultor": [cod_consultor],
        "IdSegmento": [id_segmento],
    }

    # Crear DataFrame de la nueva actividad
    new_activity_df = pd.DataFrame(actividad)

    # Si el archivo ya existe, leerlo y agregarle la nueva fila
    if os.path.exists(excel_file):
        df = pd.read_excel(excel_file, engine="openpyxl")
        df = pd.concat([df, new_activity_df], ignore_index=True)
    else:
        df = new_activity_df

    # Guardar el archivo sin agrupar
    with pd.ExcelWriter(excel_file, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Registro")

        # Formato de celdas
        workbook = writer.book
        worksheet = writer.sheets["Registro"]
        text_format = workbook.add_format({"text_wrap": True})

        # Ajuste de columnas
        worksheet.set_column("A:A", 20)  # Fecha
        worksheet.set_column("B:B", 25, text_format)  # CodConsultor
        worksheet.set_column("C:C", 20)  # IdSegmento
        worksheet.set_column("D:D", 40, text_format)  # Ruta
