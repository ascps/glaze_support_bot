from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def get_start_keyboard():
    """Клавиатура для выбора типа проблемы"""
    keyboard = [
        [InlineKeyboardButton("Не получилось наклеить стекло", callback_data='application_problem')],
        [InlineKeyboardButton("У меня другая проблема", callback_data='other_problem')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_send_confirmation_keyboard():
    """Клавиатура для подтверждения отправки данных"""
    keyboard = [
        [InlineKeyboardButton("Отправить", callback_data='confirm_send')],
        [InlineKeyboardButton("Отменить", callback_data='cancel_send')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_feedback_keyboard():
    """Клавиатура для обратной связи"""
    keyboard = [
        [InlineKeyboardButton("Спасибо, мне это помогло", callback_data='thanks')],
        [InlineKeyboardButton("Мне нужна еще помощь!, Свяжитесь со мной!", callback_data='more_help')]
    ]
    return InlineKeyboardMarkup(keyboard)