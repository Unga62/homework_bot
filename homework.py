import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import ApiError, EmptyApiResponse, TokenError

load_dotenv()

LEN_LIST = 0

STATUS = 'Новые статусы не поступили'
TOKEN_ERROR = 'Отсутствует обязательная переменная окружения'

PRACTICUM_TOKEN = os.getenv('YA_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет работоспособность переменных окружения."""
    ALL_TOKEN = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    crash_token = []
    for name, value in ALL_TOKEN.items():
        if value is None:
            logging.critical(f'Ошибка в токене {name}')
            crash_token.append(name)
    if len(crash_token) > LEN_LIST:
        return False
    return True


def send_message(bot, message):
    """Отправляет сообщения пользователю."""
    logging.debug('Начало отправки сообщения пользователю')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Сообщение отправленно: {message}')
    except telegram.error.TelegramError as error:
        logging.error(f'Ошибка отправки сообщения {error}')


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    payload = {'from_date': timestamp}
    try:
        logging.debug(
            'Начало работы телеграм бота, '
            f'ENDPOINT: {ENDPOINT}, headers: {HEADERS}, params: {payload}')
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except requests.RequestException as error:
        raise ApiError(f'Ошибка {error}')
    if response.status_code == HTTPStatus.OK:
        return response.json()
    raise ApiError('Сбой в работе программы: '
                   f'Эндпоинт [{ENDPOINT}] недоступен. '
                   f'Код ответа API: {response.status_code}')


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError('response должен быть словарем')
    if 'homeworks' not in response:
        raise EmptyApiResponse('Ключ "homeworks" не содержит элементов')
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError('Данные вернулись не в виде списка')
    return homeworks


def parse_status(homework):
    """Извлекает статус домашней работы."""
    try:
        homework_name = homework['homework_name']
    except KeyError:
        raise EmptyApiResponse('Ключ "homework_name" отсутствует')
    if 'status' not in homework:
        raise EmptyApiResponse('Ключ "status" отсутствует')
    status = homework['status']
    try:
        verdict = HOMEWORK_VERDICTS[status]
    except KeyError:
        raise EmptyApiResponse(f'Ключ {status} отсутствует'
                               'в словаре HOMEWORK_VERDICTS')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise TokenError(TOKEN_ERROR)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = 0
    old_status = ''
    new_status = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                new_status = parse_status(homeworks[0])
                if old_status != new_status:
                    send_message(bot, new_status)
            else:
                logging.debug(STATUS)
                new_status = STATUS
            timestamp = response.get('current_date', timestamp)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            if old_status != message:
                send_message(bot, message)
                new_status = error
        finally:
            old_status = new_status
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s [%(levelname)s] %(message)s',
        level=logging.DEBUG,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(
                f'{__file__}.log',
                encoding='utf-8')
        ]
    )
    main()
