def fetch_general_place_data(place_id):
    """
    Extrae información general de un lugar usando la Places Details API (New).
    Parámetros:
      place_id (str): ID único del lugar.
    Retorna:
      Diccionario con datos generales del lugar.
    """
    if not place_id:
        return {}

    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "key": API_KEY,
        "place_id": place_id,
        "fields": "place_id,name,formatted_address,user_ratings_total,rating,price_level,business_status,opening_hours,types"
    }

    try:
        resp = requests.get(url, params=params)
        data = resp.json()
        if data.get("status") != "OK":
            return {}

        result = data.get("result", {})
        return {
            "place_id": result.get("place_id"),
            "location_name": result.get("name"),
            "formatted_address": result.get("formatted_address"),
            "user_ratings_total": result.get("user_ratings_total"),
            "rating": result.get("rating"),
            "price_level": result.get("price_level"),
            "business_status": result.get("business_status"),
            "open_now": result.get("opening_hours", {}).get("open_now"),
            "types": result.get("types")
        }
    except Exception as e:
        print(f"[ERROR] fetch_general_place_data: {e}")
        return {}
