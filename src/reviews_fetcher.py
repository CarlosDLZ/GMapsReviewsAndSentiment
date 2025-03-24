"""
Módulo: reviews_fetcher.py
Funciones para interactuar con la Google Places API:
 - get_place_id_from_name: Busca el place_id a partir del nombre de un negocio.
 - fetch_reviews: Descarga reseñas para un place_id dado (limitado a 5 reseñas, las más recientes).
"""

import os
import requests
import time
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()
API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

def get_place_id_from_name(business_name):
    """
    Busca el place_id de un negocio usando la Places API (findplacefromtext).
    Parámetros:
      business_name (str): Nombre del negocio a buscar.
    Retorna:
      (place_id, name, formatted_address) o (None, None, None) si no se encuentra.
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
            candidate = data["candidates"][0]
            return candidate["place_id"], candidate["name"], candidate["formatted_address"]
    except Exception as e:
        print(f"[ERROR] get_place_id_from_name: {e}")
    return None, None, None

def fetch_reviews(place_id):
    """
    Descarga reseñas usando la Places Details API para un place_id dado.
    Parámetros:
      place_id (str): Identificador del negocio en Google.
    Retorna:
      (list_of_reviews, location_name)
      Cada review es un diccionario con:
        - place_id
        - location_name
        - author_name
        - rating
        - datetime_utc (formato "YYYY-MM-DD HH:MM:SS")
        - text
    Nota:
      La API puede devolver más de 5 reseñas si hay paginación.
      Esta función ordena las reseñas por fecha (las más recientes primero) y retorna solo las 5 más recientes.
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
        # Espera recomendada por la API antes de usar el token de paginación
        time.sleep(2)
    
    # Ordenar las reseñas por datetime_utc (las más recientes primero)
    try:
        sorted_reviews = sorted(
            all_reviews, 
            key=lambda x: datetime.strptime(x["datetime_utc"], "%Y-%m-%d %H:%M:%S") if x["datetime_utc"] else datetime.min,
            reverse=True
        )
    except Exception as e:
        print(f"[ERROR] Ordenando reseñas: {e}")
        sorted_reviews = all_reviews

    # Retornar solo las 5 reseñas más recientes
    top_reviews = sorted_reviews[:5]
    return top_reviews, location_name
