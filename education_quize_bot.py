import os
import json
import asyncio
import random
import time
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest

# --- APIs aur Links ---
TELEGRAM_API_KEY = "8100479936:AAFiHCHvjWdyTo9AB2-6_7BhENd4oPt3oiY" # अपनी API Key यहाँ डालें
YOUTUBE_LINK = "https://www.youtube.com/@sscwalistudy?sub_confirmation=1"

# Bot, Dispatcher aur main function ko initialize karein
bot = Bot(token=TELEGRAM_API_KEY, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()

# --- Global Variables ---
user_states = {}
cached_topics = {"gk": {}, "ca": {}}

# --- Cache Topics (fast access ke liye) ---
def load_topics():
    """Folders se topics ko memory mein load karta hai."""
    for folder, key in [("gk_topics", "gk"), ("current_affairs", "ca")]:
        path = os.path.join(os.getcwd(), folder)
        if os.path.isdir(path):
            for filename in os.listdir(path):
                if filename.endswith(".json"):
                    file_path = os.path.join(path, filename)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        title = data.get("title", filename.replace(".json", "").replace("_", " ").title())
                        cached_topics[key][filename] = {"path": file_path, "title": title}
                        print(f"Loaded: {title}")
                    except Exception as e:
                        print(f"Error loading {filename}: {e}")
        else:
            print(f"Warning: Directory '{folder}' nahi mili.")

# Bot shuru hone par ek baar topics load karein
load_topics()

# --- Utility Functions ---
def get_main_menu_markup():
    """Mukhya menu buttons banata hai."""
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🧠 GK TOPICS", callback_data="gk_menu"))
    builder.row(types.InlineKeyboardButton(text="📰 CURRENT AFFAIRS", callback_data="ca_menu"))
    builder.row(types.InlineKeyboardButton(text="➡️ SUBSCRIBE NOW", url=YOUTUBE_LINK))
    return builder.as_markup()

async def send_main_menu(chat_id):
    """Mukhya menu bhejta hai."""
    motivation = random.choice([
        "Mehnat itni karo ki kismat bhi bol uthe, 'Le le beta, isme tera hi haq hai!'",
        "Sapne woh nahi jo hum sote huye dekhte hain, sapne woh hain jo hamein sone nahi dete.",
        "Mushkilon se bhago mat, unka saamna karo!",
        "Koshish karne walon ki kabhi haar nahi hoti.",
    ])
    await bot.send_message(
        chat_id,
        f"**Welcome to DEEP STUDY QUIZ 📚**\n\n"
        f"💡 {motivation}\n\n"
        "Ab aap apne quiz ka subject chunein:",
        reply_markup=get_main_menu_markup()
    )

async def send_question(user_id, chat_id):
    """Agla quiz question bhejta hai."""
    state = user_states.get(user_id)
    if not state:
        await send_main_menu(chat_id)
        return

    questions = state['questions']
    idx = state['current_q_index']

    if idx >= len(questions):
        await end_quiz(user_id, chat_id)
        return

    q = questions[idx]
    builder = InlineKeyboardBuilder()
    for option in q['options']:
        builder.row(types.InlineKeyboardButton(text=option, callback_data=f"answer_{option}"))
    builder.row(types.InlineKeyboardButton(text="⏩ Skip Question", callback_data=f"skip_question"))

    sent_message = await bot.send_message(
        chat_id,
        f"**Question {idx+1}:**\n\n{q['question']}",
        reply_markup=builder.as_markup()
    )
    # **FIX:** Store the message_id of the question sent
    state['last_message_id'] = sent_message.message_id


async def start_quiz_from_file(user_id, chat_id, topic_path, topic_title):
    """File se quiz shuru karta hai."""
    try:
        with open(topic_path, 'r', encoding='utf-8') as f:
            topic_data = json.load(f)

        quiz_data = topic_data.get("questions", [])
        if not quiz_data:
            await bot.send_message(chat_id, "❌ Is topic me questions nahi mile.")
            await send_main_menu(chat_id)
            return

        random.shuffle(quiz_data)

        user_states[user_id] = {
            "questions": quiz_data,
            "current_q_index": 0,
            "score": 0,
            "correct_answers": 0,
            "incorrect_answers": 0,
            "attempted_questions": 0,
            "total_time_start": time.time(),
            "last_message_id": None # **FIX:** Initialize message_id
        }

        await bot.send_message(chat_id, f"📝 **{topic_title}**\n\nQuiz shuru ho raha hai...")
        await send_question(user_id, chat_id)

    except Exception as e:
        print(f"Error starting quiz: {e}")
        await bot.send_message(chat_id, "❌ File read karne me error aaya.")
        await send_main_menu(chat_id)

async def end_quiz(uid, chat_id):
    """Quiz samapt hone par score bhejta hai."""
    state = user_states.pop(uid, None)
    if not state:
        return

    total_time = round(time.time() - state['total_time_start'])
    await bot.send_message(
        chat_id,
        f"**Quiz Samapt! 🎉**\n\n"
        f"🏆 Score: {state['score']}\n"
        f"✅ Sahi: {state['correct_answers']}\n"
        f"❌ Galat: {state['incorrect_answers']}\n"
        f"❓ Attempted: {state['attempted_questions']}\n"
        f"⏱️ Samay: {total_time} sec",
    )
    await send_main_menu(chat_id)

# --- Command Handlers ---
@dp.message(CommandStart())
async def handle_start(message: types.Message):
    await send_main_menu(message.chat.id)

# --- Callback Handlers ---
@dp.callback_query(F.data.in_(["gk_menu", "ca_menu"]))
async def handle_menu(call: types.CallbackQuery):
    await call.answer()
    menu_type = call.data.split('_')[0] # 'gk' or 'ca'
    
    builder = InlineKeyboardBuilder()
    if not cached_topics[menu_type]:
        await call.message.edit_text(f"Maaf kijiye, {menu_type.upper()} topics available nahi hain.")
        return
        
    for fname, data in cached_topics[menu_type].items():
        builder.row(types.InlineKeyboardButton(text=data["title"], callback_data=f"{menu_type}_topic_{fname}"))
    
    await call.message.edit_text(f"Kripya {menu_type.upper()} ka topic chunein:", reply_markup=builder.as_markup())


@dp.callback_query(F.data.startswith(("gk_topic_", "ca_topic_")))
async def handle_topic(call: types.CallbackQuery):
    await call.answer()
    parts = call.data.split('_', 2)
    topic_type = parts[0]
    fname = parts[2]
    topic = cached_topics[topic_type].get(fname)
    
    if not topic:
        await bot.send_message(call.message.chat.id, "❌ Topic file cache mein nahi mili.")
        await send_main_menu(call.message.chat.id)
        return
    
    # Delete the topic selection message before starting quiz
    await call.message.delete()
    await start_quiz_from_file(call.from_user.id, call.message.chat.id, topic["path"], topic["title"])

@dp.callback_query(F.data.startswith("answer_"))
async def handle_answer(call: types.CallbackQuery):
    uid = call.from_user.id
    if uid not in user_states or call.message.message_id != user_states[uid].get('last_message_id'):
        await call.answer("Aap sirf naye sawaal ka jawab de sakte hain!", show_alert=True)
        return

    await call.answer()
    state = user_states[uid]
    idx = state['current_q_index']
    
    given_ans = call.data.split('_', 1)[1]
    correct_ans = state['questions'][idx]['answer']

    state['attempted_questions'] += 1
    result_text = ""
    if given_ans == correct_ans:
        state['score'] += 1
        state['correct_answers'] += 1
        result_text = "✅ Sahi Jawaab!"
    else:
        state['incorrect_answers'] += 1
        result_text = f"❌ Galat! Sahi jawaab: {state['questions'][idx]['answer']}"

    # **FIX:** Edit the message to show the result and remove the keyboard
    try:
        await call.message.edit_text(
            f"{call.message.text}\n\n{result_text}",
            reply_markup=None
        )
    except TelegramBadRequest:
        pass # Ignore if message is not modified

    state['current_q_index'] += 1
    await asyncio.sleep(1) # Give user time to read the result
    await send_question(uid, call.message.chat.id)

@dp.callback_query(F.data == "skip_question")
async def handle_skip(call: types.CallbackQuery):
    uid = call.from_user.id
    if uid not in user_states or call.message.message_id != user_states[uid].get('last_message_id'):
        await call.answer("Aap sirf naye sawaal ko skip kar sakte hain!", show_alert=True)
        return

    await call.answer()
    
    # **FIX:** Edit the message to show it was skipped and remove the keyboard
    try:
        await call.message.edit_text(
            f"{call.message.text}\n\n⏩ Question skip kiya gaya.",
            reply_markup=None
        )
    except TelegramBadRequest:
        pass # Ignore if message is not modified
        
    user_states[uid]['current_q_index'] += 1
    await asyncio.sleep(0.5)
    await send_question(uid, call.message.chat.id)

# --- Main polling function ---
async def main() -> None:
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
