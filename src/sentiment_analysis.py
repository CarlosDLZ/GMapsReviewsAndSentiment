"""
Módulo: sentiment_analysis.py
Función para analizar el sentimiento del texto usando TextBlob.
"""

from textblob import TextBlob

def analyze_sentiment(text):
    """
    Analiza el sentimiento del texto.
    Parámetros:
      text (str): Texto a analizar.
    Retorna:
      'positive' si la polaridad > 0.1,
      'negative' si la polaridad < -0.1,
      'neutral' en caso contrario.
    """
    if not text:
        return "neutral"
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    if polarity > 0.1:
        return "positive"
    elif polarity < -0.1:
        return "negative"
    else:
        return "neutral"
