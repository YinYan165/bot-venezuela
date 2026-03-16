import tweepy
from openai import OpenAI
import os
import time
import schedule
import feedparser
import requests
import json
import random
import re
import base64
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import Counter

# -------------------------
# CONFIG
# -------------------------

TIMEZONE = ZoneInfo("America/Caracas")

WOEID_VENEZUELA = 395269

RSS_FEEDS = [

"https://news.google.com/rss/search?q=venezuela&hl=es&gl=ES&ceid=ES:es",
"https://feeds.bbci.co.uk/mundo/rss.xml",
"https://rss.dw.com/rdf/rss-es-all",
"https://www.elnacional.com/feed/",
"https://talcualdigital.com/feed/",
"https://elpitazo.net/feed/"

]

MEMORY_FILE = "bot_memory.json"

# -------------------------
# CLIENTES API
# -------------------------

client = tweepy.Client(
consumer_key=os.environ["API_KEY"],
consumer_secret=os.environ["API_SECRET"],
access_token=os.environ["ACCESS_TOKEN"],
access_token_secret=os.environ["ACCESS_TOKEN_SECRET"]
)

api = tweepy.API(
tweepy.OAuth1UserHandler(
os.environ["API_KEY"],
os.environ["API_SECRET"],
os.environ["ACCESS_TOKEN"],
os.environ["ACCESS_TOKEN_SECRET"]
)
)

openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# -------------------------
# MEMORIA
# -------------------------

def cargar_memoria():

    try:
        with open(MEMORY_FILE,"r") as f:
            return json.load(f)
    except:
        return {"publicadas":[],"ultimo_trend":0}

def guardar_memoria(memoria):

    with open(MEMORY_FILE,"w") as f:
        json.dump(memoria,f)

# -------------------------
# HORARIO
# -------------------------

def horario_activo():

    now=datetime.now(TIMEZONE)

    h=now.hour
    m=now.minute

    if (7<=h<9) or (12<=h<15) or (19<=h<22):

        if m in [0,30]:
            return True

    if 6<=h<=23 and m==0:
        return True

    if h in [2,4] and m==0:
        return True

    return False

# -------------------------
# RSS
# -------------------------

def leer_feed(url):

    noticias=[]

    feed=feedparser.parse(url)

    for entry in feed.entries:

        imagen=None

        if "media_content" in entry:
            imagen=entry.media_content[0]["url"]

        elif "media_thumbnail" in entry:
            imagen=entry.media_thumbnail[0]["url"]

        elif "summary" in entry:

            match=re.search(r'<img[^>]+src="([^">]+)"',entry.summary)

            if match:
                imagen=match.group(1)

        noticias.append({
            "titulo":entry.title,
            "imagen":imagen
        })

    return noticias

# -------------------------
# AGREGAR FUENTES
# -------------------------

def get_news():

    todas=[]

    for url in RSS_FEEDS:

        try:

            todas.extend(leer_feed(url))

        except:

            pass

    return todas

# -------------------------
# ORDENAR NOTICIAS
# -------------------------

def ordenar_noticias(noticias):

    claves=[]

    for n in noticias:

        clave=" ".join(n["titulo"].lower().split()[:6])

        claves.append(clave)

    conteo=Counter(claves)

    noticias_ordenadas=sorted(
    noticias,
    key=lambda n: conteo[" ".join(n["titulo"].lower().split()[:6])],
    reverse=True
    )

    return noticias_ordenadas

# -------------------------
# SELECCIONAR NOTICIA
# -------------------------

def seleccionar_noticia(noticias,memoria):

    noticias=ordenar_noticias(noticias)

    for n in noticias:

        titulo=n["titulo"].lower()[:80]

        if titulo not in memoria["publicadas"]:

            return n

    return None

# -------------------------
# GENERAR TWEET
# -------------------------

def generar_tweet(titulo):

    prompt=f"""
Escribe un tweet sobre esta noticia de Venezuela.

Titular:
{titulo}

Con tono periodístico y una ligera ironía.
Máximo 180 caracteres.
"""

    r=openai_client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
    {"role":"system","content":"Analista político con ironía elegante"},
    {"role":"user","content":prompt}
    ]
    )

    return r.choices[0].message.content.strip()[:200]

# -------------------------
# CONTEXTO
# -------------------------

def generar_contexto():

    prompt="""
Escribe un tweet irónico sobre la situación política o económica de Venezuela.
Máximo 180 caracteres.
"""

    r=openai_client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
    {"role":"system","content":"Analista político latinoamericano"},
    {"role":"user","content":prompt}
    ]
    )

    return r.choices[0].message.content.strip()

# -------------------------
# IMAGEN
# -------------------------

def descargar_imagen(url):

    if not url:
        return None

    try:

        img=requests.get(url,timeout=10).content

        with open("imagen.jpg","wb") as f:
            f.write(img)

        return "imagen.jpg"

    except:

        return None

# -------------------------
# IMAGEN IA
# -------------------------

def generar_imagen_ia(titulo):

    try:

        img=openai_client.images.generate(
        model="gpt-image-1",
        prompt=f"news illustration about {titulo}",
        size="1024x1024"
        )

        image_base64=img.data[0].b64_json

        with open("imagen.jpg","wb") as f:
            f.write(base64.b64decode(image_base64))

        return "imagen.jpg"

    except:

        return None

# -------------------------
# TENDENCIAS
# -------------------------

def buscar_tendencia():

    try:

        trends = api.get_place_trends(WOEID_VENEZUELA)

        return trends[0]["trends"][0]["name"]

    except:

        return None

# -------------------------
# GENERAR BREAKING
# -------------------------

def generar_breaking(tema):

    prompt=f"""
En Venezuela es tendencia el tema:

{tema}

Escribe un tweet BREAKING con ironía inteligente.
Máximo 180 caracteres.
"""

    r=openai_client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
    {"role":"system","content":"Analista político con ironía"},
    {"role":"user","content":prompt}
    ]
    )

    return "BREAKING: "+r.choices[0].message.content.strip()

# -------------------------
# PUBLICAR NOTICIA
# -------------------------

def publicar():

    memoria=cargar_memoria()

    noticias=get_news()

    noticia=seleccionar_noticia(noticias,memoria)

    if noticia:

        tweet=generar_tweet(noticia["titulo"])

        imagen=descargar_imagen(noticia["imagen"])

        if not imagen:
            imagen=generar_imagen_ia(noticia["titulo"])

        memoria["publicadas"].append(noticia["titulo"].lower()[:80])

    else:

        tweet=generar_contexto()

        imagen=generar_imagen_ia("venezuela politics")

    if imagen:

        media=api.media_upload(imagen)

        client.create_tweet(
        text=tweet,
        media_ids=[media.media_id]
        )

    else:

        client.create_tweet(text=tweet)

    guardar_memoria(memoria)

# -------------------------
# PUBLICAR TENDENCIA
# -------------------------

def publicar_tendencia():

    memoria=cargar_memoria()

    if time.time() - memoria["ultimo_trend"] < 10800:
        return

    tema=buscar_tendencia()

    if not tema:
        return

    tweet=generar_breaking(tema)

    client.create_tweet(text=tweet)

    memoria["ultimo_trend"]=time.time()

    guardar_memoria(memoria)

# -------------------------
# SCHEDULER
# -------------------------

def ciclo():

    if horario_activo():

        publicar()

schedule.every(1).minutes.do(ciclo)
schedule.every(3).hours.do(publicar_tendencia)

print("Bot iniciado")

while True:

    schedule.run_pending()

    time.sleep(30)
