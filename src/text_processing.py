"""
Módulo: text_processing.py
Función para limpiar texto de reseñas, eliminando saltos de línea, caracteres no deseados, etc.
"""

import re

def clean_text(text):
    """
    Limpia el texto aplicando los siguientes pasos:
      - Elimina saltos de línea.
      - Convierte a minúsculas.
      - Elimina caracteres no permitidos (solo letras, números, y puntuación básica).
      - Quita espacios extra.
    Parámetros:
      text (str): Texto a limpiar.
    Retorna:
      Texto limpio (str).
    """
    if not text:
        return ""
    text = text.replace("\n", " ").replace("\r", " ")
    text = text.lower()
    text = re.sub(r"[^a-z0-9áéíóúüñ¡!¿?.,:;'\"()\s-]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
