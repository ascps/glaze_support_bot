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
    keyboard = [
        [InlineKeyboardButton("Не получилось наклеить стекло", callback_data='application_problem')],
        [InlineKeyboardButton("У меня другая проблема", callback_data='other_problem')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_send_confirmation_keyboard():
    keyboard = [
        [InlineKeyboardButton("Отправить", callback_data='confirm_send')],
        [InlineKeyboardButton("Отменить", callback_data='cancel_send')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_feedback_keyboard():
    keyboard = [
        [InlineKeyboardButton("✅ Проблема решена", callback_data='thanks')],
        [InlineKeyboardButton("🆘 Нужна помощь", callback_data='more_help')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        user_id = update.effective_user.id
        user_sessions[user_id] = UserData()
        logger.info(f"Пользователь {user_id} начал диалог")
        
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
            logger.warning(f"Сессия не найдена для пользователя {user_id}")
            return await start(update, context)

        if query.data == 'application_problem':
            user_data.problem_type = "Проблема с наклейкой"
            logger.info(f"Пользователь {user_id} выбрал: Проблема с наклейкой")
            await query.edit_message_text(
                "📎 Пришлите фото/видео проблемы и описание, затем нажмите «Отправить»",
                reply_markup=get_send_confirmation_keyboard()
            )
            return STATE_COLLECT_MEDIA
        else:
            user_data.problem_type = "Другая проблема"
            logger.info(f"Пользователь {user_id} выбрал: Другая проблема")
            await query.edit_message_text(
                "✍️ Опишите вашу проблему, затем нажмите «Отправить»",
                reply_markup=get_send_confirmation_keyboard()
            )
            return STATE_COLLECT_DESCRIPTION
    except Exception as e:
        logger.error(f"Ошибка в handle_problem_type: {str(e)}")
        return ConversationHandler.END

async def collect_application_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user_id = update.effective_user.id
        user_data = user_sessions.get(user_id)
        
        if not user_data:
            logger.warning(f"Сессия не найдена при сборе данных для {user_id}")
            return

        if update.message.photo:
            user_data.media.append(('photo', update.message.photo[-1].file_id))
            logger.info(f"Пользователь {user_id} отправил фото")
            await update.message.reply_text("📷 Фото принято. Добавьте еще файлы или описание, затем нажмите «Отправить»")
        elif update.message.video:
            user_data.media.append(('video', update.message.video.file_id))
            logger.info(f"Пользователь {user_id} отправил видео")
            await update.message.reply_text("🎥 Видео принято. Добавьте еще файлы или описание, затем нажмите «Отправить»")
        elif update.message.text:
            user_data.description = update.message.text
            logger.info(f"Пользователь {user_id} отправил описание: {update.message.text}")
            await update.message.reply_text("📝 Описание принято. Добавьте фото/видео или нажмите «Отправить»")
    except Exception as e:
        logger.error(f"Ошибка при сборе данных: {str(e)}")

async def collect_other_problem_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user_id = update.effective_user.id
        user_data = user_sessions.get(user_id)
        
        if user_data and update.message.text:
            user_data.description = update.message.text
            logger.info(f"Пользователь {user_id} описал проблему: {update.message.text}")
            await update.message.reply_text("📝 Описание принято. Нажмите «Отправить» для завершения")
    except Exception as e:
        logger.error(f"Ошибка при сборе описания: {str(e)}")

async def confirm_send(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        user_data = user_sessions.get(user_id)
        
        if not user_data:
            logger.warning(f"Сессия не найдена при подтверждении для {user_id}")
            return ConversationHandler.END

        if query.data == 'confirm_send':
            logger.info(f"Пользователь {user_id} подтвердил отправку заявки")
            try:
                await send_application_to_staff(context, user_id, user_data)
                await query.edit_message_text("✅ Ваша заявка принята! Мы ответим в ближайшее время.")
                return STATE_AWAIT_STAFF_REPLY
            except Exception as e:
                logger.error(f"Ошибка отправки заявки: {str(e)}")
                await query.edit_message_text("❌ Ошибка отправки. Пожалуйста, попробуйте позже.")
        else:
            logger.info(f"Пользователь {user_id} отменил отправку")
            await query.edit_message_text("🚫 Отправка отменена. Начните заново: /start")
        
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

        user = await context.bot.get_chat(user_id)
        username = user.username or f"ID:{user.id}"
        logger.info(f"Отправка заявки от {username} в чат {staff_chat_id}")

        # Основное сообщение
        message_text = (
            f"🆕 Новая заявка (#{user_id})\n"
            f"👤 Пользователь: @{username if user.username else 'нет username'}\n"
            f"📌 Тип: {user_data.problem_type}\n"
            f"📝 Описание: {user_data.description or 'нет описания'}\n\n"
            f"💬 Чтобы ответить:\n"
            f"1. Ответьте на это сообщение текстом\n"
            f"2. Введите /reply_{user_id}"
        )

        staff_message = await context.bot.send_message(
            chat_id=staff_chat_id,
            text=message_text
        )
        logger.info(f"Сообщение для поддержки отправлено. ID сообщения: {staff_message.message_id}")

        # Отправка медиафайлов
        for media_type, file_id in user_data.media:
            try:
                if media_type == 'photo':
                    await staff_message.reply_photo(
                        photo=file_id,
                        caption=f"Фото от @{username}"
                    )
                    logger.info(f"Фото от {username} отправлено")
                elif media_type == 'video':
                    await staff_message.reply_video(
                        video=file_id,
                        caption=f"Видео от @{username}"
                    )
                    logger.info(f"Видео от {username} отправлено")
            except Exception as e:
                logger.error(f"Ошибка отправки медиа: {str(e)}")
                await context.bot.send_message(
                    chat_id=staff_chat_id,
                    text=f"⚠ Не удалось отправить вложение от @{username}"
                )

    except Exception as e:
        logger.error(f"Критическая ошибка в send_application_to_staff: {str(e)}")
        raise

async def handle_staff_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if not update.message or not update.message.text:
            return

        # Обработка ответа через reply
        if update.message.reply_to_message:
            reply_text = update.message.text
            original_message = update.message.reply_to_message.text
            if "Новая заявка" in original_message:
                # Извлекаем ID пользователя из оригинального сообщения
                user_id_start = original_message.find("(#") + 2
                user_id_end = original_message.find(")", user_id_start)
                if user_id_start > 1 and user_id_end > user_id_start:
                    user_id = int(original_message[user_id_start:user_id_end])
                    
                    # Отправляем ответ пользователю
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"📩 Ответ от поддержки:\n\n{reply_text}",
                        reply_markup=get_feedback_keyboard()
                    )
                    await update.message.reply_text(f"✅ Ответ отправлен пользователю {user_id}")
                    return

        # Обработка команды /reply_12345
        if update.message.text.startswith('/reply_'):
            parts = update.message.text.split('_', 1)
            if len(parts) == 2:
                user_id_str = ''.join(filter(str.isdigit, parts[1].split()[0]))
                if user_id_str:
                    user_id = int(user_id_str)
                    response_text = parts[1][len(user_id_str):].strip()
                    
                    if response_text:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=f"📩 Ответ от поддержки:\n\n{response_text}",
                            reply_markup=get_feedback_keyboard()
                        )
                        await update.message.reply_text(f"✅ Ответ отправлен пользователю {user_id}")
                    else:
                        await update.message.reply_text("❌ Не указан текст ответа")
                else:
                    await update.message.reply_text("❌ Неверный формат команды. Используйте: /reply_12345 Ваш текст")
            else:
                await update.message.reply_text("❌ Неверный формат команды. Используйте: /reply_12345 Ваш текст")

    except Exception as e:
        logger.error(f"Критическая ошибка в handle_staff_response: {str(e)}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        query = update.callback_query
        user_id = query.from_user.id
        
        # Немедленно отвечаем на callback
        await query.answer()
        logger.info(f"Обработка фидбека от пользователя {user_id}")

        # Определяем тип фидбека
        if query.data == 'thanks':
            user_msg = "🙏 Спасибо за обратную связь! Если будут вопросы - пишите /start"
            feedback_msg = f"✅ Пользователь {user_id} подтвердил решение проблемы"
            logger.info(f"Пользователь {user_id} подтвердил решение")
        else:
            user_msg = "🛎 Мы свяжемся с вами для уточнения деталей. Для нового вопроса - /start"
            feedback_msg = f"⚠️ Пользователь {user_id} запросил дополнительную помощь"
            logger.info(f"Пользователь {user_id} запросил помощь")

        # Обновляем сообщение у пользователя
        await query.edit_message_text(
            text=user_msg,
            reply_markup=None  # Убираем клавиатуру
        )

        # Отправляем фидбек в чат поддержки
        staff_chat_id = context.bot_data.get('staff_chat_id')
        if staff_chat_id:
            try:
                await context.bot.send_message(
                    chat_id=staff_chat_id,
                    text=feedback_msg
                )
                logger.info(f"Фидбек отправлен в чат поддержки: {feedback_msg}")
            except Exception as e:
                logger.error(f"Ошибка отправки фидбека: {str(e)}")

    except Exception as e:
        logger.error(f"Ошибка в handle_feedback: {str(e)}")
    finally:
        # Всегда очищаем сессию
        if user_id in user_sessions:
            del user_sessions[user_id]
            logger.info(f"Сессия пользователя {user_id} очищена")
        
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        user_id = update.effective_user.id
        if user_id in user_sessions:
            del user_sessions[user_id]
            logger.info(f"Пользователь {user_id} отменил диалог")
        
        await update.message.reply_text("❌ Диалог прерван. Начните заново: /start")
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Ошибка в cancel: {str(e)}")
        return ConversationHandler.END

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    error = context.error
    logger.error(f"Глобальная ошибка: {str(error)}", exc_info=True)
    
    try:
        if update and update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                "⚠️ Произошла ошибка. Пожалуйста, начните заново: /start",
                reply_markup=None
            )
    except Exception as e:
        logger.error(f"Ошибка в error_handler: {str(e)}")