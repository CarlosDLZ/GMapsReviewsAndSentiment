import streamlit as st
import pandas as pd
import os
import datetime
from src.reviews_fetcher import get_place_id_from_name, fetch_reviews, fetch_general_place_data
from src.text_processing import clean_text
from src.sentiment_analysis import analyze_sentiment

# Configuración de la página
st.set_page_config(page_title="Análisis de Opiniones", layout="wide")

# Título principal
st.markdown("""
    <div style='text-align: center;'>
        <h1 style='font-size: 42px;'>🔎 Análisis Inteligente de Opiniones en Google Maps</h1>
        <p style='font-size: 18px; color: gray;'>Descubre lo que opinan tus clientes. Ingresa lugares y obtén insights valiosos al instante.</p>
    </div>
""", unsafe_allow_html=True)

# Input y selector de idioma
st.markdown("### 🧭 Escribe los lugares que quieres analizar (uno por línea):")
col_left, col_right = st.columns([3, 1])
with col_left:
    st.markdown("<small style='color: gray;'>Ejemplo: Starbucks CDMX o pid:ChIJN1t_tDeuEmsRUsoyG83frY4</small>", unsafe_allow_html=True)
    places_input = st.text_area(" ", height=120, key="places_input")

with col_right:
    idioma = st.selectbox("Idioma de reseñas:", options=["Predeterminado", "Español", "Inglés"], index=0)

idioma_map = {"Predeterminado": "", "Español": "es", "Inglés": "en"}

# Botón de análisis
st.markdown("<br>", unsafe_allow_html=True)
btn_col = st.columns([5, 2, 5])[1]
with btn_col:
    procesar = st.button("🚀 Analizar Opiniones", use_container_width=True)

# Procesamiento
if procesar:
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
            revs, loc_name = fetch_reviews(place_id, language=idioma_map[idioma])
            general_info = fetch_general_place_data(place_id)
        else:
            st.info(f"🔍 Buscando place_id para '{line}'...")
            p_id, name, addr = get_place_id_from_name(line)
            if p_id:
                revs, loc_name = fetch_reviews(p_id, language=idioma_map[idioma])
                general_info = fetch_general_place_data(p_id)
            else:
                st.warning(f"No se encontró place_id para '{line}'")
                revs = []
                general_info = {}

        if general_info:
            general_data.append(general_info)
        all_reviews.extend(revs)

    # Guardar en session_state
    st.session_state["df"] = pd.DataFrame(all_reviews)
    st.session_state["df_info"] = pd.DataFrame(general_data)

    # Guardar CSVs
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    if not st.session_state["df_info"].empty:
        os.makedirs("data/general_info", exist_ok=True)
        df_info_clean = st.session_state["df_info"].drop(columns=["price_level", "business_status", "open_now"], errors="ignore")
        df_info_clean.to_csv(f"data/general_info/place_info_{timestamp}.csv", index=False)

    if not st.session_state["df"].empty:
        os.makedirs("data/last5perplace", exist_ok=True)
        st.session_state["df"].to_csv(f"data/last5perplace/reviews_last5_{timestamp}.csv", index=False)

# Información general
if "df_info" in st.session_state and not st.session_state["df_info"].empty:
    st.markdown("## 🏪 Información General de los Lugares")
    df_info = st.session_state["df_info"].drop(columns=["price_level", "business_status", "open_now"], errors="ignore")
    
    colA, colB, colC = st.columns(3)
    colA.metric("Total Opiniones (Global)", int(df_info["user_ratings_total"].sum()))
    colB.metric("Promedio Rating Global", f"{df_info['rating'].mean():.2f}")
    colC.metric("Lugares Procesados", len(df_info))

    st.dataframe(df_info)

    # Botón para descargar CSV
    csv_info = df_info.to_csv(index=False, encoding="utf-8")
    st.download_button(
        label="📥 Descargar CSV (Info General)",
        data=csv_info,
        file_name="place_info.csv",
        mime="text/csv",
        key="download_info"
    )

    # Mapa con etiquetas y bolas grandes
    if "lat" in df_info.columns and "lng" in df_info.columns and "df" in st.session_state:
        st.markdown("### 🗺️ Mapa Interactivo de Ubicaciones")

        df = st.session_state["df"]
        df["text_clean"] = df["text"].apply(clean_text)
        df["sentiment"] = df["text_clean"].apply(analyze_sentiment)

        resumen_sentimiento = df.groupby("location_name").agg(
            avg_rating=("rating", "mean"),
            pct_positivo=("sentiment", lambda x: (x == "positive").mean() * 100)
        ).reset_index()

        df_info = df_info.rename(columns={"name": "location_name"})
        df_mapa = pd.merge(df_info, resumen_sentimiento, on="location_name", how="left")
        df_mapa = df_mapa.rename(columns={"lat": "latitude", "lng": "longitude"})

        import pydeck as pdk

        scatter_layer = pdk.Layer(
            "ScatterplotLayer",
            data=df_mapa,
            get_position='[longitude, latitude]',
            get_fill_color='[255, 105, 180, 160]',
            get_radius=300,
            pickable=True
        )

        df_mapa["label"] = df_mapa.apply(
            lambda row: f"{row['location_name']} ⭐{row['avg_rating']:.1f} ({row['pct_positivo']:.0f}%)", axis=1
        )

        text_layer = pdk.Layer(
            "TextLayer",
            data=df_mapa,
            get_position='[longitude, latitude]',
            get_text="label",
            get_size=16,
            get_color=[0, 0, 0],
            get_angle=0,
            get_text_anchor="'middle'",
            get_alignment_baseline="'bottom'"
        )

        view_state = pdk.ViewState(
            latitude=df_mapa["latitude"].mean(),
            longitude=df_mapa["longitude"].mean(),
            zoom=11,
            pitch=30
        )

        st.pydeck_chart(pdk.Deck(
            map_style='mapbox://styles/mapbox/light-v9',
            initial_view_state=view_state,
            layers=[scatter_layer, text_layer]
        ))

# Opiniones recientes
if "df" in st.session_state and not st.session_state["df"].empty:
    st.markdown("---")
    st.markdown("## 💬 Opiniones Recientes (últimas 5 por lugar)")

    df = st.session_state["df"]
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
        df["date_only"] = df["datetime_utc"].dt.date
        avg_rating_by_date = df.groupby("date_only")["rating"].mean().sort_index()
        sentiment_counts = df["sentiment"].value_counts()

        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            st.markdown("### 📈 Rating Promedio por Fecha")
            st.line_chart(avg_rating_by_date, use_container_width=True)

        with col_chart2:
            st.markdown("### 📊 Distribución de Sentimiento")
            st.bar_chart(sentiment_counts, use_container_width=True)
    else:
        st.info("No se pudo graficar por fecha (datetime_utc nulo).")

    st.markdown("### 🗂️ Tabla de Reseñas con Sentimiento")
    st.dataframe(df[["location_name", "author_name", "rating", "datetime_utc", "text_clean", "sentiment"]])

    csv_data = df.to_csv(index=False, encoding="utf-8")
    st.download_button(
        label="📥 Descargar CSV (Opiniones)",
        data=csv_data,
        file_name="reviews_with_sentiment.csv",
        mime="text/csv",
        key="download_reviews"
    )
