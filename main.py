import tweepy
import openai
import time
import os
import schedule

# Credenciales de X (Twitter)
client = tweepy.Client(
    consumer_key=os.environ["API_KEY"],
    consumer_secret=os.environ["API_SECRET"],
    access_token=os.environ["ACCESS_TOKEN"],
    access_token_secret=os.environ["ACCESS_TOKEN_SECRET"]
)

# OpenAI
openai.api_key = os.environ["OPENAI_API_KEY"]

def generar_tweet():
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres un experto en politica, economia y sociedad venezolana. "
                    "Genera un tweet informativo, reflexivo y objetivo sobre Venezuela. "
                    "Puede ser sobre politica, economia, cultura, migracion, derechos humanos o actualidad. "
                    "El tweet debe tener menos de 280 caracteres, sin hashtags excesivos, "
                    "en espanol y con un tono periodistico pero accesible."
                )
            },
            {
                "role": "user",
                "content": "Genera un tweet sobre Venezuela para publicar ahora."
            }
        ],
        max_tokens=100
    )
    return response.choices[0].message.content.strip()

def publicar_tweet():
    try:
        tweet = generar_tweet()
        client.create_tweet(text=tweet)
        print(f"Tweet publicado: {tweet}")
    except Exception as e:
        print(f"Error al publicar: {e}")

# Publicar cada 6 horas
schedule.every(6).hours.do(publicar_tweet)

# Publicar uno al inicio
publicar_tweet()

while True:
    schedule.run_pending()
    time.sleep(60)
