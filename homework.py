import logging
import os
import sys
import time
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telebot import apihelper, TeleBot

from exeptions import (ResponseStatusCodeNot200,
                       APIRequestException, 
                       ParseStatusError)


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


def check_tokens():
    """Проверяет доступность переменных окружения."""
    env_var = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    no_key = set()
    for key, value in env_var.items():
        if value is None:
            no_key.add(key)
    if len(no_key) > 0:
        logger.critical(
            "Отсутствует обязательная переменная окружения: "
            f"'{no_key}' Программа принудительно остановлена.")
        sys.exit(1)


def send_message(bot, message):
    """Отправка сообщения в ТГ."""
    try:
        logger.debug(f'Начинаю отправлять сообщение в ТГ')
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Бот отправил сообщение "{message}"')
        return True
    except (apihelper.ApiException, requests.RequestException) as err:
        logger.error(f'Сбой при отправки сообщениея. {err}')
        return False


def get_api_answer(timestamp):
    """Запрос к эндпоинту API-сервиса."""
    try:
        logger.debug(f'Делаю запрос к эндпонту {{ENDPOINT}}')
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
        response = homework_statuses
        logger.debug('Ответ получен.')
    except requests.RequestException as req_err:
        mes_err = (
            'Сбой в работе программы: '
            f'Код ответа API: {req_err}'
        )
        raise APIRequestException(mes_err)
    if response.status_code != HTTPStatus.OK:
        mes_err = (
            'Неожиданный статус-код от API.'
            f' Код ответа API: {response.status_code}'
        )
        raise ResponseStatusCodeNot200(mes_err)
    return response.json()


def check_response(response):
    """Проверяет ответ API."""
    if not isinstance(response, dict):
        mes = (
            f'Ключ "response" {type(homeworks)}.'
            f'Тип данных ответа от API не соответствует ожиданиям.'
        )
        raise TypeError(mes)
    try:
        homeworks = response.get('homeworks')
    except KeyError:
        mes = 'В ответе от API отсутствует ожидаемый ключ.'
        raise KeyError(mes)
    if not isinstance(homeworks, list):
        mes = (
            f'Ключ "homeworks" {type(homeworks)}.'
            f'Тип данных ответа от API не соответствует ожиданиям.'
        )
        raise TypeError(mes)
    return homeworks


def parse_status(homework):
    """Получение статуса домашней работы."""
    homework_name = homework.get('homework_name')
    homework_verdict = homework.get('status')
    if homework_name is None:
        mes = 'В ответе от API отсутствует ожидаемый ключ "homework_name".'
        raise KeyError(mes)
    if homework_verdict is None:
        mes = 'В ответе от API отсутствует ожидаемый ключ "homework_verdict".'
        raise KeyError(mes)
    verdict = HOMEWORK_VERDICTS.get(homework_verdict)
    if verdict is None:
        mes = f'В ответе API обнаружен неожиданный статус {verdict}'
        raise ParseStatusError(mes)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        last_mes = ''
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                mes = parse_status(homeworks[0])
                if send_message(bot, mes):

                    timestamp = response.get('current_date', timestamp)
            else:
                logger.debug('Список домашек пуст.')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if message != last_mes:
                send_message(bot, message)
                last_mes = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
