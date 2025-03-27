"""
Archivo: app.py
Dashboard de Streamlit que integra la descarga de reseñas, limpieza y análisis de sentimiento.
Utiliza los módulos: reviews_fetcher, text_processing y sentiment_analysis.
"""

import streamlit as st
import pandas as pd
import os
import datetime
from src.reviews_fetcher import get_place_id_from_name, fetch_reviews, fetch_general_place_data
from src.text_processing import clean_text
from src.sentiment_analysis import analyze_sentiment

# Configuración de la página
st.set_page_config(page_title="Reviews Dashboard", layout="wide")
st.title("📊 Dashboard de Reseñas con KPIs y Gráficos")

# --- Entrada de lugares
st.subheader("📍 Ingresa lugares (uno por línea):")
st.write("Si es place_id, escribe 'pid:ChIJ...' ; si es nombre, ingresa el nombre normal.")
places_input = st.text_area("Lugares:", height=100)

if st.button("Procesar"):
    all_reviews = []
    general_data = []
    lines = places_input.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("pid:"):
            place_id = line.replace("pid:", "").strip()
            st.info(f"📥 Descargando reseñas para place_id={place_id}...")
            revs, loc_name = fetch_reviews(place_id)
            general_info = fetch_general_place_data(place_id)
        else:
            st.info(f"🔍 Buscando place_id para '{line}'...")
            p_id, name, addr = get_place_id_from_name(line)
            if p_id:
                revs, loc_name = fetch_reviews(p_id)
                general_info = fetch_general_place_data(p_id)
            else:
                st.warning(f"No se encontró place_id para '{line}'")
                revs = []
                general_info = {}

        if general_info:
            general_data.append(general_info)
        all_reviews.extend(revs)

    # --- Información General
    if general_data:
        os.makedirs("data/general_info", exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        df_info = pd.DataFrame(general_data)

        # Eliminar columnas no deseadas
        columns_to_drop = ["price_level", "business_status", "open_now"]
        df_info = df_info.drop(columns=[col for col in columns_to_drop if col in df_info.columns])

        df_info.to_csv(f"data/general_info/place_info_{timestamp}.csv", index=False)

        st.markdown("## 🏪 Información General de los Lugares")
        colA, colB, colC = st.columns(3)
        colA.metric("Total Opiniones (Global)", int(df_info["user_ratings_total"].sum()))
        colB.metric("Promedio Rating Global", f"{df_info['rating'].mean():.2f}")
        colC.metric("Lugares Procesados", len(df_info))

        st.dataframe(df_info)

    # --- Opiniones recientes
    if not all_reviews:
        st.warning("No se obtuvieron reseñas.")
    else:
        st.markdown("---")
        st.markdown("## 💬 Opiniones Recientes (últimas 5 por lugar)")

        df = pd.DataFrame(all_reviews)
        df["text_clean"] = df["text"].apply(clean_text)
        df["sentiment"] = df["text_clean"].apply(analyze_sentiment)
        df["datetime_utc"] = pd.to_datetime(df["datetime_utc"], errors="coerce")

        st.markdown("### KPIs")
        col1, col2, col3, col4 = st.columns(4)
        total_reviews = len(df)
        distinct_locs = df["place_id"].nunique()
        avg_rating = df["rating"].mean() if "rating" in df.columns else None
        positive_count = (df["sentiment"] == "positive").sum()
        col1.metric("Total Reseñas", f"{total_reviews}")
        col2.metric("Locaciones Únicas", f"{distinct_locs}")
        col3.metric("Rating Promedio", f"{avg_rating:.2f}" if avg_rating else "-")
        col4.metric("% Reseñas Positivas", f"{(positive_count/total_reviews*100):.1f}%" if total_reviews else "-")

        highest_rating = df["rating"].max() if not df["rating"].empty else None
        lowest_rating = df["rating"].min() if not df["rating"].empty else None
        col5, col6 = st.columns(2)
        col5.metric("Rating Máximo", f"{highest_rating}" if highest_rating is not None else "-")
        col6.metric("Rating Mínimo", f"{lowest_rating}" if lowest_rating is not None else "-")

        if df["datetime_utc"].notnull().any():
            st.markdown("### Rating Promedio por Fecha")
            df["date_only"] = df["datetime_utc"].dt.date
            avg_rating_by_date = df.groupby("date_only")["rating"].mean().sort_index()
            st.line_chart(avg_rating_by_date, use_container_width=True)
        else:
            st.info("No se pudo graficar por fecha (datetime_utc nulo).")

        st.markdown("### Distribución de Sentimiento")
        sentiment_counts = df["sentiment"].value_counts()
        st.bar_chart(sentiment_counts, use_container_width=True)

        st.markdown("### Tabla de Reseñas con Sentimiento")
        st.dataframe(df[["location_name", "author_name", "rating", "datetime_utc", "text_clean", "sentiment"]])

        # Guardar archivo con últimas 5 opiniones por lugar
        os.makedirs("data/last5perplace", exist_ok=True)
        timestamp_reviews = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        df.to_csv(f"data/last5perplace/reviews_last5_{timestamp_reviews}.csv", index=False)

        csv_data = df.to_csv(index=False, encoding="utf-8")
        st.download_button(
            label="Descargar CSV",
            data=csv_data,
            file_name="reviews_with_sentiment.csv",
            mime="text/csv"
        )
