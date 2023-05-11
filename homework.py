from http import HTTPStatus
import logging
import os
import time
import sys

import requests

from dotenv import load_dotenv

import telegram

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())


def send_message(bot, message):
    """Отправляет сообщение."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.info('Cообщение успешно отправлено')
    except telegram.TelegramError as error:
        logging.error(f'Сбой при отправке сообщения в Telegram: {error}')


def get_api_answer(current_timestamp):
    """Выполняет запрос к API."""
    params = {'from_date': current_timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception as error:
        raise requests.ConnectionError(f'Ошибка при запросе к API: {error}')
    if response.status_code != HTTPStatus.OK:
        error_message = 'Страница недоступна'
        raise requests.HTTPError(error_message)
    return response.json()


def check_response(response):
    """Проверяет ответ от API на корректность."""
    if not isinstance(response, dict):
        raise TypeError('Ответ API не является словарём')
    homeworks = response.get('homeworks')
    if not homeworks:
        raise Exception('В ответе API нет homeworks')
    if not isinstance(homeworks, list):
        raise TypeError(f'homeworks должно быть списком.\
Сейчас homeworks: {homeworks.__class__}')
    return homeworks


def parse_status(homework):
    """Извлекает статус работы."""
    homework_name = homework.get('homework_name')
    if homework_name is None:
        message_name_none = 'homework_name отсутствует в словаре'
        raise KeyError(message_name_none)
    homework_status = homework.get('status')
    if homework_status is None:
        message_status_none = 'homework_status отсутствует в словаре'
        raise KeyError(message_status_none)
    verdict = HOMEWORK_STATUSES[homework_status]
    if verdict is None:
        verdict_none = 'Неизвестный статус домашней работы в словаре'
        raise KeyError(verdict_none)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность токенов."""
    return all([TELEGRAM_TOKEN, PRACTICUM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(0)
    if not check_tokens():
        logger.critical('Ошибка в получении токенов.')
        sys.exit()
    while True:
        try:
            if check_tokens():
                response = get_api_answer(current_timestamp)
                homework = check_response(response)
                if len(homework) == 0:
                    logger.info('Нет работ на проверке\
или их статус не изменился')
                    continue
                elif len(homework) > 0:
                    message = parse_status(homework[0])
                    send_message(bot, message)
                    print(message)
            current_timestamp = int(time.time())
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            send_message(bot, message)

        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        format=('%(asctime)s'
                '%(name)s'
                '%(levelname)s'
                '%(message)s'
                '%(funcName)s'
                '%(lineno)d'),
        level=logging.INFO,
        filename='program.log',
        filemode='w',
    )
    main()
