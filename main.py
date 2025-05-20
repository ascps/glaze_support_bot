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

async def post_init(app):
    app.bot_data['staff_chat_id'] = STAFF_CHAT_ID
    logger.info(f"Бот запущен. Чат поддержки: {STAFF_CHAT_ID}")

def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            WAITING_FOR_PROBLEM_TYPE: [CallbackQueryHandler(handle_problem_type)],
            WAITING_FOR_APPLICATION_DETAILS: [
                MessageHandler(
                    filters.PHOTO | filters.VIDEO | filters.TEXT & ~filters.COMMAND,
                    collect_application_details
                ),
                CallbackQueryHandler(confirm_send)
            ],
            WAITING_FOR_OTHER_PROBLEM_DESCRIPTION: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    collect_other_problem_details
                ),
                CallbackQueryHandler(confirm_send)
            ],
            WAITING_FOR_STAFF_RESPONSE: [],
            WAITING_FOR_FEEDBACK: [CallbackQueryHandler(handle_feedback)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=False
    )

    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.COMMAND, handle_staff_response))
    app.add_error_handler(error_handler)

    logger.info("Бот запускается...")
    app.run_polling()

if __name__ == '__main__':
    main()