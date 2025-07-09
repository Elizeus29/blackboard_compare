import streamlit as st
import zipfile
import os
import pandas as pd
import xml.etree.ElementTree as ET
import shutil
import openpyxl

# Función para extraer zip desde archivo físico
def extract_zip(zip_file_path, extract_dir):
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
    os.makedirs(extract_dir, exist_ok=True)
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)

# Procesar identifiers
def process_course_structure(base_dir):
    identifiers = []
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.lower().endswith('.xml'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    tree = ET.fromstring(content)
                    for id_elem in tree.findall('.//{*}identifier'):
                        if id_elem.text:
                            id_text = id_elem.text.strip()
                            if "/institution/duoc_coaching_ultra/gdp8900_ols/" in id_text.lower():
                                path_start = id_text.lower().find("/institution/duoc_coaching_ultra/gdp8900_ols/")
                                file_path_part = id_text[path_start:]
                                if "/" in file_path_part:
                                    path_parts = file_path_part.rsplit("/", 1)
                                    resource_path = path_parts[0] + "/"
                                    resource_name = path_parts[1] if len(path_parts) > 1 else ""
                                else:
                                    resource_path = file_path_part
                                    resource_name = ""

                                identifiers.append({
                                    "Archivo XML": file,
                                    "Identifier completo": id_text,
                                    "Ruta extraída": resource_path,
                                    "Archivo extraído": resource_name
                                })
                except Exception as e:
                    st.warning(f"Error al procesar {file}: {e}")
                    continue

    df_identifiers = pd.DataFrame(identifiers)
    df_identifiers = df_identifiers[df_identifiers["Archivo extraído"].str.contains(r"\\.", na=False)]
    df_identifiers["Archivo extraído"] = df_identifiers["Archivo extraído"].str.strip().str.lower()
    return df_identifiers

st.title("Comparador de respaldos de curso (Blackboard)")

zip1 = st.file_uploader("Selecciona el primer respaldo (versión original)", type=["zip"])
zip2 = st.file_uploader("Selecciona el segundo respaldo (versión actualizado)", type=["zip"])

if zip1 and zip2:
    with st.spinner("Procesando respaldos..."):
        # Guardar ZIP 1 en disco
        zip1_path = "temp_original.zip"
        with open(zip1_path, "wb") as f:
            f.write(zip1.read())

        # Guardar ZIP 2 en disco
        zip2_path = "temp_actualizado.zip"
        with open(zip2_path, "wb") as f:
            f.write(zip2.read())

        dir1 = "temp_extracted_v1"
        dir2 = "temp_extracted_v2"

        extract_zip(zip1_path, dir1)
        extract_zip(zip2_path, dir2)

        df_v1 = process_course_structure(dir1)
        df_v2 = process_course_structure(dir2)

        set_v1 = set(df_v1["Archivo extraído"])
        set_v2 = set(df_v2["Archivo extraído"])

        nuevos = set_v2 - set_v1
        eliminados = set_v1 - set_v2
        iguales = set_v1 & set_v2

        df_nuevos = df_v2[df_v2["Archivo extraído"].isin(nuevos)]
        df_eliminados = df_v1[df_v1["Archivo extraído"].isin(eliminados)]
        df_iguales = df_v2[df_v2["Archivo extraído"].isin(iguales)]

        st.write("### Archivos nuevos en el respaldo actualizado")
        st.dataframe(df_nuevos)

        st.write("### Archivos eliminados")
        st.dataframe(df_eliminados)

        st.write("### Archivos que se mantienen")
        st.dataframe(df_iguales)

        output_file = "reporte_comparacion.xlsx"
        with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
            df_nuevos.to_excel(writer, sheet_name="Nuevos", index=False)
            df_eliminados.to_excel(writer, sheet_name="Eliminados", index=False)
            df_iguales.to_excel(writer, sheet_name="Iguales", index=False)

        with open(output_file, "rb") as f:
            st.download_button("Descargar reporte completo (Excel)", f, file_name="reporte_comparacion.xlsx")

        shutil.rmtree(dir1)
        shutil.rmtree(dir2)
        os.remove(zip1_path)
        os.remove(zip2_path)

    st.success("¡Comparación completada!")
