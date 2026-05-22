import asyncio, aiosqlite, os, random, logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
from threading import Thread

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получаем конфиг из переменных окружения
TOKEN = os.environ.get("BOT_TOKEN", "7890123456:ABCdefGHIjklmnoPQRstuvwxyz")
OWNER_ID = int(os.environ.get("OWNER_ID", "33939932932"))  # ID владельца из переменной окружения
PORT = int(os.environ.get("PORT", 10000))

bot = Bot(token=TOKEN)
dp = Dispatcher()

app = Flask(__name__)

@app.route('/')
def home():
    return "OK"

def run_flask():
    app.run(host='0.0.0.0', port=PORT)

async def init_db():
    """Инициализация базы данных"""
    try:
        async with aiosqlite.connect("bio_game.db") as db:
            await db.execute("""CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY, name TEXT, bio_exp INTEGER DEFAULT 0, resources REAL DEFAULT 0,
                pathogen_name TEXT DEFAULT 'Вирус', pathogens_count INTEGER DEFAULT 1,
                lab_level INTEGER DEFAULT 1, contagiousness INTEGER DEFAULT 1, immunity INTEGER DEFAULT 1, 
                lethality INTEGER DEFAULT 1, security_service INTEGER DEFAULT 1, 
                ops_total INTEGER DEFAULT 0, ops_won INTEGER DEFAULT 0, prevented INTEGER DEFAULT 0, is_banned INTEGER DEFAULT 0)""")
            await db.commit()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        raise

async def check_user_banned(user_id: int) -> bool:
    """Проверка, забанен ли пользователь"""
    try:
        async with aiosqlite.connect("bio_game.db") as db:
            result = await (await db.execute("SELECT is_banned FROM users WHERE id=?", (user_id,))).fetchone()
            return result[0] == 1 if result else False
    except Exception as e:
        logger.error(f"Error checking ban status for user {user_id}: {e}")
        return False

def is_owner(user_id: int) -> bool:
    """Проверка, является ли пользователь владельцем"""
    return user_id == OWNER_ID and OWNER_ID != 0

def get_main_kb(user_id):
    """Получить главную клавиатуру"""
    kb = [[InlineKeyboardButton(text="🧪 Лаба", callback_data="lab"), 
           InlineKeyboardButton(text="🧬 Патоген", callback_data="pathogen")],
          [InlineKeyboardButton(text="💰 Ресурсы", callback_data="res"), 
           InlineKeyboardButton(text="⚔️ Атака", callback_data="attack")]]
    if is_owner(user_id):
        kb.append([InlineKeyboardButton(text="⚙️ ROOT-ПАНЕЛЬ", callback_data="root_admin")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_lab_kb():
    """Получить клавиатуру лаборатории"""
    kb = [[InlineKeyboardButton(text="⬆️ Улучшить", callback_data="lab_upgrade"),
           InlineKeyboardButton(text="📊 Статус", callback_data="lab_status")],
          [InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_back_kb():
    """Получить клавиатуру возврата в главное меню"""
    kb = [[InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)

@dp.callback_query(F.data == "back_main")
async def back_main(call: CallbackQuery):
    """Возврат в главное меню"""
    await call.answer()
    try:
        async with aiosqlite.connect("bio_game.db") as db:
            u = await (await db.execute("SELECT * FROM users WHERE id=?", (call.from_user.id,))).fetchone()
        
        if not u:
            await call.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        status = "👑 ВЛАДЕЛЕЦ" if is_owner(call.from_user.id) else "🧬 Мутант"
        ops_percentage = (u[12] / u[11] * 100) if u[11] > 0 else 0
        
        text = (
            f"Статус: {status}\n"
            f"🏷 Патоген: {u[4]} (x{u[5]})\n"
            f"🧪 Квал: {u[6]} ур.\n\n"
            f"⚡️ НАВЫКИ:\n"
            f"🦠 Заразность: {u[7]} | 🛡 Иммунитет: {u[8]}\n"
            f"💀 Летальность: {u[9]} | 👮 СБ: {u[10]}\n\n"
            f"📊 СТАТИСТИКА:\n"
            f"☣️ Опыт: {u[2]} | 🧬 Рес: {u[3]:.1f}k\n"
            f"😷 Спецопер: {u[12]}/{u[11]} ({ops_percentage:.1f}%)\n"
            f"🕶 Предотвращено: {u[13]}\n\n"
            f"💡 Выберите действие"
        )
        
        await call.message.edit_text(text, reply_markup=get_main_kb(call.from_user.id))
    except Exception as e:
        logger.error(f"Back main error: {e}")
        await call.answer("❌ Произошла ошибка", show_alert=True)

@dp.callback_query(F.data.in_(["lab", "pathogen", "res", "attack", "root_admin"]))
async def menu_handler(call: CallbackQuery):
    """Обработчик главного меню"""
    await call.answer()
    
    # Проверка прав доступа в начале
    if call.data == "root_admin" and not is_owner(call.from_user.id):
        await call.answer("❌ Нет прав доступа", show_alert=True)
        return
    
    try:
        async with aiosqlite.connect("bio_game.db") as db:
            u = await (await db.execute("SELECT * FROM users WHERE id=?", (call.from_user.id,))).fetchone()
        
        if not u:
            await call.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        if u[14]:  # Проверка на бан
            await call.answer("🚫 Вы заблокированы", show_alert=True)
            return
        
        if call.data == "lab":
            text = f"🧪 ЛАБОРАТОРИЯ\n\nТекущий уровень: {u[6]} ур.\nОпыт для улучшения: {u[2]}\nРесурсы: {u[3]:.1f}k\n\nСтоимость улучшения: 50 опыта и 10k ресурсов"
            await call.message.edit_text(text, reply_markup=get_lab_kb())
        
        elif call.data == "pathogen":
            text = (
                f"🧬 ПАТОГЕН: {u[4]}\n\n"
                f"Количество: {u[5]}\n"
                f"Уровень лаборатории: {u[6]}\n\n"
                f"ХАРАКТЕРИСТИКИ:\n"
                f"🦠 Заразность: {u[7]}\n"
                f"🛡 Иммунитет: {u[8]}\n"
                f"💀 Летальность: {u[9]}\n"
                f"👮 Безопасность: {u[10]}"
            )
            await call.message.edit_text(text, reply_markup=get_back_kb())
        
        elif call.data == "res":
            text = (
                f"💰 РЕСУРСЫ\n\n"
                f"Вашего склада:\n"
                f"🧬 Ресурсы: {u[3]:.1f}k\n"
                f"☣️ Опыт: {u[2]}\n\n"
                f"Дополнительно:\n"
                f"😷 Спецоперации: {u[12]}/{u[11]}\n"
                f"🕶 Предотвращено заболеваний: {u[13]}"
            )
            await call.message.edit_text(text, reply_markup=get_back_kb())
        
        elif call.data == "attack":
            enemy_pathogens = random.randint(1, 10)
            attack_result = random.choice(["Успех! 🎯", "Попадание! ✅", "Критический удар! 💥"])
            text = (
                f"⚔️ АТАКА\n\n"
                f"Найдена цель...\n"
                f"Патогенов врага: {enemy_pathogens}\n"
                f"Результат: {attack_result}\n\n"
                f"Спецоперация выполнена!"
            )
            await call.message.edit_text(text, reply_markup=get_back_kb())
        
        elif call.data == "root_admin":
            text = (
                f"⚙️ ROOT-ПАНЕЛЬ\n\n"
                f"Команды администратора:\n"
                f"/ban <user_id> - заблокировать пользователя\n"
                f"/sudo <column> <user_id> <value> - изменить параметр\n\n"
                f"Доступные колонки:\n"
                f"bio_exp, resources, pathogens_count, lab_level,\n"
                f"contagiousness, immunity, lethality, security_service,\n"
                f"ops_total, ops_won, prevented"
            )
            await call.message.edit_text(text, reply_markup=get_back_kb())
    
    except Exception as e:
        error_msg = str(e)
        if "message is not modified" not in error_msg:
            logger.error(f"Menu handler error: {e}")
            await call.answer("❌ Произошла ошибка", show_alert=True)

@dp.callback_query(F.data == "lab_upgrade")
async def lab_upgrade(call: CallbackQuery):
    """Улучшение лаборатории"""
    await call.answer()
    try:
        async with aiosqlite.connect("bio_game.db") as db:
            u = await (await db.execute("SELECT * FROM users WHERE id=?", (call.from_user.id,))).fetchone()
            
            if u[2] >= 50 and u[3] >= 10:
                await db.execute(
                    "UPDATE users SET lab_level = lab_level + 1, bio_exp = bio_exp - 50, resources = resources - 10 WHERE id=?",
                    (call.from_user.id,)
                )
                await db.commit()
                text = "✅ Лаборатория улучшена на 1 уровень!"
            else:
                text = f"❌ Недостаточно ресурсов!\nНужно: 50 опыта и 10k ресурсов\nЕсть: {u[2]} опыта и {u[3]:.1f}k ресурсов"
        
        await call.answer(text, show_alert=True)
        
        # Обновляем информацию
        async with aiosqlite.connect("bio_game.db") as db:
            u = await (await db.execute("SELECT * FROM users WHERE id=?", (call.from_user.id,))).fetchone()
        
        text = f"🧪 ЛАБОРАТОРИЯ\n\nТекущий уровень: {u[6]} ур.\nОпыт для улучшения: {u[2]}\nРесурсы: {u[3]:.1f}k\n\nСтоимость улучшения: 50 опыта и 10k ресурсов"
        await call.message.edit_text(text, reply_markup=get_lab_kb())
    except Exception as e:
        logger.error(f"Lab upgrade error: {e}")
        await call.answer("❌ Произошла ошибка", show_alert=True)

@dp.callback_query(F.data == "lab_status")
async def lab_status(call: CallbackQuery):
    """Статус лаборатории"""
    await call.answer()
    try:
        async with aiosqlite.connect("bio_game.db") as db:
            u = await (await db.execute("SELECT * FROM users WHERE id=?", (call.from_user.id,))).fetchone()
        
        bonus = u[6] * 5  # Бонус опыта за уровень
        text = (
            f"📊 СТАТУС ЛАБОРАТОРИИ\n\n"
            f"Уровень: {u[6]}\n"
            f"Бонус опыта: +{bonus}%\n"
            f"Текущий опыт: {u[2]}\n"
            f"Ресурсы: {u[3]:.1f}k\n\n"
            f"Каждое улучшение дает +5% к опыту!"
        )
        await call.message.edit_text(text, reply_markup=get_lab_kb())
    except Exception as e:
        logger.error(f"Lab status error: {e}")
        await call.answer("❌ Произошла ошибка", show_alert=True)

@dp.message(F.text.lower().contains("заразить"))
async def infect_cmd(msg: Message):
    """Команда заражения"""
    try:
        if await check_user_banned(msg.from_user.id):
            await msg.answer("🚫 Вы заблокированы")
            return
        
        async with aiosqlite.connect("bio_game.db") as db:
            await db.execute("UPDATE users SET pathogens_count = pathogens_count + 1 WHERE id=?", (msg.from_user.id,))
            await db.commit()
        await msg.answer("🦠 Патоген внедрен!")
        logger.info(f"User {msg.from_user.id} infected")
    except Exception as e:
        logger.error(f"Infection command error: {e}")
        await msg.answer("❌ Произошла ошибка")

@dp.message(Command("start"))
async def start(msg: Message):
    """Команда /start"""
    try:
        async with aiosqlite.connect("bio_game.db") as db:
            await db.execute(
                "INSERT OR IGNORE INTO users (id, name) VALUES (?, ?)", 
                (msg.from_user.id, msg.from_user.first_name)
            )
            await db.commit()
        await msg.answer("Система BioGame активна.", reply_markup=get_main_kb(msg.from_user.id))
        logger.info(f"User {msg.from_user.id} started the bot")
    except Exception as e:
        logger.error(f"Start command error: {e}")
        await msg.answer("❌ Произошла ошибка при инициализации")

@dp.message(Command("ban"))
async def ban(msg: Message):
    """Команда бана пользователя (только для владельца)"""
    if not is_owner(msg.from_user.id):
        await msg.answer("❌ Нет прав доступа")
        return
    
    args = msg.text.split()
    if len(args) < 2:
        await msg.answer("❌ Использование: /ban <user_id>")
        return
    
    try:
        user_id = int(args[1])
        async with aiosqlite.connect("bio_game.db") as db:
            await db.execute("UPDATE users SET is_banned = 1 WHERE id=?", (user_id,))
            await db.commit()
        await msg.answer(f"🚫 Юзер {user_id} заблокирован.")
        logger.warning(f"User {user_id} banned by {msg.from_user.id}")
    except ValueError:
        await msg.answer("❌ user_id должен быть числом")
    except Exception as e:
        logger.error(f"Ban command error: {e}")
        await msg.answer("❌ Произошла ошибка при блокировке")

@dp.message(Command("sudo"))
async def sudo(msg: Message):
    """Команда администратора для изменения параметров (только для владельца)"""
    if not is_owner(msg.from_user.id):
        await msg.answer("❌ Нет прав доступа")
        return
    
    args = msg.text.split()
    if len(args) < 4:
        await msg.answer("❌ Использование: /sudo <column> <user_id> <value>")
        return
    
    try:
        column = args[1]
        user_id = int(args[2])
        value = int(args[3])
        
        # Допустимые колонки для защиты от SQL-инъекции
        allowed_columns = {
            "bio_exp", "resources", "pathogens_count", "lab_level", 
            "contagiousness", "immunity", "lethality", "security_service", 
            "ops_total", "ops_won", "prevented"
        }
        
        if column not in allowed_columns:
            await msg.answer(f"❌ Колонка '{column}' не разрешена")
            return
        
        async with aiosqlite.connect("bio_game.db") as db:
            # Используем параметризованный запрос безопасно
            await db.execute(
                f"UPDATE users SET {column} = {column} + ? WHERE id=?", 
                (value, user_id)
            )
            await db.commit()
        
        await msg.answer(f"✅ ROOT: {column} увеличено на {value} для пользователя {user_id}")
        logger.warning(f"Sudo command executed: {column}+{value} for user {user_id} by {msg.from_user.id}")
    
    except ValueError:
        await msg.answer("❌ user_id и value должны быть числами")
    except Exception as e:
        logger.error(f"Sudo command error: {e}")
        await msg.answer("❌ Произошла ошибка при выполнении команды")

if __name__ == "__main__":
    if not TOKEN:
        logger.error("BOT_TOKEN not set in environment variables")
        print("❌ Ошибка: BOT_TOKEN не установлен в переменных окружения")
        exit(1)
    
    if OWNER_ID == 0:
        logger.error("OWNER_ID not set in environment variables")
        print("❌ Ошибка: OWNER_ID не установлен в переменных окружения")
        exit(1)
    
    logger.info("Starting BioGame bot...")
    Thread(target=run_flask, daemon=True).start()
    asyncio.run(init_db())
    asyncio.run(dp.start_polling(bot))
