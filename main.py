import tweepy
from openai import OpenAI
import time
import os
import schedule
import feedparser
import random

# ----------- X CLIENT -----------

twitter_client = tweepy.Client(
    consumer_key=os.environ["API_KEY"],
    consumer_secret=os.environ["API_SECRET"],
    access_token=os.environ["ACCESS_TOKEN"],
    access_token_secret=os.environ["ACCESS_TOKEN_SECRET"],
    wait_on_rate_limit=True
)

# ----------- OPENAI -----------

openai_client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"]
)

# ----------- RSS DE NOTICIAS -----------

FUENTES = [
    "https://news.google.com/rss/search?q=venezuela&hl=es&gl=ES&ceid=ES:es",
    "https://feeds.bbci.co.uk/mundo/topics/cvenezuel/rss.xml"
]

# guardar titulares ya usados
titulares_usados = set()

# ----------- OBTENER TITULAR -----------

def obtener_titular():
    for fuente in FUENTES:
        feed = feedparser.parse(fuente)

        for entry in feed.entries:
            titulo = entry.title

            if titulo not in titulares_usados:
                titulares_usados.add(titulo)
                return titulo

    return None


# ----------- GENERAR TWEET -----------

def generar_tweet(titular):

    prompt = f"""
    A partir del siguiente titular sobre Venezuela, escribe un tweet informativo
    breve, claro y objetivo en español.

    Titular:
    {titular}

    El tweet debe tener máximo 250 caracteres.
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


# ----------- PUBLICAR -----------

def publicar_tweet():

    try:

        titular = obtener_titular()

        if not titular:
            print("No se encontraron titulares nuevos")
            return

        tweet = generar_tweet(titular)

        print("Titular:", titular)
        print("Tweet:", tweet)

        response = twitter_client.create_tweet(text=tweet)

        print("Tweet publicado:", response.data["id"])

    except Exception as e:
        print("Error:", e)


# ----------- SCHEDULER -----------

schedule.every(2).hours.do(publicar_tweet)

print("Bot iniciado")

# primer tweet al arrancar
publicar_tweet()

while True:
    schedule.run_pending()
    time.sleep(60)
