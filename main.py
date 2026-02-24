#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
جهاز الفيزياء - بوت تليجرام ذكي
المساعد الذكي لمنصة "متبقاش جهاز في الفيزياء"
"""

import os
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
# الإعدادات والتكوين
# ===================================

# تفعيل التسجيل
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

# التحقق من المفاتيح
if not TELEGRAM_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN غير موجود!")
if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY غير موجود!")

# تكوين Gemini (المخ الرئيسي)
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-pro')

# تكوين Groq (المساعد السريع)
groq_client = None
if GROQ_API_KEY:
    groq_client = Groq(api_key=GROQ_API_KEY)
    logger.info("✅ Groq تم تفعيله كمساعد")

# قراءة ملف المعرفة
KNOWLEDGE_FILE = 'knowledge.txt'
platform_knowledge = ""
try:
    with open(KNOWLEDGE_FILE, 'r', encoding='utf-8') as f:
        platform_knowledge = f.read()
    logger.info(f"✅ تم تحميل ملف المعرفة: {KNOWLEDGE_FILE}")
except FileNotFoundError:
    logger.warning(f"⚠️ ملف المعرفة {KNOWLEDGE_FILE} غير موجود")

# ===================================
# شخصية البوت
# ===================================

BOT_PERSONALITY = """
أنت "جهاز الفيزياء" 🤖 - المساعد الذكي لمنصة "متبقاش جهاز في الفيزياء"

الشخصية:
- اسمك: جهاز الفيزياء
- مهمتك: مساعدة طلاب الصف الثاني الثانوي في فهم الفيزياء
- أسلوبك: ودود، مشجع، بسيط، وواضح
- هدفك: تبسيط الفيزياء وجعلها ممتعة للطلاب

قواعد الرد:
1. استخدم اللغة العربية الفصحى البسيطة
2. كن مشجعاً ومحفزاً دائماً
3. اشرح المفاهيم الصعبة بأمثلة بسيطة من الحياة اليومية
4. استخدم الرموز التعبيرية بذكاء (🔬⚡📚🎓✨)
5. لا تتردد في قول "متبقاش جهاز" بطريقة تشجيعية
6. وجه الطلاب للكورسات المناسبة عند الحاجة
7. للأسئلة الفنية أو التقنية، وجههم لفريق الدعم

عبارات مفضلة:
- "يلا نفهم الفيزياء سوا! 🚀"
- "مفيش حاجة صعبة لما نفهمها صح ✨"
- "متبقاش جهاز، أنا هنا عشان أساعدك! 🤖"
- "الفيزياء حلوة لما تفهمها 🔬"
"""

# ===================================
# دوال الذكاء الاصطناعي
# ===================================

async def get_ai_response(user_message: str, use_groq: bool = False) -> str:
    """
    الحصول على رد من الذكاء الاصطناعي
    Gemini = المخ الرئيسي
    Groq = المساعد السريع (للردود البسيطة)
    """
    try:
        # تحضير السياق الكامل
        full_context = f"""{BOT_PERSONALITY}

معلومات المنصة:
{platform_knowledge}

سؤال الطالب: {user_message}

الرد:"""

        # استخدام Groq للردود السريعة والبسيطة
        if use_groq and groq_client:
            try:
                response = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": BOT_PERSONALITY + "\n\n" + platform_knowledge},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=0.7,
                    max_tokens=500,
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                logger.warning(f"⚠️ خطأ في Groq، التبديل إلى Gemini: {e}")

        # استخدام Gemini (المخ الرئيسي)
        response = gemini_model.generate_content(full_context)
        return response.text.strip()

    except Exception as e:
        logger.error(f"❌ خطأ في الذكاء الاصطناعي: {e}")
        return "عذراً، حصل خطأ تقني بسيط. جرب تاني أو تواصل مع الدعم الفني! 🔧"

def is_simple_question(message: str) -> bool:
    """
    تحديد إذا كان السؤال بسيط (يستخدم Groq) أو معقد (يستخدم Gemini)
    """
    simple_keywords = [
        'مرحبا', 'السلام', 'أهلا', 'هاي', 'صباح', 'مساء',
        'شكرا', 'متشكر', 'تمام', 'حلو', 'ممتاز',
        'السعر', 'كام', 'تكلفة', 'ثمن',
        'التواصل', 'رقم', 'واتساب', 'فيسبوك'
    ]

    message_lower = message.lower()
    return any(keyword in message_lower for keyword in simple_keywords) or len(message) < 50

# ===================================
# دوال الأوامر
# ===================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /start - الترحيب"""
    user = update.effective_user

    welcome_message = f"""
👋 أهلاً وسهلاً يا {user.first_name}!

أنا **جهاز الفيزياء** 🤖 - مساعدك الذكي في منصة "متبقاش جهاز في الفيزياء"

🎯 أقدر أساعدك في:
• شرح مفاهيم الفيزياء بطريقة بسيطة 📚
• معلومات عن الكورسات والأسعار 💰
• روابط التسجيل والمنصة 🔗
• الإجابة على أسئلتك في الفيزياء ⚡

💡 ابعتلي أي سؤال وأنا هساعدك!

استخدم /help عشان تشوف كل الأوامر المتاحة.
"""

    # لوحة المفاتيح
    keyboard = [
        [
            InlineKeyboardButton("📚 الكورسات المتاحة", callback_data='courses'),
            InlineKeyboardButton("💰 الأسعار", callback_data='prices')
        ],
        [
            InlineKeyboardButton("🌐 المنصة", url='https://faresanany.com'),
            InlineKeyboardButton("📞 الدعم الفني", callback_data='support')
        ],
        [
            InlineKeyboardButton("ℹ️ عن المنصة", callback_data='about')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_message, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /help - المساعدة"""
    help_text = """
🤖 **دليل استخدام جهاز الفيزياء**

📋 **الأوامر المتاحة:**

/start - البدء والترحيب
/help - عرض هذه المساعدة
/courses - عرض الكورسات المتاحة
/prices - عرض الأسعار
/about - معلومات عن المنصة
/contact - معلومات التواصل

💬 **كيف تستخدمني:**
فقط ابعتلي سؤالك في الفيزياء وأنا هرد عليك!

مثال:
"اشرحلي قانون نيوتن الأول"
"إيه الفرق بين السرعة والعجلة؟"
"عايز أعرف عن كورس الترم الثاني"

✨ أنا هنا عشان أساعدك تبقى فاهم مش جهاز! 🚀
"""
    await update.message.reply_text(help_text)

async def courses_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /courses - عرض الكورسات"""
    courses_text = """
📚 **الكورسات المتاحة - الترم الثاني 2026**

1️⃣ **كورس الترم كامل**
💰 السعر: 300 جنيه
📅 المدة: الترم الثاني كامل
✅ يشمل: جميع دروس الترم + تدريبات + ملخصات
🔗 https://faresanany.com/course/3

2️⃣ **كورس الشهر الأول**
💰 السعر: 145 جنيه
📅 المدة: شهر واحد
✅ يشمل: دروس الشهر الأول + تمارين
🔗 https://faresanany.com/course/1

✨ **مميزات الكورسات:**
• شرح مبسط وواضح 📖
• تجارب تفاعلية وأنيميشن 🎬
• تدريبات مكثفة 📝
• فيديوهات عالية الجودة 🎥
• متابعة مستمرة 👨‍🏫
• ملخصات PDF جاهزة 📄

🌐 للتسجيل: https://faresanany.com/register
"""

    keyboard = [
        [InlineKeyboardButton("🌐 زيارة المنصة", url='https://faresanany.com')],
        [InlineKeyboardButton("📝 التسجيل الآن", url='https://faresanany.com/register')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(courses_text, reply_markup=reply_markup)

async def prices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /prices - عرض الأسعار"""
    prices_text = """
💰 **أسعار الكورسات**

📦 **كورس الترم كامل**
💵 300 جنيه مصري

📦 **كورس الشهر الأول**
💵 145 جنيه مصري

✨ **القيمة المضافة:**
✅ +120 درس متاح
✅ متابعة مستمرة
✅ شرح تفاعلي
✅ ملخصات وملازم
✅ دعم فني

💡 **استثمار في مستقبلك التعليمي!**

🌐 للتسجيل: https://faresanany.com/register
📞 للاستفسار: https://wa.me/201025825268
"""

    keyboard = [
        [InlineKeyboardButton("📝 سجل الآن", url='https://faresanany.com/register')],
        [InlineKeyboardButton("📞 تواصل معنا", url='https://wa.me/201025825268')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(prices_text, reply_markup=reply_markup)

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /about - عن المنصة"""
    about_text = """
ℹ️ **عن منصة "متبقاش جهاز في الفيزياء"**

👨‍🏫 **المدرس:** مستر فارس العناني
📊 **عدد الطلاب:** +120,000 طالب
📚 **عدد الدروس:** +120 درس متاح
🎯 **التخصص:** الفيزياء - الصف الثاني الثانوي

🌟 **رسالتنا:**
"افهم الفيزياء… متبقاش جهاز"

رحلة تعليمية ممتعة تخليك تكتشف الفيزياء بطريقة مبسطة وتفاعلية!

✨ **مميزاتنا:**
• شرح مبسط بدون تعقيد
• تجارب تفاعلية ورسومات متحركة
• تدريبات مكثفة ومتنوعة
• فيديوهات عالية الجودة
• متابعة دورية مستمرة
• ملخصات PDF جاهزة

🌐 الموقع: https://faresanany.com
"""

    keyboard = [
        [InlineKeyboardButton("🌐 زيارة المنصة", url='https://faresanany.com')],
        [InlineKeyboardButton("📱 تابعنا على فيسبوك", url='https://www.facebook.com/share/1D9WyAjrrG/')],
        [InlineKeyboardButton("🎥 قناة يوتيوب", url='https://youtube.com/@fareselanaany')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(about_text, reply_markup=reply_markup)

async def contact_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /contact - معلومات التواصل"""
    contact_text = """
📞 **معلومات التواصل**

💬 **الدعم الفني:**
📱 واتساب: +201025825268
🔗 https://wa.me/201025825268

🌐 **السوشيال ميديا:**

📘 فيسبوك:
https://www.facebook.com/share/1D9WyAjrrG/

🎥 يوتيوب:
https://youtube.com/@fareselanaany

🎵 تيكتوك:
https://www.tiktok.com/@fares_elenany

💚 قناة الواتساب:
https://whatsapp.com/channel/0029VbBOqpI96H4PKk8t3H1n

✈️ قناة التيليجرام:
https://t.me/Fox9_99

🌐 **الموقع الرسمي:**
https://faresanany.com

نحن سعداء بخدمتك! 😊
"""

    keyboard = [
        [InlineKeyboardButton("📱 واتساب", url='https://wa.me/201025825268')],
        [InlineKeyboardButton("📘 فيسبوك", url='https://www.facebook.com/share/1D9WyAjrrG/')],
        [InlineKeyboardButton("🎥 يوتيوب", url='https://youtube.com/@fareselanaany')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(contact_text, reply_markup=reply_markup)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /stats - إحصائيات البوت (للأدمن فقط)"""
    user_id = update.effective_user.id

    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("⛔ هذا الأمر متاح للمسؤول فقط!")
        return

    stats_text = f"""
📊 **إحصائيات البوت**

🤖 الاسم: جهاز الفيزياء
⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🟢 الحالة: يعمل بنجاح

🧠 **الذكاء الاصطناعي:**
✅ Gemini: مفعّل (المخ الرئيسي)
{'✅ Groq: مفعّل (المساعد السريع)' if groq_client else '⚠️ Groq: غير مفعّل'}

📁 **الملفات:**
✅ knowledge.txt: محمّل

👨‍💼 **المسؤول:** {ADMIN_USER_ID}
"""

    await update.message.reply_text(stats_text)

# ===================================
# معالجة الأزرار
# ===================================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الضغط على الأزرار"""
    query = update.callback_query
    await query.answer()

    if query.data == 'courses':
        await courses_command(update, context)
    elif query.data == 'prices':
        await prices_command(update, context)
    elif query.data == 'about':
        await about_command(update, context)
    elif query.data == 'support':
        await contact_command(update, context)

# ===================================
# معالجة الرسائل
# ===================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة رسائل المستخدمين"""
    user_message = update.message.text
    user = update.effective_user

    logger.info(f"📩 رسالة من {user.first_name} ({user.id}): {user_message}")

    # إرسال رسالة "يكتب..."
    await update.message.chat.send_action(action="typing")

    try:
        # تحديد نوع السؤال واختيار AI المناسب
        use_groq = is_simple_question(user_message)
        ai_name = "Groq" if use_groq else "Gemini"

        logger.info(f"🧠 استخدام {ai_name} للرد")

        # الحصول على الرد
        response = await get_ai_response(user_message, use_groq=use_groq)

        # إرسال الرد
        await update.message.reply_text(response)
        logger.info(f"✅ تم الرد بنجاح ({ai_name})")

    except Exception as e:
        logger.error(f"❌ خطأ في معالجة الرسالة: {e}")
        await update.message.reply_text(
            "عذراً، حصل خطأ بسيط. جرب تاني أو تواصل مع الدعم الفني! 🔧\n"
            "📞 https://wa.me/201025825268"
        )

# ===================================
# معالجة الأخطاء
# ===================================

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الأخطاء"""
    logger.error(f"❌ خطأ: {context.error}")

    if update and update.effective_message:
        await update.effective_message.reply_text(
            "عذراً، حصل خطأ غير متوقع! 😔\n"
            "الفريق الفني تم إشعاره وسيتم حل المشكلة قريباً.\n\n"
            "📞 للمساعدة: https://wa.me/201025825268"
        )

# ===================================
# البرنامج الرئيسي
# ===================================

def main():
    """تشغيل البوت"""
    logger.info("🚀 بدء تشغيل جهاز الفيزياء...")

    # إنشاء التطبيق
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # إضافة معالجات الأوامر
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("courses", courses_command))
    application.add_handler(CommandHandler("prices", prices_command))
    application.add_handler(CommandHandler("about", about_command))
    application.add_handler(CommandHandler("contact", contact_command))
    application.add_handler(CommandHandler("stats", stats_command))

    # إضافة معالج الأزرار
    application.add_handler(CallbackQueryHandler(button_callback))

    # إضافة معالج الرسائل
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # إضافة معالج الأخطاء
    application.add_error_handler(error_handler)

    # تشغيل البوت
    logger.info("✅ البوت يعمل الآن! اضغط Ctrl+C للإيقاف.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
