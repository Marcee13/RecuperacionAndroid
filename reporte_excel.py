import os
import pandas as pd
from datetime import datetime

def registrar_actividad_en_excel(output_folder, cod_consultor, id_segmento):
    # Ruta del archivo Excel
    excel_file = os.path.join(output_folder, "registro_backup.xlsx")
    
    # Datos a registrar
    actividad = {
        "Fecha": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        "CodConsultor": [cod_consultor],
        "IdSegmento": [id_segmento],
        "Ruta": [output_folder],
    }

    # Si el archivo existe, leerlo; si no, crear un DataFrame vacío
    if os.path.exists(excel_file):
        df = pd.read_excel(excel_file, engine="openpyxl")  # Usa openpyxl para evitar conflictos
    else:
        df = pd.DataFrame(columns=["Fecha", "CodConsultor", "IdSegmento", "Ruta"])

    # Agregar nueva actividad
    df = pd.concat([df, pd.DataFrame(actividad)], ignore_index=True)

    # Agrupar CodConsultor por IdSegmento con saltos de línea
    df_grouped = df.groupby("IdSegmento", as_index=False).agg({
        "CodConsultor": lambda x: "\n".join(x.dropna().astype(str)),  # Evita NaN y asegura que sean strings
        "Fecha": "first",  
        "Ruta": "first"
    })

    # Guardar en Excel con formato
    with pd.ExcelWriter(excel_file, engine="xlsxwriter") as writer:
        df_grouped.to_excel(writer, index=False, sheet_name="Registro")

        # Aplicar formato para ajuste de texto en Excel
        workbook = writer.book
        worksheet = writer.sheets["Registro"]
        text_format = workbook.add_format({"text_wrap": True})  # Ajuste de texto

        # Ajustar la columna "CodConsultor" con saltos de línea y ancho adecuado
        worksheet.set_column("A:A", 20)
        worksheet.set_column("B:B", 25, text_format)
        worksheet.set_column("C:C", 20)
        worksheet.set_column("D:D", 40, text_format)