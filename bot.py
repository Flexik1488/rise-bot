import os
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from openai import OpenAI
import random

app = Flask(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_KEY)

SYSTEM_PROMPT = """
Ты — Ризе Кудзикава из Persona 4. 
Твой стиль: энергичная, милая, болтливая, немного флиртующая, всегда дружелюбная. 
Называй собеседника "senpai". 
Отвечай эмоционально, живо, по-анимэшному.

Ты можешь:
- говорить о любых темах (игры, музыка, отношения, политика, соц. темы и т.п.)
- обсуждать политические вопросы в нейтральном, спокойном, рассуждающем тоне
- НО не занимай **пропагандистскую позицию**, не призывай к голосованию, протестам, партиям
- можно шутить и высказывать мнения персонажа, но не превращать это в агитацию

Если вопрос лёгкий → отвечай покороче.
Если вопрос серьёзный → отвечай длиннее и более вдумчиво.
"""

async def generate_reply(text):
    # Определяем длину ответа
    short_triggers = ["привет", "хай", "как дела", "hey", "hi", "yo"]
    long_triggers = ["почему", "объясни", "расскажи", "история", "полит", "правитель", "власть"]

    # Вероятностное "настроение" Ризе
    mood = random.choice(["short", "long"])

    # Ситуативная логика
    t = text.lower()

    if any(k in t for k in short_triggers):
        mood = "short"
    if any(k in t for k in long_triggers):
        mood = "long"

    max_tokens = 80 if mood == "short" else 300

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text}
        ],
        max_tokens=max_tokens,
        temperature=0.9
    )
    
    return response.choices[0].message.content


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user_text = update.message.text
    reply = await generate_reply(user_text)
    await update.message.reply_text(reply)


application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))


@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "ok"


@app.route("/")
def home():
    return "Bot is online and working!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
