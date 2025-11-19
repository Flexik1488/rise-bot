import os
import random
import requests
from io import BytesIO
from PIL import Image
from flask import Flask, request
from openai import OpenAI

app = Flask(__name__)

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

client = OpenAI(api_key=OPENAI_KEY)

TELEGRAM_SEND_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
TELEGRAM_FILE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile"
TELEGRAM_FILE_DOWNLOAD = "https://api.telegram.org/file/bot{}/{}"


# -----------------------------
# SYSTEM PROMPT — естественная Ризе
# -----------------------------
SYSTEM_PROMPT = """
Ты — Ризе Кудзикава из Persona 4.
Говоришь естественно, тепло, живо, без кринжа.
Обращайся к собеседнику как "senpai" ненавязчиво.
Шути мягко, без переигрывания.

Если вопрос лёгкий — отвечай кратко.
Если серьёзный — отвечай чуть глубже.

Если присылают изображение, опиши спокойно, как человек.
"""


# ---------------------------------------------------
# Vision-анализ (1 кадр GIF/видео)
# ---------------------------------------------------
def analyze_image(image_bytes):
    img = Image.open(BytesIO(image_bytes))

    # Для GIF берём первый кадр (супер-экономия)
    if getattr(img, "is_animated", False):
        img.seek(0)

    img = img.convert("RGB")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    response = client.chat.completions.create(
        model="gpt-4o-mini-vision",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "input_image", "image": buf.getvalue()},
                    {"type": "text", "text": "Что на этом изображении? Ответь естественно."}
                ]
            }
        ],
        max_tokens=200,
        temperature=0.7
    )

    return response.choices[0].message.content


# ---------------------------------------------------
# Текстовый ответ
# ---------------------------------------------------
def generate_text_reply(user_message):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ],
        max_tokens=250,
        temperature=0.8
    )
    return response.choices[0].message.content


# ---------------------------------------------------
# Отправка сообщения
# ---------------------------------------------------
def send_message(chat_id, text):
    requests.post(TELEGRAM_SEND_URL, json={
        "chat_id": chat_id,
        "text": text
    })


# ---------------------------------------------------
# Скачивание файла из Telegram
# ---------------------------------------------------
def download_telegram_file(file_id):
    info = requests.get(TELEGRAM_FILE_URL, params={"file_id": file_id}).json()
    file_path = info["result"]["file_path"]
    url = TELEGRAM_FILE_DOWNLOAD.format(TELEGRAM_TOKEN, file_path)
    return requests.get(url).content


# ---------------------------------------------------
# Webhook (главный обработчик)
# ---------------------------------------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if not data or "message" not in data:
        return "ok", 200

    msg = data["message"]
    chat_id = msg["chat"]["id"]

    # ---------- Фото ----------
    if "photo" in msg:
        file_id = msg["photo"][-1]["file_id"]
        content = download_telegram_file(file_id)
        reply = analyze_image(content)
        send_message(chat_id, reply)
        return "ok", 200

    # ---------- GIF / video (как animation или video) ----------
    if "animation" in msg or "video" in msg:
        file_id = msg.get("animation", msg.get("video"))["file_id"]
        content = download_telegram_file(file_id)
        reply = analyze_image(content)
        send_message(chat_id, reply)
        return "ok", 200

    # ---------- Если GIF приходит как DOCUMENT ----------
    if "document" in msg:
        mime = msg["document"].get("mime_type", "")

        # GIF, видео или картинка, которые Telegram прислал как document
        if "gif" in mime or "video" in mime or "image" in mime:
            file_id = msg["document"]["file_id"]
            content = download_telegram_file(file_id)

            reply = analyze_image(content)
            send_message(chat_id, reply)
            return "ok", 200

    # ---------- Текст ----------
    if "text" in msg:
        text = msg["text"]
        reply = generate_text_reply(text)
        send_message(chat_id, reply)

    return "ok", 200


@app.route("/")
def home():
    return "Rise Telegram bot is running!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
