import logging
import os
import time

from dotenv import load_dotenv
import requests
import telegram

load_dotenv()


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

logging.basicConfig(
    filename='bot.log',
    filemode='a',
    format='%(asctime)s [%(levelname)s] %(message)s',
    level=logging.DEBUG
)


def check_tokens():
    """Проверяет работоспособность переменных окружения."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True
    else:
        return (f'PRACTICUM_TOKEN: {PRACTICUM_TOKEN},\n'
                f'TELEGRAM_TOKEN: {TELEGRAM_TOKEN},\n'
                f'TELEGRAM_CHAT_ID: {TELEGRAM_CHAT_ID}')


def send_message(bot, message):
    """Отправляет сообщения пользователю."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Сообщение отправленно: {message}')
    except Exception as error:
        logging.error(f'Ошибка отправки сообщения {error}')


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except requests.RequestException as error:
        raise f'Ошибка {error}'
    if response.status_code == 200:
        return response.json()
    raise logging.error(f'Сбой в работе программы: '
                        f'Эндпоинт [{ENDPOINT}] недоступен. '
                        f'Код ответа API: {response.status_code}')


def check_response(response):
    """проверяет ответ API на соответствие документации."""
    if 'homeworks' not in response:
        raise logging.error('Ключ "homeworks" отсутсвует в ответе API')
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError('Данные вернулись не в виде списка')
    return homeworks


def parse_status(homework):
    """Извлекает статус домашней работы."""
    try:
        homework_name = homework['homework_name']
    except KeyError:
        raise logging.error('В ответе API домашки нет ключа "homework_name"')
    status = homework['status']
    try:
        verdict = HOMEWORK_VERDICTS[status]
    except KeyError:
        raise logging.error('Неожиданный ключ'
                            'для словаря HOMEWORK_VERDICTS', {status})
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if check_tokens() is not True:
        raise logging.critical(
            f'Отсутствует обязательная переменная окружения:\n{check_tokens()}'
        )
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            status = parse_status(homeworks[0])
            logging.debug('Бот запустился')
            send_message(bot, status)
            timestamp = int(time.time())
        except Exception as error:
            logging.error(f'Сбой в работе программы: {error}')
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
