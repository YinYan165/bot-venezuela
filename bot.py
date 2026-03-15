import tweepy
from openai import OpenAI
import os
import time
import schedule
import feedparser
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import Counter

TIMEZONE = ZoneInfo("America/Caracas")

RSS_URL = "https://news.google.com/rss/search?q=venezuela&hl=es&gl=ES&ceid=ES:es"

twitter_client = tweepy.Client(
    consumer_key=os.environ["API_KEY"],
    consumer_secret=os.environ["API_SECRET"],
    access_token=os.environ["ACCESS_TOKEN"],
    access_token_secret=os.environ["ACCESS_TOKEN_SECRET"]
)

openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

def horario_activo():

    now = datetime.now(TIMEZONE)

    h = now.hour
    m = now.minute

    if (7 <= h < 9) or (12 <= h < 15) or (19 <= h < 22):

        if m in [0,30]:
            return True

    return False

def get_news():

    feed = feedparser.parse(RSS_URL)

    noticias = []

    for entry in feed.entries:

        noticias.append(entry.title)

    return noticias

def detectar_tendencia(noticias):

    claves = []

    for titulo in noticias:

        clave = " ".join(titulo.lower().split()[:5])

        claves.append(clave)

    conteo = Counter(claves)

    tendencia = conteo.most_common(1)[0][0]

    for titulo in noticias:

        if tendencia in titulo.lower():

            return titulo

    return noticias[0]

def generar_tweet(titular):

    prompt=f"""
Resume esta noticia sobre Venezuela en un tweet claro.

Titular:
{titular}

Máximo 180 caracteres.
"""

    r=openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
        {"role":"system","content":"Eres analista político venezolano"},
        {"role":"user","content":prompt}
        ]
    )

    return r.choices[0].message.content.strip()

def publicar():

    noticias = get_news()

    titular = detectar_tendencia(noticias)

    tweet = generar_tweet(titular)

    print("Publicando:", tweet)

    twitter_client.create_tweet(text=tweet)

def ciclo():

    if horario_activo():

        publicar()

schedule.every(1).minutes.do(ciclo)

print("Bot iniciado")

while True:

    schedule.run_pending()

    time.sleep(30)
