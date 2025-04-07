# --------------------------------------------------------------------------------
# app.py
# Este archivo implementa la funcionalidad principal de la aplicación Streamlit
# para obtener, procesar y visualizar reseñas de lugares en Google Maps.
# --------------------------------------------------------------------------------

import streamlit as st
import pandas as pd
import os
import datetime
from src.reviews_fetcher import get_place_id_from_name, fetch_reviews, fetch_general_place_data
from src.text_processing import clean_text
from src.sentiment_analysis import analyze_sentiment
import pydeck as pdk

# JuancaM - Se agregan las librerías necesarias para generar la WordCloud y personalizarla.
from wordcloud import WordCloud, STOPWORDS
import matplotlib.pyplot as plt

# Configuración inicial de la página de Streamlit: título y layout
st.set_page_config(page_title="Análisis de Opiniones", layout="wide")

# --------------------------------------------------------------------------------
# JuancaM - Función para generar una WordCloud más limpia y ordenada.
# Se reciben las reseñas limpias en df["text_clean"].
# --------------------------------------------------------------------------------
def generar_wordcloud(df):
    """
    JuancaM - Genera y muestra una nube de palabras (WordCloud) usando los textos limpios
              presentes en la columna 'text_clean' del DataFrame.
    """
    # Unimos todo el texto limpio de las reseñas.
    text_data = " ".join(df["text_clean"].dropna().tolist())

    # Validamos que exista texto, de lo contrario no se genera la nube.
    if not text_data.strip():
        st.warning("No hay texto suficiente para generar la nube de palabras.")
        return

    # JuancaM - Definimos algunas 'stopwords' adicionales para eliminar términos irrelevantes.
    custom_stopwords = STOPWORDS.union({"https", "http", "www", "com", "google", "maps"})

    # JuancaM - Configuración del WordCloud para hacerlo más ordenado:
    #           - collocations=False evita que se unan palabras por bigramas
    #           - prefer_horizontal=1.0 hace que todas las palabras aparezcan en horizontal
    #           - colormap="Blues" define la paleta de colores
    #           - max_words=200 limita la cantidad de palabras
    wordcloud = WordCloud(
        width=800,
        height=400,
        background_color="white",
        stopwords=custom_stopwords,
        collocations=False,
        max_words=200,
        prefer_horizontal=1.0,
        colormap="Blues",
        contour_width=1,
        contour_color="gray",
        min_font_size=10,
        max_font_size=150,
        random_state=42
    ).generate(text_data)

    # JuancaM - Renderizamos la nube con matplotlib y la mostramos en Streamlit.
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wordcloud, interpolation="bilinear")
    ax.axis("off")
    st.pyplot(fig)

# --------------------------------------------------------------------------------
# Encabezado principal (HTML) para darle estilo al título y subtítulo
# --------------------------------------------------------------------------------
st.markdown("""
    <div style='text-align: center;'>
        <h1 style='font-size: 42px;'>🔎 Análisis Inteligente de Opiniones en Google Maps</h1>
        <p style='font-size: 18px; color: gray;'>Descubre lo que opinan tus clientes. Ingresa lugares y obtén insights valiosos al instante.</p>
    </div>
""", unsafe_allow_html=True)

# Sección de entrada de datos: lugares a analizar
st.markdown("### 🧭 Escribe los lugares que quieres analizar (uno por línea):")
col_left, col_right = st.columns([3, 1])
with col_left:
    # Input de lugares: los usuarios pueden poner un nombre de lugar o pid:ID
    st.markdown("<small style='color: gray;'>Ejemplo: Starbucks CDMX o pid:ChIJN1t_tDeuEmsRUsoyG83frY4</small>", unsafe_allow_html=True)
    places_input = st.text_area(" ", height=120, key="places_input")
with col_right:
    # Desplegable para seleccionar el idioma de las reseñas
    idioma = st.selectbox("Idioma de reseñas:", options=["Predeterminado", "Español", "Inglés"], index=0)

# Se mapea la elección de idioma a los códigos que la API puede utilizar
idioma_map = {"Predeterminado": "", "Español": "es", "Inglés": "en"}

# Margen visual
st.markdown("<br>", unsafe_allow_html=True)

# Botón para procesar la información de los lugares
btn_col = st.columns([5, 2, 5])[1]
with btn_col:
    procesar = st.button("🚀 Analizar Opiniones", use_container_width=True)

# --------------------------------------------------------------------------------
# Al hacer clic en "Analizar Opiniones", se desencadena el siguiente bloque:
# 1. Se leen las líneas ingresadas, determinando si se trata de un place_id o un nombre.
# 2. Se llama a las funciones para obtener información y reseñas del lugar.
# 3. Se almacenan los resultados en el estado de la sesión y se guardan en CSV.
# --------------------------------------------------------------------------------
if procesar:
    all_reviews = []   # Almacena todas las reseñas de todos los lugares
    general_data = []  # Almacena información general de cada lugar
    lines = places_input.split("\n")  # Separa la entrada por líneas

    for line in lines:
        line = line.strip()
        if not line:
            # Si la línea está vacía, se omite
            continue
        
        # Caso 1: el usuario ingresa directamente el place_id con prefijo "pid:"
        if line.startswith("pid:"):
            place_id = line.replace("pid:", "").strip()
            st.info(f"📥 Descargando reseñas para place_id={place_id}..")
            # Se obtienen las reseñas y el nombre del lugar
            revs, loc_name = fetch_reviews(place_id, language=idioma_map[idioma])
            # Se obtiene la información general del lugar
            general_info = fetch_general_place_data(place_id)
        else:
            # Caso 2: el usuario ingresa el nombre de un lugar
            st.info(f"🔍 Recopilando datos para '{line}'...")
            p_id, name, addr = get_place_id_from_name(line)
            if p_id:
                revs, loc_name = fetch_reviews(p_id, language=idioma_map[idioma])
                general_info = fetch_general_place_data(p_id)
            else:
                # Si no se encuentra un place_id para ese nombre, emitimos una alerta
                st.warning(f"No se encontró place_id para '{line}'")
                revs = []
                general_info = {}

        # Si se obtuvo información general del lugar, la almacenamos
        if general_info:
            general_data.append(general_info)
        # Agregamos las reseñas al listado total
        all_reviews.extend(revs)

    # Se guarda la información en el estado de la sesión (session_state)
    st.session_state["df"] = pd.DataFrame(all_reviews)
    st.session_state["df_info"] = pd.DataFrame(general_data)

    # Se generan sellos de tiempo para diferenciar los archivos CSV
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Si existe información de lugares, se guarda en data/general_info
    if not st.session_state["df_info"].empty:
        os.makedirs("data/general_info", exist_ok=True)
        df_info_clean = st.session_state["df_info"].drop(columns=["price_level", "business_status", "open_now"], errors="ignore")
        df_info_clean.to_csv(f"data/general_info/place_info_{timestamp}.csv", index=False)

    # Si existen reseñas, se guardan en data/last5perplace
    if not st.session_state["df"].empty:
        os.makedirs("data/last5perplace", exist_ok=True)
        st.session_state["df"].to_csv(f"data/last5perplace/reviews_last5_{timestamp}.csv", index=False)

# --------------------------------------------------------------------------------
# Sección: Ranking e Información General
# 1. Verificamos si hay información de los lugares (df_info).
# 2. Se limpia y se combina con estadísticas de reseñas (sentimiento, rating).
# 3. Se visualiza un ranking general y se muestra un mapa interactivo si hay coords.
# --------------------------------------------------------------------------------
if "df_info" in st.session_state and not st.session_state["df_info"].empty:
    st.markdown("## 🏪 Ranking e Información de los Lugares")

    # Eliminamos columnas que no se usarán para simplificar la vista
    df_info = st.session_state["df_info"].drop(columns=["price_level", "business_status", "open_now"], errors="ignore")

    # Para poder agrupar reseñas por lugar, necesitamos acceder a df de reseñas
    df = st.session_state["df"]
    df["text_clean"] = df["text"].apply(clean_text)         # Limpieza de texto
    df["sentiment"] = df["text_clean"].apply(analyze_sentiment)  # Análisis de sentimiento
    df["datetime_utc"] = pd.to_datetime(df["datetime_utc"], errors="coerce")  # Conversión a fecha

    # Agrupación por nombre de lugar para obtener estadísticas
    resumen_sentimiento = df.groupby("location_name").agg(
        avg_rating=("rating", "mean"),
        pct_positivo=("sentiment", lambda x: (x == "positive").mean() * 100),
        last_review_date=("datetime_utc", "max")
    ).reset_index()

    # Se unifica df_info con los datos de sentimiento / último review
    df_info = df_info.rename(columns={"name": "location_name"})
    df_info["last_review_date"] = df_info["location_name"].map(
        resumen_sentimiento.set_index("location_name")["last_review_date"]
    )

    # Se crea la columna de URL para Google Maps con base en el place_id
    df_info["maps_url"] = "https://www.google.com/maps/place/?q=place_id=" + df_info["place_id"]

    # Métricas principales a nivel global
    colA, colB, colC = st.columns(3)
    colA.metric("Total Opiniones (Global)", int(df_info["user_ratings_total"].sum()))
    colB.metric("Promedio Rating Global", f"{df_info['rating'].mean():.2f}")
    colC.metric("Lugares Procesados", len(df_info))

    # Creamos un dataframe para el ranking
    df_ranking = df_info[["location_name", "user_ratings_total", "rating", "formatted_address", "last_review_date", "maps_url"]].copy()
    df_ranking = df_ranking.rename(columns={
        "location_name": "📍 Lugar",
        "user_ratings_total": "💬 Opiniones Totales",
        "rating": "⭐ Promedio Rating",
        "formatted_address": "📌 Dirección",
        "last_review_date": "🕓 Última Opinión",
        "maps_url": "🔗 Ver en Google Maps"
    }).sort_values("⭐ Promedio Rating", ascending=False).reset_index(drop=True)

    # Visualización del ranking en una tabla estilizada
    st.dataframe(df_ranking.style.format({
        "⭐ Promedio Rating": "{:.2f}",
        "💬 Opiniones Totales": "{:.0f}",
        "🕓 Última Opinión": lambda x: x.strftime("%Y-%m-%d") if pd.notnull(x) else "-"
    }))

    # Botón para descargar el CSV con info + ranking
    csv_info = df_ranking.to_csv(index=False, encoding="utf-8")
    st.download_button("📥 Descargar CSV (Info + Ranking)", csv_info, "ranking_info.csv", "text/csv", key="download_combined")

    # --------------------------------------------------------------------------------
    # Sección de mapa interactivo
    # Si se cuenta con columnas lat y lng, se genera un mapa con pydeck.
    # --------------------------------------------------------------------------------
    if "lat" in df_info.columns and "lng" in df_info.columns:
        st.markdown("### 🗺️ Mapa Interactivo de Ubicaciones")
        df_map = df_info.rename(columns={"lat": "latitude", "lng": "longitude"})
        # Se genera una etiqueta combinando nombre y rating
        df_map["label"] = df_map.apply(lambda row: f"{row['location_name']} ⭐{row['rating']:.1f}", axis=1)

        # Capa de dispersión para las ubicaciones
        scatter_layer = pdk.Layer(
            "ScatterplotLayer",
            data=df_map,
            get_position='[longitude, latitude]',
            get_fill_color='[255, 105, 180, 160]',
            get_radius=300,
            pickable=True
        )
        # Capa de texto para mostrar el nombre + rating
        text_layer = pdk.Layer(
            "TextLayer",
            data=df_map,
            get_position='[longitude, latitude]',
            get_text="label",
            get_size=16,
            get_color=[0, 0, 0],
            get_angle=0,
            get_text_anchor="'middle'",
            get_alignment_baseline="'bottom'"
        )
        # Vista inicial del mapa (centrada en la media de lat/long de los lugares)
        view_state = pdk.ViewState(
            latitude=df_map["latitude"].mean(),
            longitude=df_map["longitude"].mean(),
            zoom=11,
            pitch=30
        )
        # Se muestra el mapa con ambas capas
        st.pydeck_chart(pdk.Deck(
            map_style='mapbox://styles/mapbox/light-v9',
            initial_view_state=view_state,
            layers=[scatter_layer, text_layer]
        ))

# --------------------------------------------------------------------------------
# Sección: Opiniones Recientes
# 1. Se visualizan las últimas reseñas junto con sentimiento.
# 2. Se presentan KPIs y un histograma de la distribución de sentimientos.
# 3. Se muestra un WordCloud "limpio" y "ordenado" con las palabras más frecuentes.
# --------------------------------------------------------------------------------
if "df" in st.session_state and not st.session_state["df"].empty:
    st.markdown("---")
    st.markdown("## 💬 Opiniones Recientes (últimas 5 por lugar)")

    df = st.session_state["df"]
    df["text_clean"] = df["text"].apply(clean_text)          # Limpieza de texto
    df["sentiment"] = df["text_clean"].apply(analyze_sentiment)  # Análisis de sentimiento
    df["datetime_utc"] = pd.to_datetime(df["datetime_utc"], errors="coerce")  # Conversión a fecha

    # KPIs principales de la sección
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

    # Conteo de sentimientos para graficar
    sentiment_counts = df["sentiment"].value_counts()

    # JuancaM - Creamos dos columnas: la primera para la gráfica de distribución de sentimientos
    #           y la segunda para el WordCloud con la función generar_wordcloud.
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.markdown("### 📊 Distribución de Sentimiento")
        st.bar_chart(sentiment_counts, use_container_width=True)

    with col_chart2:
        st.markdown("### 🌐 WordCloud de Palabras Más Frecuentes")
        # JuancaM - Llamamos a la función para generar la nube de palabras.
        generar_wordcloud(df)

    # Tabla de reseñas con sentimiento
    st.markdown("### 🗂️ Tabla de Reseñas con Sentimiento")

    def style_sentiment(val):
        # Esta función aplica color en base al tipo de sentimiento
        if val == "positive":
            return "color: green;"
        elif val == "negative":
            return "color: red;"
        else:
            return "color: gray;"

    # Mostramos algunas columnas relevantes en la tabla
    st.dataframe(df[["location_name", "author_name", "rating", "datetime_utc", "text_clean", "sentiment"]].style.format({
        "rating": "{:.1f}",
        "datetime_utc": lambda x: x.strftime("%Y-%m-%d %H:%M") if pd.notnull(x) else "-"
    }).map(style_sentiment, subset=["sentiment"]))

    # Botón de descarga con CSV de todas las reseñas (limpias y con sentimiento)
    csv_data = df.to_csv(index=False, encoding="utf-8")
    st.download_button("📥 Descargar CSV (Opiniones)", csv_data, "reviews_with_sentiment.csv", "text/csv", key="download_reviews")

# --------------------------------------------------------------------------------
# JuancaM - Sugerencia de commit (trabajo colaborativo en GitHub):
# --------------------------------------------------------------------------------
# "feat: integrar un WordCloud limpio y ordenado junto a la gráfica de sentimiento"
#
# - Se agregaron comentarios con prefijo "JuancaM -" para identificar modificaciones.
# - Se implementó la función generar_wordcloud() para crear nubes de palabras más estéticas.
# - Se agregaron parámetros como collocations=False y prefer_horizontal=1.0.
# - Se muestra la WordCloud en la segunda columna, junto a la gráfica de distribución de sentimientos.
# --------------------------------------------------------------------------------
