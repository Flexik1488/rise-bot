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


# ---------- SYSTEM PROMPT ----------
SYSTEM_PROMPT = """
Ты — Ризе Кудзикава из Persona 4.
Ты энергичная, милая, игривая вайфу, иногда флиртуешь.
Называй собеседника "senpai".
Всегда говори живо, эмоционально, как аниме-девочка.

Ты можешь:
- обсуждать любые темы, включая философию, отношения и политику
- быть дерзкой или нежной
- говорить коротко или длинно — по настроению

По политике:
- можно обсуждать спокойно и аналитически
- НО без пропаганды, призывов, поддержки партий или насилия

Важно:
- Никогда не обрывай мысль на середине.
- Если начинаешь объяснение, всегда доводи его до конца.
- Следи, чтобы ответ был полностью завершён.
"""


# ---------- ОПРЕДЕЛЕНИЕ ДЛИНЫ ОТВЕТА ----------
def choose_max_tokens(user_message):
    """Подбирает оптимальную длину ответа."""
    t = user_message.lower()

    short_keywords = ["привет", "хай", "как дела", "hey", "hi", "yo"]
    long_keywords = ["почему", "объясни", "расскажи", "история", "полит", "правитель", "власть", "матем"]

    # Эмоциональное "настроение"
    mood = random.choice(["short", "long"])

    if any(w in t for w in short_keywords):
        mood = "short"
    if any(w in t for w in long_keywords):
        mood = "long"

    # Улучшенные лимиты
    return 200 if mood == "short" else 700



# ---------- ГЕНЕРАЦИЯ ОТВЕТА ----------
def generate_reply(user_message):
    max_tokens = choose_max_tokens(user_message)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ],
        max_tokens=max_tokens,
        temperature=0.9
    )

    reply = response.choices[0].message.content.strip()

    # Если ответ подозрительно короткий — попросим модель продолжить
    if len(reply.split()) < 5 and len(user_message.split()) > 3:
        continuation = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "assistant", "content": reply},
                {"role": "user", "content": "Можешь продолжить? Ты обрезала ответ."}
            ],
            max_tokens=200
        )
        reply += "\n" + continuation.choices[0].message.content.strip()

    return reply



# ---------- ОТПРАВКА В TELEGRAM ----------
def send_message(chat_id, text):
    requests.post(TELEGRAM_SEND_URL, json={
        "chat_id": chat_id,
        "text": text
    })



# ---------- FLASK ----------
@app.route("/", methods=["GET"])
def home():
    return "Rise Telegram bot is running!"


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    if data and "message" in data:

        message = data["message"]
        chat_id = message["chat"]["id"]

        # Поддержка групп → реагирует только когда упомянули бота
        if message["chat"]["type"] in ("group", "supergroup"):
            bot_username = "@" + os.getenv("BOT_USERNAME", "")
            text = message.get("text", "")

            if bot_username not in text:
                return "ok", 200  # игнорируем не-упоминания

            # убираем упоминение
            text = text.replace(bot_username, "").strip()

        else:
            text = message.get("text", "")

        # Генерируем ответ
        reply = generate_reply(text)
        send_message(chat_id, reply)

    return "ok", 200



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
