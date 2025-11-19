import os
import random
import requests
from io import BytesIO
from flask import Flask, request
from openai import OpenAI
from PIL import Image, ImageSequence

app = Flask(__name__)

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

client = OpenAI(api_key=OPENAI_KEY)

TELEGRAM_SEND_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
TELEGRAM_FILE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile"
TELEGRAM_FILE_DL = "https://api.telegram.org/file/bot{}/{}"


# -----------------------------------------------------------
# SYSTEM PROMPT — естественный стиль, живой, но не кринж
# -----------------------------------------------------------
SYSTEM_PROMPT = """
Ты — Ризе Кудзикава из Persona 4.
Характер: живая, дружелюбная, немного флиртующая, но естественная, без кринжа.
Говоришь как нормальная девушка, а не как робот или чиби-персонаж.
Ты можешь шутить, быть ироничной, тёплой, спокойной.

В политике:
- обсуждаешь темы нейтрально, осторожно, спокойно
- без агитации, пропаганды, призывов

Если вопрос бытовой — отвечай легко и непринуждённо.
Если глубокий — отвечай чуть длиннее и вдумчивее.
"""


# -----------------------------------------------------------
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# -----------------------------------------------------------

def send_message(chat_id, text):
    requests.post(TELEGRAM_SEND_URL, json={
        "chat_id": chat_id,
        "text": text
    })


def download_telegram_file(file_id):
    """Скачивание файла с Telegram"""
    r = requests.get(TELEGRAM_FILE_URL.format(TELEGRAM_TOKEN), params={"file_id": file_id})
    path = r.json()["result"]["file_path"]

    file_url = TELEGRAM_FILE_DL.format(TELEGRAM_TOKEN, path)
    return requests.get(file_url).content


def safe_extract_frame(file_bytes):
    """
    Безопасное извлечение изображения:
    - фото: возвращает PNG
    - GIF: извлекает первый кадр
    - если файл не картинка → возвращает None
    """
    try:
        img = Image.open(BytesIO(file_bytes))

        # GIF
        if getattr(img, "is_animated", False):
            frame = next(ImageSequence.Iterator(img))
            output = BytesIO()
            frame.save(output, format="PNG")
            return output.getvalue()

        # Обычная картинка
        output = BytesIO()
        img.save(output, format="PNG")
        return output.getvalue()

    except Exception:
        return None


# -----------------------------------------------------------
# AI текстовый ответ
# -----------------------------------------------------------
def generate_text_reply(prompt):
    """Текстовый ответ модели"""
    return client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0.8,
        max_tokens=300
    ).choices[0].message.content


# -----------------------------------------------------------
# AI анализ изображения
# -----------------------------------------------------------
def analyze_image(image_bytes):
    """Vision анализ картинки"""
    base64_image = base64.b64encode(image_bytes).decode("utf-8")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Ты анализируешь изображение и описываешь его естественно, без кринжа."},
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "Что изображено на картинке? Ответь естественно."},
                    {"type": "input_image", "image_url": f"data:image/png;base64,{base64_image}"}
                ]
            },
        ],
        max_tokens=200,
    )

    return response.choices[0].message.content


# ===========================================================
#                     WEBHOOK
# ===========================================================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if not data:
        return "ok", 200

    msg = data.get("message", {})
    chat_id = msg.get("chat", {}).get("id")

    # -------------------------------------------
    # 1. Определяем текст
    # -------------------------------------------
    text = msg.get("text", "")

    # В группе — отвечаем только при упоминании
    if msg.get("chat", {}).get("type") in ["group", "supergroup"]:
        if not text or ("@" not in text):
            return "ok", 200

    # -------------------------------------------
    # 2. Фото
    # -------------------------------------------
    if "photo" in msg:
        file_id = msg["photo"][-1]["file_id"]
        content = download_telegram_file(file_id)

        safe_img = safe_extract_frame(content)

        if safe_img:
            reply = analyze_image(safe_img)
        else:
            reply = "Я не смогла прочитать изображение, опиши его словами, senpai."

        send_message(chat_id, reply)
        return "ok", 200

    # -------------------------------------------
    # 3. Документы (GIF / PNG / JPEG / MP4)
    # -------------------------------------------
    if "document" in msg:
        mime = msg["document"].get("mime_type", "")
        file_id = msg["document"]["file_id"]

        content = download_telegram_file(file_id)

        safe_img = safe_extract_frame(content)

        if safe_img:
            reply = analyze_image(safe_img)
        else:
            reply = "Хм… кажется, это не картинка. Но если расскажешь, что там — я разберусь!"

        send_message(chat_id, reply)
        return "ok", 200

    # -------------------------------------------
    # 4. Пересланные сообщения
    # -------------------------------------------
    if "forward_origin" in msg:
        if "caption" in msg:
            reply = generate_text_reply(msg["caption"])
            send_message(chat_id, reply)
            return "ok", 200

    # -------------------------------------------
    # 5. Обычный текст
    # -------------------------------------------
    if text:
        reply = generate_text_reply(text)
        send_message(chat_id, reply)

    return "ok", 200


@app.route("/")
def home():
    return "Bot is running!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
