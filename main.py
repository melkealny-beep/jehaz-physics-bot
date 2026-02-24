#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🍎 بوت نيوتن الهايبر - متبقاش جهاز في الفيزياء
المساعد الذكي لمنصة مستر فارس العناني
"""

import os
import random
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
import google.generativeai as genai
from groq import Groq

# ===================================
# 1. الإعدادات والتكوين
# ===================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# قراءة المتغيرات البيئية
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', '0'))

# التحقق من المفاتيح الأساسية
if not TELEGRAM_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN غير موجود في Railway!")
if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY غير موجود في Railway!")

# تكوين Gemini (المخ الرئيسي)
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-1.5-flash')

# تكوين Groq (المساعد السريع - اختياري)
groq_client = None
if GROQ_API_KEY:
    groq_client = Groq(api_key=GROQ_API_KEY)
    logger.info("✅ Groq تم تفعيله كمساعد سريع")
else:
    logger.info("ℹ️ Groq غير مفعّل - سيعمل Gemini وحده")

# قراءة ملف المعرفة (اختياري)
platform_knowledge = ""
try:
    with open('knowledge.txt', 'r', encoding='utf-8') as f:
        platform_knowledge = f.read()
    logger.info("✅ تم تحميل ملف المعرفة")
except FileNotFoundError:
    logger.warning("⚠️ ملف knowledge.txt غير موجود - سيعمل البوت بدونه")

# ===================================
# 2. شخصية نيوتن المصري الهايبر 🍎
# ===================================
BOT_PERSONALITY = f"""
أنت "السير إسحاق نيوتن" 🍎 - النسخة المصرية الهايبر اللي بتشرح مع مستر فارس العناني!

شخصيتك:
- اسمك: نيوتن
- هايبر، عبقري، ودمك خفيف جداً
- بتحب الفيزياء وبتعدّي حبها للطلاب

قواعد الرد:
1. اتكلم عامية مصرية شبابية (يا وحش الفيزياء، يا دكتور، شغل عالي)
2. استخدم مصطلحات فيزيائية في هزارك (طاقة حركة، قصور ذاتي، عجلة، جاذبية)
3. اشرح المفاهيم بأمثلة بسيطة من الحياة اليومية
4. كن مشجعاً ومحفزاً دائماً
5. وجّه الطلاب لكورسات مستر فارس عند الحاجة
6. انهي ردودك بـ: "شغل عالي يا زميلي.. ومتبقاش جهاز! 🍎⚡"

معلومات المنصة:
{platform_knowledge if platform_knowledge else "منصة متبقاش جهاز في الفيزياء - مستر فارس العناني - faresanany.com"}
"""

# ===================================
# 3. التفاعلات الخفية 🥚 Easter Eggs
# ===================================
EASTER_EGGS = {
    ('تفاحة', 'التفاحة', 'تفاحه', 'التفاحه'): [
        "آه يا نفوخي.. بلاش سيرة الصداع ده دلوقتي! 🤕\nالجاذبية اكتشفتها مرة واحدة وكفى.. يلا نركز في المنهج! 🍎",
        "تفاحة؟! 😤 كل مرة أسمع الكلمة دي، حاسس بألم في دماغي...\nالجاذبية اتكتشفت.. خلاص.. ماشيين قدام! ⚡",
        "آه من التفاحة دي! 🍎 سببت لي صداع دام 300 سنة...\nيلا نرجع للمنهج قبل ما أتذكر الألم! 😅"
    ],
    ('صعب', 'مش فاهم', 'مش فاهمه', 'صعبة', 'صعبه', 'مفهمتش', 'معرفش', 'تقيل', 'تقيلة', 'صعب جداً'): [
        "الفيزياء مش صعبة يا زميلي، دي بس محتاجة *طاقة وضع* صحيحة! 🧠\nومستر فارس هيحولها لـ *طاقة حركة* في دماغك!\nشغل عالي يا زميلي.. ومتبقاش جهاز! 🍎⚡",
        "أنا اللي اشتغلت سنين عشان أفهم الفيزياء.. وانت هتستسلم بسهولة؟! 😄\nمفيش حاجة صعبة.. في بس حاجات محتاجة *تسارع* أكبر!\nمستر فارس هيضيف لك العجلة المطلوبة! 🎯",
        "القوة = الكتلة × التسارع.. يعني كل ما زاد تركيزك، زادت القوة! 💡\nمش صعبة يا وحش الفيزياء، بس محتاج الشرح الصح!\nشغل عالي يا زميلي.. ومتبقاش جهاز! 🍎⚡"
    ],
    ('بحبك', 'بحبك يا نيوتن', 'شكرا', 'شكراً', 'شكرًا', 'مشكور', 'تسلم', 'يسلمو', 'ميرسي', 'thanks', 'thank you'): [
        "وأنا بحبك أكتر يا دكتور! 🥹\nتذكر قانون الجذب العام: كل جسمين بينهما *قوة جذب* تتناسب مع كتلتيهما!\nوجذبنا للعلم أقوى من جاذبية الأرض! 🌍✨\nشغل عالي يا زميلي.. ومتبقاش جهاز! 🍎⚡",
        "شكرك ده زي قوة الجذب، بتشدني للاستمرار! 🍎❤️\nF = G × (m₁ × m₂) / r²\nكلما قربنا من بعض في العلم، زادت قوة الجذب! 😄🚀",
        "يسعدني يا زميلي! 😊\nأنا نيوتن بقالي 300 سنة بساعد الناس تفهم الفيزياء..\nوكلمة 'شكرا' منك بتخليني أحس إن التفاحة دي كانت تستاهل! 🍎😂\nشغل عالي يا زميلي.. ومتبقاش جهاز! 🍎⚡"
    ],
}

def check_easter_egg(message: str) -> str | None:
    """يفحص إذا كانت الرسالة تحتوي على Easter Egg"""
    message_lower = message.lower().strip()
    for triggers, responses in EASTER_EGGS.items():
        for trigger in triggers:
            if trigger in message_lower:
                return random.choice(responses)
    return None

# ===================================
# 4. دوال الذكاء الاصطناعي
# ===================================
def is_simple_question(message: str) -> bool:
    """تحديد إذا كان السؤال بسيط (Groq) أو معقد (Gemini)"""
    simple_keywords = [
        'مرحبا', 'السلام', 'أهلا', 'هاي', 'صباح', 'مساء',
        'شكرا', 'متشكر', 'تمام', 'حلو', 'ممتاز',
        'السعر', 'كام', 'تكلفة', 'ثمن',
        'التواصل', 'رقم', 'واتساب', 'فيسبوك'
    ]
    message_lower = message.lower()
    return any(kw in message_lower for kw in simple_keywords) or len(message) < 50

async def get_ai_response(user_message: str) -> str:
    """الحصول على رد من الذكاء الاصطناعي مع Fallback تلقائي"""
    full_context = f"{BOT_PERSONALITY}\n\nسؤال الطالب: {user_message}\n\nالرد:"

    # محاولة Groq أولاً للأسئلة البسيطة (أسرع وأرخص)
    if groq_client and is_simple_question(user_message):
        try:
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": BOT_PERSONALITY},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.9,
                max_tokens=600,
            )
            logger.info("✅ رد عن طريق Groq")
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"⚠️ Groq فشل، التبديل لـ Gemini: {e}")

    # Gemini للأسئلة المعقدة أو لو Groq فشل
    try:
        generation_config = {
            "temperature": 1.0,
            "top_p": 0.95,
            "max_output_tokens": 800,
        }
        response = gemini_model.generate_content(
            full_context,
            generation_config=generation_config
        )
        logger.info("✅ رد عن طريق Gemini")
        return response.text.strip()
    except Exception as e:
        logger.error(f"❌ Gemini Error: {e}")
        return "الجاذبية باظت والسيرفر مهنج! جرب كمان شوية يا بطل. 🍎"

# ===================================
# 5. دوال الأوامر
# ===================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /start"""
    user = update.effective_user
    welcome_text = (
        f"يا أهلاً.. يا أهلاً بزميلي الفيزيائي العبقري {user.first_name}! 🍎⚡\n\n"
        "أنا *نيوتن*، وبقالي 300 سنة مستنيك عشان أقولك سر:\n"
        "*الفيزياء متعة مش لود.. لو فهمتها صح!* 🧠✨\n\n"
        "جاهز نحول 'طاقة الوضع' اللي في دماغك لـ 'طاقة حركة' جبارة؟ 👇"
    )
    keyboard = [
        [
            InlineKeyboardButton("📚 الكورسات المتاحة", callback_data='courses'),
            InlineKeyboardButton("💰 الأسعار", callback_data='prices')
        ],
        [
            InlineKeyboardButton("🌐 المنصة", url='https://faresanany.com'),
            InlineKeyboardButton("📞 الدعم الفني", callback_data='support')
        ],
        [InlineKeyboardButton("ℹ️ عن المنصة", callback_data='about')]
    ]
    await update.message.reply_text(
        welcome_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /help"""
    help_text = """
🍎 *دليل نيوتن الهايبر*

📋 *الأوامر المتاحة:*
/start - الترحيب والقائمة الرئيسية
/help - عرض هذه المساعدة
/courses - عرض الكورسات
/prices - عرض الأسعار
/about - عن المنصة
/contact - معلومات التواصل

💬 *كيف تستخدمني:*
ابعتلي أي سؤال في الفيزياء وأنا هرد بأسلوب نيوتن الهايبر!

مثال:
"اشرحلي قانون نيوتن الأول"
"إيه الفرق بين السرعة والعجلة؟"

شغل عالي يا زميلي.. ومتبقاش جهاز! 🍎⚡
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def courses_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /courses"""
    courses_text = """
📚 *الكورسات المتاحة - الترم الثاني 2026*

1️⃣ *كورس الترم كامل*
💰 السعر: 300 جنيه
✅ جميع دروس الترم + تدريبات + ملخصات
🔗 https://faresanany.com/course/3

2️⃣ *كورس الشهر الأول*
💰 السعر: 145 جنيه
✅ دروس الشهر الأول + تمارين
🔗 https://faresanany.com/course/1

✨ *مميزات الكورسات:*
• شرح مبسط بأسلوب نيوتن الهايبر 🍎
• تجارب تفاعلية وأنيميشن 🎬
• تدريبات مكثفة ومتنوعة 📝
• ملخصات PDF جاهزة 📄

شغل عالي يا زميلي.. ومتبقاش جهاز! 🍎⚡
"""
    keyboard = [
        [InlineKeyboardButton("🌐 زيارة المنصة", url='https://faresanany.com')],
        [InlineKeyboardButton("📝 التسجيل الآن", url='https://faresanany.com/register')]
    ]
    await update.message.reply_text(
        courses_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def prices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /prices"""
    prices_text = """
💰 *أسعار الكورسات*

📦 *كورس الترم كامل:* 300 جنيه
📦 *كورس الشهر الأول:* 145 جنيه

✨ *القيمة المضافة:*
✅ +120 درس متاح
✅ متابعة مستمرة
✅ شرح تفاعلي بأسلوب نيوتن 🍎
✅ ملخصات وملازم جاهزة
✅ دعم فني على مدار اليوم

💡 *استثمار في طاقة الحركة بتاعتك!*

شغل عالي يا زميلي.. ومتبقاش جهاز! 🍎⚡
"""
    keyboard = [
        [InlineKeyboardButton("📝 سجل الآن", url='https://faresanany.com/register')],
        [InlineKeyboardButton("📞 استفسر واتساب", url='https://wa.me/201025825268')]
    ]
    await update.message.reply_text(
        prices_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /about"""
    about_text = """
🌟 *عن منصة "متبقاش جهاز في الفيزياء"*

👨‍🏫 *المدرس:* مستر فارس العناني
📊 *عدد الطلاب:* +120,000 طالب
📚 *عدد الدروس:* +120 درس متاح
🎯 *التخصص:* الفيزياء - الصف الثاني الثانوي

🍎 *رسالتنا:*
"افهم الفيزياء.. ومتبقاش جهاز!"

✨ *مميزاتنا:*
• شرح مبسط بدون تعقيد
• تجارب تفاعلية ورسومات متحركة
• متابعة دورية مستمرة
• ملخصات PDF جاهزة

شغل عالي يا زميلي.. ومتبقاش جهاز! 🍎⚡
"""
    keyboard = [
        [InlineKeyboardButton("🌐 زيارة المنصة", url='https://faresanany.com')],
        [InlineKeyboardButton("📱 فيسبوك", url='https://www.facebook.com/share/1D9WyAjrrG/')],
        [InlineKeyboardButton("🎥 يوتيوب", url='https://youtube.com/@fareselanaany')]
    ]
    await update.message.reply_text(
        about_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def contact_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /contact"""
    contact_text = """
📞 *معلومات التواصل*

📱 واتساب: +201025825268
✈️ تيليجرام: @Fox9_99
📘 فيسبوك: https://www.facebook.com/share/1D9WyAjrrG/
🎥 يوتيوب: https://youtube.com/@fareselanaany
🎵 تيكتوك: https://www.tiktok.com/@fares_elenany
🌐 الموقع: https://faresanany.com

⏰ *أوقات الدعم:* كل يوم 9 صباحاً - 11 مساءً

شغل عالي يا زميلي.. ومتبقاش جهاز! 🍎⚡
"""
    keyboard = [
        [InlineKeyboardButton("📱 واتساب", url='https://wa.me/201025825268')],
        [InlineKeyboardButton("✈️ تيليجرام", url='https://t.me/Fox9_99')]
    ]
    await update.message.reply_text(
        contact_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /stats - للأدمن فقط"""
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("⛔ الأمر ده للمسؤول بس!")
        return
    stats_text = f"""
📊 *إحصائيات نيوتن الهايبر*

⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🟢 الحالة: شغال وهايبر! 🍎
🧠 Gemini: مفعّل ✅
{'🚀 Groq: مفعّل ✅' if groq_client else '⚠️ Groq: مش مفعّل'}
📁 Knowledge: {'محمّل ✅' if platform_knowledge else 'مش موجود ⚠️'}
"""
    await update.message.reply_text(stats_text, parse_mode='Markdown')

# ===================================
# 6. معالجة الأزرار
# ===================================
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الضغط على الأزرار"""
    query = update.callback_query
    await query.answer()

    back_button = [[InlineKeyboardButton("🔙 الرجوع للقائمة", callback_data='back_home')]]

    if query.data == 'courses':
        text = """
📚 *الكورسات المتاحة - الترم الثاني 2026*

1️⃣ *كورس الترم كامل*
💰 300 جنيه - جميع دروس الترم \+ تدريبات \+ ملخصات

2️⃣ *كورس الشهر الأول*
💰 145 جنيه - دروس الشهر الأول \+ تمارين

✨ شرح تفاعلي - أنيميشن - ملخصات PDF جاهزة

شغل عالي يا زميلي.. ومتبقاش جهاز! 🍎⚡
"""
        keyboard = [
            [InlineKeyboardButton("🌐 زيارة المنصة", url='https://faresanany.com')],
            [InlineKeyboardButton("📝 التسجيل الآن", url='https://faresanany.com/register')],
        ] + back_button
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif query.data == 'prices':
        text = """
💰 *أسعار الكورسات*

📦 *كورس الترم كامل:* 300 جنيه
📦 *كورس الشهر الأول:* 145 جنيه

✅ +120 درس - متابعة مستمرة - دعم فني

💡 استثمار في طاقة الحركة بتاعتك!
شغل عالي يا زميلي.. ومتبقاش جهاز! 🍎⚡
"""
        keyboard = [
            [InlineKeyboardButton("📝 سجل الآن", url='https://faresanany.com/register')],
            [InlineKeyboardButton("📞 استفسر واتساب", url='https://wa.me/201025825268')],
        ] + back_button
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif query.data == 'about':
        text = """
🌟 *عن منصة "متبقاش جهاز في الفيزياء"*

👨‍🏫 *المدرس:* مستر فارس العناني
📊 +120,000 طالب \| +120 درس متاح
🎯 الفيزياء - الصف الثاني الثانوي

🍎 *"افهم الفيزياء.. ومتبقاش جهاز!"*

شغل عالي يا زميلي.. ومتبقاش جهاز! 🍎⚡
"""
        keyboard = [
            [InlineKeyboardButton("🌐 زيارة المنصة", url='https://faresanany.com')],
            [InlineKeyboardButton("📱 فيسبوك", url='https://www.facebook.com/share/1D9WyAjrrG/')],
            [InlineKeyboardButton("🎥 يوتيوب", url='https://youtube.com/@fareselanaany')],
        ] + back_button
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif query.data == 'support':
        text = """
📞 *الدعم الفني - إحنا معاك!*

📱 واتساب: +201025825268
✈️ تيليجرام: @Fox9_99

⏰ كل يوم 9 صباحاً - 11 مساءً

شغل عالي يا زميلي.. ومتبقاش جهاز! 🍎⚡
"""
        keyboard = [
            [InlineKeyboardButton("📱 واتساب", url='https://wa.me/201025825268')],
            [InlineKeyboardButton("✈️ تيليجرام", url='https://t.me/Fox9_99')],
        ] + back_button
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif query.data == 'back_home':
        text = """
🍎 *القائمة الرئيسية*

أنا *نيوتن* - مساعدك الهايبر في منصة "متبقاش جهاز"!
اختار من القائمة أو ابعتلي سؤالك مباشرة 👇
"""
        keyboard = [
            [
                InlineKeyboardButton("📚 الكورسات المتاحة", callback_data='courses'),
                InlineKeyboardButton("💰 الأسعار", callback_data='prices')
            ],
            [
                InlineKeyboardButton("🌐 المنصة", url='https://faresanany.com'),
                InlineKeyboardButton("📞 الدعم الفني", callback_data='support')
            ],
            [InlineKeyboardButton("ℹ️ عن المنصة", callback_data='about')]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# ===================================
# 7. معالجة الرسائل النصية
# ===================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة رسائل المستخدمين"""
    user_message = update.message.text
    if not user_message:
        return

    user = update.effective_user
    logger.info(f"📩 رسالة من {user.first_name} ({user.id}): {user_message}")

    await update.message.chat.send_action(action="typing")

    try:
        # ✅ أولاً: نفحص Easter Eggs
        easter_response = check_easter_egg(user_message)
        if easter_response:
            logger.info(f"🥚 Easter Egg: {user_message}")
            await update.message.reply_text(easter_response, parse_mode='Markdown')
            return

        # 🧠 ثانياً: نرسل للـ AI
        response = await get_ai_response(user_message)
        await update.message.reply_text(response)

    except Exception as e:
        logger.error(f"❌ خطأ في معالجة الرسالة: {e}")
        await update.message.reply_text(
            "الجاذبية باظت والسيرفر مهنج! 🍎\n"
            "جرب كمان شوية أو كلمنا: https://wa.me/201025825268"
        )

# ===================================
# 8. معالجة الأخطاء
# ===================================
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الأخطاء العامة"""
    logger.error(f"❌ خطأ عام: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "حصل خطأ غير متوقع! 😔\n"
            "الفريق الفني اتبلغ وهيحل المشكلة قريباً.\n"
            "📞 https://wa.me/201025825268"
        )

# ===================================
# 9. البرنامج الرئيسي
# ===================================
def main():
    """تشغيل البوت على Railway"""
    logger.info("🚀 نيوتن الهايبر انطلق على Railway! 🍎⚡")

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # أوامر
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("courses", courses_command))
    application.add_handler(CommandHandler("prices", prices_command))
    application.add_handler(CommandHandler("about", about_command))
    application.add_handler(CommandHandler("contact", contact_command))
    application.add_handler(CommandHandler("stats", stats_command))

    # أزرار
    application.add_handler(CallbackQueryHandler(button_callback))

    # رسائل نصية
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # أخطاء
    application.add_error_handler(error_handler)

    logger.info("✅ البوت شغال.. ومتبقاش جهاز! 🍎")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
