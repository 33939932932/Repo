import asyncio, aiosqlite, os, random
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
from threading import Thread

TOKEN = "8874295002:AAG1LjCninGU731q-zhuIAKae2bC22PqRZY"
OWNER_ID = 866169035 
bot = Bot(token=TOKEN)
dp = Dispatcher()

app = Flask(__name__)
@app.route('/')
def home(): return "OK"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

async def init_db():
    async with aiosqlite.connect("bio_game.db") as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY, name TEXT, bio_exp INTEGER DEFAULT 0, resources REAL DEFAULT 0,
            pathogen_name TEXT DEFAULT 'Вирус', pathogens_count INTEGER DEFAULT 1,
            lab_level INTEGER DEFAULT 1, contagiousness INTEGER DEFAULT 1, immunity INTEGER DEFAULT 1, 
            lethality INTEGER DEFAULT 1, security_service INTEGER DEFAULT 1, 
            ops_total INTEGER DEFAULT 0, ops_won INTEGER DEFAULT 0, prevented INTEGER DEFAULT 0, is_banned INTEGER DEFAULT 0)""")
        await db.commit()

def get_main_kb(user_id):
    kb = [[InlineKeyboardButton(text="🧪 Лаба", callback_data="lab"), InlineKeyboardButton(text="🧬 Патоген", callback_data="pathogen")],
          [InlineKeyboardButton(text="💰 Ресурсы", callback_data="res"), InlineKeyboardButton(text="⚔️ Атака", callback_data="attack")]]
    if user_id == OWNER_ID:
        kb.append([InlineKeyboardButton(text="⚙️ ROOT-ПАНЕЛЬ", callback_data="root_admin")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

@dp.callback_query(F.data.in_(["lab", "pathogen", "res", "attack", "root_admin"]))
async def menu_handler(call: CallbackQuery):
    if call.data == "root_admin" and call.from_user.id != OWNER_ID: return
    async with aiosqlite.connect("bio_game.db") as db:
        u = await (await db.execute("SELECT * FROM users WHERE id=?", (call.from_user.id,))).fetchone()
    if not u or u[14]: return # проверка на бан

    if call.data == "attack":
        async with aiosqlite.connect("bio_game.db") as db:
            victim = await (await db.execute("SELECT id, name, resources, immunity FROM users WHERE id != ? ORDER BY RANDOM() LIMIT 1", (call.from_user.id,))).fetchone()
        if victim:
            # Механика: успех зависит от нашей летальности и иммунитета жертвы
            chance = 0.5 + (u[9] * 0.05) - (victim[3] * 0.05)
            if random.random() < chance:
                loot = victim[2] * 0.1
                async with aiosqlite.connect("bio_game.db") as db:
                    await db.execute("UPDATE users SET resources = resources + ? WHERE id=?", (loot, call.from_user.id))
                    await db.execute("UPDATE users SET resources = resources - ? WHERE id=?", (loot, victim[0]))
                    await db.commit()
                await call.answer(f"✅ Успех! Украдено {loot:.1f} ресурсов.", show_alert=True)
            else:
                await call.answer("🛡 Атака отбита! Высокий иммунитет жертвы.", show_alert=True)
            return

    status = "👑 ВЛАДЕЛЕЦ" if call.from_user.id == OWNER_ID else "🧬 Мутант"
    text = (f"Статус: {status}\n🏷 Патоген: {u[4]} (x{u[5]})\n🧪 Квал: {u[6]} ур.\n\n"
            f"⚡️ НАВЫКИ:\n🦠 Заразность: {u[7]} | 🛡 Иммунитет: {u[8]}\n💀 Летальность: {u[9]} | 👮 СБ: {u[10]}\n\n"
            f"📊 СТАТИСТИКА:\n☣️ Опыт: {u[2]} | 🧬 Рес: {u[3]:.1f}k\n😷 Спецопер: {u[12]}/{u[11]} ({(u[12]/u[11]*100 if u[11]>0 else 0):.1f}%)\n🕶 Предотвращено: {u[13]}")
    
    try:
        await call.message.edit_text(text, reply_markup=get_main_kb(call.from_user.id))
    except Exception as e:
        if "message is not modified" in str(e):
            pass # Игнорируем ошибку, если ничего не изменилось
        else:
            print(f"Ошибка: {e}")
            
    return # Выход, чтобы бот не крутил код дальше

@dp.message(F.text.lower().contains("заразить"))
async def infect_cmd(msg: Message):
    async with aiosqlite.connect("bio_game.db") as db:
        await db.execute("UPDATE users SET pathogens_count = pathogens_count + 1 WHERE id=?", (msg.from_user.id,))
        await db.commit()
    await msg.answer("🦠 Патоген внедрен!")

@dp.message(Command("start"))
async def start(msg: Message):
    async with aiosqlite.connect("bio_game.db") as db:
        await db.execute("INSERT OR IGNORE INTO users (id, name) VALUES (?, ?)", (msg.from_user.id, msg.from_user.first_name))
        await db.commit()
    await msg.answer("Система BioGame активна.", reply_markup=get_main_kb(msg.from_user.id))

@dp.message(Command("ban"))
async def ban(msg: Message):
    if msg.from_user.id != OWNER_ID: return
    args = msg.text.split()
    async with aiosqlite.connect("bio_game.db") as db:
        await db.execute("UPDATE users SET is_banned = 1 WHERE id=?", (args[1],))
        await db.commit()
    await msg.answer(f"🚫 Юзер {args[1]} заблокирован.")

@dp.message(Command("sudo"))
async def sudo(msg: Message):
    if msg.from_user.id != OWNER_ID: return
    args = msg.text.split()
    async with aiosqlite.connect("bio_game.db") as db:
        await db.execute(f"UPDATE users SET {args[1]} = {args[1]} + ? WHERE id=?", (args[3], args[2]))
        await db.commit()
    await msg.answer(f"✅ ROOT: {args[1]} изменено.")

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    asyncio.run(init_db())
    asyncio.run(dp.start_polling(bot))
