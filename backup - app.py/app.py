import streamlit as st
import pandas as pd
import requests
import time
import re
from datetime import datetime
from textblob import TextBlob
from dotenv import load_dotenv
import os

# Carga variables de entorno
load_dotenv()
API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

def get_place_id_from_name(business_name):
    """
    Dado un nombre de negocio, busca el place_id usando la Places API (findplacefromtext).
    Retorna (place_id, name, formatted_address) o (None, None, None) si no encuentra resultados.
    """
    url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
    params = {
        "key": API_KEY,
        "input": business_name,
        "inputtype": "textquery",
        "fields": "place_id,name,formatted_address"
    }
    try:
        resp = requests.get(url, params=params)
        data = resp.json()
        if data.get("status") == "OK" and data.get("candidates"):
            c = data["candidates"][0]
            return c["place_id"], c["name"], c["formatted_address"]
    except Exception as e:
        st.error(f"[ERROR] {e}")
    return None, None, None

def fetch_reviews(place_id):
    """
    Obtiene reseñas de la Places Details API para el place_id dado.
    Retorna (lista_de_reseñas, location_name) y cada reseña incluye:
      place_id, location_name, author_name, rating, datetime_utc y text.
    """
    if not place_id:
        return [], ""
    all_reviews = []
    location_name = "Unknown"
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    next_page_token = None

    while True:
        params = {
            "key": API_KEY,
            "place_id": place_id,
            "fields": "name,reviews"
        }
        if next_page_token:
            params["pagetoken"] = next_page_token

        resp = requests.get(url, params=params)
        data = resp.json()
        if data.get("status") != "OK":
            break

        result = data.get("result", {})
        if location_name == "Unknown":
            location_name = result.get("name", "Unknown")

        reviews = result.get("reviews", [])
        for r in reviews:
            utime = r.get("time")
            dt_utc = None
            if utime:
                dt_utc_obj = datetime.utcfromtimestamp(utime)
                dt_utc = dt_utc_obj.strftime("%Y-%m-%d %H:%M:%S")
            item = {
                "place_id": place_id,
                "location_name": location_name,
                "author_name": r.get("author_name"),
                "rating": r.get("rating"),
                "datetime_utc": dt_utc,
                "text": r.get("text", "")
            }
            all_reviews.append(item)

        next_page_token = data.get("next_page_token")
        if not next_page_token:
            break
        st.info("[INFO] Más reseñas encontradas (paginación). Esperamos 2s...")
        time.sleep(2)

    return all_reviews, location_name

def clean_text(text):
    """
    Limpia el texto removiendo saltos de línea, pasando a minúsculas,
    eliminando caracteres fuera del rango permitido y quitando espacios extra.
    """
    if not text:
        return ""
    text = text.replace("\n", " ").replace("\r", " ")
    text = text.lower()
    text = re.sub(r"[^a-z0-9áéíóúüñ¡!¿?.,:;'\"()\s-]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def analyze_sentiment(text):
    """
    Analiza el sentimiento del texto usando TextBlob.
    Retorna 'positive' si polarity > 0.1, 'negative' si polarity < -0.1, de lo contrario 'neutral'.
    """
    if not text:
        return "neutral"
    blob = TextBlob(text)
    pol = blob.sentiment.polarity
    if pol > 0.1:
        return "positive"
    elif pol < -0.1:
        return "negative"
    else:
        return "neutral"

def main():
    st.set_page_config(page_title="Reviews Dashboard", layout="wide")
    st.title("Dashboard de Reseñas con KPIs y Gráficos")

    # Login sencillo
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if not st.session_state["logged_in"]:
        user = st.text_input("Usuario:")
        pwd = st.text_input("Contraseña:", type="password")
        if st.button("Acceder"):
            if user == "admin" and pwd == "1234":
                st.session_state["logged_in"] = True
            else:
                st.warning("Usuario/Contraseña incorrectos.")
        return

    st.subheader("Ingresa lugares (uno por línea):")
    st.write("Si es place_id, comienza la línea con 'pid:'. Si es nombre, escribe el nombre normal.")
    places_input = st.text_area("Lugares:", height=120)

    if st.button("Procesar"):
        all_reviews = []
        lines = places_input.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("pid:"):
                place_id = line.replace("pid:", "").strip()
                st.info(f"Descargando reseñas para place_id={place_id}...")
                revs, loc_name = fetch_reviews(place_id)
            else:
                st.info(f"Buscando place_id para '{line}'...")
                p_id, name, addr = get_place_id_from_name(line)
                if p_id:
                    revs, loc_name = fetch_reviews(p_id)
                else:
                    st.warning(f"No se encontró place_id para '{line}'")
                    revs = []
            all_reviews.extend(revs)

        if not all_reviews:
            st.warning("No se obtuvieron reseñas.")
            return

        df = pd.DataFrame(all_reviews)
        df["text_clean"] = df["text"].apply(clean_text)
        df["sentiment"] = df["text_clean"].apply(analyze_sentiment)
        df["datetime_utc"] = pd.to_datetime(df["datetime_utc"], errors="coerce")

        # KPIs adicionales
        col1, col2, col3, col4 = st.columns(4)
        total_reviews = len(df)
        distinct_locs = df["place_id"].nunique()
        avg_rating = df["rating"].mean() if "rating" in df.columns else None
        positive_count = (df["sentiment"] == "positive").sum()
        negative_count = (df["sentiment"] == "negative").sum()
        neutral_count = (df["sentiment"] == "neutral").sum()
        highest_rating = df["rating"].max() if not df["rating"].empty else None
        lowest_rating = df["rating"].min() if not df["rating"].empty else None

        col1.metric("Total Reseñas", f"{total_reviews}")
        col2.metric("Locaciones Únicas", f"{distinct_locs}")
        col3.metric("Rating Promedio", f"{avg_rating:.2f}" if avg_rating else "-")
        col4.metric("% Reseñas Positivas", f"{(positive_count / total_reviews * 100):.1f}%" if total_reviews else "-")
        
        col5, col6 = st.columns(2)
        col5.metric("Rating Máximo", f"{highest_rating}" if highest_rating is not None else "-")
        col6.metric("Rating Mínimo", f"{lowest_rating}" if lowest_rating is not None else "-")

        # Gráfico: Rating Promedio por Fecha
        if df["datetime_utc"].notnull().any():
            df["date_only"] = df["datetime_utc"].dt.date
            avg_rating_by_date = df.groupby("date_only")["rating"].mean()
            st.write("## Rating Promedio por Fecha")
            st.line_chart(avg_rating_by_date)
        else:
            st.info("No se pudo graficar por fecha (datetime_utc nulo).")

        # Gráfico: Distribución de Sentimiento
        sentiment_counts = df["sentiment"].value_counts()
        st.write("## Distribución de Sentimiento")
        st.bar_chart(sentiment_counts)

        # Tabla final de reseñas
        st.write("## Reseñas con Sentimiento")
        st.dataframe(df[["location_name", "author_name", "rating", "datetime_utc", "text_clean", "sentiment"]])

        # Botón para descargar CSV
        csv_data = df.to_csv(index=False, encoding="utf-8")
        st.download_button(
            label="Descargar CSV",
            data=csv_data,
            file_name="reviews_with_sentiment.csv",
            mime="text/csv"
        )

if __name__ == "__main__":
    main()

