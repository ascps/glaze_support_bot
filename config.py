import logging

# Настройка логгирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Прямые настройки (замените на свои)
TOKEN = "7221937653:AAEcpvhUWFEK9muvKFKfPjcRJmAMpvP2Mc4"
STAFF_CHAT_ID = -1002587758467

# Состояния ConversationHandler
(
    WAITING_FOR_PROBLEM_TYPE,
    WAITING_FOR_APPLICATION_DETAILS,
    WAITING_FOR_STAFF_RESPONSE,
    WAITING_FOR_FEEDBACK,
    WAITING_FOR_OTHER_PROBLEM_DESCRIPTION
) = range(5)