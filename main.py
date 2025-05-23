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
    try:
        application.bot_data['staff_chat_id'] = STAFF_CHAT_ID
        chat = await application.bot.get_chat(STAFF_CHAT_ID)
        logger.info(f"Бот подключен к чату поддержки: {chat.title}")
        me = await application.bot.get_me()
        logger.info(f"Бот @{me.username} запущен")
    except Exception as e:
        logger.error(f"Ошибка инициализации: {str(e)}")
        raise

def main():
    try:
        application = Application.builder() \
            .token(TOKEN) \
            .post_init(post_init) \
            .build()

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
                STATE_AWAIT_STAFF_REPLY: [],
                STATE_AWAIT_CLIENT_FEEDBACK: [CallbackQueryHandler(handle_feedback)]
            },
            fallbacks=[CommandHandler('cancel', cancel)],
            allow_reentry=True
        )

        application.add_handler(conv_handler)
        application.add_handler(CallbackQueryHandler(handle_staff_reply_button, pattern='^staff_reply_'))
        application.add_handler(MessageHandler(
            filters.TEXT & filters.Chat(STAFF_CHAT_ID) & ~filters.COMMAND,
            handle_staff_response
        ))
        application.add_handler(CallbackQueryHandler(
            handle_feedback,
            pattern='^(thanks|more_help)$'
        ))
        application.add_error_handler(error_handler)

        logger.info("Запуск бота...")
        application.run_polling(
            poll_interval=1.0,
            timeout=20,
            drop_pending_updates=True
        )
    except Exception as e:
        logger.critical(f"Ошибка запуска: {str(e)}")

if __name__ == '__main__':
    main()