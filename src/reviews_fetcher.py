import os
import requests
import time
from datetime import datetime
from dotenv import load_dotenv

# Cargar API Key
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
        resp = requests.get(url, params=params)
        data = resp.json()
        if data.get("status") == "OK" and data.get("candidates"):
            candidate = data["candidates"][0]
            return candidate["place_id"], candidate["name"], candidate["formatted_address"]
    except Exception as e:
        print(f"[ERROR] get_place_id_from_name: {e}")
    return None, None, None


def fetch_reviews(place_id, language=""):
    """
    Descarga reseñas usando la Places Details API para un place_id dado.
    Parámetros:
      place_id (str): ID del lugar en Google
      language (str): Código de idioma ("es", "en", etc.). Si se deja vacío, se usa el predeterminado
    Retorna:
      (list_of_reviews, location_name)
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
        if language:
            params["language"] = language
        if next_page_token:
            params["pagetoken"] = next_page_token

        try:
            resp = requests.get(url, params=params)
            data = resp.json()
        except Exception as e:
            print(f"[ERROR] fetch_reviews: {e}")
            break

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
                dt_utc = datetime.utcfromtimestamp(utime).strftime("%Y-%m-%d %H:%M:%S")
            review_item = {
                "place_id": place_id,
                "location_name": location_name,
                "author_name": r.get("author_name"),
                "rating": r.get("rating"),
                "datetime_utc": dt_utc,
                "text": r.get("text", "")
            }
            all_reviews.append(review_item)

        next_page_token = data.get("next_page_token")
        if not next_page_token:
            break
        time.sleep(2)

    return all_reviews, location_name


def fetch_general_place_data(place_id):
    """
    Extrae información general de un lugar (rating, total reseñas, ubicación, etc.)
    """
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    fields = (
        "name,rating,user_ratings_total,formatted_address,types,"
        "geometry/location,international_phone_number,website,price_level,"
        "business_status,opening_hours"
    )
    params = {
        "key": API_KEY,
        "place_id": place_id,
        "fields": fields
    }

    try:
        resp = requests.get(url, params=params)
        data = resp.json()
        if data.get("status") != "OK":
            return {}
        result = data.get("result", {})
        return {
            "place_id": place_id,
            "name": result.get("name"),
            "rating": result.get("rating"),
            "user_ratings_total": result.get("user_ratings_total"),
            "formatted_address": result.get("formatted_address"),
            "types": ", ".join(result.get("types", [])),
            "lat": result.get("geometry", {}).get("location", {}).get("lat"),
            "lng": result.get("geometry", {}).get("location", {}).get("lng"),
            "phone": result.get("international_phone_number"),
            "website": result.get("website"),
            "price_level": result.get("price_level"),
            "business_status": result.get("business_status"),
            "open_now": result.get("opening_hours", {}).get("open_now")
        }
    except Exception as e:
        print(f"[ERROR] fetch_general_place_data: {e}")
        return {}
