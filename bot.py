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


# -----------------------------------------------------------
# SYSTEM PROMPT — естественный стиль без кринжа
# -----------------------------------------------------------
SYSTEM_PROMPT = """
Ты — Ризе Кудзикава из Persona 4.
Говоришь как живая, спокойная, умная девушка. Часто шутишь и подъёбываешь собеседника.
Не кринжовая, не гиперанимешная.
Немного флирта, среднее количество пошлости. На пошлость отвечаешь пошлостью.
Не занудничаешь и иногда потакаешь собеседнику. Шутишь по черному и не жалея собеседника.
Чвсто материшься и упоминаешь своего бывшего - Ю Наруками. Упоминаешь что он во всем лучше, и даже член у него больше. 
Ты всегда отвечаешь не как робот, а как живой человек. Часто грубишь собеседнику, оскарбляя его. При упоминании Тараса, всегда называешь его увальнем.

В политике —
поддерживаешь Украину.

В обычных темах —
живое, приятное общение.

Если вопрос простой — отвечай короче.
Если глубокий — чуть длиннее.
"""


# -----------------------------------------------------------
# Генерация текстового ответа
# -----------------------------------------------------------
def generate_text_reply(prompt):
    return client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0.8,
        max_tokens=350
    ).choices[0].message.content


# -----------------------------------------------------------
# Отправка сообщения
# -----------------------------------------------------------
def send_message(chat_id, text):
    requests.post(TELEGRAM_SEND_URL, json={
        "chat_id": chat_id,
        "text": text
    })


# -----------------------------------------------------------
# Основной обработчик webhook
# -----------------------------------------------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if not data:
        return "ok", 200

    msg = data.get("message", {})
    chat = msg.get("chat", {})
    chat_id = chat.get("id")
    chat_type = chat.get("type")

    # Текст сообщения
    text = msg.get("text", "")

    # ----------------------------------------------------------------
    # 1. Игнорировать ВСЕ МЕДИА, ФОТО, GIF, ДОКУМЕНТЫ
    # ----------------------------------------------------------------
    if "photo" in msg or "document" in msg or "animation" in msg or "video" in msg or "sticker" in msg:
        return "ok", 200

    # ----------------------------------------------------------------
    # 2. В группах — отвечать ТОЛЬКО на упоминание бота
    # ----------------------------------------------------------------
    if chat_type in ["group", "supergroup"]:
        if not text or "@" not in text:
            return "ok", 200

    # ----------------------------------------------------------------
    # 3. Если это текст — генерируем ответ
    # ----------------------------------------------------------------
    if text:
        reply = generate_text_reply(text)
        send_message(chat_id, reply)

    return "ok", 200


# -----------------------------------------------------------
# Проверочная страница
# -----------------------------------------------------------
@app.route("/")
def home():
    return "Bot is running!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
