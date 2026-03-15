import tweepy
from openai import OpenAI
import os
import time
import schedule
import feedparser
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import Counter

TIMEZONE = ZoneInfo("America/Caracas")

RSS_URL = "https://news.google.com/rss/search?q=venezuela&hl=es&gl=ES&ceid=ES:es"

# CLIENTE TWITTER V2
twitter_client = tweepy.Client(
    consumer_key=os.environ["API_KEY"],
    consumer_secret=os.environ["API_SECRET"],
    access_token=os.environ["ACCESS_TOKEN"],
    access_token_secret=os.environ["ACCESS_TOKEN_SECRET"]
)

# CLIENTE TWITTER MEDIA
twitter_media = tweepy.API(
    tweepy.OAuth1UserHandler(
        os.environ["API_KEY"],
        os.environ["API_SECRET"],
        os.environ["ACCESS_TOKEN"],
        os.environ["ACCESS_TOKEN_SECRET"]
    )
)

# CLIENTE OPENAI
openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


# -------------------------
# HORARIO
# -------------------------

def horario_activo():

    now = datetime.now(TIMEZONE)

    h = now.hour
    m = now.minute

    if (7 <= h < 9) or (12 <= h < 15) or (19 <= h < 22):

        if m in [0,30]:
            return True

    return False


# -------------------------
# LEER NOTICIAS
# -------------------------

def get_news():

    feed = feedparser.parse(RSS_URL)

    noticias = []

    for entry in feed.entries:

        imagen = None

        if "media_content" in entry:

            imagen = entry.media_content[0]["url"]

        noticias.append({
            "titulo": entry.title,
            "imagen": imagen
        })

    return noticias


# -------------------------
# DETECTAR TENDENCIA
# -------------------------

def detectar_tendencia(noticias):

    claves = []

    for n in noticias:

        clave = " ".join(n["titulo"].lower().split()[:5])

        claves.append(clave)

    conteo = Counter(claves)

    tendencia = conteo.most_common(1)[0][0]

    for n in noticias:

        if tendencia in n["titulo"].lower():

            return n

    return noticias[0]


# -------------------------
# GENERAR TWEET
# -------------------------

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


# -------------------------
# DESCARGAR IMAGEN
# -------------------------

def descargar_imagen(url):

    if not url:
        return None

    try:

        img = requests.get(url).content

        with open("imagen.jpg","wb") as f:
            f.write(img)

        return "imagen.jpg"

    except:

        return None


# -------------------------
# PUBLICAR
# -------------------------

def publicar():

    noticias = get_news()

    noticia = detectar_tendencia(noticias)

    tweet = generar_tweet(noticia["titulo"])

    print("Publicando:", tweet)

    imagen = descargar_imagen(noticia["imagen"])

    try:

        if imagen:

            media = twitter_media.media_upload(imagen)

            twitter_client.create_tweet(
                text=tweet,
                media_ids=[media.media_id]
            )

        else:

            twitter_client.create_tweet(text=tweet)

    except Exception as e:

        print("Error publicando:", e)


# -------------------------
# CICLO
# -------------------------

def ciclo():

    if horario_activo():

        publicar()


schedule.every(1).minutes.do(ciclo)

print("Bot iniciado")


while True:

    schedule.run_pending()

    time.sleep(30)
