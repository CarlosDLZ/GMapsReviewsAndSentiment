import streamlit as st
import pandas as pd
import requests
import time
import re
from datetime import datetime
from textblob import TextBlob
from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

def get_place_id_from_name(business_name):
    url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
    params = {
        "key": API_KEY,
        "input": business_name,
        "inputtype": "textquery",
        "fields": "place_id,name,formatted_address"
    }
    try:
        r = requests.get(url, params=params)
        data = r.json()
        if data.get("status") == "OK" and data.get("candidates"):
            c = data["candidates"][0]
            return c["place_id"], c["name"], c["formatted_address"]
    except:
        pass
    return None, None, None

def fetch_reviews(place_id):
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
        time.sleep(2)

    return all_reviews, location_name

def clean_text(text):
    if not text:
        return ""
    text = text.replace("\n", " ").replace("\r", " ")
    text = text.lower()
    text = re.sub(r"[^a-z0-9áéíóúüñ¡!¿?.,:;'\"()\s-]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def analyze_sentiment(text):
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
    st.title("Mini Dashboard de Reseñas (Demo)")

    # Sencillo login de ejemplo
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

    st.subheader("Ingresa lugares por nombre o place_id:")
    st.write("Al final, haz clic en 'Procesar' para descargar reseñas, limpiarlas y analizar sentimiento.")

    places_list = st.text_area(
        "Pon cada lugar en una línea. Si es place_id, escribe 'pid:ChIJ...' o si es un nombre normal, solo pon 'Starbucks Polanco'.",
        height=150
    )

    if st.button("Procesar"):
        all_reviews = []
        lines = places_list.split("\n")
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

        st.success(f"Total reseñas brutas: {len(all_reviews)}")

        if all_reviews:
            import pandas as pd
            df = pd.DataFrame(all_reviews)
            df["text_clean"] = df["text"].apply(clean_text)
            df["sentiment"] = df["text_clean"].apply(analyze_sentiment)

            sentiment_counts = df["sentiment"].value_counts()
            st.write("## Distribución de Sentimiento:")
            st.bar_chart(sentiment_counts)

            if "rating" in df.columns and pd.api.types.is_numeric_dtype(df["rating"]):
                rating_mean = df["rating"].mean()
                st.write(f"**Rating promedio:** {rating_mean:.2f}")

            st.write("## Reseñas con Sentimiento:")
            st.dataframe(df[["location_name","author_name","rating","datetime_utc","text_clean","sentiment"]])

            csv_data = df.to_csv(index=False, encoding="utf-8")
            st.download_button(
                label="Descargar CSV",
                data=csv_data,
                file_name="reviews_with_sentiment.csv",
                mime="text/csv"
            )

if __name__ == "__main__":
    main()
