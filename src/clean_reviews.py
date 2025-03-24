import csv
import os
import re
from datetime import datetime

################################################################################
# Fix para doble codificación (latin-1 interpretado como utf-8).
################################################################################
def fix_double_encoded_text(s):
    """
    Intenta reparar textos con símbolos extraños (ej. 'â€œ', 'Ã±') 
    generados por doble-encoding. 
    - Convierte a bytes interpretando 'latin-1'.
    - Luego decodifica como 'utf-8'.
    - Si no se puede, devuelve el original sin cambios.
    """
    if not s:
        return ""
    try:
        # 'errors="replace"' evita excepción en caracteres imposibles.
        return s.encode("latin-1", errors="replace").decode("utf-8", errors="replace")
    except:
        return s

################################################################################
# Limpieza de texto (remover saltos, símbolos especiales, etc.)
################################################################################
def clean_text(text):
    """
    Aplica:
      1) Reemplazo de saltos de línea.
      2) Pasar a minúsculas.
      3) Eliminar caracteres fuera de [a-z0-9áéíóúüñ..., etc.].
      4) Quitar espacios sobrantes.
    """
    if not text:
        return ""

    # Primero, intentamos corregir posible doble encoding.
    text = fix_double_encoded_text(text)

    # Reemplazar saltos de línea
    text = text.replace("\n", " ").replace("\r", " ")

    # Convertir a minúsculas
    text = text.lower()

    # Eliminar caracteres especiales (ajusta a tus necesidades)
    text = re.sub(r"[^a-z0-9áéíóúüñ¡!¿?.,:;'\"()\s-]", "", text)

    # Quitar exceso de espacios
    text = re.sub(r"\s+", " ", text).strip()

    return text

################################################################################
# Proceso principal de limpieza
################################################################################
def clean_reviews(input_csv, output_csv):
    """
    Lee 'input_csv', repara posible doble encoding y aplica 'clean_text'
    a los campos 'text' y 'author_name', luego genera 'output_csv'.

    Campos esperados:
      place_id, location_name, author_name, rating, datetime_utc, text
    """
    if not os.path.isfile(input_csv):
        print(f"[ERROR] No se encontró el archivo {input_csv}.")
        return

    with open(input_csv, mode="r", encoding="utf-8") as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames

        # Verificamos que existan estas columnas
        required_cols = ["author_name", "text"]
        for col in required_cols:
            if col not in fieldnames:
                print(f"[ERROR] El CSV no contiene la columna '{col}'.")
                return

        with open(output_csv, mode="w", encoding="utf-8", newline="") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()

            for row in reader:
                # Reparar / limpiar 'author_name'
                row["author_name"] = fix_double_encoded_text(row["author_name"])
                # Reparar / limpiar 'text'
                row["text"] = clean_text(row["text"])

                writer.writerow(row)

    print(f"[INFO] Limpieza completa. Resultado en: {output_csv}")

################################################################################
# main: Punto de entrada
################################################################################
def main():
    input_file = "reviews_combined.csv"
    output_file = "reviews_clean.csv"
    print("[INFO] Iniciando limpieza de reseñas...")
    clean_reviews(input_file, output_file)
    print("[INFO] Proceso finalizado.")

if __name__ == "__main__":
    main()
