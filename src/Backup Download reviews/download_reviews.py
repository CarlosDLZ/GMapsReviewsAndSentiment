import os
import requests
import csv
import time
from dotenv import load_dotenv

################################################################################
# 1) Carga de Variables de Entorno
################################################################################
load_dotenv()
API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

################################################################################
# 2) Función para Obtener place_id Dado un Nombre de Negocio
################################################################################
def get_place_id_from_name(business_name):
    """
    Busca el place_id de un negocio usando la Places API con 'findplacefromtext'.
    Retorna (place_id, nombre, dirección) o (None, None, None) si no encuentra nada.
    """
    print(f"\n[INFO] Buscando place_id para: {business_name}")
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
        print(f"[ERROR] No se pudo conectar a la API. Error: {e}")
        return None, None, None

    status = data.get("status")
    if status == "OK" and data.get("candidates"):
        candidate = data["candidates"][0]
        place_id = candidate.get("place_id")
        name = candidate.get("name")
        address = candidate.get("formatted_address")
        print(f"[INFO] Se encontró place_id: {place_id} para {name}")
        return place_id, name, address
    else:
        print(f"[WARNING] No se encontró place_id para '{business_name}'. status={status}")
        return None, None, None

################################################################################
# 3) Función para Descarga de Reseñas (API de Place Details)
################################################################################
def fetch_reviews(place_id):
    """
    Obtiene reseñas para el place_id dado usando la API de Place Details.
    Maneja paginación con next_page_token. Retorna una lista de dicts con reseñas.
    """
    if not place_id:
        print("[ERROR] No se proporcionó un place_id válido.")
        return []

    all_reviews = []
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
            response = requests.get(url, params=params)
            data = response.json()
        except Exception as e:
            print(f"[ERROR] Error al conectar con la API: {e}")
            break
        
        status = data.get("status")
        if status != "OK":
            print(f"[WARNING] Status de la API: {status}")
            break
        
        result = data.get("result", {})
        reviews = result.get("reviews", [])
        
        for r in reviews:
            item = {
                "author_name": r.get("author_name"),
                "rating": r.get("rating"),
                "text": r.get("text"),
                "time": r.get("time"),  # Unix timestamp
                "relative_time": r.get("relative_time_description")
            }
            all_reviews.append(item)
        
        next_page_token = data.get("next_page_token")
        if not next_page_token:
            # No hay más páginas
            break
        
        # Google pide esperar ~2s antes de usar el next_page_token
        print("[INFO] Paginación detectada. Esperando 2s para la siguiente página...")
        time.sleep(2)
    
    return all_reviews

################################################################################
# 4) Guardar Reseñas en CSV
################################################################################
def save_reviews_to_csv(reviews, csv_filename):
    if not reviews:
        print("[INFO] No hay reseñas para guardar en CSV.")
        return
    
    fieldnames = ["author_name", "rating", "text", "time", "relative_time"]
    
    with open(csv_filename, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for review in reviews:
            writer.writerow(review)
    
    print(f"[INFO] Se guardaron {len(reviews)} reseñas en {csv_filename}")

################################################################################
# 5) Función Principal con Lógica Interactiva
################################################################################
def main():
    print("======================================================")
    print("  Bienvenido al Descargador de Reseñas (Beta)         ")
    print("======================================================")
    
    # Verificamos que exista la API_KEY
    if not API_KEY:
        print("[ERROR] La variable GOOGLE_PLACES_API_KEY no está configurada en .env")
        print("Cierra el programa y revisa tu archivo .env")
        return
    
    # Preguntamos al usuario si tiene un place_id o desea buscar por nombre
    print("\n¿Tienes un place_id o deseas buscar el ID por nombre de negocio?")
    print("  1) Tengo un place_id y quiero usarlo directo")
    print("  2) No tengo place_id, prefiero buscar por nombre")
    print("  3) Cancelar/SALIR")
    
    opcion = input("\nElige una opción (1/2/3): ").strip()
    
    if opcion == "3":
        print("[INFO] Saliendo del programa. ¡Hasta pronto!")
        return
    
    place_id = None
    nombre_del_lugar = None
    
    if opcion == "1":
        # Pedimos el place_id directamente
        place_id = input("Ingresa el place_id: ").strip()
        if not place_id:
            print("[ERROR] No ingresaste ningún place_id válido. Saliendo.")
            return
    elif opcion == "2":
        # Pedimos el nombre del lugar
        nombre_del_lugar = input("Ingresa el nombre del lugar (ej. 'Starbucks Polanco'): ").strip()
        if not nombre_del_lugar:
            print("[ERROR] No ingresaste ningún nombre. Saliendo.")
            return
        
        # Intentamos obtener el place_id
        p_id, name, address = get_place_id_from_name(nombre_del_lugar)
        if not p_id:
            print("[ERROR] No se pudo obtener el place_id. Saliendo.")
            return
        place_id = p_id
        print(f"[INFO] place_id para '{name}' -> {place_id} (Dirección: {address})")
    else:
        print("[ERROR] Opción inválida. Saliendo.")
        return
    
    # Ya tenemos un place_id (sea directo o buscado)
    print("\n[INFO] Descargando reseñas para place_id:", place_id)
    reviews = fetch_reviews(place_id)
    print(f"[INFO] Se obtuvieron {len(reviews)} reseñas en total.")
    
    if reviews:
        # Preguntamos si desea guardarlas en CSV
        print("\n¿Deseas guardar las reseñas en un archivo CSV? (S/N)")
        resp = input(">>> ").strip().lower()
        if resp == "s":
            # Nombramos el CSV
            csv_filename = f"reviews_{place_id}.csv"
            save_reviews_to_csv(reviews, csv_filename)
        else:
            print("[INFO] No se guardaron reseñas en CSV.")
    else:
        print("[WARNING] No se encontraron reseñas para este lugar.")
    
    print("\n[INFO] Proceso finalizado. ¡Gracias por usar el script!")
    
if __name__ == "__main__":
    main()

