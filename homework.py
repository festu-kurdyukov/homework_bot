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

CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')

RETRY_PERIOD = 600
NINE_MIN = 540
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


class ResponseStatusCodeNot200(Exception):
    """Ответ сервера не равен 200."""


class RequestException(Exception):
    """Сбой при запросе к эндпоинту."""


def check_tokens():
    """Проверяет доступность переменных окружения."""
    env_var = ['PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']
    for var in env_var:
        if os.getenv(var) is None:
            logger.critical(
                "Отсутствует обязательная переменная окружения: "
                f"'{var}' Программа принудительно остановлена.")
            sys.exit(1)


def send_message(bot, message):
    try:
        text = message
        bot.send_message(CHAT_ID, text)
        logger.debug(f'Бот отправил сообщение {text}.')
    except Exception:
        logger.error('Сбой при отправки сообщениея.')


def get_api_answer(timestamp):
    """Запрос к эндпоинту API-сервиса."""
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
        response = homework_statuses
        if response.status_code != 200:
            mes_err = (
                f'Сбой в работе программы: Эндпоинт {ENDPOINT} недоступен.'
                f' Код ответа API: {response.status_code}'
            )
            logger.error(mes_err)
            raise ResponseStatusCodeNot200(mes_err)
        print(response.json())
        return response.json().get('homeworks')
    except requests.exceptions.RequestException as req_err:
        mes_err = (
            'Сбой в работе программы: '
            f'Код ответа API: {req_err}'
        )
        raise RequestException(mes_err)


def check_response(response):
    """Проверяет ответ API."""
    if len(response) > 0:
        homework = (
            response[0]['homework_name'],
            response[0]['status']
        )
        str = parse_status(homework)
        return str
    else:
        logger.debug('В ответе нет новых статусов.')
        return 'В ответе нет новых статусов.'


def parse_status(homework):
    homework_name, homework_verdict = homework
    verdict = HOMEWORK_VERDICTS.get(homework_verdict)
    if verdict is not None:
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        logger.error(f'В ответе API обнаружен неожиданный статус {verdict}')
        return f'Неожиданный статус домашней работы: {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time()) - NINE_MIN

    while True:
        try:
            response = get_api_answer(timestamp)
            mes = ''
            print(mes)
            if response is not None:
                mes = check_response(response)
            else:
                mes = 'В ответе отсутствуют ожидаемые ключи.'
                logger.error(mes)
            send_message(bot, mes)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
