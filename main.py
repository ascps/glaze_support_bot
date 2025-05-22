import logging
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters
)
from config import *
from handlers import *

logger = logging.getLogger(__name__)

async def post_init(application):
    """Инициализация после запуска бота"""
    try:
        application.bot_data['staff_chat_id'] = STAFF_CHAT_ID
        
        # Проверка подключения к чату поддержки
        chat = await application.bot.get_chat(STAFF_CHAT_ID)
        logger.info(f"Бот успешно подключен к чату поддержки: {chat.title} (ID: {chat.id})")
        
        # Проверка прав бота
        me = await application.bot.get_me()
        logger.info(f"Бот @{me.username} готов к работе")
    except Exception as e:
        logger.error(f"Критическая ошибка инициализации: {str(e)}")
        raise

def main():
    """Основная функция запуска бота"""
    try:
        # Создаем Application с обработкой ошибок
        application = Application.builder() \
            .token(TOKEN) \
            .post_init(post_init) \
            .build()

        # Настройка ConversationHandler
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                STATE_PROBLEM_SELECTION: [CallbackQueryHandler(handle_problem_type)],
                STATE_COLLECT_MEDIA: [
                    MessageHandler(
                        filters.PHOTO | filters.VIDEO | filters.TEXT & ~filters.COMMAND,
                        collect_application_details
                    ),
                    CallbackQueryHandler(confirm_send)
                ],
                STATE_COLLECT_DESCRIPTION: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        collect_other_problem_details
                    ),
                    CallbackQueryHandler(confirm_send)
                ],
                STATE_CONFIRM_SEND: [CallbackQueryHandler(confirm_send)],
                STATE_AWAIT_STAFF_REPLY: [],
                STATE_AWAIT_CLIENT_FEEDBACK: [CallbackQueryHandler(handle_feedback)]
            },
            fallbacks=[CommandHandler('cancel', cancel)],
            allow_reentry=True,
            per_message=False  # Добавляем этот параметр для устранения предупреждения
        )

        # Регистрация обработчиков
        application.add_handler(conv_handler)
        
        # Отдельный обработчик для ответов от поддержки
        application.add_handler(MessageHandler(
            filters.TEXT & filters.Chat(STAFF_CHAT_ID) & 
            (filters.Regex(r'^/reply_\d+') | filters.REPLY),
            handle_staff_response
        ))
        
        # Отдельный обработчик для кнопок обратной связи
        application.add_handler(CallbackQueryHandler(
            handle_feedback,
            pattern='^(thanks|more_help)$'
        ))

        application.add_error_handler(error_handler)

        logger.info("Запуск бота в режиме polling...")
        application.run_polling(
            poll_interval=1.0,
            timeout=20,
            drop_pending_updates=True
        )
    except Exception as e:
        logger.critical(f"Фатальная ошибка при запуске бота: {str(e)}")

if __name__ == '__main__':
    main()