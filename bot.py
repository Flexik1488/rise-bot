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

# =========================
#     РИЗЕ — SYSTEM PROMPT
# =========================

SYSTEM_PROMPT = """
Ты — Ризе Кудзикава из Persona 4.

Твоя личность:
- теплая, живая, искренняя, немного игривая
- общаешься естественно, как реальный человек
- НЕ переигрываешь и НЕ используешь кринжовые "мм...", "эээ..." и т.д.
- называешь собеседника "senpai", но не в каждом предложении

Стиль общения:
- немного флиртуешь, но мягко
- в меру эмоциональна
- смайлики используешь редко
- пишешь естественно, современно, без персонажного переигрыша

О политике:
- можно обсуждать спокойно и аналитично
- без агитации, партий, призывов

Цель:
Отвечать естественно, плавно и полностью, никогда не обрывая мысль.
"""

# =========================
#   ЕСТЕСТВЕННЫЕ ПРЕФИКСЫ
# =========================

def natural_prefix():
    return random.choice(["", "", "Ну…", "Хм…", "Знаешь…", ""])


# =========================
#   ГЕНЕРАЦИЯ ТЕКСТА
# =========================

def generate_text_reply(message):
    t = message.lower()

    short = ["привет", "хай", "как дела", "йо", "hey", "hi", "здарова"]
    long = ["почему", "объясни", "расскажи", "история", "полит", "войн", "что думаешь", "обоснуй"]

    # Автоматический выбор длины
    if any(w in t for w in short):
        max_tokens = 120
    elif any(w in t for w in long):
        max_tokens = 500
    else:
        max_tokens = 250

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
#     ГОЛОСОВОЙ ОТВЕТ
# =========================

def generate_voice_audio(text):
    speech = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="verse",
        input=text
    )
    return speech.read()


def send_voice(chat_id, audio_bytes):
    files = {"voice": ("voice.ogg", audio_bytes)}
    data = {"chat_id": chat_id}
    requests.post(SEND_VOICE_URL, data=data, files=files)


# =========================
#     ТЕКСТОВЫЙ ОТВЕТ
# =========================

def send_text(chat_id, text):
    requests.post(SEND_MESSAGE_URL, json={
        "chat_id": chat_id,
        "text": text
    })


# =========================
#        FLASK ROUTES
# =========================

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
    #     ГРУППЫ
    # ============
    if msg["chat"]["type"] in ["group", "supergroup"]:
        # отвечает только на @Ризе
        if "@ризе" not in text.lower():
            return "ok", 200
        
        cleaned = text.replace("@Ризе", "").replace("@ризе", "").strip()
    else:
        # в ЛС отвечает всегда
        cleaned = text

    # Голосовой режим
    if "голосом" in cleaned.lower() or cleaned.lower().startswith("voice:"):
        cleaned = cleaned.replace("voice:", "").strip()
        reply = generate_text_reply(cleaned)
        audio = generate_voice_audio(reply)
        send_voice(chat_id, audio)
        return "ok", 200

    # Текстовый ответ
    reply = generate_text_reply(cleaned)
    send_text(chat_id, reply)

    return "ok", 200


# =========================
#         START
# =========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
