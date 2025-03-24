import os
import requests
import csv
import time
from dotenv import load_dotenv
from datetime import datetime

################################################################################
# 1) Carga de variables de entorno
################################################################################
load_dotenv()
API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

################################################################################
# 2) Buscar place_id a partir de nombre (Opcional)
################################################################################
def get_place_id_from_name(business_name):
    """
    Dado un nombre de negocio, busca el place_id usando la Places API (findplacefromtext).
    Retorna (place_id, name, address) o (None, None, None) si no encuentra nada.
    """
    print(f"[INFO] Buscando place_id para: {business_name}")

    url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
    params = {
        "key": API_KEY,
        "input": business_name,
        "inputtype": "textquery",
        "fields": "place_id,formatted_address,name"
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()
    except Exception as e:
        print(f"[ERROR] Conexión fallida con la API. Error: {e}")
        return None, None, None

    status = data.get("status")
    if status == "OK" and data.get("candidates"):
        candidate = data["candidates"][0]
        place_id = candidate.get("place_id")
        name = candidate.get("name")
        address = candidate.get("formatted_address")
        print(f"[INFO] place_id={place_id} para '{name}'")
        return place_id, name, address
    else:
        print(f"[WARNING] No se encontró place_id para '{business_name}'. status={status}")
        return None, None, None

################################################################################
# 3) Descarga reseñas dada un place_id (API Place Details)
################################################################################
def fetch_reviews(place_id):
    """
    Retorna (all_reviews_list, location_name).
      - all_reviews_list es una lista de dicts con:
          place_id, location_name, author_name, rating, datetime_utc, text
      - location_name es el nombre oficial del lugar (devuelto por la API).
    Maneja paginación (next_page_token).
    """
    if not place_id:
        print("[ERROR] place_id inválido, no se pueden descargar reseñas.")
        return [], None

    all_reviews = []
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    next_page_token = None

    # Guardaremos el nombre del lugar cuando se obtenga
    location_name = None

    while True:
        # Pedimos 'name' y 'reviews' para conocer el nombre oficial del lugar
        params = {
            "key": API_KEY,
            "place_id": place_id,
            "fields": "name,reviews"
        }
        if next_page_token:
            params["pagetoken"] = next_page_token

        try:
            response = requests.get(url, params=params)
            data = response.json()
        except Exception as e:
            print(f"[ERROR] Error al conectar con la API: {e}")
            break

        status = data.get("status")
        if status != "OK":
            print(f"[WARNING] API status={status}. Terminamos descargas.")
            break

        result = data.get("result", {})
        if location_name is None:
            # Tomamos el 'name' del lugar si está disponible
            location_name = result.get("name", "Unknown")

        reviews = result.get("reviews", [])
        for r in reviews:
            # 'time' (UNIX) está presente, pero no lo guardaremos en el CSV final.
            unix_ts = r.get("time", None)
            dt_utc = None
            if unix_ts:
                dt_utc_obj = datetime.utcfromtimestamp(unix_ts)
                dt_utc = dt_utc_obj.strftime("%Y-%m-%d %H:%M:%S")

            # Creamos un dict con las columnas deseadas
            item = {
                "place_id": place_id,
                "location_name": location_name,
                "author_name": r.get("author_name"),
                "rating": r.get("rating"),
                "datetime_utc": dt_utc,   # fecha/hora legible
                "text": r.get("text")    # reseña
            }
            all_reviews.append(item)

        next_page_token = data.get("next_page_token")
        if not next_page_token:
            # No hay más páginas
            break

        print("[INFO] Más reseñas encontradas (paginación). Esperamos 2s...")
        time.sleep(2)

    return all_reviews, location_name

################################################################################
# 4) Guardar TODAS las reseñas en un solo CSV
################################################################################
def save_all_reviews_to_csv(all_reviews, csv_filename="reviews_combined.csv"):
    """
    Dado que 'all_reviews' es una lista con dicts de distintos lugares,
    se guardan en un único CSV con columnas:
      place_id, location_name, author_name, rating, datetime_utc, text
    """
    if not all_reviews:
        print("[INFO] No se guardaron reseñas (lista vacía).")
        return
    
    fieldnames = [
        "place_id",
        "location_name",
        "author_name",
        "rating",
        "datetime_utc",
        "text"
    ]

    with open(csv_filename, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rev in all_reviews:
            writer.writerow(rev)
    
    print(f"[INFO] Se guardaron {len(all_reviews)} reseñas combinadas en: {csv_filename}")

################################################################################
# 5) main: Menú para ingresar varios lugares (por place_id o nombre)
#    y al final descargar TODAS las reseñas en un SOLO CSV.
################################################################################
def main():
    print("==========================================================")
    print("  Descargador Múltiple - Reseñas Combinadas en un CSV     ")
    print("  (Sin 'time' ni 'relative_time', con fecha legible UTC)  ")
    print("==========================================================\n")

    if not API_KEY:
        print("[ERROR] No se encontró GOOGLE_PLACES_API_KEY en .env")
        return

    print("[INFO] Ingresar varios lugares (place_id o nombre). Escribe 'fin' para terminar.\n")
    lugares = []

    while True:
        print("¿Deseas ingresar un place_id o un nombre de negocio?")
        print("   1) place_id")
        print("   2) nombre")
        print("   3) terminar (fin)")
        opcion = input("Elige (1/2/3): ").strip()

        if opcion == "3":
            print("[INFO] Terminamos de agregar lugares.")
            break
        elif opcion == "1":
            pid = input("Ingresa place_id (o 'fin' para saltar): ").strip()
            if pid.lower() == "fin":
                continue
            if pid:
                lugares.append(('id', pid))
                print(f"[INFO] Se agregó place_id={pid}")
            else:
                print("[WARNING] place_id vacío, no se agrega.")
        elif opcion == "2":
            nombre = input("Ingresa el nombre (o 'fin' para saltar): ").strip()
            if nombre.lower() == "fin":
                continue
            if nombre:
                lugares.append(('name', nombre))
                print(f"[INFO] Se agregó nombre='{nombre}'")
            else:
                print("[WARNING] No ingresaste nada.")
        else:
            print("[ERROR] Opción inválida. Intenta de nuevo.")
    
    if not lugares:
        print("[INFO] No agregaste lugares. Saliendo.")
        return

    # Lista global para todas las reseñas
    all_reviews_global = []

    print(f"\n[INFO] Vamos a procesar {len(lugares)} lugar(es).")

    for idx, (tipo, valor) in enumerate(lugares, start=1):
        if tipo == 'id':
            place_id = valor
            print(f"\n[{idx}] Descargando reseñas para place_id='{place_id}'")
            reviews_list, loc_name = fetch_reviews(place_id)
        else:
            # tipo='name'
            business_name = valor
            print(f"\n[{idx}] Buscando place_id para el nombre='{business_name}'")
            p_id, found_name, address = get_place_id_from_name(business_name)
            if not p_id:
                print("[ERROR] No se pudo obtener place_id. Omitimos este negocio.")
                continue
            print(f"[INFO] place_id={p_id} para '{found_name}' (Dir: {address})")
            reviews_list, loc_name = fetch_reviews(p_id)
        
        print(f"[INFO] Se obtuvieron {len(reviews_list)} reseñas.")
        # Agregamos todas las reseñas a la lista global
        all_reviews_global.extend(reviews_list)

    if not all_reviews_global:
        print("\n[INFO] Ninguna reseña encontrada en total. Saliendo.")
        return

    # Guardar en un SOLO CSV
    csv_filename = "reviews_combined.csv"
    save_all_reviews_to_csv(all_reviews_global, csv_filename)

    print("\n[INFO] ¡Proceso finalizado! Se combinó todo en reviews_combined.csv.")

if __name__ == "__main__":
    main()
