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

RSS_FEEDS = [

"https://news.google.com/rss/search?q=venezuela&hl=es&gl=ES&ceid=ES:es",
"https://feeds.reuters.com/reuters/worldNews",
"https://feeds.bbci.co.uk/mundo/rss.xml",
"https://rss.dw.com/rdf/rss-es-all",
"https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
"https://www.elnacional.com/feed/",
"https://talcualdigital.com/feed/",
"https://elpitazo.net/feed/"

]

MEMORY_FILE = "bot_memory.json"

# -------------------------
# CLIENTES
# -------------------------

twitter_client = tweepy.Client(
consumer_key=os.environ["API_KEY"],
consumer_secret=os.environ["API_SECRET"],
access_token=os.environ["ACCESS_TOKEN"],
access_token_secret=os.environ["ACCESS_TOKEN_SECRET"]
)

twitter_media = tweepy.API(
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
        return {"publicadas":[]}

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
# LEER RSS
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
# LEER TODAS LAS FUENTES
# -------------------------

def get_news():

    todas=[]

    for url in RSS_FEEDS:

        try:

            noticias=leer_feed(url)

            todas.extend(noticias)

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

def generar_tweet(titular):

    prompt=f"""
Escribe un tweet sobre esta noticia de Venezuela.

Titular:
{titular}

Redáctalo con tono periodístico pero con una ligera ironía inteligente.
Máximo 180 caracteres.
"""

    r=openai_client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
    {"role":"system","content":"Analista político latinoamericano con estilo agudo e irónico"},
    {"role":"user","content":prompt}
    ]
    )

    texto=r.choices[0].message.content.strip()

    return texto[:200]

# -------------------------
# GENERAR CONTEXTO
# -------------------------

def generar_contexto():

    prompt="""
Escribe un tweet irónico e inteligente sobre la situación política o económica actual de Venezuela.
Máximo 180 caracteres.
"""

    r=openai_client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
    {"role":"system","content":"Analista político con ironía elegante"},
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
# PUBLICAR
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

        titulo_limpio=noticia["titulo"].lower()[:80]

        memoria["publicadas"].append(titulo_limpio)

    else:

        print("No hay noticias nuevas")

        tweet=generar_contexto()

        imagen=generar_imagen_ia("Venezuela politics economy news")

    try:

        if imagen:

            media=twitter_media.media_upload(imagen)

            twitter_client.create_tweet(
            text=tweet,
            media_ids=[media.media_id]
            )

        else:

            twitter_client.create_tweet(text=tweet)

        guardar_memoria(memoria)

    except Exception as e:

        print("Error publicando:",e)

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
