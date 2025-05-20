import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, filters
from config import *

logger = logging.getLogger(__name__)

class UserData:
    def __init__(self):
        self.problem_type = None
        self.description = None
        self.media = []
        self.staff_response = None

user_sessions = {}

def get_start_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Не получилось наклеить стекло", callback_data='application_problem')],
        [InlineKeyboardButton("У меня другая проблема", callback_data='other_problem')]
    ])

def get_send_confirmation_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Отправить", callback_data='confirm_send')],
        [InlineKeyboardButton("Отменить", callback_data='cancel_send')]
    ])

def get_feedback_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Спасибо, помогло", callback_data='thanks')],
        [InlineKeyboardButton("Нужна помощь", callback_data='more_help')]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    user_sessions[user_id] = UserData()
    await update.message.reply_text(
        "👋 Добрый день! Я бот поддержки Глазурь. Выберите тип проблемы:",
        reply_markup=get_start_keyboard()
    )
    return WAITING_FOR_PROBLEM_TYPE

async def handle_problem_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_data = user_sessions[query.from_user.id]

    if query.data == 'application_problem':
        user_data.problem_type = "Наклейка стекла"
        await query.edit_message_text(
            "📎 Пришлите фото/видео и описание проблемы, затем нажмите 'Отправить'",
            reply_markup=get_send_confirmation_keyboard()
        )
        return WAITING_FOR_APPLICATION_DETAILS
    else:
        user_data.problem_type = "Другая проблема"
        await query.edit_message_text(
            "✍️ Опишите проблему, затем нажмите 'Отправить'",
            reply_markup=get_send_confirmation_keyboard()
        )
        return WAITING_FOR_OTHER_PROBLEM_DESCRIPTION

async def collect_application_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = user_sessions[update.effective_user.id]
    if update.message.photo:
        user_data.media.append(('photo', update.message.photo[-1].file_id))
    elif update.message.video:
        user_data.media.append(('video', update.message.video.file_id))
    elif update.message.text:
        user_data.description = update.message.text

async def collect_other_problem_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_sessions[update.effective_user.id].description = update.message.text

async def confirm_send(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == 'confirm_send':
        try:
            await send_application_to_staff(context, user_id, user_sessions[user_id])
            await query.edit_message_text("✅ Заявка отправлена! Ожидайте ответа.")
            return WAITING_FOR_STAFF_RESPONSE
        except Exception as e:
            logger.error(f"Ошибка отправки: {e}")
            await query.edit_message_text("❌ Ошибка отправки. Попробуйте позже.")
    else:
        await query.edit_message_text("🚫 Отправка отменена")
    
    user_sessions.pop(user_id, None)
    return ConversationHandler.END

async def send_application_to_staff(context: ContextTypes.DEFAULT_TYPE, user_id: int, user_data: UserData):
    staff_chat_id = context.bot_data['staff_chat_id']
    user = await context.bot.get_chat(user_id)
    
    message = await context.bot.send_message(
        chat_id=staff_chat_id,
        text=f"ID: {user_id}\n"
             f"Тип проблемы: {user_data.problem_type}\n"
             f"Описание: {user_data.description or 'Не указано'}\n\n"
             f"Чтобы ответить:\n"
             f"1. Ответьте на это сообщение текстом и введите /reply_{user_id}\n"
             f"2. Или введите /reply_{user_id} Ваш текст"
    )
    
    for media_type, file_id in user_data.media:
        try:
            if media_type == 'photo':
                await message.reply_photo(
                    photo=file_id,
                    caption=f"Фото от {user.username or user.id}"
                )
            elif media_type == 'video':
                await message.reply_video(
                    video=file_id,
                    caption=f"Видео от {user.username or user.id}"
                )
        except Exception as e:
            logger.error(f"Ошибка медиа: {e}")
            await context.bot.send_message(
                chat_id=staff_chat_id,
                text=f"⚠ Не удалось отправить вложение от {user.username or user.id}"
            )

async def handle_staff_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if not update.message or not update.message.text.startswith('/reply'):
            return

        # Удаляем все нецифровые символы из ID пользователя
        command_parts = update.message.text.split('_', 1)
        if len(command_parts) < 2:
            await update.message.reply_text("❌ Неверный формат команды. Используйте: /reply_12345 Ваш текст")
            return

        user_id_str = ''.join(filter(str.isdigit, command_parts[1].split()[0]))
        if not user_id_str:
            await update.message.reply_text("❌ Не удалось извлечь ID пользователя")
            return

        user_id = int(user_id_str)
        logger.info(f"Попытка ответа пользователю {user_id}")

        # Получаем текст ответа
        response_text = command_parts[1][len(user_id_str):].strip()
        if not response_text and update.message.reply_to_message:
            response_text = update.message.reply_to_message.text

        if not response_text:
            await update.message.reply_text("❌ Не указан текст ответа")
            return

        # Отправляем ответ пользователю
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📨 Ответ от поддержки:\n\n{response_text}",
                reply_markup=get_feedback_keyboard()
            )
            await update.message.reply_text(f"✅ Ответ отправлен пользователю {user_id}")
        except Exception as e:
            error_msg = f"❌ Не удалось отправить ответ: {str(e)}"
            await update.message.reply_text(error_msg)
            logger.error(error_msg)

    except Exception as e:
        logger.error(f"Ошибка обработки ответа: {str(e)}", exc_info=True)
        await update.message.reply_text("⚠️ Произошла ошибка при обработке команды")

async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    user_id = query.from_user.id
    
    try:
        await query.answer()
        
        if query.data == 'thanks':
            msg = "🙏 Спасибо! Обращайтесь снова!"
            feedback = f"✅ Пользователь {user_id} подтвердил решение"
        else:
            msg = "🛎 Мы скоро с вами свяжемся!"
            feedback = f"⚠️ Пользователь {user_id} запросил помощь"
        
        await query.edit_message_text(msg, reply_markup=None)
        await context.bot.send_message(
            chat_id=context.bot_data['staff_chat_id'],
            text=feedback
        )
    except Exception as e:
        logger.error(f"Ошибка фидбека: {e}")
    finally:
        user_sessions.pop(user_id, None)
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    user_sessions.pop(user_id, None)
    await update.message.reply_text("❌ Диалог прерван. Начните заново: /start")
    return ConversationHandler.END

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    error = context.error
    logger.error(f"Ошибка: {error}", exc_info=True)
    
    if update and update.callback_query:
        try:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                "⚠️ Ошибка. Начните заново: /start",
                reply_markup=None
            )
        except:
            pass