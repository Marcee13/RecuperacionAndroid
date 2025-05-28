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

    # Crear DataFrame de la nueva actividad
    new_activity_df = pd.DataFrame(actividad)

    # Si el archivo Excel ya existe
    if os.path.exists(excel_file):
        # Leer el archivo y concatenar la nueva actividad
        df = pd.read_excel(excel_file, engine="openpyxl")
        df = pd.concat([df, new_activity_df], ignore_index=True)
        
        # Agrupar por 'IdSegmento' y unir los 'CodConsultor' por salto de línea
        df_grouped = df.groupby("IdSegmento", as_index=False).agg({
            "CodConsultor": lambda x: "\n".join(x.dropna().astype(str)),  # Unir consultores
            "Fecha": "first",  # Usar la primera fecha por segmento
            "Ruta": "first"    # Usar la primera ruta por segmento
        })
    else:
        # Si el archivo no existe, usar solo el nuevo DataFrame
        df_grouped = new_activity_df

    # Guardar o sobrescribir el archivo Excel con el DataFrame agrupado
    with pd.ExcelWriter(excel_file, engine="xlsxwriter") as writer:
        df_grouped.to_excel(writer, index=False, sheet_name="Registro")

        # Formatear las celdas
        workbook = writer.book
        worksheet = writer.sheets["Registro"]
        text_format = workbook.add_format({"text_wrap": True})  # Ajuste de texto

        # Ajuste de columnas
        worksheet.set_column("A:A", 20)  # Fecha
        worksheet.set_column("B:B", 25, text_format)  # CodConsultor
        worksheet.set_column("C:C", 20)  # IdSegmento
        worksheet.set_column("D:D", 40, text_format)  # Ruta