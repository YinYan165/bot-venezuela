import tweepy
from openai import OpenAI
import time
import os
import schedule

# ----------- X (Twitter) CLIENT -----------

client = tweepy.Client(
    consumer_key=os.environ["API_KEY"],
    consumer_secret=os.environ["API_SECRET"],
    access_token=os.environ["ACCESS_TOKEN"],
    access_token_secret=os.environ["ACCESS_TOKEN_SECRET"],
    wait_on_rate_limit=True
)

# ----------- OPENAI CLIENT -----------

openai_client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"]
)

# ----------- GENERAR TWEET -----------

def generar_tweet():
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un analista experto en política, economía y sociedad venezolana. "
                        "Escribe un tweet informativo y reflexivo sobre Venezuela. "
                        "Debe ser objetivo, claro y con tono periodístico. "
                        "Máximo 250 caracteres. Español. Sin hashtags innecesarios."
                    )
                },
                {
                    "role": "user",
                    "content": "Escribe un tweet breve sobre la situación actual de Venezuela."
                }
            ],
            max_tokens=100
        )

        tweet = response.choices[0].message.content.strip()

        # seguridad longitud
        if len(tweet) > 280:
            tweet = tweet[:277] + "..."

        return tweet

    except Exception as e:
        print("Error generando tweet:", e)
        return None


# ----------- PUBLICAR TWEET -----------

def publicar_tweet():
    try:
        tweet = generar_tweet()

        if not tweet:
            print("Tweet vacío. No se publica.")
            return

        response = client.create_tweet(text=tweet)

        print("Tweet publicado correctamente")
        print("ID:", response.data["id"])
        print("Texto:", tweet)

    except Exception as e:
        print("Error al publicar:", e)


# ----------- SCHEDULER -----------

schedule.every(6).hours.do(publicar_tweet)

# publicar uno al inicio
print("Bot iniciado...")
publicar_tweet()

# loop infinito
while True:
    schedule.run_pending()
    time.sleep(60)
