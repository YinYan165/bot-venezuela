import tweepy
from openai import OpenAI
import time
import os
import schedule
import feedparser
from collections import Counter
import random

# -----------------------------
# CONFIG
# -----------------------------

QUERY = "venezuela"
RSS_URL = f"https://news.google.com/rss/search?q={QUERY}&hl=es&gl=ES&ceid=ES:es"

# -----------------------------
# TWITTER CLIENT
# -----------------------------

twitter_client = tweepy.Client(
    consumer_key=os.environ["API_KEY"],
    consumer_secret=os.environ["API_SECRET"],
    access_token=os.environ["ACCESS_TOKEN"],
    access_token_secret=os.environ["ACCESS_TOKEN_SECRET"],
    wait_on_rate_limit=True
)

# -----------------------------
# OPENAI CLIENT
# -----------------------------

openai_client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"]
)

# -----------------------------
# MEMORIA DE TITULARES
# -----------------------------

titulares_publicados = set()

# -----------------------------
# OBTENER NOTICIAS
# -----------------------------

def obtener_noticias():

    feed = feedparser.parse(RSS_URL)

    noticias = []

    for entry in feed.entries:

        titulo = entry.title
        fuente = entry.source.title if "source" in entry else ""

        noticias.append({
            "titulo": titulo,
            "fuente": fuente
        })

    return noticias


# -----------------------------
# DETECTAR NOTICIA TENDENCIA
# -----------------------------

def detectar_tendencia(noticias):

    # simplificación de titulares
    claves = []

    for n in noticias:

        titulo = n["titulo"].lower()

        palabras = titulo.split()

        claves.append(" ".join(palabras[:6]))

    conteo = Counter(claves)

    tendencia = conteo.most_common(1)[0][0]

    for n in noticias:

        if tendencia in n["titulo"].lower():

            if n["titulo"] not in titulares_publicados:
                return n["titulo"]

    return random.choice(noticias)["titulo"]


# -----------------------------
# GENERAR TWEET
# -----------------------------

def generar_tweet(titular):

    prompt = f"""
    Escribe un tweet periodístico breve sobre esta noticia relacionada con Venezuela.

    Titular:
    {titular}

    Reglas:
    - máximo 250 caracteres
    - español
    - tono informativo
    - no usar hashtags
    """

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Eres un periodista especializado en Venezuela."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=120
    )

    tweet = response.choices[0].message.content.strip()

    if len(tweet) > 280:
        tweet = tweet[:277] + "..."

    return tweet


# -----------------------------
# PUBLICAR TWEET
# -----------------------------

def publicar_tweet():

    try:

        noticias = obtener_noticias()

        titular = detectar_tendencia(noticias)

        titulares_publicados.add(titular)

        tweet = generar_tweet(titular)

        print("Titular:", titular)
        print("Tweet:", tweet)

        intentos = 3

        for intento in range(intentos):

            try:

                response = twitter_client.create_tweet(text=tweet)

                print("Tweet publicado:", response.data["id"])

                return

            except Exception as e:

                print("Intento", intento + 1, "falló:", e)

                if intento < intentos - 1:
                    time.sleep(30)

        print("No se pudo publicar el tweet")

    except Exception as e:

        print("Error general:", e)


# -----------------------------
# SCHEDULER
# -----------------------------

schedule.every(2).hours.do(publicar_tweet)

print("Bot iniciado...")

publicar_tweet()

while True:

    schedule.run_pending()

    time.sleep(60)
