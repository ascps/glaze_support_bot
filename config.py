import logging

# -- Замените на ваш реальный токен бота!
TOKEN = "7221937653:AAEcpvhUWFEK9muvKFKfPjcRJmAMpvP2Mc4"

# -- Замените на реальный chat_id вашей группы поддержки (или лички)
STAFF_CHAT_ID = -1002587758467  # Например: -1001599097521 для супергруппы

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
(
    STATE_PROBLEM_SELECTION,
    STATE_COLLECT_MEDIA,
    STATE_COLLECT_DESCRIPTION,
    STATE_CONFIRM_SEND,
    STATE_AWAIT_STAFF_REPLY,
    STATE_AWAIT_CLIENT_FEEDBACK
) = range(6)