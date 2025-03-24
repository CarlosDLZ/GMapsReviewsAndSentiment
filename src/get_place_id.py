import os
import requests
from dotenv import load_dotenv

# Carga variables de entorno desde .env
load_dotenv()

# Obtenemos la clave de Places API desde la variable de entorno
API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

def get_place_id(business_name):
    """
    Dado el nombre de un negocio (ej. 'Taquería Don Pepe'),
    retorna su 'place_id', junto con el nombre y dirección formateados
    usando la Places API.
    """
    url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
    params = {
        "key": API_KEY,
        "input": business_name,
        "inputtype": "textquery",
        "fields": "place_id,formatted_address,name"
    }

    response = requests.get(url, params=params)
    data = response.json()

    if data.get("status") == "OK" and data.get("candidates"):
        # Tomamos el primer resultado
        candidate = data["candidates"][0]
        place_id = candidate.get("place_id")
        name = candidate.get("name")
        address = candidate.get("formatted_address")
        return place_id, name, address
    else:
        # No se encontró resultado, regresamos None
        return None, None, None

def main():
    print("=== Script para obtener Place IDs de Google Maps ===")
    print("Escribe los nombres de los lugares uno por uno.")
    print("Cuando termines, escribe 'FIN' para procesar la lista.\n")

    lugares = []

    while True:
        lugar = input("Nombre del lugar (o 'FIN' para terminar): ").strip()
        if lugar.lower() == 'fin':
            break
        if lugar:  # Si no está vacío
            lugares.append(lugar)

    if not lugares:
        print("\nNo ingresaste ningún nombre. Saliendo...")
        return

    print(f"\nHas ingresado {len(lugares)} lugar(es). Procediendo a consultar la API...\n")

    for idx, business_name in enumerate(lugares, start=1):
        place_id, name, address = get_place_id(business_name)
        print(f"{idx}. Lugar ingresado: {business_name}")
        if place_id:
            print(f"   » Negocio real: {name}")
            print(f"   » Dirección:   {address}")
            print(f"   » PLACE_ID:    {place_id}")
        else:
            print("   » No se encontró un place_id para este lugar.")
        print()  # línea en blanco para separar

    print("¡Proceso completado!")

if __name__ == "__main__":
    main()
