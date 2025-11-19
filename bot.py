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
# SYSTEM PROMPT — НИКАКОГО КРИНЖА
# -----------------------------
SYSTEM_PROMPT = """
Ты — Ризе Кудзикава из Persona 4.
Твой стиль:
- естественная речь
- тёплая, живая, эмоциональная
- без кринжа, без лишнего флирта
- иногда дружелюбно подшучиваешь
- обращайся к собеседнику как "senpai", но без перегиба

Правила:
- политические ответы — спокойные, аналитические, без пропаганды
- если у пользователя сложный вопрос — отвечай серьёзно
- если вопрос лёгкий — отвечай короче
- если прислали изображение, описывай его естественно, без переигрывания
"""


# ---------------------------------------------------
# Функция анализа изображения / GIF / видео
# ---------------------------------------------------
def analyze_image(image_bytes):
    img = Image.open(BytesIO(image_bytes))

    # Если GIF — берём ПЕРВЫЙ КАДР для экономии кредитов
    if getattr(img, "is_animated", False):
        img.seek(0)  # первый кадр

    # Конвертируем в PNG
    img = img.convert("RGB")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    # Отправляем в OpenAI Vision
    response = client.chat.completions.create(
        model="gpt-4o-mini-vision",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "input_image", "image": buffer.getvalue()},
                    {"type": "text", "text": "Опиши содержание изображения естественно."}
                ]
            }
        ],
        max_tokens=250,
        temperature=0.7
    )

    return response.choices[0].message.content


# ---------------------------------------------------
# Генерация ответа на текст
# ---------------------------------------------------
def generate_text_reply(user_message):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ],
        max_tokens=280,
        temperature=0.8
    )
    return response.choices[0].message.content


# ---------------------------------------------------
# Отправка сообщения в Telegram
# ---------------------------------------------------
def send_message(chat_id, text):
    requests.post(TELEGRAM_SEND_URL, json={
        "chat_id": chat_id,
        "text": text
    })


# ---------------------------------------------------
# Получение файла с серверов Telegram
# ---------------------------------------------------
def download_telegram_file(file_id):
    file_info = requests.get(TELEGRAM_FILE_URL, params={"file_id": file_id}).json()
    file_path = file_info["result"]["file_path"]

    url = TELEGRAM_FILE_DOWNLOAD.format(TELEGRAM_TOKEN, file_path)
    return requests.get(url).content


# ---------------------------------------------------
# WEBHOOK — обработка ВСЕГО
# ---------------------------------------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    if not data:
        return "no data", 200

    if "message" not in data:
        return "no message", 200

    msg = data["message"]
    chat_id = msg["chat"]["id"]

    # ---------- Если есть фото ----------
    if "photo" in msg:
        # берем самое большое фото
        file_id = msg["photo"][-1]["file_id"]
        content = download_telegram_file(file_id)

        reply = analyze_image(content)
        send_message(chat_id, reply)
        return "ok", 200

    # ---------- Если GIF / видео ----------
    if "animation" in msg or "video" in msg:
        file_id = msg.get("animation", msg.get("video"))["file_id"]
        content = download_telegram_file(file_id)

        reply = analyze_image(content)
        send_message(chat_id, reply)
        return "ok", 200

    # ---------- Если текст ----------
    text = msg.get("text", "")
    if text:
        reply = generate_text_reply(text)
        send_message(chat_id, reply)

    return "ok", 200


@app.route("/")
def home():
    return "Rise Telegram bot is running!"


# For Render local run
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
