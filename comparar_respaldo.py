import zipfile
import os
import pandas as pd
import xml.etree.ElementTree as ET
import shutil
import streamlit as st
import openpyxl

log_file = "log_proceso.txt"

def write_log(text):
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(text + "\n")
    print(text)

def extract_zip(zip_file, extract_dir):
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
    os.makedirs(extract_dir, exist_ok=True)
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    write_log(f"✅ Extraído: {zip_file} en {extract_dir}")

def process_course_structure(base_dir):
    identifiers = []
    xml_count = 0
    ids_found = 0
    write_log(f"🔍 Procesando carpeta: {base_dir}")

    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.lower().endswith('.xml'):
                xml_count += 1
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    xml_root = ET.fromstring(content)
                    found_in_file = 0
                    for id_elem in xml_root.findall('.//{*}identifier'):
                        if id_elem.text:
                            id_text = id_elem.text.strip()
                            identifiers.append({
                                "Archivo XML": file,
                                "Identifier completo": id_text,
                                "Archivo extraído": id_text.split("/")[-1]
                            })
                            ids_found += 1
                            found_in_file += 1
                    write_log(f"✅ XML leído: {file} — Identifiers encontrados: {found_in_file}")
                except Exception as e:
                    write_log(f"⚠️ Error en {file}: {e}")

    write_log(f"✅ Archivos XML procesados: {xml_count}")
    write_log(f"✅ Total identifiers encontrados: {ids_found}\n")

    df_identifiers = pd.DataFrame(identifiers)
    if not df_identifiers.empty:
        df_identifiers["Archivo extraído"] = df_identifiers["Archivo extraído"].str.strip().str.lower()
        df_identifiers["Clave comparación"] = df_identifiers["Archivo extraído"]
    return df_identifiers

st.title("Comparador de respaldos (Blackboard) — Versión Final Sin Filtrar")

zip1 = st.file_uploader("Selecciona el primer respaldo (versión original)", type=["zip"])
zip2 = st.file_uploader("Selecciona el segundo respaldo (versión actualizado)", type=["zip"])

if os.path.exists(log_file):
    os.remove(log_file)

if zip1 and zip2:
    with st.spinner("Procesando respaldos..."):
        zip1_path = "temp_v1.zip"
        with open(zip1_path, "wb") as f:
            f.write(zip1.read())

        zip2_path = "temp_v2.zip"
        with open(zip2_path, "wb") as f:
            f.write(zip2.read())

        dir1 = "extracted_v1"
        dir2 = "extracted_v2"

        extract_zip(zip1_path, dir1)
        extract_zip(zip2_path, dir2)

        df_v1 = process_course_structure(dir1)
        df_v2 = process_course_structure(dir2)

        if not df_v1.empty and not df_v2.empty:
            set_v1 = set(df_v1["Clave comparación"])
            set_v2 = set(df_v2["Clave comparación"])

            nuevos = set_v2 - set_v1
            eliminados = set_v1 - set_v2
            iguales = set_v1 & set_v2

            df_nuevos = df_v2[df_v2["Clave comparación"].isin(nuevos)]
            df_eliminados = df_v1[df_v1["Clave comparación"].isin(eliminados)]
            df_iguales = df_v2[df_v2["Clave comparación"].isin(iguales)]

            st.subheader("Archivos nuevos en el respaldo actualizado")
            st.dataframe(df_nuevos)

            st.subheader("Archivos eliminados")
            st.dataframe(df_eliminados)

            st.subheader("Archivos que se mantienen")
            st.dataframe(df_iguales)

            output_file = "reporte_comparacion.xlsx"
            with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
                df_nuevos.to_excel(writer, sheet_name="Nuevos", index=False)
                df_eliminados.to_excel(writer, sheet_name="Eliminados", index=False)
                df_iguales.to_excel(writer, sheet_name="Iguales", index=False)

            with open(output_file, "rb") as f:
                st.download_button("Descargar reporte completo (Excel)", f, file_name="reporte_comparacion.xlsx")
        else:
            st.warning("⚠️ No se encontraron identifiers en uno o ambos respaldos. Revisa log_proceso.txt.")

        shutil.rmtree(dir1)
        shutil.rmtree(dir2)
        os.remove(zip1_path)
        os.remove(zip2_path)

    st.success("¡Comparación completada!")

    with open(log_file, "r", encoding="utf-8") as f:
        log_content = f.read()
    st.download_button("Descargar log detallado", log_content, file_name="log_proceso.txt")
