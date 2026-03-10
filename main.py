import tweepy
from openai import OpenAI
import os
import time
import schedule
import feedparser
import random
import json
from collections import Counter

# ------------------------
# CONFIG
# ------------------------

QUERY = "venezuela"
RSS_URL = f"https://news.google.com/rss/search?q={QUERY}&hl=es&gl=ES&ceid=ES:es"

MEMORY_FILE = "bot_memory.json"

MEDIOS_FIABLES = [
"BBC",
"Reuters",
"El País",
"DW",
"France24",
"EFE",
"Associated Press"
]

# ------------------------
# TWITTER CLIENT
# ------------------------

twitter_client = tweepy.Client(
    consumer_key=os.environ["API_KEY"],
    consumer_secret=os.environ["API_SECRET"],
    access_token=os.environ["ACCESS_TOKEN"],
    access_token_secret=os.environ["ACCESS_TOKEN_SECRET"],
    wait_on_rate_limit=True
)

# ------------------------
# OPENAI CLIENT
# ------------------------

openai_client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"]
)

# ------------------------
# MEMORIA
# ------------------------

def load_memory():

    if os.path.exists(MEMORY_FILE):

        with open(MEMORY_FILE, "r") as f:
            return json.load(f)

    return {
        "published_titles": [],
        "replied_tweets": []
    }


def save_memory(memory):

    memory["published_titles"] = memory["published_titles"][-200:]
    memory["replied_tweets"] = memory["replied_tweets"][-200:]

    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f)


memory = load_memory()

# ------------------------
# OBTENER NOTICIAS
# ------------------------

def get_news():

    feed = feedparser.parse(RSS_URL)

    noticias = []

    for entry in feed.entries:

        noticias.append(entry.title)

    return noticias


# ------------------------
# DETECTAR NOTICIA RELEVANTE
# ------------------------

def detect_trend(noticias):

    filtradas = []

    for titulo in noticias:

        if any(medio.lower() in titulo.lower() for medio in MEDIOS_FIABLES):

            if titulo not in memory["published_titles"]:
                filtradas.append(titulo)

    if filtradas:
        return random.choice(filtradas)

    return random.choice(noticias)


# ------------------------
# GENERAR TWEET
# ------------------------

def generate_tweet(titular):

    prompt = f"""
Escribe un tweet informativo sobre esta noticia relacionada con Venezuela.

Titular:
{titular}

Incluye:
- breve contexto político o económico
- tono periodístico
- máximo 250 caracteres
- sin hashtags
"""

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Eres analista político especializado en Venezuela."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=120
    )

    tweet = response.choices[0].message.content.strip()

    if len(tweet) > 280:
        tweet = tweet[:277] + "..."

    return tweet


# ------------------------
# PUBLICAR TWEET
# ------------------------

def publish_tweet():

    try:

        noticias = get_news()

        titular = detect_trend(noticias)

        tweet = generate_tweet(titular)

        print("Titular:", titular)
        print("Tweet:", tweet)

        for intento in range(3):

            try:

                response = twitter_client.create_tweet(text=tweet)

                print("Tweet publicado:", response.data["id"])

                memory["published_titles"].append(titular)
                save_memory(memory)

                return

            except Exception as e:

                print("Intento fallido:", e)

                if intento < 2:
                    time.sleep(30)

        print("No se pudo publicar")

    except Exception as e:

        print("Error publicando:", e)


# ------------------------
# BUSCAR TWEET VIRAL
# ------------------------

def find_relevant_tweet():

    try:

        resultados = twitter_client.search_recent_tweets(
            query="venezuela lang:es -is:retweet",
            max_results=10,
            tweet_fields=["public_metrics"]
        )

        if not resultados.data:
            return None

        candidatos = []

        for tweet in resultados.data:

            if tweet.id in memory["replied_tweets"]:
                continue

            metrics = tweet.public_metrics

            score = metrics["like_count"] + metrics["retweet_count"]

            if score > 200:
                candidatos.append(tweet)

        if candidatos:
            return random.choice(candidatos)

    except Exception as e:

        print("Error buscando tweets:", e)

    return None


# ------------------------
# GENERAR RESPUESTA
# ------------------------

def generate_reply(texto):

    prompt = f"""
Responde con un comentario breve y analítico al siguiente tweet sobre Venezuela.

Tweet:
{texto}

Reglas:
- máximo 200 caracteres
- tono informativo
"""

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Eres analista político venezolano."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=80
    )

    return response.choices[0].message.content.strip()


# ------------------------
# RESPONDER TWEET
# ------------------------

def reply_to_tweet():

    tweet = find_relevant_tweet()

    if not tweet:
        print("No tweet viral encontrado")
        return

    respuesta = generate_reply(tweet.text)

    try:

        twitter_client.create_tweet(
            text=respuesta,
            in_reply_to_tweet_id=tweet.id
        )

        memory["replied_tweets"].append(tweet.id)
        save_memory(memory)

        print("Respuesta enviada")

    except Exception as e:

        print("Error respondiendo:", e)


# ------------------------
# CICLO BOT
# ------------------------

def ciclo_bot():

    publish_tweet()

    time.sleep(20)

    reply_to_tweet()


# ------------------------
# SCHEDULER
# ------------------------

schedule.every(4).hours.do(ciclo_bot)

print("Bot iniciado")

ciclo_bot()

while True:

    schedule.run_pending()

    time.sleep(60)
