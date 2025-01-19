import logging
import os
import sys
import time
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telebot import TeleBot


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s'
)

handler.setFormatter(formatter)

load_dotenv()

TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')

RETRY_PERIOD = 600
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
    """Отправка сообщения в ТГ."""
    try:
        text = message
        bot.send_message(TELEGRAM_CHAT_ID, text)
        logger.debug(f'Бот отправил сообщение "{text}"')
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
        if response.status_code != HTTPStatus.OK:
            mes_err = (
                f'Эндпоинт {ENDPOINT} недоступен.'
                f' Код ответа API: {response.status_code}'
            )
            raise ResponseStatusCodeNot200(mes_err)
        return response.json()
    except requests.RequestException as req_err:
        mes_err = (
            'Сбой в работе программы: '
            f'Код ответа API: {req_err}'
        )
        raise RequestException(mes_err)


def check_response(response):
    """Проверяет ответ API."""
    try:
        homeworks = response['homeworks']
    except KeyError:
        mes = 'В ответе от API отсутствует ожидаемый ключ.'
        raise KeyError(mes)
    if not isinstance(homeworks, list):
        mes = 'Тип данных ответа от API не соответствует ожиданиям.'
        raise TypeError(mes)


def parse_status(homework):
    """Получение статуса домашней работы."""
    homework_name = homework.get('homework_name')
    homework_verdict = homework.get('status')
    if homework_name is None or homework_verdict is None:
        mes = 'В ответе от API отсутствует ожидаемый ключ.'
        raise KeyError(mes)
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
    timestamp = int(time.time())

    while True:
        err_message = ''
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homeworks = response.get('homeworks')
            if homeworks:
                for homework in homeworks:
                    mes = parse_status(homework)
                    send_message(bot, mes)
            else:
                logger.debug('В ответе не новых статусов.')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
        finally:
            if err_message:
                logger.error(err_message)
                send_message(bot, message)
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
