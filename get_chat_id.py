from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)

# Конфигурация
BOT_TOKEN = "7221937653:AAEcpvhUWFEK9muvKFKfPjcRJmAMpvP2Mc4"  # Замените на реальный токен

async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /get_chat_id"""
    chat = update.effective_chat
    await update.message.reply_text(
        f"📌 Информация о чате:\n\n"
        f"Тип: {chat.type}\n"
        f"ID: `{chat.id}`\n"
        f"Название: {chat.title or 'Личная переписка'}\n\n"
        f"Для групп используйте этот ID в конфиге: `STAFF_CHAT_ID={chat.id}`",
        parse_mode="Markdown"
    )

async def handle_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветствие при добавлении бота в группу"""
    for user in update.message.new_chat_members:
        if user.id == context.bot.id:
            await update.message.reply_text(
                "👋 Привет! Я бот поддержки Глазурь.\n\n"
                "Чтобы получить ID этого чата для настройки, отправьте команду:\n"
                "/get_chat_id"
            )

def main():
    """Запуск бота"""
    app = Application.builder().token(BOT_TOKEN).build()

    # Регистрация обработчиков
    app.add_handler(CommandHandler("get_chat_id", get_chat_id))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_members))

    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()