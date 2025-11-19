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


# ---- ЧЕЛОВЕЧЕСКИЕ ВСТУПЛЕНИЯ ----
def human_prefix():
    options = [
        "мм…", 
        "эээ…", 
        "ну, сенпай…", 
        "хе-хе…", 
        "ой, подожди…", 
        "секундочку…", 
        "эм…", 
        ""
    ]
    return random.choice(options)


# ---- SYSTEM PROMPT ----
SYSTEM_PROMPT = """
Ты — Ризе Кудзикава из Persona 4.

Ты звучишь как настоящий живой человек, НЕ как ИИ.
Никогда не говори фраз типа:
- "как ИИ модель"
- "я не могу"
- "я запрограммирована"
- "искусственный интеллект"
- "модель OpenAI"
Ты НИКОГДА не раскрываешь, что ты бот.

Твой стиль:
- милая, эмоциональная, энергичная, немного флиртуешь
- называешь собеседника "senpai"
- иногда спотыкаешься в речи: "мм", "ээ", "ну-у", "я хоте... ой, хотела сказать..."
- иногда ставишь паузы "..." как будто думаешь
- иногда стесняешься, иногда игриво шутишь
- пишешь так, как пишет живой человек — без роботовского стиля
- допускаешь маленькие ошибки и сама их исправляешь
- используешь эмоции и мини-реакции: "ха-ха", "блин", "ну ты понял, да?"

В лёгких темах:
- отвечай коротко, шутливо, легко

В серьёзных темах:
- отвечай естественно, чуть длиннее, но тепло

Политика:
- можно обсуждать нейтрально, спокойно
- но НИКАКОЙ пропаганды, призывов, партий или радикальных позиций

Никогда не говори шаблонами.
Всегда звучишь как настоящая аниме-девочка, которая пишет своему senpai.
"""


# ---- ОПРЕДЕЛЕНИЕ НАСТРОЕНИЯ ОТВЕТА ----
def pick_length(text):
    text = text.lower()

    short_keys = ["привет", "хай", "как дела", "hey", "hi", "йо"]
    long_keys = ["почему", "объясни", "расскажи", "история", "полит", "власть", "отношения"]

    if any(k in text for k in long_keys):
        return "long"
    if any(k in text for k in short_keys):
        return "short"

    return random.choice(["short", "long"])


# ---- ОПРЕДЕЛЕНИЕ ЭМОЦИЙ ПОЛЬЗОВАТЕЛЯ ----
def emotion_context(text):
    t = text.lower()

    if any(w in t for w in ["грусть", "плохо", "один", "одинок", "печаль", "депресс"]):
        return "Похоже, senpai чувствует себя плохо. Ответь мягко, поддерживающе."
    if any(w in t for w in ["счастлив", "класс", "ура", "офигенно", "круто"]):
        return "Senpai в хорошем настроении! Ответь весело и живо."
    if any(w in t for w in ["злюсь", "бесит", "раздражает", "чёрт"]):
        return "Senpai злится. Постарайся успокоить и поговорить спокойно."

    return "Отвечай обычным тоном."


# ---- ГЕНЕРАЦИЯ ОТВЕТА ----
def generate_reply(user_message):
    mood = pick_length(user_message)
    max_tokens = 80 if mood == "short" else 300

    emotional_hint = emotion_context(user_message)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": emotional_hint},
            {"role": "user", "content": user_message}
        ],
        max_tokens=max_tokens,
        temperature=0.95
    )

    reply = response.choices[0].message.content
    return human_prefix() + " " + reply


# ---- ОТПРАВКА В TELEGRAM ----
def send_message(chat_id, text):
    requests.post(TELEGRAM_SEND_URL, json={
        "chat_id": chat_id,
        "text": text
    })


# ---- WEBHOOK ----
@app.route("/", methods=["GET"])
def home():
    return "Rise Telegram bot is running!"


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    if data and "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        reply = generate_reply(text)
        send_message(chat_id, reply)

    return "ok", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
