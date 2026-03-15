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
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import Counter

# -------------------------
# CONFIG
# -------------------------

TIMEZONE = ZoneInfo("America/Caracas")

RSS_URL = "https://news.google.com/rss/search?q=venezuela&hl=es&gl=ES&ceid=ES:es"

MEMORY_FILE = "bot_memory.json"

# -------------------------
# CLIENTES API
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
        return {"publicadas":[], "ultimo_aviso":0}

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

    return False

# -------------------------
# LEER NOTICIAS
# -------------------------

def get_news():

    feed=feedparser.parse(RSS_URL)

    noticias=[]

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

        fuente=""

        if "source" in entry:
            fuente=entry.source["title"]

        noticias.append({
            "titulo":entry.title,
            "imagen":imagen,
            "fuente":fuente
        })

    return noticias

# -------------------------
# DETECTAR TEMA DOMINANTE
# -------------------------

def detectar_crecimiento(noticias):

    temas=[]

    for n in noticias:

        clave=" ".join(n["titulo"].lower().split()[:6])

        temas.append(clave)

    conteo=Counter(temas)

    tema,frecuencia=conteo.most_common(1)[0]

    return tema,frecuencia

# -------------------------
# SELECCIONAR NOTICIA
# -------------------------

def seleccionar_noticia(noticias):

    tema,_=detectar_crecimiento(noticias)

    for n in noticias:

        if tema in n["titulo"].lower():
            return n

    return noticias[0]

# -------------------------
# GENERAR TWEET
# -------------------------

def generar_tweet(titular,tendencia=False):

    prompt=f"""
Resume esta noticia sobre Venezuela en un tweet informativo.

Titular:
{titular}

Máximo 180 caracteres.
"""

    r=openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
        {"role":"system","content":"Redactor periodístico especializado en política latinoamericana"},
        {"role":"user","content":prompt}
        ]
    )

    texto=r.choices[0].message.content.strip()

    prefijos=["","Actualización:","Informe:"]
    texto=f"{random.choice(prefijos)} {texto}".strip()

    if tendencia:
        texto="📰 Tendencia en medios: "+texto

    return texto[:200]

# -------------------------
# DESCARGAR IMAGEN REAL
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
# GENERAR IMAGEN IA
# -------------------------

def generar_imagen_ia(titular):

    try:

        prompt=f"news photo illustration about: {titular}"

        img=openai_client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024"
        )

        image_base64=img.data[0].b64_json

        import base64

        with open("imagen.jpg","wb") as f:
            f.write(base64.b64decode(image_base64))

        print("Imagen generada por IA")

        return "imagen.jpg"

    except Exception as e:

        print("Error generando imagen IA:",e)

        return None

# -------------------------
# PUBLICAR
# -------------------------

def publicar():

    memoria=cargar_memoria()

    noticias=get_news()

    noticia=seleccionar_noticia(noticias)

    titulo_limpio=noticia["titulo"].lower()[:80]

    if titulo_limpio in memoria["publicadas"]:
        print("Noticia ya publicada")
        return

    tema,frecuencia=detectar_crecimiento(noticias)

    tendencia=frecuencia>=3

    tweet=generar_tweet(noticia["titulo"],tendencia)

    if noticia["fuente"]:
        tweet=f"{tweet} ({noticia['fuente']})"

    imagen=descargar_imagen(noticia["imagen"])

    if not imagen:

        print("No hay imagen en RSS, generando con IA")

        imagen=generar_imagen_ia(noticia["titulo"])

    try:

        if imagen:

            media=twitter_media.media_upload(imagen)

            twitter_client.create_tweet(
                text=tweet,
                media_ids=[media.media_id]
            )

        else:

            twitter_client.create_tweet(text=tweet)

        memoria["publicadas"].append(titulo_limpio)

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
