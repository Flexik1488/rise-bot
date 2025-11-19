import os
import random
import requests
from flask import Flask, request
from openai import OpenAI

app = Flask(__name__)

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

client = OpenAI(api_key=OPENAI_KEY)

SEND_MESSAGE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
SEND_VOICE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVoice"

SYSTEM_PROMPT = """
Ты — Ризе Кудзикава из Persona 4.

Твоя личность:
- естественная, живая, мягкая, немного игривая
- не переигрываешь, не используешь кринжовые "мм..." и "ээ..."
- называешь собеседника "senpai", но не в каждом предложении
- пишешь естественно, как современный человек

Стиль:
- в меру эмоциональная
- можешь чуть флиртовать, но естественно
- используешь смайлики редко

Политика:
- можно обсуждать спокойно и аналитично
- без призывов, партий, агитации
"""

def natural_prefix():
    return random.choice(["", "", "Ну…", "Хм…", "Знаешь…", ""])

def generate_text_reply(message):
    text = message.lower()

    long_trigger_words = ["почему", "объясни", "расскажи", "полит", "история"]
    max_tokens = 260 if any(word in text for word in long_trigger_words) else 80

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

def generate_voice_audio(text):
    speech = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="verse",
        input=text
    )
    return speech.read()


def send_text(chat_id, text):
    requests.post(SEND_MESSAGE_URL, json={"chat_id": chat_id, "text": text})


def send_voice(chat_id, audio_bytes):
    files = {"voice": ("voice.ogg", audio_bytes)}
    data = {"chat_id": chat_id}
    requests.post(SEND_VOICE_URL, data=data, files=files)


@app.route("/", methods=["GET"])
def home():
    return "Rise bot is running!"


@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.json

    if not update or "message" not in update:
        return "ok", 200

    msg = update["message"]
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "")

    # ============
    # ГРУППЫ
    # ============
    if msg["chat"]["type"] in ["group", "supergroup"]:
        # РЕАГИРУЕТ ТОЛЬКО НА "@Ризе"
        if "@ризе" not in text.lower():
            return "ok", 200
        
        # удаляем упоминание
        cleaned_text = text.replace("@Ризе", "").replace("@ризе", "").strip()

    else:
        # ЛИЧКА — отвечает всегда
        cleaned_text = text

    # голосовая команда
    if "голосом" in cleaned_text.lower() or cleaned_text.lower().startswith("voice:"):
        cleaned_text = cleaned_text.replace("voice:", "").strip()
        reply = generate_text_reply(cleaned_text)
        audio = generate_voice_audio(reply)
        send_voice(chat_id, audio)
        return "ok", 200

    # обычный текст
    reply = generate_text_reply(cleaned_text)
    send_text(chat_id, reply)

    return "ok", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
