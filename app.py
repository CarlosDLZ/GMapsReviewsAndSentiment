"""
Archivo: app.py
Dashboard de Streamlit que integra la descarga de reseñas, limpieza y análisis de sentimiento.
Utiliza los módulos: reviews_fetcher, text_processing y sentiment_analysis.
"""

import streamlit as st
import pandas as pd
import os
from src.reviews_fetcher import get_place_id_from_name, fetch_reviews
from src.text_processing import clean_text
from src.sentiment_analysis import analyze_sentiment

# Configuración de la página
st.set_page_config(page_title="Reviews Dashboard", layout="wide")
st.title("Dashboard de Reseñas con KPIs y Gráficos")

# Login simple para acceso
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
    st.stop()

st.subheader("Ingresa lugares (uno por línea):")
st.write("Si es place_id, escribe 'pid:ChIJ...' ; si es nombre, ingresa el nombre normal.")
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
    else:
        df = pd.DataFrame(all_reviews)
        df["text_clean"] = df["text"].apply(clean_text)
        df["sentiment"] = df["text_clean"].apply(analyze_sentiment)
        df["datetime_utc"] = pd.to_datetime(df["datetime_utc"], errors="coerce")

        # KPIs
        col1, col2, col3, col4 = st.columns(4)
        total_reviews = len(df)
        distinct_locs = df["place_id"].nunique()
        avg_rating = df["rating"].mean() if "rating" in df.columns else None
        positive_count = (df["sentiment"] == "positive").sum()
        col1.metric("Total Reseñas", f"{total_reviews}")
        col2.metric("Locaciones Únicas", f"{distinct_locs}")
        col3.metric("Rating Promedio", f"{avg_rating:.2f}" if avg_rating else "-")
        col4.metric("% Reseñas Positivas", f"{(positive_count/total_reviews*100):.1f}%" if total_reviews else "-")
        
        # KPIs adicionales
        highest_rating = df["rating"].max() if not df["rating"].empty else None
        lowest_rating = df["rating"].min() if not df["rating"].empty else None
        col5, col6 = st.columns(2)
        col5.metric("Rating Máximo", f"{highest_rating}" if highest_rating is not None else "-")
        col6.metric("Rating Mínimo", f"{lowest_rating}" if lowest_rating is not None else "-")
        
        # Gráfico: Rating Promedio por Fecha (Fecha en eje X, Rating en eje Y)
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
        
        # Tabla Final
        st.write("## Tabla de Reseñas con Sentimiento")
        st.dataframe(df[["location_name", "author_name", "rating", "datetime_utc", "text_clean", "sentiment"]])
        
        # Botón para descargar CSV
        csv_data = df.to_csv(index=False, encoding="utf-8")
        st.download_button(
            label="Descargar CSV",
            data=csv_data,
            file_name="reviews_with_sentiment.csv",
            mime="text/csv"
        )
