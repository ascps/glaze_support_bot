import logging
import time
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup
)
from telegram.ext import ContextTypes, ConversationHandler, filters
from config import *
import re

logger = logging.getLogger(__name__)

class UserData:
    def __init__(self):
        self.problem_type = None
        self.description = None
        self.media = []
        self.staff_response = None
        self.message_ids = []
        self.username = None
        self.phone_number = None

user_sessions = {}

def get_start_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔧 Не получилось наклеить стекло", callback_data='application_problem')],
        [InlineKeyboardButton("❓ У меня другая проблема", callback_data='other_problem')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_send_confirmation_keyboard():
    keyboard = [
        [InlineKeyboardButton("📤 Отправить заявку", callback_data='confirm_send')],
        [InlineKeyboardButton("❌ Отменить", callback_data='cancel_send')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_feedback_keyboard():
    keyboard = [
        [InlineKeyboardButton("✅ Проблема решена", callback_data='thanks')],
        [InlineKeyboardButton("🆘 Нужна помощь", callback_data='more_help')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_staff_reply_keyboard(user_id, username):
    keyboard = [
        [InlineKeyboardButton(f"✉️ Ответить @{username}", callback_data=f'staff_reply_{user_id}')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def delete_previous_keyboards(context, user_id):
    if user_id in user_sessions:
        for msg_id in user_sessions[user_id].message_ids:
            try:
                await context.bot.delete_message(chat_id=user_id, message_id=msg_id)
            except Exception as e:
                logger.error(f"Ошибка удаления сообщения: {e}")
        user_sessions[user_id].message_ids = []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        user_id = update.effective_user.id
        user_sessions[user_id] = UserData()
        user_sessions[user_id].username = update.effective_user.username or "пользователь"
        
        await update.message.reply_text(
            "👋 Здравствуйте! Я бот поддержки Глазурь. Выберите тип проблемы:",
            reply_markup=get_start_keyboard()
        )
        return STATE_PROBLEM_SELECTION
    except Exception as e:
        logger.error(f"Ошибка в start: {str(e)}")
        await update.message.reply_text("⚠️ Произошла ошибка. Попробуйте позже.")
        return ConversationHandler.END

async def handle_problem_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        user_data = user_sessions.get(user_id)
        
        if not user_data:
            return await start(update, context)

        if query.data == 'application_problem':
            user_data.problem_type = "Проблема с наклейкой"
            await query.edit_message_text(
                "📎 Пришлите фото/видео проблемы и описание:",
                reply_markup=None
            )
            
            msg = await context.bot.send_message(
                chat_id=user_id,
                text="⬇️ Добавьте файлы или описание, затем нажмите:",
                reply_markup=get_send_confirmation_keyboard()
            )
            user_data.message_ids.append(msg.message_id)
            
            return STATE_COLLECT_MEDIA
        else:
            user_data.problem_type = "Другая проблема"
            await query.edit_message_text(
                "✍️ Опишите вашу проблему:",
                reply_markup=None
            )
            
            msg = await context.bot.send_message(
                chat_id=user_id,
                text="⬇️ Напишите описание, затем нажмите:",
                reply_markup=get_send_confirmation_keyboard()
            )
            user_data.message_ids.append(msg.message_id)
            
            return STATE_COLLECT_DESCRIPTION
    except Exception as e:
        logger.error(f"Ошибка в handle_problem_type: {str(e)}")
        return ConversationHandler.END

async def collect_application_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user_id = update.effective_user.id
        user_data = user_sessions.get(user_id)
        
        if not user_data:
            return

        await delete_previous_keyboards(context, user_id)

        if update.message.photo:
            user_data.media.append(('photo', update.message.photo[-1].file_id))
            reply_text = "📷 Фото принято. Добавьте еще файлы или описание."
        elif update.message.video:
            user_data.media.append(('video', update.message.video.file_id))
            reply_text = "🎥 Видео принято. Добавьте еще файлы или описание."
        elif update.message.text:
            user_data.description = update.message.text
            reply_text = "📝 Описание принято. Добавьте фото/видео или отправляйте заявку."

        msg = await update.message.reply_text(
            text=f"{reply_text}\n\n⬇️ Когда готово, нажмите:",
            reply_markup=get_send_confirmation_keyboard()
        )
        user_data.message_ids.append(msg.message_id)

    except Exception as e:
        logger.error(f"Ошибка при сборе данных: {str(e)}")

async def collect_other_problem_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user_id = update.effective_user.id
        user_data = user_sessions.get(user_id)
        
        if user_data and update.message.text:
            await delete_previous_keyboards(context, user_id)
            user_data.description = update.message.text
            
            msg = await update.message.reply_text(
                text="📝 Описание принято.\n\n⬇️ Нажмите для отправки:",
                reply_markup=get_send_confirmation_keyboard()
            )
            user_data.message_ids.append(msg.message_id)
    except Exception as e:
        logger.error(f"Ошибка при сборе описания: {str(e)}")

async def confirm_send(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        user_data = user_sessions.get(user_id)
        
        if not user_data:
            return ConversationHandler.END

        if query.data == 'confirm_send':
            try:
                await delete_previous_keyboards(context, user_id)
                await send_application_to_staff(context, user_id, user_data)
                await context.bot.send_message(
                    chat_id=user_id,
                    text="✅ Ваша заявка принята! Мы ответим в ближайшее время."
                )
                return STATE_AWAIT_STAFF_REPLY
            except Exception as e:
                logger.error(f"Ошибка отправки заявки: {str(e)}")
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ Ошибка отправки. Пожалуйста, попробуйте позже."
                )
        else:
            await delete_previous_keyboards(context, user_id)
            await context.bot.send_message(
                chat_id=user_id,
                text="🚫 Отправка отменена. Начните заново: /start"
            )
        
        user_sessions.pop(user_id, None)
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Ошибка в confirm_send: {str(e)}")
        return ConversationHandler.END

async def send_application_to_staff(context: ContextTypes.DEFAULT_TYPE, user_id: int, user_data: UserData) -> None:
    try:
        staff_chat_id = context.bot_data.get('staff_chat_id')
        if not staff_chat_id:
            raise ValueError("ID чата поддержки не настроен")

        username = user_data.username
        phone = user_data.phone_number or "не указан"
        
        ticket_number = f"TICKET-{user_id}-{int(time.time()) % 10000:04d}"
        
        message_text = (
            f"🆕 Новая заявка: #{ticket_number}\n"
            f"👤 Пользователь: @{username} (ID: {user_id})\n"
            f"📞 Телефон: {phone}\n"
            f"📌 Тип: {user_data.problem_type}\n"
            f"📝 Описание: {user_data.description or 'нет описания'}\n\n"
            f"💬 Для ответа нажмите кнопку ниже или ответьте на это сообщение"
        )

        staff_message = await context.bot.send_message(
            chat_id=staff_chat_id,
            text=message_text,
            reply_markup=get_staff_reply_keyboard(user_id, username)
        )

        for media_type, file_id in user_data.media:
            try:
                if media_type == 'photo':
                    await staff_message.reply_photo(
                        photo=file_id,
                        caption=f"📷 Фото от @{username}",
                        reply_markup=get_staff_reply_keyboard(user_id, username)
                    )
                elif media_type == 'video':
                    await staff_message.reply_video(
                        video=file_id,
                        caption=f"🎥 Видео от @{username}",
                        reply_markup=get_staff_reply_keyboard(user_id, username)
                    )
            except Exception as e:
                logger.error(f"Ошибка отправки медиа: {str(e)}")
                await context.bot.send_message(
                    chat_id=staff_chat_id,
                    text=f"⚠ Не удалось отправить вложение от @{username}",
                    reply_markup=get_staff_reply_keyboard(user_id, username)
                )

    except Exception as e:
        logger.error(f"Ошибка в send_application_to_staff: {str(e)}")
        raise

async def handle_staff_reply_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        query = update.callback_query
        await query.answer()
        
        if query.data.startswith('staff_reply_'):
            user_id = int(query.data.split('_')[-1])
            context.user_data['replying_to'] = {
                'user_id': user_id,
                'username': user_sessions[user_id].username
            }
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"✍️ Введите ваш ответ для @{user_sessions[user_id].username}:"
            )
    except Exception as e:
        logger.error(f"Ошибка в handle_staff_reply_button: {str(e)}")
        await query.edit_message_text("⚠️ Ошибка. Попробуйте ответить через reply.")

async def handle_staff_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user_id = None
        username = None
        response_text = update.message.text
        
        # Обработка ответа через кнопку
        if 'replying_to' in context.user_data:
            user_id = context.user_data['replying_to']['user_id']
            username = context.user_data['replying_to']['username']
            del context.user_data['replying_to']
        # Обработка ответа через reply
        elif update.message.reply_to_message:
            original_message = update.message.reply_to_message.text
            match = re.search(r'ID: (\d+)', original_message)
            if match:
                user_id = int(match.group(1))
                username_match = re.search(r'Пользователь: @(\w+)', original_message)
                if username_match:
                    username = username_match.group(1)

        if not user_id or not username:
            await update.message.reply_text("❌ Не удалось определить пользователя для ответа")
            return

        # Отправляем ответ пользователю
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📩 Ответ от поддержки:\n\n{response_text}",
                reply_markup=get_feedback_keyboard()
            )
            await update.message.reply_text(
                f"✅ Ответ отправлен пользователю @{username}"
            )
        except Exception as e:
            error_msg = f"Не удалось отправить ответ пользователю {user_id}: {str(e)}"
            logger.error(error_msg)
            await update.message.reply_text("❌ Не удалось отправить ответ пользователю")

    except Exception as e:
        logger.error(f"Ошибка в handle_staff_response: {str(e)}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        query = update.callback_query
        user_id = query.from_user.id
        
        await query.answer()

        if query.data == 'thanks':
            user_msg = "🙏 Спасибо за обратную связь! Если будут вопросы - пишите /start"
            feedback_msg = f"✅ Пользователь @{user_sessions[user_id].username} подтвердил решение"
        else:
            user_msg = "🛎 Мы свяжемся с вами. Для нового вопроса - /start"
            feedback_msg = f"⚠️ Пользователь @{user_sessions[user_id].username} запросил помощь"

        await query.edit_message_text(
            text=user_msg,
            reply_markup=None
        )

        staff_chat_id = context.bot_data.get('staff_chat_id')
        if staff_chat_id:
            try:
                await context.bot.send_message(
                    chat_id=staff_chat_id,
                    text=feedback_msg
                )
            except Exception as e:
                logger.error(f"Ошибка отправки фидбека: {str(e)}")

    except Exception as e:
        logger.error(f"Ошибка в handle_feedback: {str(e)}")
    finally:
        if user_id in user_sessions:
            del user_sessions[user_id]
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        user_id = update.effective_user.id
        if user_id in user_sessions:
            await delete_previous_keyboards(context, user_id)
            del user_sessions[user_id]
        
        await update.message.reply_text("❌ Диалог прерван. Начните заново: /start")
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Ошибка в cancel: {str(e)}")
        return ConversationHandler.END

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    error = context.error
    logger.error(f"Ошибка: {str(error)}", exc_info=True)
    
    try:
        if update and update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                "⚠️ Произошла ошибка. Пожалуйста, начните заново: /start",
                reply_markup=None
            )
    except Exception as e:
        logger.error(f"Ошибка в error_handler: {str(e)}")