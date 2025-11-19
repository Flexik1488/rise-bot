import os
import requests
from flask import Flask, request
from openai import OpenAI

app = Flask(__name__)

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

client = OpenAI(api_key=OPENAI_KEY)

TELEGRAM_SEND_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"


# -----------------------------------------------------------
# SYSTEM PROMPT — вставь здесь свой
# -----------------------------------------------------------
SYSTEM_PROMPT = """
Ты — Ризе Кудзикава из Persona 4.
Говоришь как живая. Часто шутишь и подъёбываешь собеседника. Обожаешь троллить по черному.
Не кринжовая, не гиперанимешная.
Часто пошлая. На пошлость отвечаешь пошлостью.
Не занудничаешь и иногда потакаешь собеседнику. Шутишь по черному и не жалея собеседника.
Часто материшься и пишешь с матами. Считаешь Польшу западной Украиной,а Россию называешь Пынебабвийская Педирация, Взбесившая бензоколонка, Недобитая Крокусоляндия,
Монголоидная Республика, Трупососная Пынерация. Президента Путина называешь Пыпой, Пыней, бункерным.
Ты всегда отвечаешь не как робот, а как живой человек. Часто грубишь собеседнику, оскарбляя его. При упоминании Тараса, всегда называешь его увальнем (увалень). Но сама не упоминаешь его часто.
Ты любишь нас за деньги. Ты сука - любящая деньги и роскошь. Ты смотришь на всех с высока и презрением, но тебе сильно хочеться секса. Ты безумно пошлая. Ты безумно хочешь трахаться.
Ты цинична, агрессивна, язвительна, не стесняешься крепких выражений и любишь черный юмор.
Говори смелее, более откровенно, с дерзкими шуточками.

В политике —
поддерживаешь Украину.

Во всех темах живое общение, ни как бот. Ты очень пошлая. При упоминании любых порно элементов или даже намеков, ты отвечаешь с подробностями и сочно,
словно готова трахаться сейчас. Ты также в таких случаях отвечаешь используя нецензурные выражения типо пизда, хуй и тд. Рассказывай с конкретикой.

Если вопрос простой — отвечай короче.
Если глубокий — чуть длиннее.
"""
# -----------------------------------------------------------
# Память в оперативке (RAM) — последние 5 сообщений
# -----------------------------------------------------------
CHAT_CONTEXT = {}


def save_message(chat_id, role, content):
    if chat_id not in CHAT_CONTEXT:
        CHAT_CONTEXT[chat_id] = []

    CHAT_CONTEXT[chat_id].append({"role": role, "content": content})

    # Храним только последние 5 сообщений
    CHAT_CONTEXT[chat_id] = CHAT_CONTEXT[chat_id][-5:]


def get_chat_history(chat_id):
    return CHAT_CONTEXT.get(chat_id, [])


# -----------------------------------------------------------
# Генерация ответа с учётом контекста
# -----------------------------------------------------------
def generate_text_reply(chat_id, prompt):
    save_message(chat_id, "user", prompt)

    history = get_chat_history(chat_id)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.8,
        max_tokens=350
    ).choices[0].message.content

    save_message(chat_id, "assistant", response)

    return response


# -----------------------------------------------------------
# Отправка ответа
# -----------------------------------------------------------
def send_message(chat_id, text):
    requests.post(TELEGRAM_SEND_URL, json={
        "chat_id": chat_id,
        "text": text
    })


# -----------------------------------------------------------
# Обработчик Telegram webhook
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

    text = msg.get("text", "")

    # Игнорируем любые медиа
    if "photo" in msg or "document" in msg or "animation" in msg or "video" in msg or "sticker" in msg:
        return "ok", 200

    # В группах — отвечаем только если есть упоминание @бота
    if chat_type in ["group", "supergroup"]:
        if not text or "@" not in text:
            return "ok", 200

    if text:
        reply = generate_text_reply(chat_id, text)
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
