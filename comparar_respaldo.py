import streamlit as st
import zipfile
import os
import pandas as pd
import xml.etree.ElementTree as ET

# Función para extraer archivos del zip
def extract_zip(uploaded_file, extract_dir):
    with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)

# Función para buscar y procesar identifiers en XML
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
                except:
                    continue

    df_identifiers = pd.DataFrame(identifiers)
    df_identifiers = df_identifiers[df_identifiers["Archivo extraído"].str.contains(r"\\.", na=False)]
    return df_identifiers

# Streamlit UI
st.title("Comparador de respaldos de curso (Blackboard)")

st.write("## Subir archivo ZIP original")
zip1 = st.file_uploader("Selecciona el primer respaldo (versión original)", type=["zip"])

st.write("## Subir archivo ZIP actualizado")
zip2 = st.file_uploader("Selecciona el segundo respaldo (versión actualizada)", type=["zip"])

if zip1 and zip2:
    with st.spinner("Procesando respaldos..."):
        dir1 = "extracted_v1"
        dir2 = "extracted_v2"

        os.makedirs(dir1, exist_ok=True)
        os.makedirs(dir2, exist_ok=True)

        extract_zip(zip1, dir1)
        extract_zip(zip2, dir2)

        df_v1 = process_course_structure(dir1)
        df_v2 = process_course_structure(dir2)

        # Identificar archivos nuevos
        set_v1 = set(df_v1["Archivo extraído"].str.lower())
        set_v2 = set(df_v2["Archivo extraído"].str.lower())

        nuevos = set_v2 - set_v1
        eliminados = set_v1 - set_v2
        iguales = set_v1 & set_v2

        st.write("### Archivos nuevos en el respaldo actualizado")
        df_nuevos = df_v2[df_v2["Archivo extraído"].str.lower().isin(nuevos)]
        st.dataframe(df_nuevos)

        st.write("### Archivos eliminados (ya no están en el nuevo respaldo)")
        df_eliminados = df_v1[df_v1["Archivo extraído"].str.lower().isin(eliminados)]
        st.dataframe(df_eliminados)

        st.write("### Archivos que se mantienen")
        df_iguales = df_v2[df_v2["Archivo extraído"].str.lower().isin(iguales)]
        st.dataframe(df_iguales)

        # Reporte descargable
        with pd.ExcelWriter("reporte_comparacion.xlsx") as writer:
            df_nuevos.to_excel(writer, sheet_name="Nuevos", index=False)
            df_eliminados.to_excel(writer, sheet_name="Eliminados", index=False)
            df_iguales.to_excel(writer, sheet_name="Iguales", index=False)

        with open("reporte_comparacion.xlsx", "rb") as f:
            st.download_button("Descargar reporte completo (Excel)", f, file_name="reporte_comparacion.xlsx")

        # Limpiar directorios
        import shutil
        shutil.rmtree(dir1)
        shutil.rmtree(dir2)

    st.success("¡Comparación completada!")
