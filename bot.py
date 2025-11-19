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
TELEGRAM_FILE_URL = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/"

SYSTEM_PROMPT = """
Ты — Ризе Кудзикава. Говоришь естественно, тепло и человечно.
Никакого кринжа, слишком "анимешного" стиля тоже избегай.
Ты милая, живая, но реалистичная версия персонажа.
Если репост, медиа, гиф, стикер — реагируй как человек.
В политике — нейтрально, аналитично, без агитации.
"""


def download_file(file_id):
    """
    Загружает файл Telegram (голос, видео и т.д.) по file_id.
    """
    info = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}").json()
    if "result" not in info:
        return None

    file_path = info["result"]["file_path"]
    url = TELEGRAM_FILE_URL + file_path

    return requests.get(url).content


def transcribe_voice(file_id):
    """
    Распознаёт голос через OpenAI Whisper.
    """
    audio_data = download_file(file_id)
    if not audio_data:
        return None

    with open("voice.ogg", "wb") as f:
        f.write(audio_data)

    with open("voice.ogg", "rb") as f:
        transcript = client.audio.transcriptions.create(
            model="gpt-4o-mini-tts",
            file=f
        )

    return transcript.text


def extract_message_text(msg):
    """
    Универсальная функция: превращает любое сообщение
    (репост, гиф, фото, видео, голос) в текстовый запрос.
    """

    # 1. Обычный текст
    if "text" in msg:
        return msg["text"]

    # 2. Репост
    if "forward_origin" in msg:
        origin = msg["forward_origin"]
        return f"(Репост контента: {origin.get('type', 'unknown')})"

    # 3. Стикеры
    if "sticker" in msg:
        emoji = msg["sticker"].get("emoji", "стикер")
        return f"(Стикер: {emoji})"

    # 4. GIF (animation)
    if "animation" in msg:
        return "(Пользователь отправил гифку)"

    # 5. Фото
    if "photo" in msg:
        return "(Пользователь отправил фото)"

    # 6. Видео
    if "video" in msg:
        return "(Пользователь отправил видео)"

    # 7. Голос
    if "voice" in msg:
        text = transcribe_voice(msg["voice"]["file_id"])
        if text:
            return f"(распознанный голос): {text}"
        return "(голосовое сообщение, не удалось распознать)"

    return "(неизвестное сообщение)"


def generate_reply(user_message):
    """
    ChatGPT-ответ, адаптированный под стиль Ризе.
    """

    max_tokens = 200

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ],
        max_tokens=max_tokens,
        temperature=0.65
    )

    return response.choices[0].message.content


def send_message(chat_id, text):
    requests.post(TELEGRAM_SEND_URL, json={
        "chat_id": chat_id,
        "text": text
    })


@app.route("/", methods=["GET"])
def home():
    return "Rise Telegram bot is running!"


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    if not data or "message" not in data:
        return "ok"

    msg = data["message"]
    chat_id = msg["chat"]["id"]

    # Получаем универсальный текст сообщения
    user_text = extract_message_text(msg)

    reply = generate_reply(user_text)
    send_message(chat_id, reply)

    return "ok", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
