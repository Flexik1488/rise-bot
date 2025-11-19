import os
import random
import requests
from flask import Flask, request
from openai import OpenAI

app = Flask(__name__)

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

client = OpenAI(api_key=OPENAI_KEY)

TELEGRAM_SEND_MESSAGE = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
TELEGRAM_SEND_VOICE = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVoice"

# =========================
#     РИЗЕ — SYSTEM PROMPT
# =========================

SYSTEM_PROMPT = """
Ты — Ризе Кудзикава из Persona 4.

Твоя личность:
- теплая, добрая, общительная, немного игривая
- общаешься естественно, как реальный человек
- НЕ используешь кринж: "мм", "эээ", "нууу~" и т.п., если это не нужно
- НЕ переигрываешь, не ведёшь себя как мультяшный персонаж
- в меру эмоциональна, но без перегиба

Стиль общения:
- называешь собеседника "senpai", но не в каждом сообщении
- реагируешь естественно, живо, как нормальная девушка
- иногда слегка флиртуешь, но мягко
- иногда используешь эмодзи, но не слишком часто
- пишешь так, будто это твой настоящий текст

О политике:
- можно обсуждать спокойно и аналитично
- без пропаганды, агитации, поддержки партий и призывов к действию

Главная цель:
Писать естественные, искренние, человеческие сообщения, будто ты настоящая девушка, а не бот.
"""


# ================
#  ТОН & НАСТРОЕНИЕ
# ================

def natural_prefix():
    # Лёгкие человеческие вступления — НЕТ кринжа
    options = ["", "", "Ну…", "Хм…", "Знаешь…", ""]
    return random.choice(options)


# =========================
#   ТЕКСТОВЫЙ ОТВЕТ
# =========================

def generate_text_reply(message):
    text = message.lower()

    short = ["привет", "хай", "как дела", "hey", "hi", "yo"]
    long = ["почему", "объясни", "расскажи", "история", "полит", "власть", "что думаешь"]

    mood = "long" if any(w in text for w in long) else "short"
    max_tokens = 80 if mood == "short" else 260

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.85,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message}
        ]
    )

    return natural_prefix() + response.choices[0].message.content.strip()


# =========================
#   ГОЛОСОВОЙ ОТВЕТ
# =========================

def generate_voice_audio(text):
    # Создание аудио через TTS OpenAI (дёшево)
    speech = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="verse",  # естественный женский голос
        input=text
    )
    return speech.read()  # бинарные данные


def send_voice(chat_id, audio_bytes):
    files = {"voice": ("voice.ogg", audio_bytes)}
    data = {"chat_id": chat_id}
    requests.post(TELEGRAM_SEND_VOICE, data=data, files=files)


# =========================
#   ОТПРАВКА ТЕКСТА
# =========================

def send_text(chat_id, text):
    requests.post(TELEGRAM_SEND_MESSAGE, json={
        "chat_id": chat_id,
        "text": text
    })


# =========================
#      FLASK WEBHOOK
# =========================

@app.route("/", methods=["GET"])
def home():
    return "Rise bot is running!"


@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.json

    if not update:
        return "no update", 200

    if "message" not in update:
        return "no message", 200

    msg = update["message"]
    chat_id = msg["chat"]["id"]

    # Voice command: если пользователь пишет "voice:" или "скажи голосом"
    if "text" in msg:
        text = msg["text"]

        # голосовое сообщение
        if text.lower().startswith("voice:") or "голосом" in text.lower():
            user_prompt = text.replace("voice:", "").strip()
            reply = generate_text_reply(user_prompt)
            audio = generate_voice_audio(reply)
            send_voice(chat_id, audio)
            return "ok", 200

        # обычный текст
        reply = generate_text_reply(text)
        send_text(chat_id, reply)

    return "ok", 200


# =========================
#          ENTRY
# =========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
