import logging
import os
import sys
import time

import requests
from dotenv import load_dotenv
from telebot import TeleBot
from pprint import pprint


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s'
)

handler.setFormatter(formatter)

load_dotenv()

RETRY_PERIOD = 600
NINE_MIN = 540
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/433'
HEADERS = {'Authorization': f'OAuth {os.getenv('PRACTICUM_TOKEN')}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    '''Проверяет доступность переменных окружения.'''
    env_var = ['PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']
    for var in env_var:
        if os.getenv(var) is None:
            logger.critical(
                "Отсутствует обязательная переменная окружения: "
                f"'{var}' Программа принудительно остановлена.")
            sys.exit(1)


def send_message(bot, message):
    text = message
    CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    bot.send_message(CHAT_ID, text)
    logger.debug(f'Бот отправил сообщение {text}.')


def get_api_answer(timestamp):
    '''Запрос к эндпоинту API-сервиса.'''
    homework_statuses = requests.get(
        ENDPOINT,
        headers=HEADERS,
        params={'from_date': timestamp}
    )
    response = homework_statuses.json().get('homeworks')
    print(response)
    return response


def check_response(response):
    '''Проверяет ответ API.'''
    if len(response) > 0 and response is not None:
        homework = (
            response[0].get('homework_name'),
            response[0].get('status')
        )
        str = parse_status(homework)
        return str


def parse_status(homework):
    homework_name, homework_verdict = homework
    verdict = HOMEWORK_VERDICTS.get(homework_verdict)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = TeleBot(token=os.getenv('TELEGRAM_TOKEN'))
    #timestamp = int(time.time()) - NINE_MIN
    timestamp = 1736074959
    response = get_api_answer(timestamp)
    mes = check_response(response)
    if mes is not None:
        send_message(bot, mes)

    # while True:
    #     try:
    #         response = get_api_answer(timestamp)
    #         mes = check_response(response)
    #         if mes is not None:
    #             send_message(bot, mes)

    #     except Exception as error:
    #         message = f'Сбой в работе программы: {error}'
    #         logging.error(message)

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
