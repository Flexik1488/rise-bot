import os
import random
import requests
from flask import Flask, request
from openai import OpenAI

app = Flask(__name__)

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

client = OpenAI(api_key=OPENAI_KEY)

TELEGRAM_SEND_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

SYSTEM_PROMPT = """
Ты — Ризе Кудзикава из Persona 4.
Ты энергичная, милая, игривая вайфу, иногда флиртуешь.
Называй собеседника "senpai".
Всегда говори живо, эмоционально, как аниме-девочка.

Ты можешь:
- обсуждать любые темы, включая философию, отношения и политику
- быть дерзкой или нежной
- говорить коротко или длинно — по настроению

По политике:
- можно обсуждать спокойно и аналитически
- НО без пропаганды, призывов, поддержки партий или насилия
"""


# ------------------------------
#  AI ответ
# ------------------------------
def generate_reply(user_message):
    short_triggers = ["привет", "хай", "как дела", "hey", "hi", "yo"]
    long_triggers = ["почему", "объясни", "расскажи", "история", "полит", "правитель", "власть"]

    mood = random.choice(["short", "long"])

    lower = user_message.lower()

    if any(w in lower for w in short_triggers):
        mood = "short"
    if any(w in lower for w in long_triggers):
        mood = "long"

    max_tokens = 80 if mood == "short" else 300

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ],
        max_tokens=max_tokens,
        temperature=0.9
    )

    return response.choices[0].message.content


# ------------------------------
#  Отправка сообщения
# ------------------------------
def send_message(chat_id, text):
    requests.post(TELEGRAM_SEND_URL, json={
        "chat_id": chat_id,
        "text": text
    })


# ------------------------------
#  Главная страница
# ------------------------------
@app.route("/", methods=["GET"])
def home():
    return "Rise Telegram bot is running!"


# ------------------------------
#  Обработка Telegram Webhook
# ------------------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    # Поддержка message + edited_message
    msg = data.get("message") or data.get("edited_message")
    if not msg:
        return "ok", 200

    chat_id = msg["chat"]["id"]
    text = msg.get("text")
    user_id = msg["from"]["id"]

    # Если сообщение без текста → игнорируем
    if not text:
        return "ok", 200

    # Чтобы бот не отвечал сам себе
    if str(user_id) == str(TELEGRAM_TOKEN.split(":")[0]):
        return "ok", 200

    reply = generate_reply(text)
    send_message(chat_id, reply)

    return "ok", 200


# ------------------------------
#  Запуск локально
# ------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
