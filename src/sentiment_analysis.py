import os
import csv
from textblob import TextBlob

def analyze_sentiment(text):
    """
    Utiliza TextBlob para analizar la polaridad.
    Retorna una etiqueta ('positive', 'neutral', 'negative') según umbrales:
      - polarity >  0.1 => positive
      - polarity < -0.1 => negative
      - caso contrario => neutral
    """
    if not text:
        return "neutral"  # Sin texto
    
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    
    if polarity > 0.1:
        return "positive"
    elif polarity < -0.1:
        return "negative"
    else:
        return "neutral"

def process_sentiment(input_csv, output_csv):
    """
    Lee 'input_csv' (reviews_clean.csv) y añade columna 'sentiment' (positivo/negativo/neutro).
    Genera 'output_csv' (ej. reviews_with_sentiment.csv).
    """
    if not os.path.isfile(input_csv):
        print(f"[ERROR] No se encontró el archivo {input_csv}.")
        return

    with open(input_csv, mode="r", encoding="utf-8") as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames + ["sentiment"]

        with open(output_csv, mode="w", encoding="utf-8", newline="") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()

            for row in reader:
                text = row.get("text", "")
                row["sentiment"] = analyze_sentiment(text)
                writer.writerow(row)

    print(f"[INFO] Análisis de sentimiento completado. Resultado en: {output_csv}")

def main():
    input_file = "reviews_clean.csv"
    output_file = "reviews_with_sentiment.csv"

    print("[INFO] Iniciando análisis de sentimiento (TextBlob)...")
    process_sentiment(input_file, output_file)
    print("[INFO] Finalizado.")

if __name__ == "__main__":
    main()
