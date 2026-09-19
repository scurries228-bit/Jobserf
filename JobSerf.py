import os
import json
import time
import html
import telebot
from telebot import types

BOT_TOKEN = "8246195131:AAFA-pju40tG8zbYrQ5YwH4-5UQ6rP56RsY"
DATA_FILE = "jobserf_data.json"
ADMIN_IDS = {7396218587}

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
players = {}
registration = {}
support_cooldown = {}
admin_states = {}
known_chats = set()
pending_transfers = {}


def format_money(amount):
    return f"{int(amount):,}".replace(",", ".") + "₽"


def esc(value):
    return html.escape(str(value))


def is_admin(uid):
    return uid in ADMIN_IDS


def save_data():
    try:
        payload = {"players": players, "known_chats": list(known_chats), "admins": list(ADMIN_IDS)}
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("save error:", e)


def load_data():
    global players, known_chats, ADMIN_IDS
    if not os.path.exists(DATA_FILE):
        return
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            payload = json.load(f)
        players = {int(k): v for k, v in payload.get("players", {}).items()}
        known_chats = set(payload.get("known_chats", []))
        ADMIN_IDS |= set(payload.get("admins", []))
        for p in players.values():
            normalize_player(p)
    except Exception as e:
        print("load error:", e)


def normalize_player(player):
    player.setdefault("balance", 30000)
    player.setdefault("businesses", 0)
    player.setdefault("branches", 0)
    player.setdefault("employees", 0)
    player.setdefault("business_balance", 0)
    player.setdefault("level", 0)
    player.setdefault("notifications", True)
    player.setdefault("support_waiting", False)
    b = player.get("business")
    if b:
        defaults = {
            "level": 1, "balance": 30000, "income": 0, "expenses": 0,
            "employees": 0, "branches": 1, "clients": 0,
            "marketing_spent": 0, "contracts": [], "employees_list": [],
            "vacancies": [], "positions": [], "operations": [],
            "campaigns": [], "campaign_history": [], "partners": [],
            "offers_in": [], "offers_out": [], "branches_list": [],
            "warehouse_capacity": 100, "stock": 0, "stock_cost": 0,
            "room_area": 50, "client_capacity": 20, "workplaces": 5,
            "room_condition": 100, "room_cost": 1000,
            "equipment_performance": 100, "equipment_condition": 100,
            "equipment_capacity": 100, "equipment_cost": 500,
            "marketing_efficiency": 0, "description": "", "logo": "",
            "name": "Бизнес", "sphere": "Другое", "owner_id": 0,
            "suspended": False, "managers": []
        }
        for k, v in defaults.items():
            b.setdefault(k, v.copy() if isinstance(v, list) else v)
        if not b["branches_list"]:
            b["branches_list"] = [{"id": 1, "name": "Основной филиал", "location": "Центральный", "income": 0, "expenses": 0, "clients": 0, "employees": 0, "capacity": b["client_capacity"], "active": True}]
        player["business_balance"] = b["balance"]
        player["employees"] = len(b["employees_list"])
        player["branches"] = len(b["branches_list"])


def business(uid):
    p = players.get(uid)
    return p.get("business") if p else None


def record_op(b, kind, amount, text):
    b["operations"].append({"time": int(time.time()), "kind": kind, "amount": int(amount), "text": text})
    b["operations"] = b["operations"][-100:]


def sync_player(uid):
    p = players[uid]
    b = p.get("business")
    if not b:
        return
    p["business_balance"] = b["balance"]
    p["employees"] = len(b["employees_list"])
    p["branches"] = len(b["branches_list"])
    p["businesses"] = 1
    p["branches"] = len(b["branches_list"])
    p["level"] = b["level"]
    save_data()


def main_menu_keyboard(uid):
    k = types.ReplyKeyboardMarkup(resize_keyboard=True)
    k.row("💼 Мой бизнес", "👤 Профиль")
    k.row("⚙️ Настройки", "🆘 Поддержка")
    if is_admin(uid):
        k.row("🎚️ Админ панель")
    return k


def show_main_menu(chat_id, uid=None):
    if uid is None:
        uid = chat_id
    bot.send_message(chat_id, "Выбери нужное действие.", reply_markup=main_menu_keyboard(uid))


def inline_back(data):
    k = types.InlineKeyboardMarkup()
    k.add(types.InlineKeyboardButton("🔙 Назад", callback_data=data))
    return k


def edit_callback(call, text, markup=None):
    try:
        if getattr(call.message, "content_type", None) == "photo":
            bot.edit_message_caption(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
        else:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception:
        bot.send_message(call.message.chat.id, text, reply_markup=markup)


def biz_menu():
    k = types.InlineKeyboardMarkup()
    k.row(types.InlineKeyboardButton("📊 Статистика", callback_data="b_stats"), types.InlineKeyboardButton("📈 Развитие", callback_data="b_dev"))
    k.row(types.InlineKeyboardButton("👥 Персонал", callback_data="b_staff"), types.InlineKeyboardButton("🏪 Филиалы", callback_data="b_branches"))
    k.row(types.InlineKeyboardButton("💰 Финансы", callback_data="b_finance"), types.InlineKeyboardButton("📢 Маркетинг", callback_data="b_marketing"))
    k.row(types.InlineKeyboardButton("🤝 Партнёры", callback_data="b_partners"), types.InlineKeyboardButton("⚙️ Управление", callback_data="b_manage"))
    k.add(types.InlineKeyboardButton("🔙 Назад", callback_data="b_main_back"))
    return k


def send_business_card(chat_id, uid):
    b=business(uid)
    if not b: return
    text=f"""[ 🚀 ] <b>Бизнес — {esc(b['name'])} №1.</b>"""
    try:
        bot.send_photo(chat_id,b["logo"],caption=text,reply_markup=biz_menu())
    except Exception:
        bot.send_message(chat_id,text,reply_markup=biz_menu())


@bot.message_handler(commands=["start"])
def start(message):
    uid=message.from_user.id
    if uid in players:
        p=players[uid]
        bot.send_message(message.chat.id,f"""[ 👋 ] <b>С возвращением, {esc(p['nickname'])}!</b>

Рады снова видеть тебя в Jobserf.

Твой бизнес ждёт новых решений, развития и возможностей.

💰 Баланс: <b>{format_money(p['balance'])}</b>.

Готов продолжить свой путь? 🚀""")
        show_main_menu(message.chat.id,uid); return
    k=types.InlineKeyboardMarkup(); k.add(types.InlineKeyboardButton("🚀 Начать!",callback_data="reg_start"))
    bot.send_message(message.chat.id,"""[ 🏢 ] <b>Добро пожаловать в Jobserf!</b>

Здесь ты создашь свой собственный бизнес и попробуешь превратить его из маленького стартапа в настоящую империю.

<blockquote>💼 Создавай бизнесы.

👥 Нанимай игроков.

💰 Зарабатывай и развивайся.

🏪 Открывай новые филиалы.

⚔️ Конкурируй с другими игроками.

🤝 Заключай сделки и сотрудничай.</blockquote>

И самое главное — <u>ты сам решаешь, каким будет твой бизнес.</u>""",reply_markup=k)


@bot.callback_query_handler(func=lambda c:c.data=="reg_start")
def reg_start(call):
    registration[call.from_user.id]=True
    edit_callback(call,"""[ 👤 ] <b>Регистрация в Jobserf.</b>

Перед началом игры тебе нужно создать свой игровой профиль.

Придумай себе игровое имя, под которым тебя будут видеть другие игроки. Это имя можно будет использовать в бизнесах, сделках и других игровых взаимодействиях.

✏️ Отправь своё игровое имя следующим сообщением. От <u>3 до 20 символов</u>.""")
    bot.answer_callback_query(call.id)


@bot.message_handler(content_types=["text"],func=lambda m:m.from_user.id in registration)
def reg_nick(message):
    n=message.text.strip()
    if not 3<=len(n)<=20:
        bot.send_message(message.chat.id,"[ ❌ ] Игровое имя должно содержать от <u>3 до 20 символов</u>."); return
    uid=message.from_user.id
    players[uid]={"nickname":n,"balance":30000,"businesses":0,"branches":0,"employees":0,"business_balance":0,"level":0,"notifications":True,"support_waiting":False,"business":None}
    registration.pop(uid,None); save_data()
    k=types.InlineKeyboardMarkup(); k.add(types.InlineKeyboardButton("Благодарю! 🚀",callback_data="reg_done"))
    bot.send_message(message.chat.id,f"""[ 👤 ] <b>Профиль создан!</b>

Добро пожаловать в Jobserf, {esc(n)}! 🎉

<blockquote>Перед тобой открывается мир бизнеса и больших возможностей. Теперь всё зависит только от тебя: придумай свою идею, создай первый бизнес и начни развивать его с нуля. Нанимай игроков, зарабатывай деньги, открывай новые филиалы и постепенно превращай небольшой бизнес в настоящую империю.</blockquote>

💰 Твой стартовый капитал — <u>30.000₽</u>.

Удачи тебе, <u>{esc(n)}</u>! 🚀""",reply_markup=k)

@bot.callback_query_handler(func=lambda c:c.data=="reg_done")
def reg_done(call): bot.answer_callback_query(call.id); show_main_menu(call.message.chat.id,call.from_user.id)


@bot.message_handler(func=lambda m:m.text=="💼 Мой бизнес")
def my_business(message):
    uid=message.from_user.id
    if uid not in players:return
    if not business(uid):
        k=types.InlineKeyboardMarkup(); k.add(types.InlineKeyboardButton("🏗️ Создать бизнес",callback_data="biz_create")); k.add(types.InlineKeyboardButton("🔙 Назад",callback_data="b_main_back"))
        bot.send_message(message.chat.id,"""[ 🏢 ] <b>Мой бизнес.</b>

У тебя пока нет собственного бизнеса.

Создай его с нуля: придумай название, выбери сферу, добавь описание и установи логотип.

💰 <b>Доступный капитал:</b> 30.000₽""",reply_markup=k); return
    send_business_card(message.chat.id,uid)


@bot.callback_query_handler(func=lambda c:c.data=="biz_create")
def biz_create(call):
    uid=call.from_user.id
    admin_states[uid]={"state":"biz_name"}
    edit_callback(call,"""[ 🏗️ ] <b>Создание бизнеса.</b>

Придумай название компании.

✏️ Отправь название следующим сообщением.

<blockquote>Например:

<b>Gloybly Market</b>

От 3 до 30 символов.</blockquote>""")
    bot.answer_callback_query(call.id)

@bot.message_handler(content_types=["text"],func=lambda m:m.from_user.id in admin_states and admin_states[m.from_user.id].get("state")=="biz_name")
def biz_name(message):
    n=message.text.strip()
    if not 3<=len(n)<=30:
        bot.send_message(message.chat.id,"[ ❌ ] Название бизнеса должно содержать от <u>3 до 30 символов</u>.");return
    admin_states[message.from_user.id]={"state":"biz_sphere","name":n}
    k=types.InlineKeyboardMarkup()
    vals=[("🛒 Торговля","Торговля"),("🍔 Еда","Еда"),("💻 IT","IT"),("🏗️ Строительство","Строительство"),("🚗 Транспорт","Транспорт"),("🎮 Развлечения","Развлечения"),("💼 Услуги","Услуги"),("📦 Другое","Другое")]
    for i in range(0,len(vals),2): k.row(*[types.InlineKeyboardButton(vals[j][0],callback_data=f"sp_{j}") for j in range(i,min(i+2,len(vals)))])
    admin_states[message.from_user.id]["spheres"]={str(i):v for i,v in enumerate([x[1] for x in vals])}
    bot.send_message(message.chat.id,f"[ 🏷️ ] <b>Название сохранено.</b>\n\n<blockquote>🏢 <b>{esc(n)}</b></blockquote>\n\nВыбери сферу деятельности.",reply_markup=k)

@bot.callback_query_handler(func=lambda c:c.data.startswith("sp_"))
def choose_sphere(call):
    uid=call.from_user.id;s=admin_states.get(uid)
    if not s:return
    sphere=s["spheres"].get(call.data[3:]);s.update(state="biz_desc",sphere=sphere);s.pop("spheres",None)
    bot.send_message(call.message.chat.id,f"""[ 💼 ] <b>Сфера выбрана.</b>

<blockquote>🏢 <b>{esc(s['name'])}</b>

💼 <b>{esc(sphere)}</b></blockquote>

✏️ Напиши описание компании.

<b>От 10 до 500 символов.</b>

🎨 После этого можно будет установить логотип или пропустить этот шаг.""")
    bot.answer_callback_query(call.id)

@bot.message_handler(content_types=["text"],func=lambda m:m.from_user.id in admin_states and admin_states[m.from_user.id].get("state")=="biz_desc")
def biz_desc(message):
    d=message.text.strip()
    if not 10<=len(d)<=500:
        bot.send_message(message.chat.id,"[ ❌ ] Описание должно содержать от <u>10 до 500 символов</u>.");return
    s=admin_states[message.from_user.id];s.update(state="biz_logo",desc=d)
    k=types.InlineKeyboardMarkup();k.add(types.InlineKeyboardButton("⏩ Пропустить",callback_data="logo_skip"))
    bot.send_message(message.chat.id,"""[ 🎨 ] <b>Логотип бизнеса.</b>

Основная информация готова.

📷 Отправь логотип своей компании фотографией.

Если логотип пока не нужен, нажми «⏩ Пропустить».""",reply_markup=k)

@bot.callback_query_handler(func=lambda c:c.data=="logo_skip")
def logo_skip(call):
    uid=call.from_user.id;s=admin_states.get(uid)
    if not s:return
    s["logo"]="";s["state"]="biz_confirm";show_biz_confirm(call.message.chat.id,s);bot.answer_callback_query(call.id)

@bot.message_handler(content_types=["photo"],func=lambda m:m.from_user.id in admin_states and admin_states[m.from_user.id].get("state")=="biz_logo")
def biz_logo(message):
    s=admin_states[message.from_user.id];s["logo"]=message.photo[-1].file_id;s["state"]="biz_confirm";show_biz_confirm(message.chat.id,s)

def show_biz_confirm(chat_id,s):
    text=f"""[ 🔎 ] <b>Проверь данные компании.</b>

━━━━━━━━━━━━━━━━━━

<blockquote>🏢 <b>{esc(s['name'])}</b>

💼 <b>Сфера:</b> {esc(s['sphere'])}

📝 <b>Описание:</b>
{esc(s['desc'])}</blockquote>

━━━━━━━━━━━━━━━━━━

🎨 <b>Логотип:</b> {'установлен' if s.get('logo') else 'не установлен'}

💰 <b>Стартовый капитал:</b> 30.000₽

━━━━━━━━━━━━━━━━━━"""
    k=types.InlineKeyboardMarkup();k.add(types.InlineKeyboardButton("🏗️ Создать бизнес",callback_data="biz_confirm"));k.add(types.InlineKeyboardButton("✏️ Начать заново",callback_data="biz_restart"))
    if s.get("logo"):
        bot.send_photo(chat_id,s["logo"],caption=text,reply_markup=k)
    else:bot.send_message(chat_id,text,reply_markup=k)

@bot.callback_query_handler(func=lambda c:c.data=="biz_restart")
def biz_restart(call):
    admin_states[call.from_user.id]={"state":"biz_name"};edit_callback(call,"[ ✏️ ] <b>Создание бизнеса заново.</b>\n\n✏️ Отправь новое название компании.");bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="biz_confirm")
def biz_confirm(call):
    uid=call.from_user.id;s=admin_states.get(uid)
    if not s or s.get("state")!="biz_confirm":return
    logo=s.get("logo") or ""
    b={"name":s["name"],"sphere":s["sphere"],"description":s["desc"],"logo":logo,"level":1,"balance":30000,"income":0,"expenses":0,"employees":0,"branches":1,"clients":0,"marketing_spent":0,"contracts":[],"employees_list":[],"vacancies":[],"positions":[],"operations":[],"campaigns":[],"campaign_history":[],"partners":[],"offers_in":[],"offers_out":[],"branches_list":[{"id":1,"name":"Основной филиал","location":"Центральный","income":0,"expenses":0,"clients":0,"employees":0,"capacity":20,"active":True}],"warehouse_capacity":100,"stock":0,"stock_cost":0,"room_area":50,"client_capacity":20,"workplaces":5,"room_condition":100,"room_cost":1000,"equipment_performance":100,"equipment_condition":100,"equipment_capacity":100,"equipment_cost":500,"marketing_efficiency":0,"owner_id":uid,"suspended":False,"managers":[]}
    players[uid]["business"]=b;players[uid]["balance"]=0;players[uid]["business_balance"]=30000;players[uid]["businesses"]=1;players[uid]["branches"]=1;players[uid]["level"]=1;admin_states.pop(uid,None);save_data()
    text=f"""[ 🎉 ] <b>Бизнес успешно создан!</b>

━━━━━━━━━━━━━━━━━━

<blockquote>🏢 <b>{esc(b['name'])}</b>

💼 Сфера: <b>{esc(b['sphere'])}</b>

⭐ Уровень: <b>1</b>

💳 Баланс: <b>30.000₽</b>

🏪 Филиалов: <b>1</b></blockquote>

━━━━━━━━━━━━━━━━━━

Компания официально создана.

🚀 Твой бизнес готов к работе."""
    k=types.InlineKeyboardMarkup();k.add(types.InlineKeyboardButton("🏢 Открыть бизнес",callback_data="open_biz"));edit_callback(call,text,k);bot.answer_callback_query(call.id,"Бизнес создан!")

@bot.callback_query_handler(func=lambda c:c.data=="open_biz")
def open_biz(call):
    send_business_card(call.message.chat.id,call.from_user.id);bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="b_main_back")
def b_main_back(call):
    bot.answer_callback_query(call.id);show_main_menu(call.message.chat.id,call.from_user.id)


def stats_text(b):
    profit=b["income"]-b["expenses"]
    return f"""[ 📊 ] <b>Статистика — {esc(b['name'])} №1.</b>

━━━━━━━━━━━━━━━━━━

<blockquote>🏢 Уровень бизнеса: {b['level']}

💼 Сфера: {esc(b['sphere'])}

💰 Оборот: {format_money(b['income'])}

📈 Доход: {format_money(b['income'])}

📉 Расходы: {format_money(b['expenses'])}

💵 Чистая прибыль: {format_money(profit)}

👥 Сотрудники: {len(b['employees_list'])}

🏪 Филиалы: {len(b['branches_list'])}

👤 Клиенты: {b['clients']}

📢 Расходы на маркетинг: {format_money(b['marketing_spent'])}

🤝 Активных контрактов: {len(b['contracts'])}</blockquote>

━━━━━━━━━━━━━━━━━━

📅 Показатели за текущий период."""

@bot.callback_query_handler(func=lambda c:c.data=="b_stats")
def b_stats(call):
    b=business(call.from_user.id);edit_callback(call,stats_text(b),inline_back("open_biz"));bot.answer_callback_query(call.id)


def dev_menu():
    k=types.InlineKeyboardMarkup();k.row(types.InlineKeyboardButton("🏗️ Помещение",callback_data="d_room"),types.InlineKeyboardButton("🛠️ Оборудование",callback_data="d_equip"));k.row(types.InlineKeyboardButton("📦 Товарные запасы",callback_data="d_stock"),types.InlineKeyboardButton("👥 Персонал",callback_data="d_staff"));k.row(types.InlineKeyboardButton("📢 Маркетинг",callback_data="d_marketing"),types.InlineKeyboardButton("⚡ Эффективность",callback_data="d_eff"));k.add(types.InlineKeyboardButton("🔙 Назад",callback_data="open_biz"));return k

@bot.callback_query_handler(func=lambda c:c.data=="b_dev")
def b_dev(call):
    b=business(call.from_user.id)
    text="""[ 📈 ] <b>Развитие — {}</b>

━━━━━━━━━━━━━━━━━━

🏢 Состояние бизнеса:

🏗️ Помещение

🛠️ Оборудование

📦 Товарные запасы

👥 Персонал

📢 Маркетинг

⚡ Эффективность

━━━━━━━━━━━━━━━━━━

Развивай отдельные направления бизнеса,
чтобы увеличивать его возможности и доходность.""".format(esc(b["name"])+" №1")
    edit_callback(call,text,dev_menu());bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="d_room")
def d_room(call):
    b=business(call.from_user.id);text=f"""[ 🏗️ ] <b>Помещение — {esc(b['name'])} №1.</b>

━━━━━━━━━━━━━━━━━━

<blockquote>🏢 Площадь: {b['room_area']} м²

👤 Вместимость клиентов: {b['client_capacity']}

💼 Рабочих мест: {b['workplaces']}

🔧 Состояние: {b['room_condition']}%

💰 Содержание: {format_money(b['room_cost'])} / период</blockquote>

━━━━━━━━━━━━━━━━━━

Развивай помещение, чтобы увеличить вместимость
бизнеса и количество доступных рабочих мест."""
    k=types.InlineKeyboardMarkup();k.row(types.InlineKeyboardButton("🏗️ Расширить помещение",callback_data="room_expand"),types.InlineKeyboardButton("🔧 Ремонт",callback_data="room_repair"));k.add(types.InlineKeyboardButton("🔙 Назад",callback_data="b_dev"));edit_callback(call,text,k);bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="room_expand")
def room_expand(call):
    uid=call.from_user.id;b=business(uid);cost=5000
    if b["balance"]<cost:bot.answer_callback_query(call.id,"Недостаточно средств на счёте бизнеса.",show_alert=True);return
    b["balance"]-=cost;b["expenses"]+=cost;b["room_area"]+=25;b["client_capacity"]+=10;b["workplaces"]+=2;b["room_cost"]+=250;record_op(b,"expense",cost,"Расширение помещения");sync_player(uid);d_room(call)

@bot.callback_query_handler(func=lambda c:c.data=="room_repair")
def room_repair(call):
    uid=call.from_user.id;b=business(uid);cost=1000
    if b["room_condition"]>=100:bot.answer_callback_query(call.id,"Помещение уже в идеальном состоянии.");return
    if b["balance"]<cost:bot.answer_callback_query(call.id,"Недостаточно средств.",show_alert=True);return
    b["balance"]-=cost;b["expenses"]+=cost;b["room_condition"]=100;record_op(b,"expense",cost,"Ремонт помещения");sync_player(uid);d_room(call)

@bot.callback_query_handler(func=lambda c:c.data=="d_equip")
def d_equip(call):
    b=business(call.from_user.id);text=f"""[ 🛠️ ] <b>Оборудование — {esc(b['name'])} №1.</b>

━━━━━━━━━━━━━━━━━━

<blockquote>⚙️ Производительность: {b['equipment_performance']}%

🔧 Состояние: {b['equipment_condition']}%

📦 Мощность: {b['equipment_capacity']} ед.

💰 Содержание: {format_money(b['equipment_cost'])} / период</blockquote>

━━━━━━━━━━━━━━━━━━

Улучшай оборудование, чтобы повысить
производительность и возможности бизнеса.""";k=types.InlineKeyboardMarkup();k.row(types.InlineKeyboardButton("🛠️ Модернизировать",callback_data="equip_upgrade"),types.InlineKeyboardButton("🔧 Обслуживание",callback_data="equip_service"));k.add(types.InlineKeyboardButton("🔙 Назад",callback_data="b_dev"));edit_callback(call,text,k);bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="equip_upgrade")
def equip_upgrade(call):
    uid=call.from_user.id;b=business(uid);cost=3000
    if b["balance"]<cost:bot.answer_callback_query(call.id,"Недостаточно средств.",show_alert=True);return
    b["balance"]-=cost;b["expenses"]+=cost;b["equipment_performance"]=min(200,b["equipment_performance"]+10);b["equipment_capacity"]+=10;record_op(b,"expense",cost,"Модернизация оборудования");sync_player(uid);d_equip(call)

@bot.callback_query_handler(func=lambda c:c.data=="equip_service")
def equip_service(call):
    uid=call.from_user.id;b=business(uid);cost=800
    if b["equipment_condition"]>=100:bot.answer_callback_query(call.id,"Оборудование уже в идеальном состоянии.");return
    if b["balance"]<cost:bot.answer_callback_query(call.id,"Недостаточно средств.",show_alert=True);return
    b["balance"]-=cost;b["expenses"]+=cost;b["equipment_condition"]=100;record_op(b,"expense",cost,"Обслуживание оборудования");sync_player(uid);d_equip(call)

@bot.callback_query_handler(func=lambda c:c.data=="d_stock")
def d_stock(call):
    b=business(call.from_user.id);text=f"""[ 📦 ] <b>Товарные запасы — {esc(b['name'])} №1.</b>

━━━━━━━━━━━━━━━━━━

<blockquote>📦 Товара на складе: {b['stock']} ед.

🏢 Вместимость склада: {b['warehouse_capacity']} ед.

🛒 Доступно к продаже: {b['stock']} ед.

💰 Стоимость запасов: {format_money(b['stock_cost'])}</blockquote>

━━━━━━━━━━━━━━━━━━

Поддерживай запасы, чтобы бизнес мог
продолжать работу и обслуживать клиентов.""";k=types.InlineKeyboardMarkup();k.row(types.InlineKeyboardButton("📦 Закупить товар",callback_data="stock_buy"),types.InlineKeyboardButton("🏢 Расширить склад",callback_data="stock_expand"));k.add(types.InlineKeyboardButton("📋 Ассортимент",callback_data="stock_assort"));k.add(types.InlineKeyboardButton("🔙 Назад",callback_data="b_dev"));edit_callback(call,text,k);bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="stock_buy")
def stock_buy(call):
    uid=call.from_user.id;b=business(uid);available=b["warehouse_capacity"]-b["stock"];units=min(10,available);cost=units*100
    if units<=0:bot.answer_callback_query(call.id,"Склад заполнен.",show_alert=True);return
    if b["balance"]<cost:bot.answer_callback_query(call.id,"Недостаточно средств.",show_alert=True);return
    b["balance"]-=cost;b["expenses"]+=cost;b["stock"]+=units;b["stock_cost"]+=cost;record_op(b,"expense",cost,f"Закупка товара: {units} ед.");sync_player(uid);d_stock(call)

@bot.callback_query_handler(func=lambda c:c.data=="stock_expand")
def stock_expand(call):
    uid=call.from_user.id;b=business(uid);cost=2500
    if b["balance"]<cost:bot.answer_callback_query(call.id,"Недостаточно средств.",show_alert=True);return
    b["balance"]-=cost;b["expenses"]+=cost;b["warehouse_capacity"]+=50;record_op(b,"expense",cost,"Расширение склада");sync_player(uid);d_stock(call)

@bot.callback_query_handler(func=lambda c:c.data=="stock_assort")
def stock_assort(call):
    edit_callback(call,"""[ 📋 ] <b>Ассортимент.</b>

━━━━━━━━━━━━━━━━━━

<blockquote>📦 Базовый ассортимент

🛒 Доступен к продаже

💰 Средняя закупочная цена: 100₽ / ед.</blockquote>

━━━━━━━━━━━━━━━━━━

Расширение ассортимента будет открывать новые категории товаров и источники дохода.""",inline_back("d_stock"));bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="d_staff")
def d_staff(call):
    staff_screen(call,"d_staff")

def staff_eff(b):
    if not b["employees_list"]:return 100
    return max(50,min(150,int(sum(e.get("eff",100) for e in b["employees_list"])/len(b["employees_list"]))))

def staff_screen(call,back="b_staff"):
    b=business(call.from_user.id);eff=staff_eff(b);text=f"""[ 👥 ] <b>Персонал — {esc(b['name'])} №1.</b>

━━━━━━━━━━━━━━━━━━

<blockquote>👥 Сотрудников: {len(b['employees_list'])}

💼 Рабочих мест: {b['workplaces']}

💰 Фонд заработной платы: {format_money(sum(e['salary'] for e in b['employees_list']))}

⚡ Эффективность персонала: {eff}%</blockquote>

━━━━━━━━━━━━━━━━━━

Развивай персонал, открывай новые должности
и повышай производительность сотрудников."""
    k=types.InlineKeyboardMarkup();k.row(types.InlineKeyboardButton("👤 Сотрудники",callback_data="staff_list"),types.InlineKeyboardButton("📋 Вакансии",callback_data="staff_vac"));k.row(types.InlineKeyboardButton("💼 Должности",callback_data="staff_pos"),types.InlineKeyboardButton("💰 Зарплаты",callback_data="staff_salary"));k.row(types.InlineKeyboardButton("📊 Эффективность",callback_data="staff_eff"));k.add(types.InlineKeyboardButton("🔙 Назад",callback_data=back));edit_callback(call,text,k);bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="b_staff")
def b_staff(call):staff_screen(call)

@bot.callback_query_handler(func=lambda c:c.data=="staff_list")
def staff_list(call):
    b=business(call.from_user.id);lines=[]
    for i,e in enumerate(b["employees_list"],1):lines.append(f"👤 {i}. {esc(e['name'])}\n💼 {esc(e['position'])}\n💰 {format_money(e['salary'])}")
    body="\n\n".join(lines) if lines else "👥 Сотрудников пока нет."
    text=f"[ 👤 ] <b>Сотрудники — {esc(b['name'])} №1.</b>\n\n━━━━━━━━━━━━━━━━━━\n\n<blockquote>{body}</blockquote>\n\n━━━━━━━━━━━━━━━━━━"
    k=types.InlineKeyboardMarkup();k.add(types.InlineKeyboardButton("➕ Нанять сотрудника",callback_data="staff_hire"));k.add(types.InlineKeyboardButton("🔙 Назад",callback_data="b_staff"));edit_callback(call,text,k);bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="staff_hire")
def staff_hire(call):
    uid=call.from_user.id;b=business(uid)
    if len(b["employees_list"])>=b["workplaces"]:bot.answer_callback_query(call.id,"Нет свободных рабочих мест.",show_alert=True);return
    admin_states[uid]={"state":"hire_name"}
    edit_callback(call,"""[ ➕ ] <b>Найм сотрудника.</b>

Отправь игровое имя сотрудника.

После этого выбери должность и установи заработную плату.""",inline_back("staff_list"));bot.answer_callback_query(call.id)

@bot.message_handler(content_types=["text"],func=lambda m:m.from_user.id in admin_states and admin_states[m.from_user.id].get("state")=="hire_name")
def hire_name(message):
    uid=message.from_user.id;n=message.text.strip()
    if not n:return
    s=admin_states[uid];s.update(state="hire_salary",employee_name=n)
    k=types.InlineKeyboardMarkup();
    for amt in (1000,2500,5000,10000):k.add(types.InlineKeyboardButton(format_money(amt),callback_data=f"hire_sal_{amt}"))
    bot.send_message(message.chat.id,"[ 💰 ] <b>Заработная плата.</b>\n\nВыбери зарплату сотрудника за период.",reply_markup=k)

@bot.callback_query_handler(func=lambda c:c.data.startswith("hire_sal_"))
def hire_salary(call):
    uid=call.from_user.id;s=admin_states.get(uid)
    if not s:return
    salary=int(call.data.split("_")[-1]);b=business(uid)
    if len(b["employees_list"])>=b["workplaces"]:bot.answer_callback_query(call.id,"Рабочих мест больше нет.",show_alert=True);return
    emp={"name":s["employee_name"],"position":"Сотрудник","salary":salary,"eff":100,"branch":1}
    b["employees_list"].append(emp);record_op(b,"employee",0,f"Нанят сотрудник {s['employee_name']}");admin_states.pop(uid,None);sync_player(uid)
    edit_callback(call,f"[ ✅ ] <b>Сотрудник нанят.</b>\n\n<blockquote>👤 {esc(emp['name'])}\n\n💼 Должность: Сотрудник\n\n💰 Зарплата: {format_money(salary)}</blockquote>",inline_back("staff_list"));bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="staff_vac")
def staff_vac(call):
    b=business(call.from_user.id);text=f"[ 📋 ] <b>Вакансии — {esc(b['name'])} №1.</b>\n\n━━━━━━━━━━━━━━━━━━\n\n<blockquote>📋 Активных вакансий: {len(b['vacancies'])}\n\n👥 Откликов: {sum(v.get('applications',0) for v in b['vacancies'])}\n\n💼 Свободных рабочих мест: {max(0,b['workplaces']-len(b['employees_list']))}</blockquote>\n\n━━━━━━━━━━━━━━━━━━"
    k=types.InlineKeyboardMarkup();k.add(types.InlineKeyboardButton("➕ Создать вакансию",callback_data="vac_create"));k.add(types.InlineKeyboardButton("📋 Мои вакансии",callback_data="vac_list"));k.add(types.InlineKeyboardButton("📨 Отклики",callback_data="vac_apps"));k.add(types.InlineKeyboardButton("🔙 Назад",callback_data="b_staff"));edit_callback(call,text,k);bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="vac_create")
def vac_create(call):
    admin_states[call.from_user.id]={"state":"vac_name"};edit_callback(call,"[ ➕ ] <b>Создание вакансии.</b>\n\nОтправь название должности.",inline_back("staff_vac"));bot.answer_callback_query(call.id)

@bot.message_handler(content_types=["text"],func=lambda m:m.from_user.id in admin_states and admin_states[m.from_user.id].get("state")=="vac_name")
def vac_name(message):
    uid=message.from_user.id;b=business(uid);b["vacancies"].append({"title":message.text.strip(),"salary":1000,"applications":0});admin_states.pop(uid,None);sync_player(uid);bot.send_message(message.chat.id,"[ ✅ ] <b>Вакансия создана.</b>",reply_markup=inline_back("staff_vac"))

@bot.callback_query_handler(func=lambda c:c.data=="vac_list")
def vac_list(call):
    b=business(call.from_user.id);body="\n\n".join(f"📋 {esc(v['title'])}\n💰 Зарплата: {format_money(v['salary'])}\n👥 Откликов: {v['applications']}" for v in b["vacancies"]) or "Активных вакансий нет."
    edit_callback(call,f"[ 📋 ] <b>Мои вакансии.</b>\n\n<blockquote>{body}</blockquote>",inline_back("staff_vac"));bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="vac_apps")
def vac_apps(call):edit_callback(call,"[ 📨 ] <b>Отклики.</b>\n\n<blockquote>📨 Новых откликов: 0</blockquote>\n\nЗдесь будут отображаться отклики на опубликованные вакансии.",inline_back("staff_vac"));bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="staff_pos")
def staff_pos(call):
    b=business(call.from_user.id);body="\n\n".join(f"💼 {esc(x['name'])}\n👥 Сотрудников: {x.get('count',0)}" for x in b["positions"]) or "Должностей пока нет."
    k=types.InlineKeyboardMarkup();k.add(types.InlineKeyboardButton("➕ Создать должность",callback_data="pos_create"));k.add(types.InlineKeyboardButton("🔙 Назад",callback_data="b_staff"));edit_callback(call,f"[ 💼 ] <b>Должности — {esc(b['name'])} №1.</b>\n\n<blockquote>{body}</blockquote>",k);bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="pos_create")
def pos_create(call):admin_states[call.from_user.id]={"state":"pos_name"};edit_callback(call,"[ ➕ ] <b>Создание должности.</b>\n\nОтправь название должности.",inline_back("staff_pos"));bot.answer_callback_query(call.id)

@bot.message_handler(content_types=["text"],func=lambda m:m.from_user.id in admin_states and admin_states[m.from_user.id].get("state")=="pos_name")
def pos_name(message):
    uid=message.from_user.id;b=business(uid);name=message.text.strip();b["positions"].append({"name":name,"count":0});admin_states.pop(uid,None);sync_player(uid);bot.send_message(message.chat.id,"[ ✅ ] <b>Должность создана.</b>",reply_markup=inline_back("staff_pos"))

@bot.callback_query_handler(func=lambda c:c.data=="staff_salary")
def staff_salary(call):
    b=business(call.from_user.id);fund=sum(e['salary'] for e in b['employees_list']);text=f"[ 💰 ] <b>Зарплаты — {esc(b['name'])} №1.</b>\n\n<blockquote>💰 Фонд заработной платы: {format_money(fund)}\n\n👥 Сотрудников: {len(b['employees_list'])}\n\n📅 Следующая выплата: следующий период</blockquote>";k=types.InlineKeyboardMarkup();k.add(types.InlineKeyboardButton("📋 Зарплаты сотрудников",callback_data="salary_list"));k.add(types.InlineKeyboardButton("📜 История выплат",callback_data="salary_history"));k.add(types.InlineKeyboardButton("🔙 Назад",callback_data="b_staff"));edit_callback(call,text,k);bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="salary_list")
def salary_list(call):
    b=business(call.from_user.id);body="\n\n".join(f"👤 {esc(e['name'])}\n💰 {format_money(e['salary'])}" for e in b['employees_list']) or "Сотрудников нет.";edit_callback(call,f"[ 📋 ] <b>Зарплаты сотрудников.</b>\n\n<blockquote>{body}</blockquote>",inline_back("staff_salary"));bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="salary_history")
def salary_history(call):edit_callback(call,"[ 📜 ] <b>История выплат.</b>\n\n<blockquote>📜 Выплат пока не было.</blockquote>\n\nЗаработная плата списывается с бизнес-счёта в конце расчётного периода.",inline_back("staff_salary"));bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="staff_eff")
def staff_eff_screen(call):
    b=business(call.from_user.id);edit_callback(call,f"[ 📊 ] <b>Эффективность — {esc(b['name'])} №1.</b>\n\n<blockquote>⚡ Общая эффективность: {staff_eff(b)}%\n\n👥 Персонал: {staff_eff(b)}%\n\n💼 Рабочие места: {len(b['employees_list'])} / {b['workplaces']}\n\n📈 Производительность: {staff_eff(b)}%</blockquote>",inline_back("b_staff"));bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="d_staff")
def duplicate_d_staff(call):pass

@bot.callback_query_handler(func=lambda c:c.data=="d_marketing")
def d_marketing(call):b=business(call.from_user.id);edit_callback(call,f"[ 📢 ] <b>Маркетинг — {esc(b['name'])} №1.</b>\n\n<blockquote>📣 Активных кампаний: {len(b['campaigns'])}\n\n👤 Привлечено клиентов: {b['clients']}\n\n👁️ Охват: {sum(x.get('reach',0) for x in b['campaigns'])}\n\n💰 Расходы на маркетинг: {format_money(b['marketing_spent'])}\n\n📈 Эффективность рекламы: {b['marketing_efficiency']}%</blockquote>",inline_back("b_dev"));bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="d_eff")
def d_eff(call):
    b=business(call.from_user.id);overall=int((b['room_condition']+b['equipment_condition']+staff_eff(b)+min(100,b['stock']/max(1,b['warehouse_capacity'])*100))/4);edit_callback(call,f"[ ⚡ ] <b>Эффективность — {esc(b['name'])} №1.</b>\n\n<blockquote>⚡ Общая эффективность: {overall}%\n\n🏗️ Помещение: {b['room_condition']}%\n\n🛠️ Оборудование: {b['equipment_condition']}%\n\n👥 Персонал: {staff_eff(b)}%\n\n📦 Запасы: {int(min(100,b['stock']/max(1,b['warehouse_capacity'])*100))}%\n\n📢 Маркетинг: {b['marketing_efficiency']}%</blockquote>\n\n━━━━━━━━━━━━━━━━━━\n\nПовышай эффективность отдельных направлений, чтобы улучшать общие показатели бизнеса.",inline_back("b_dev"));bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="b_branches")
def b_branches(call):
    b=business(call.from_user.id);inc=sum(x['income'] for x in b['branches_list']);exp=sum(x['expenses'] for x in b['branches_list']);text=f"[ 🏪 ] <b>Филиалы — {esc(b['name'])} №1.</b>\n\n━━━━━━━━━━━━━━━━━━\n\n<blockquote>🏪 Всего филиалов: {len(b['branches_list'])}\n\n💰 Доход филиалов: {format_money(inc)}\n\n📉 Расходы филиалов: {format_money(exp)}\n\n👥 Сотрудников в филиалах: {len(b['employees_list'])}\n\n📈 Прибыль филиалов: {format_money(inc-exp)}</blockquote>\n\n━━━━━━━━━━━━━━━━━━\n\nОткрывай новые филиалы, расширяй присутствие компании и управляй каждой точкой отдельно.""";k=types.InlineKeyboardMarkup();k.add(types.InlineKeyboardButton("🏪 Мои филиалы",callback_data="br_list"));k.add(types.InlineKeyboardButton("➕ Открыть филиал",callback_data="br_open"));k.add(types.InlineKeyboardButton("📊 Статистика филиалов",callback_data="br_stats"));k.add(types.InlineKeyboardButton("🔙 Назад",callback_data="open_biz"));edit_callback(call,text,k);bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="br_list")
def br_list(call):
    b=business(call.from_user.id);body="\n\n".join(f"🏢 {esc(x['name'])}\n📍 {esc(x['location'])}\n💰 Доход: {format_money(x['income'])}\n📉 Расходы: {format_money(x['expenses'])}\n💵 Прибыль: {format_money(x['income']-x['expenses'])}\n👥 Сотрудников: {x['employees']}\n👤 Клиентов: {x['clients']}" for x in b['branches_list']);edit_callback(call,f"[ 🏪 ] <b>Мои филиалы — {esc(b['name'])} №1.</b>\n\n<blockquote>{body}</blockquote>\n\n━━━━━━━━━━━━━━━━━━\n\nВыбери филиал для управления.",inline_back("b_branches"));bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="br_open")
def br_open(call):
    uid=call.from_user.id;b=business(uid);cost=15000
    if b['balance']<cost:bot.answer_callback_query(call.id,"Недостаточно средств на счёте бизнеса.",show_alert=True);return
    new_id=len(b['branches_list'])+1;b['balance']-=cost;b['expenses']+=cost;branch={"id":new_id,"name":f"Филиал №{new_id}","location":"Не выбрано","income":0,"expenses":0,"clients":0,"employees":0,"capacity":20,"active":True};b['branches_list'].append(branch);record_op(b,'expense',cost,f'Открытие филиала №{new_id}');sync_player(uid);edit_callback(call,f"[ 🎉 ] <b>Филиал открыт.</b>\n\n<blockquote>🏪 {branch['name']}\n\n💰 Стоимость: {format_money(cost)}\n\n📍 Место: не выбрано</blockquote>",inline_back("b_branches"));bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="br_stats")
def br_stats(call):
    b=business(call.from_user.id);inc=sum(x['income'] for x in b['branches_list']);exp=sum(x['expenses'] for x in b['branches_list']);clients=sum(x['clients'] for x in b['branches_list']);edit_callback(call,f"[ 📊 ] <b>Статистика филиалов — {esc(b['name'])} №1.</b>\n\n<blockquote>🏪 Всего филиалов: {len(b['branches_list'])}\n\n💰 Общий доход: {format_money(inc)}\n\n📉 Общие расходы: {format_money(exp)}\n\n💵 Общая прибыль: {format_money(inc-exp)}\n\n👥 Всего сотрудников: {len(b['employees_list'])}\n\n👤 Всего клиентов: {clients}</blockquote>",inline_back("b_branches"));bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="b_finance")
def b_finance(call):
    b=business(call.from_user.id);profit=b['income']-b['expenses'];text=f"[ 💰 ] <b>Финансы — {esc(b['name'])} №1.</b>\n\n━━━━━━━━━━━━━━━━━━\n\n<blockquote>💳 Счёт бизнеса: {format_money(b['balance'])}\n\n📈 Доходы: {format_money(b['income'])}\n\n📉 Расходы: {format_money(b['expenses'])}\n\n💵 Прибыль: {format_money(profit)}\n\n🔄 Переведено на личный баланс: 0₽</blockquote>\n\n━━━━━━━━━━━━━━━━━━\n\nУправляй средствами бизнеса, контролируй доходы и расходы и переводи доступные средства на личный баланс.""";k=types.InlineKeyboardMarkup();k.row(types.InlineKeyboardButton("📈 Доходы",callback_data="fin_in"),types.InlineKeyboardButton("📉 Расходы",callback_data="fin_out"));k.row(types.InlineKeyboardButton("🔄 Перевести средства",callback_data="fin_transfer"),types.InlineKeyboardButton("📜 История операций",callback_data="fin_history"));k.add(types.InlineKeyboardButton("🔙 Назад",callback_data="open_biz"));edit_callback(call,text,k);bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="fin_in")
def fin_in(call):
    b=business(call.from_user.id);edit_callback(call,f"[ 📈 ] <b>Доходы — {esc(b['name'])} №1.</b>\n\n<blockquote>📈 Общий доход: {format_money(b['income'])}\n\n🛒 Продажи: {format_money(b['income'])}\n\n🤝 Партнёрства: 0₽</blockquote>\n\nДоход формируется продажами, клиентами и договорами.",inline_back("b_finance"));bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="fin_out")
def fin_out(call):
    b=business(call.from_user.id);edit_callback(call,f"[ 📉 ] <b>Расходы — {esc(b['name'])} №1.</b>\n\n<blockquote>📉 Общие расходы: {format_money(b['expenses'])}\n\n👥 Зарплаты: {format_money(sum(e['salary'] for e in b['employees_list']))}\n\n🏗️ Развитие: учитывается в операциях\n\n📢 Маркетинг: {format_money(b['marketing_spent'])}\n\n🏪 Филиалы: учитываются в операциях</blockquote>",inline_back("b_finance"));bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="fin_transfer")
def fin_transfer(call):
    admin_states[call.from_user.id]={"state":"fin_transfer"};b=business(call.from_user.id);edit_callback(call,f"[ 🔄 ] <b>Перевод средств.</b>\n\nДоступно на счёте бизнеса: <b>{format_money(b['balance'])}</b>\n\nСколько средств перевести на личный баланс?\n\nОтправь целое число.",inline_back("b_finance"));bot.answer_callback_query(call.id)

@bot.message_handler(content_types=["text"],func=lambda m:m.from_user.id in admin_states and admin_states[m.from_user.id].get("state")=="fin_transfer")
def fin_transfer_msg(message):
    uid=message.from_user.id;b=business(uid)
    try:amt=int(message.text.replace(".","").replace("₽","").strip())
    except:bot.send_message(message.chat.id,"[ ❌ ] Укажи сумму целым числом.");return
    if amt<=0 or amt>b['balance']:bot.send_message(message.chat.id,"[ ❌ ] Недостаточно средств или сумма некорректна.");return
    b['balance']-=amt;players[uid]['balance']+=amt;record_op(b,'transfer',amt,'Перевод на личный баланс');admin_states.pop(uid,None);sync_player(uid);bot.send_message(message.chat.id,f"[ ✅ ] <b>Средства переведены.</b>\n\nНа личный баланс зачислено <b>{format_money(amt)}</b>.",reply_markup=inline_back("b_finance"))

@bot.callback_query_handler(func=lambda c:c.data=="fin_history")
def fin_history(call):
    b=business(call.from_user.id);ops=b['operations'][-10:];body="\n\n".join(f"📌 {esc(x['text'])}\n💰 {format_money(x['amount'])}" for x in reversed(ops)) or "Операций пока нет.";edit_callback(call,f"[ 📜 ] <b>История операций.</b>\n\n<blockquote>{body}</blockquote>",inline_back("b_finance"));bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="b_marketing")
def b_marketing(call):
    b=business(call.from_user.id);reach=sum(x.get('reach',0) for x in b['campaigns']);text=f"[ 📢 ] <b>Маркетинг — {esc(b['name'])} №1.</b>\n\n━━━━━━━━━━━━━━━━━━\n\n<blockquote>📣 Активных кампаний: {len(b['campaigns'])}\n\n👁️ Общий охват: {reach}\n\n👤 Привлечено клиентов: {b['clients']}\n\n💰 Потрачено: {format_money(b['marketing_spent'])}\n\n📈 Эффективность: {b['marketing_efficiency']}%</blockquote>\n\n━━━━━━━━━━━━━━━━━━\n\nПродвигай бизнес, привлекай новых клиентов и увеличивай узнаваемость компании.""";k=types.InlineKeyboardMarkup();k.add(types.InlineKeyboardButton("📣 Создать кампанию",callback_data="ad_create"));k.add(types.InlineKeyboardButton("📋 Активные кампании",callback_data="ad_active"));k.add(types.InlineKeyboardButton("📊 Результаты",callback_data="ad_results"));k.add(types.InlineKeyboardButton("📜 История рекламы",callback_data="ad_history"));k.add(types.InlineKeyboardButton("🔙 Назад",callback_data="open_biz"));edit_callback(call,text,k);bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="ad_create")
def ad_create(call):
    k=types.InlineKeyboardMarkup()
    for amt in (1000,5000,10000,25000,50000):k.add(types.InlineKeyboardButton(format_money(amt),callback_data=f"ad_amt_{amt}"))
    edit_callback(call,"[ 📣 ] <b>Создание рекламной кампании.</b>\n\nВыбери бюджет кампании. Деньги будут списаны со счёта бизнеса после запуска.",k);bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data.startswith("ad_amt_"))
def ad_amt(call):
    uid=call.from_user.id;amt=int(call.data.split("_")[-1]);b=business(uid)
    if b['balance']<amt:bot.answer_callback_query(call.id,"Недостаточно средств.",show_alert=True);return
    k=types.InlineKeyboardMarkup()
    for days in (1,3,7,14,30):k.add(types.InlineKeyboardButton(f"{days} дн.",callback_data=f"ad_launch_{amt}_{days}"))
    edit_callback(call,f"[ ⏱️ ] <b>Срок кампании.</b>\n\nБюджет: <b>{format_money(amt)}</b>\n\nВыбери срок.",k);bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data.startswith("ad_launch_"))
def ad_launch(call):
    uid=call.from_user.id;b=business(uid);_,_,amt,days=call.data.split("_");amt=int(amt);days=int(days)
    if b['balance']<amt:bot.answer_callback_query(call.id,"Недостаточно средств.",show_alert=True);return
    eff=max(20,min(100,50+int((b['equipment_performance']-100)/2)+int(staff_eff(b)/10)))
    reach=int(amt*3.5*(eff/100));clients=max(1,int(reach*0.005));sales=clients*200
    b['balance']-=amt;b['expenses']+=amt;b['marketing_spent']+=amt;b['marketing_efficiency']=eff;b['clients']+=clients;b['income']+=sales
    camp={"budget":amt,"days":days,"reach":reach,"clients":clients,"sales":sales,"eff":eff};b['campaign_history'].append(camp);record_op(b,'marketing',amt,f'Рекламная кампания на {days} дн.');sync_player(uid)
    edit_callback(call,f"[ 📣 ] <b>Кампания запущена.</b>\n\n<blockquote>💰 Бюджет: {format_money(amt)}\n\n⏱️ Срок: {days} дн.\n\n👁️ Охват: {reach}\n\n👤 Клиенты: {clients}\n\n📈 Продажи: {format_money(sales)}\n\n⚡ Эффективность: {eff}%</blockquote>\n\nРезультат зависит от бюджета, состояния бизнеса, персонала и эффективности рекламы.",inline_back("b_marketing"));bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="ad_active")
def ad_active(call):edit_callback(call,"[ 📋 ] <b>Активные кампании.</b>\n\n<blockquote>📣 Активных кампаний: 0</blockquote>\n\nВ этой версии результаты кампании рассчитываются при запуске.",inline_back("b_marketing"));bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="ad_results")
def ad_results(call):
    b=business(call.from_user.id);body="\n\n".join(f"📣 Кампания\n\n💰 Бюджет: {format_money(x['budget'])}\n\n👁️ Охват: {x['reach']}\n\n👤 Клиенты: {x['clients']}\n\n📈 Продажи: {format_money(x['sales'])}" for x in b['campaign_history'][-5:]) or "Результатов пока нет.";edit_callback(call,f"[ 📊 ] <b>Результаты рекламы.</b>\n\n<blockquote>{body}</blockquote>",inline_back("b_marketing"));bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="ad_history")
def ad_history(call):
    b=business(call.from_user.id);body="\n\n".join(f"📣 {format_money(x['budget'])} / {x['days']} дн.\n👤 Клиенты: {x['clients']}\n📈 Продажи: {format_money(x['sales'])}" for x in b['campaign_history']) or "История рекламы пуста.";edit_callback(call,f"[ 📜 ] <b>История рекламы.</b>\n\n<blockquote>{body}</blockquote>",inline_back("b_marketing"));bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="b_partners")
def b_partners(call):
    b=business(call.from_user.id);edit_callback(call,f"[ 🤝 ] <b>Партнёры — {esc(b['name'])} №1.</b>\n\n━━━━━━━━━━━━━━━━━━\n\n<blockquote>🤝 Активных партнёров: {len(b['partners'])}\n\n📄 Активных договоров: {len(b['contracts'])}\n\n💰 Доход от партнёров: 0₽\n\n📉 Расходы на партнёров: 0₽\n\n📈 Прибыль от сотрудничества: 0₽</blockquote>\n\n━━━━━━━━━━━━━━━━━━\n\nНаходи партнёров, заключай договоры и развивай взаимовыгодное сотрудничество.",partners_menu());bot.answer_callback_query(call.id)

def partners_menu():
    k=types.InlineKeyboardMarkup();k.add(types.InlineKeyboardButton("🤝 Найти партнёра",callback_data="p_find"));k.add(types.InlineKeyboardButton("📄 Мои договоры",callback_data="p_contracts"));k.add(types.InlineKeyboardButton("📋 Предложения",callback_data="p_offers"));k.add(types.InlineKeyboardButton("📊 Эффективность",callback_data="p_eff"));k.add(types.InlineKeyboardButton("🔙 Назад",callback_data="open_biz"));return k

@bot.callback_query_handler(func=lambda c:c.data=="p_find")
def p_find(call):
    uid=call.from_user.id;b=business(uid);items=[]
    for oid,p in players.items():
        if oid!=uid and p.get('business'):
            ob=p['business'];items.append((oid,ob['name']))
    k=types.InlineKeyboardMarkup()
    for oid,name in items[:10]:k.add(types.InlineKeyboardButton(f"🤝 {name}",callback_data=f"p_offer_{oid}"))
    k.add(types.InlineKeyboardButton("🔙 Назад",callback_data="b_partners"))
    edit_callback(call,"[ 🤝 ] <b>Поиск партнёра.</b>\n\n━━━━━━━━━━━━━━━━━━\n\n<blockquote>🏢 Твой бизнес: {}\n\n🤝 Доступных компаний: {}</blockquote>\n\nВыбери компанию, которой хочешь отправить предложение.".format(esc(b['name']),len(items)),k);bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data.startswith("p_offer_"))
def p_offer(call):
    uid=call.from_user.id;target=int(call.data.split("_")[-1]);tb=business(target);b=business(uid)
    if not tb:bot.answer_callback_query(call.id,"Компания недоступна.");return
    offer={"from":uid,"to":target,"status":"pending"};tb['offers_in'].append(offer);b['offers_out'].append(offer);sync_player(uid);sync_player(target)
    bot.send_message(target,f"[ 🤝 ] <b>Новое предложение о сотрудничестве.</b>\n\n<blockquote>🏢 Компания: {esc(b['name'])}\n\n👤 Владелец: {esc(players[uid]['nickname'])}</blockquote>\n\nХочешь принять предложение?",reply_markup=types.InlineKeyboardMarkup(row_width=2));bot.answer_callback_query(call.id,"Предложение отправлено.")

@bot.callback_query_handler(func=lambda c:c.data=="p_contracts")
def p_contracts(call):
    b=business(call.from_user.id);body="\n\n".join(f"📄 Договор №{i+1}\n🤝 {esc(x.get('name','Партнёр'))}" for i,x in enumerate(b['contracts'])) or "Активных договоров нет.";edit_callback(call,f"[ 📄 ] <b>Договоры — {esc(b['name'])} №1.</b>\n\n<blockquote>{body}</blockquote>",partners_menu());bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="p_offers")
def p_offers(call):
    b=business(call.from_user.id);body="\n\n".join(f"📨 Предложение от {esc(players.get(x['from'],{}).get('nickname','Игрок'))}" for x in b['offers_in'] if x.get('status')=='pending') or "Новых предложений нет.";k=types.InlineKeyboardMarkup();k.add(types.InlineKeyboardButton("🔙 Назад",callback_data="b_partners"));edit_callback(call,f"[ 📋 ] <b>Предложения — {esc(b['name'])} №1.</b>\n\n<blockquote>{body}</blockquote>",k);bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="p_eff")
def p_eff(call):b=business(call.from_user.id);edit_callback(call,f"[ 📊 ] <b>Эффективность — {esc(b['name'])} №1.</b>\n\n<blockquote>🤝 Активных партнёров: {len(b['partners'])}\n\n💰 Доход: 0₽\n\n📉 Расходы: 0₽\n\n💵 Прибыль: 0₽\n\n📈 Эффективность: 0%</blockquote>",partners_menu());bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="b_manage")
def b_manage(call):
    b=business(call.from_user.id);text=f"[ ⚙️ ] <b>Управление — {esc(b['name'])} №1.</b>\n\n━━━━━━━━━━━━━━━━━━\n\n<blockquote>🏢 Название: {esc(b['name'])}\n\n💼 Сфера: {esc(b['sphere'])}\n\n📝 Описание: установлено\n\n🎨 Логотип: {'установлен' if b['logo'] else 'не установлен'}\n\n📍 Основной филиал: открыт\n\n👤 Владелец: {esc(players[call.from_user.id]['nickname'])}</blockquote>\n\n━━━━━━━━━━━━━━━━━━\n\nУправляй информацией о бизнесе, доступом и действиями компании.""";k=types.InlineKeyboardMarkup();k.add(types.InlineKeyboardButton("✏️ Изменить информацию",callback_data="m_info"));k.add(types.InlineKeyboardButton("🎨 Изменить логотип",callback_data="m_logo"));k.add(types.InlineKeyboardButton("👥 Доступ к управлению",callback_data="m_access"));k.add(types.InlineKeyboardButton("📋 Журнал действий",callback_data="m_log"));k.add(types.InlineKeyboardButton("⚠️ Управление бизнесом",callback_data="m_danger"));k.add(types.InlineKeyboardButton("🔙 Назад",callback_data="open_biz"));edit_callback(call,text,k);bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="m_info")
def m_info(call):
    k=types.InlineKeyboardMarkup();k.row(types.InlineKeyboardButton("🏢 Название",callback_data="m_name"),types.InlineKeyboardButton("💼 Сфера",callback_data="m_sphere"));k.add(types.InlineKeyboardButton("📝 Описание",callback_data="m_desc"));k.add(types.InlineKeyboardButton("🔙 Назад",callback_data="b_manage"));edit_callback(call,"[ ✏️ ] <b>Изменение информации.</b>\n\nВыбери, какую информацию изменить.",k);bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data in {"m_name","m_sphere","m_desc"})
def m_info_action(call):
    uid=call.from_user.id
    if call.data=="m_name":admin_states[uid]={"state":"edit_name"};prompt="[ 🏢 ] <b>Новое название.</b>\n\nОтправь новое название бизнеса."
    elif call.data=="m_desc":admin_states[uid]={"state":"edit_desc"};prompt="[ 📝 ] <b>Новое описание.</b>\n\nОтправь новое описание от 10 до 500 символов."
    else:
        admin_states[uid]={"state":"edit_sphere"};prompt="[ 💼 ] <b>Новая сфера.</b>\n\nОтправь новую сферу деятельности."
    edit_callback(call,prompt,inline_back("m_info"));bot.answer_callback_query(call.id)

@bot.message_handler(content_types=["text"],func=lambda m:m.from_user.id in admin_states and admin_states[m.from_user.id].get("state") in {"edit_name","edit_desc","edit_sphere"})
def edit_business_text(message):
    uid=message.from_user.id;s=admin_states.pop(uid);b=business(uid);state=s['state'];val=message.text.strip()
    if state=="edit_name" and not 3<=len(val)<=30:bot.send_message(message.chat.id,"[ ❌ ] Название должно содержать от 3 до 30 символов.");return
    if state=="edit_desc" and not 10<=len(val)<=500:bot.send_message(message.chat.id,"[ ❌ ] Описание должно содержать от 10 до 500 символов.");return
    if state=="edit_name":b['name']=val
    elif state=="edit_desc":b['description']=val
    else:b['sphere']=val
    record_op(b,'management',0,'Изменена информация о бизнесе');sync_player(uid);bot.send_message(message.chat.id,"[ ✅ ] <b>Информация обновлена.</b>",reply_markup=inline_back("b_manage"))

@bot.callback_query_handler(func=lambda c:c.data=="m_logo")
def m_logo(call):admin_states[call.from_user.id]={"state":"edit_logo"};edit_callback(call,"[ 🎨 ] <b>Изменение логотипа.</b>\n\nОтправь новое изображение логотипа фотографией.",inline_back("b_manage"));bot.answer_callback_query(call.id)

@bot.message_handler(content_types=["photo"],func=lambda m:m.from_user.id in admin_states and admin_states[m.from_user.id].get("state")=="edit_logo")
def edit_logo(message):
    uid=message.from_user.id;b=business(uid);b['logo']=message.photo[-1].file_id;admin_states.pop(uid,None);sync_player(uid);bot.send_message(message.chat.id,"[ ✅ ] <b>Логотип успешно изменён.</b>",reply_markup=inline_back("b_manage"))

@bot.callback_query_handler(func=lambda c:c.data=="m_access")
def m_access(call):edit_callback(call,"[ 👥 ] <b>Доступ к управлению.</b>\n\n<blockquote>👤 Владельцев: 1\n\n👥 Управляющих: 0\n\n🔐 Доступов выдано: 0</blockquote>\n\nСистема ролей подготовлена для дальнейшего назначения управляющих.",inline_back("b_manage"));bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="m_log")
def m_log(call):
    b=business(call.from_user.id);body="\n\n".join(f"📌 {esc(x['text'])}" for x in reversed(b['operations'][-10:])) or "Действий пока нет.";edit_callback(call,f"[ 📋 ] <b>Журнал действий.</b>\n\n<blockquote>{body}</blockquote>",inline_back("b_manage"));bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="m_danger")
def m_danger(call):
    b=business(call.from_user.id);k=types.InlineKeyboardMarkup();k.add(types.InlineKeyboardButton("⏸️ Приостановить бизнес",callback_data="m_suspend"));k.add(types.InlineKeyboardButton("🔄 Передать бизнес",callback_data="m_transfer"));k.add(types.InlineKeyboardButton("🗑️ Закрыть бизнес",callback_data="m_close"));k.add(types.InlineKeyboardButton("🔙 Назад",callback_data="b_manage"));edit_callback(call,f"[ ⚠️ ] <b>Управление бизнесом.</b>\n\n<blockquote>🏢 {esc(b['name'])} №1\n\n👤 Владелец: {esc(players[call.from_user.id]['nickname'])}\n\n⭐ Уровень: {b['level']}\n\n🏪 Филиалов: {len(b['branches_list'])}</blockquote>\n\nВыбери действие.",k);bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="m_suspend")
def m_suspend(call):
    uid=call.from_user.id;b=business(uid);b['suspended']=not b['suspended'];sync_player(uid);edit_callback(call,f"[ {'⏸️' if b['suspended'] else '▶️'} ] <b>Бизнес {'приостановлен' if b['suspended'] else 'возобновлён'}.</b>",inline_back("m_danger"));bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="m_close")
def m_close(call):
    uid=call.from_user.id;k=types.InlineKeyboardMarkup();k.add(types.InlineKeyboardButton("🗑️ Да, закрыть",callback_data="m_close_yes"),types.InlineKeyboardButton("↩️ Отмена",callback_data="m_danger"));edit_callback(call,"[ ⚠️ ] <b>Закрыть бизнес?</b>\n\nПосле подтверждения бизнес будет удалён, а восстановить его нельзя.",k);bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="m_close_yes")
def m_close_yes(call):
    uid=call.from_user.id;players[uid]['business']=None;players[uid]['businesses']=0;players[uid]['branches']=0;players[uid]['employees']=0;players[uid]['business_balance']=0;players[uid]['level']=0;save_data();edit_callback(call,"[ 🗑️ ] <b>Бизнес закрыт.</b>",inline_back("b_main_back"));bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="m_transfer")
def m_transfer(call):
    uid=call.from_user.id
    admin_states[uid]={"state":"transfer_business"}
    edit_callback(call,"""[ 🔄 ] <b>Передача бизнеса.</b>

Отправь Telegram ID игрока, которому хочешь передать бизнес.

⚠️ Получатель должен отдельно подтвердить передачу.""",inline_back("m_danger"))
    bot.answer_callback_query(call.id)

@bot.message_handler(content_types=["text"],func=lambda m:m.from_user.id in admin_states and admin_states[m.from_user.id].get("state")=="transfer_business")
def receive_transfer_business(message):
    uid=message.from_user.id
    try: target=int(message.text.strip())
    except ValueError: return
    b=business(uid)
    if target not in players or target==uid or not b: return
    if business(target):
        bot.send_message(message.chat.id,"[ ❌ ] <b>Передача невозможна.</b>\n\nУ выбранного игрока уже есть собственный бизнес.")
        return
    tid=f"{uid}_{target}_{int(time.time())}"
    pending_transfers[tid]={"from":uid,"to":target}
    admin_states.pop(uid,None)
    k=types.InlineKeyboardMarkup();k.row(types.InlineKeyboardButton("📤 Отправить предложение",callback_data=f"transfer_send_{tid}"),types.InlineKeyboardButton("↩️ Отмена",callback_data="m_danger"))
    bot.send_message(message.chat.id,f"""[ 🔄 ] <b>Передача бизнеса.</b>

<blockquote>🏢 Бизнес: {esc(b['name'])}

👤 Получатель: {esc(players[target]['nickname'])}

🆔 Telegram ID: <code>{target}</code></blockquote>

━━━━━━━━━━━━━━━━━━

После отправки игрок получит предложение и сможет принять или отклонить его.""",reply_markup=k)

@bot.callback_query_handler(func=lambda c:c.data.startswith("transfer_send_"))
def transfer_send(call):
    tid=call.data.replace("transfer_send_",""); data=pending_transfers.get(tid)
    if not data or data["from"]!=call.from_user.id: return
    b=business(data["from"]); target=data["to"]
    if not b: return
    k=types.InlineKeyboardMarkup();k.row(types.InlineKeyboardButton("✅ Принять",callback_data=f"transfer_accept_{tid}"),types.InlineKeyboardButton("❌ Отказать",callback_data=f"transfer_decline_{tid}"))
    bot.send_message(target,f"""[ 🔄 ] <b>Передача бизнеса.</b>

Игрок <b>{esc(players[data['from']]['nickname'])}</b> хочет передать тебе свой бизнес.

━━━━━━━━━━━━━━━━━━

<blockquote>🏢 Бизнес: {esc(b['name'])}

💼 Сфера: {esc(b['sphere'])}

⭐ Уровень: {b['level']}

🏪 Филиалов: {len(b['branches_list'])}</blockquote>

━━━━━━━━━━━━━━━━━━

Прими передачу, если согласен стать владельцем бизнеса.""",reply_markup=k)
    edit_callback(call,"[ 📤 ] <b>Предложение отправлено игроку.</b>",inline_back("m_danger"));bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data.startswith("transfer_accept_"))
def transfer_accept(call):
    tid=call.data.replace("transfer_accept_",""); data=pending_transfers.get(tid)
    if not data or data["to"]!=call.from_user.id: return
    old_owner,new_owner=data["from"],data["to"]; b=business(old_owner)
    if not b or business(new_owner): bot.answer_callback_query(call.id,"Передача больше недоступна.",show_alert=True); return
    b["owner_id"]=new_owner
    players[new_owner]["business"]=b; players[old_owner]["business"]=None
    players[old_owner]["businesses"]=0;players[old_owner]["branches"]=0;players[old_owner]["employees"]=0;players[old_owner]["business_balance"]=0;players[old_owner]["level"]=0
    players[new_owner]["businesses"]=1;players[new_owner]["branches"]=len(b["branches_list"]);players[new_owner]["employees"]=len(b["employees_list"]);players[new_owner]["business_balance"]=b["balance"];players[new_owner]["level"]=b["level"]
    record_op(b,"management",0,f"Бизнес передан игроку {new_owner}");pending_transfers.pop(tid,None);save_data()
    bot.send_message(old_owner,f"[ ✅ ] <b>Бизнес передан.</b>\n\nИгрок <b>{esc(players[new_owner]['nickname'])}</b> принял бизнес <b>{esc(b['name'])}</b>.")
    edit_callback(call,"[ ✅ ] <b>Ты стал владельцем бизнеса.</b>\n\nБизнес успешно передан тебе.",inline_back("b_main_back"));bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data.startswith("transfer_decline_"))
def transfer_decline(call):
    tid=call.data.replace("transfer_decline_",""); data=pending_transfers.get(tid)
    if not data or data["to"]!=call.from_user.id: return
    pending_transfers.pop(tid,None)
    bot.send_message(data["from"],"[ ❌ ] <b>Передача бизнеса отклонена.</b>\n\nПолучатель отказался от передачи бизнеса.")
    edit_callback(call,"[ ❌ ] <b>Передача бизнеса отклонена.</b>",inline_back("b_main_back"));bot.answer_callback_query(call.id)


@bot.message_handler(func=lambda m:m.text=="👤 Профиль")
def profile(message):
    p=players.get(message.from_user.id)
    if not p:return
    bot.send_message(message.chat.id,f"""[ 👤 ] <b>Профиль игрока {esc(p['nickname'])}.</b>

━━━━━━━━━━━━━━━━━━

<blockquote>💰 Баланс – {format_money(p['balance'])}.

🏢 Бизнесов – {p['businesses']}.

🏪 Филиалов – {p['branches']}.

👥 Сотрудников – {p['employees']}.

💳 Баланс бизнеса – {format_money(p['business_balance'])}.

⭐ Уровень – {p['level']}.</blockquote>

━━━━━━━━━━━━━━━━━━""",reply_markup=inline_back("profile_back"))

@bot.callback_query_handler(func=lambda c:c.data=="profile_back")
def profile_back(call):bot.answer_callback_query(call.id);show_main_menu(call.message.chat.id,call.from_user.id)

@bot.message_handler(func=lambda m:m.text=="⚙️ Настройки")
def settings(message):
    k=types.InlineKeyboardMarkup();k.add(types.InlineKeyboardButton("🔔 Уведомления",callback_data="notifications"));bot.send_message(message.chat.id,"[ ⚙️ ] <b>Настройки – Jobserf.</b>",reply_markup=k)

@bot.callback_query_handler(func=lambda c:c.data=="notifications")
def notifications(call):
    p=players[call.from_user.id];status="🔔 На данный момент уведомления включены." if p['notifications'] else "🔕 На данный момент уведомления выключены.";k=types.InlineKeyboardMarkup();k.row(types.InlineKeyboardButton("🔛 Включить",callback_data="notifications_on"),types.InlineKeyboardButton("📴 Выключить",callback_data="notifications_off"));k.add(types.InlineKeyboardButton("🔙 Назад",callback_data="settings_back"));edit_callback(call,f"[ 🔔 ] <b>Уведомления.</b>\n\nЗдесь ты можешь управлять уведомлениями от Jobserf.\n\n{status}",k);bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="notifications_on")
def notifications_on(call):players[call.from_user.id]['notifications']=True;save_data();edit_callback(call,"[ ✅ ] <b>Уведомления успешно включены.</b>",inline_back("settings_back"));bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="notifications_off")
def notifications_off(call):
    k=types.InlineKeyboardMarkup();k.row(types.InlineKeyboardButton("📴 Да",callback_data="notifications_yes"),types.InlineKeyboardButton("↩️ Отмена",callback_data="notifications"));edit_callback(call,"[ ⚠️ ] <b>Отключить уведомления?</b>\n\nПосле отключения ты не будешь получать уведомления от Jobserf.\n\nЭто может привести к тому, что ты пропустишь важные события, сообщения и изменения, связанные с твоим бизнесом.\n\nТы действительно хочешь отключить уведомления?",k);bot.answer_callback_query(call.id)
@bot.callback_query_handler(func=lambda c:c.data=="notifications_yes")
def notifications_yes(call):players[call.from_user.id]['notifications']=False;save_data();edit_callback(call,"[ ✅ ] <b>Уведомления успешно отключены.</b>",inline_back("settings_back"));bot.answer_callback_query(call.id)
@bot.callback_query_handler(func=lambda c:c.data=="settings_back")
def settings_back(call):
    k=types.InlineKeyboardMarkup();k.add(types.InlineKeyboardButton("🔔 Уведомления",callback_data="notifications"))
    edit_callback(call,"[ ⚙️ ] <b>Настройки – Jobserf.</b>",k);bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m:m.text=="🆘 Поддержка")
def support(message):
    k=types.InlineKeyboardMarkup();k.add(types.InlineKeyboardButton("📩 Обратиться в поддержку",callback_data="support_create"));k.add(types.InlineKeyboardButton("🔙 Назад",callback_data="support_back"));bot.send_message(message.chat.id,"""[ 🆘 ] <b>Поддержка Jobserf.</b>

Возникли вопросы, столкнулись с ошибкой или вам нужна помощь?

Здесь ты можешь обратиться в службу поддержки Jobserf и получить помощь по игровым вопросам.""",reply_markup=k)
@bot.callback_query_handler(func=lambda c:c.data=="support_back")
def support_back(call):bot.answer_callback_query(call.id);show_main_menu(call.message.chat.id,call.from_user.id)
@bot.callback_query_handler(func=lambda c:c.data=="support_create")
def support_create(call):
    uid=call.from_user.id
    if time.time()-support_cooldown.get(uid,0)<120:edit_callback(call,"[ ⏳ ] <b>Слишком частые обращения.</b>\n\nТы уже отправил обращение в службу поддержки. Повторно обратиться можно будет через 2 минуты.\n\nПожалуйста, дождись окончания ограничения.",inline_back("support_back"));bot.answer_callback_query(call.id);return
    players[uid]['support_waiting']=True;edit_callback(call,"📩 Опиши свою проблему как можно подробнее, чтобы мы могли быстрее разобраться в ситуации.");bot.answer_callback_query(call.id)
@bot.message_handler(content_types=["text","photo"],func=lambda m:m.from_user.id in players and players[m.from_user.id].get('support_waiting',False))
def receive_support(message):
    uid=message.from_user.id;players[uid]['support_waiting']=False;support_cooldown[uid]=time.time();p=players[uid];txt=message.caption if message.content_type=='photo' else message.text;cap=f"[ 🆘 ] <b>Новое обращение.</b>\n\n<blockquote>👤 Игрок: {esc(p['nickname'])}\n\n🆔 Telegram ID: <code>{uid}</code></blockquote>\n\n<blockquote>{esc(txt or 'Без текста')}</blockquote>";k=types.InlineKeyboardMarkup();k.add(types.InlineKeyboardButton("💁‍♀️ Ответить",callback_data=f"sup_reply_{uid}"));
    for aid in list(ADMIN_IDS):
        try:
            if message.content_type=='photo':bot.send_photo(aid,message.photo[-1].file_id,caption=cap,reply_markup=k)
            else:bot.send_message(aid,cap,reply_markup=k)
        except:pass
    bot.send_message(message.chat.id,"[ ✅ ] <b>Обращение отправлено.</b>\n\nСпасибо! Твоё обращение успешно передано в службу поддержки Jobserf.\n\nМы рассмотрим его и постараемся помочь как можно скорее.",reply_markup=inline_back("support_back"))
@bot.callback_query_handler(func=lambda c:c.data.startswith("sup_reply_"))
def sup_reply(call):
    if not is_admin(call.from_user.id):return
    target=int(call.data.split('_')[-1]);admin_states[call.from_user.id]={"state":"sup_reply","target":target};bot.send_message(call.message.chat.id,f"[ 💁‍♀️ ] <b>Ответ на обращение.</b>\n\n<blockquote>Игрок: {esc(players.get(target,{}).get('nickname','Игрок'))}\n\nTelegram ID: {target}</blockquote>\n\nНапиши сообщение, которое хочешь отправить пользователю.")
@bot.message_handler(content_types=["text"],func=lambda m:m.from_user.id in admin_states and admin_states[m.from_user.id].get('state')=='sup_reply')
def sup_reply_msg(message):
    s=admin_states.pop(message.from_user.id);target=s['target'];
    try:bot.send_message(target,f"[ 🆘 ] <b>Ответ от службы поддержки.</b>\n\n━━━━━━━━━━━━━━━━━━\n\n<blockquote>💁‍♀️ <b>Ответ администратора:</b>\n\n{esc(message.text)}</blockquote>")
    except:pass
    bot.send_message(message.chat.id,"[ ✅ ] <b>Ответ отправлен пользователю.</b>")

@bot.my_chat_member_handler()
def track_chat(message):
    status=getattr(message.new_chat_member,'status','')
    if status in {'member','administrator','creator'}:known_chats.add(message.chat.id)
    elif status in {'left','kicked'}:known_chats.discard(message.chat.id)
    save_data()

@bot.message_handler(func=lambda m:m.text=="🎚️ Админ панель")
def admin_panel(message):
    if not is_admin(message.from_user.id):return
    k=types.InlineKeyboardMarkup();k.add(types.InlineKeyboardButton("➕ Выдать администратора",callback_data="give_admin"));k.add(types.InlineKeyboardButton("💰 Выдать деньги",callback_data="give_money"));k.add(types.InlineKeyboardButton("📤 Рассылка",callback_data="broadcast"));k.add(types.InlineKeyboardButton("🔃 Сброс БД",callback_data="reset_db"));k.add(types.InlineKeyboardButton("🔙 Назад",callback_data="admin_main_back"));bot.send_message(message.chat.id,"[ 🎚️ ] <b>Админ панель.</b>\n\nДобро пожаловать в панель управления Jobserf, администратор.",reply_markup=k)
@bot.callback_query_handler(func=lambda c:c.data=="admin_back")
def admin_back(call):
    if not is_admin(call.from_user.id): return
    k=types.InlineKeyboardMarkup()
    k.add(types.InlineKeyboardButton("➕ Выдать администратора",callback_data="give_admin"))
    k.add(types.InlineKeyboardButton("💰 Выдать деньги",callback_data="give_money"))
    k.add(types.InlineKeyboardButton("📤 Рассылка",callback_data="broadcast"))
    k.add(types.InlineKeyboardButton("🔃 Сброс БД",callback_data="reset_db"))
    k.add(types.InlineKeyboardButton("🔙 Назад",callback_data="admin_main_back"))
    edit_callback(call,"[ 🎚️ ] <b>Админ панель.</b>\n\nДобро пожаловать в панель управления Jobserf, администратор.",k)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="admin_main_back")
def admin_main_back(call):
    bot.answer_callback_query(call.id)
    show_main_menu(call.message.chat.id,call.from_user.id)
@bot.callback_query_handler(func=lambda c:c.data=="give_admin")
def give_admin(call):admin_states[call.from_user.id]={"state":"give_admin"};edit_callback(call,"[ ➕ ] <b>Выдача администратора.</b>\n\nОтправь Telegram ID пользователя, которому хочешь выдать права администратора.\n\n⚠️ Убедись, что ID указан правильно. После выдачи пользователь получит доступ к админ-панели Jobserf.",inline_back("admin_back"));bot.answer_callback_query(call.id)
@bot.message_handler(content_types=["text"],func=lambda m:is_admin(m.from_user.id) and m.from_user.id in admin_states and admin_states[m.from_user.id].get('state')=='give_admin')
def give_admin_msg(message):
    try:target=int(message.text.strip())
    except:return
    if target not in players:return
    ADMIN_IDS.add(target);admin_states.pop(message.from_user.id,None);save_data();bot.send_message(message.chat.id,f"[ ✅ ] <b>Администратор назначен.</b>\n\nПользователь с Telegram ID <code>{target}</code> теперь имеет доступ к админ-панели.",reply_markup=inline_back("admin_back"))
@bot.callback_query_handler(func=lambda c:c.data=="give_money")
def give_money(call):admin_states[call.from_user.id]={"state":"give_money"};edit_callback(call,"[ 💰 ] <b>Выдача денег.</b>\n\nОтправь Telegram ID пользователя, которому хочешь выдать деньги.\n\nПосле этого укажи сумму, которую необходимо зачислить на баланс пользователя.",inline_back("admin_back"));bot.answer_callback_query(call.id)
@bot.message_handler(content_types=["text"],func=lambda m:is_admin(m.from_user.id) and m.from_user.id in admin_states and admin_states[m.from_user.id].get('state')=='give_money')
def give_money_msg(message):
    try:target,amt=[x.strip() for x in message.text.split(',',1)];target=int(target);amt=int(amt)
    except:return
    if target not in players or not 0<=amt<=1_000_000_000:return
    players[target]['balance']+=amt;admin_states.pop(message.from_user.id,None);save_data();bot.send_message(message.chat.id,f"[ ✅ ] <b>Деньги выданы.</b>\n\nПользователю с Telegram ID {target} успешно зачислено {format_money(amt)}.",reply_markup=inline_back("admin_back"))
@bot.callback_query_handler(func=lambda c:c.data=="reset_db")
def reset_db(call):
    if not is_admin(call.from_user.id): return
    k=types.InlineKeyboardMarkup()
    k.row(types.InlineKeyboardButton("✅ Да",callback_data="reset_db_yes"),types.InlineKeyboardButton("❌ Отмена",callback_data="reset_db_no"))
    edit_callback(call,"Вы действительно хотите сбросить базу данных 🔃?",k)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c:c.data=="reset_db_no")
def reset_db_no(call):
    if not is_admin(call.from_user.id): return
    admin_states.pop(call.from_user.id,None)
    bot.answer_callback_query(call.id)
    show_main_menu(call.message.chat.id,call.from_user.id)

@bot.callback_query_handler(func=lambda c:c.data=="reset_db_yes")
def reset_db_yes(call):
    if not is_admin(call.from_user.id): return
    global players, registration, support_cooldown, admin_states, known_chats, pending_transfers
    players={}
    registration={}
    support_cooldown={}
    admin_states={}
    known_chats=set()
    pending_transfers={}
    save_data()
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id,"[ ✅ ] Прогресс сброшен.")
    show_main_menu(call.message.chat.id,call.from_user.id)

@bot.callback_query_handler(func=lambda c:c.data=="broadcast")
def broadcast(call):admin_states[call.from_user.id]={"state":"broadcast"};edit_callback(call,"[ 📤 ] <b>Рассылка.</b>\n\nЗдесь ты можешь отправить сообщение всем пользователям и чатам, в которых присутствует бот.\n\n⚠️ Перед отправкой убедись, что сообщение полностью готово. Оно будет отправлено всем доступным получателям.",inline_back("admin_back"));bot.answer_callback_query(call.id)
@bot.message_handler(content_types=["text","photo","video","document","animation","audio","voice","sticker"],func=lambda m:is_admin(m.from_user.id) and m.from_user.id in admin_states and admin_states[m.from_user.id].get('state')=='broadcast')
def broadcast_msg(message):
    admin_states[message.from_user.id]={"state":"broadcast_confirm","src_chat":message.chat.id,"src_msg":message.message_id};k=types.InlineKeyboardMarkup();k.row(types.InlineKeyboardButton("📤 Да, отправить",callback_data="broadcast_yes"),types.InlineKeyboardButton("↩️ Отмена",callback_data="admin_back"));bot.send_message(message.chat.id,"[ ⚠️ ] <b>Подтвердить рассылку?</b>\n\nСообщение будет отправлено всем доступным пользователям и чатам.\n\nВы действительно хотите начать рассылку?",reply_markup=k)
@bot.callback_query_handler(func=lambda c:c.data=="broadcast_yes")
def broadcast_yes(call):
    s=admin_states.pop(call.from_user.id,None)
    if not s:return
    rec={uid for uid,p in players.items() if p.get('notifications',True)}|known_chats;ok=bad=0
    for rid in rec:
        try:bot.copy_message(rid,s['src_chat'],s['src_msg']);ok+=1
        except:bad+=1
    bot.edit_message_text(f"[ 📤 ] <b>Рассылка завершена.</b>\n\n━━━━━━━━━━━━━━━━━━\n\n<blockquote>👥 Получателей: {len(rec)}\n\n✅ Успешно: {ok}\n\n❌ Не доставлено: {bad}</blockquote>\n\n━━━━━━━━━━━━━━━━━━",call.message.chat.id,call.message.message_id,reply_markup=inline_back("admin_back"));bot.answer_callback_query(call.id)

@bot.message_handler(content_types=["text"])
def unknown(message):return

load_data()

if __name__=="__main__":
    print("Jobserf запущен.")
    bot.delete_webhook(drop_pending_updates=True)
    bot.infinity_polling(skip_pending=True,timeout=30,long_polling_timeout=30)
