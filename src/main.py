import os
from telethon import TelegramClient, events
import random
from asyncio import sleep
from dotenv import load_dotenv
from datetime import datetime
import pandas as pd

# Загружаем конфиг в котором хранится апи ключ и апи хэш
load_dotenv('config.env')

API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')

# Подключаемся к аккаунту в телеграмм
client = TelegramClient('anon', API_ID, API_HASH)

# Загружаем таблицы
users = pd.read_csv('users.csv')
exceptions = pd.read_csv('exceptions.csv')


def list_files_in_directory(directory) -> list[str]:
    """Функция проверяет директорию photos и возвращает список с файлами директории"""
    with os.scandir(directory) as entries:
        return [entry.name for entry in entries if entry.is_file()]


# Записываем все пикчи в список
photos = list_files_in_directory('photos')
# Создаём переменную которая отвечает за название изображений и является их индексом
PHOTO_INDEX = len(photos)


def is_user_in_csv(sender, csv_file) -> bool:
    """Функция проверяет есть ли пользователь с таким именем в таблице"""
    return sender.first_name in csv_file['user_name'].astype(str).tolist()


async def help_command(me):
    """Отправляет пользователю информацию о командах"""
    await client.send_message(me.id, '/list - Информация к каким пользователем применяется автоответ'
                                     '/add <Имя пользователя в контактах> '
                                     '- Включает автоответчик для этого пользователя\n'
                                     '/delete <Имя пользователя в контактах>'
                                     '- Выключает автоответчик для этого пользователя\n'
                                     '/except <Имя пользователя в контактах>'
                                     '- Фотографии от этого пользователя не будут сохраняться\n'
                                     '/delete_exception <Имя пользователей в контактах>'
                                     '- Фотографии от этого пользователя теперь будут вновь сохраняться\n')


async def list_command(me):
    user_list = '\n'.join([f'{row["user_name"]}' for _, row in users.iterrows()])
    exception_list = '\n'.join([f'{row["user_name"]}' for _, row in exceptions.iterrows()])
    await client.send_message(me.id, f'Список пользователей для автоответа:\n{user_list}\n'
                                     f'Список пользователей картинки от которых не сохраняются:\n{exception_list}')


async def add_user(event, me):
    """Функция добавляет пользователя в таблицу и на него работает автоответчик"""
    user_name = ' '.join(event.message.message.split()[1:])
    if len(user_name) > 0:
        # Добавляем если пользователя ещё нет в таблице
        if user_name not in users['user_name'].astype(str).tolist():
            users.loc[len(users)] = [user_name]
            users.to_csv('users.csv', index=False)
            await client.send_message(me.id, f'Пользователь {user_name} добавлен')
        else:
            await client.send_message(me.id, 'Этот пользователь уже добавлен')
    else:
        await client.send_message(me.id, 'Неверный формат команды. Используйте: '
                                         '/add <Имя пользователя в контактах>')


async def remove_user(event, me):
    """Удаляет пользователя из таблицы и ему больше не шлются авто-ответы"""
    user_name = ' '.join(event.message.message.split()[1:])
    if len(user_name) > 0:
        if user_name in users['user_name'].astype(str).tolist():
            users.drop(users[users['user_name'] == user_name].index, inplace=True)
            users.to_csv('users.csv', index=False)
            await client.send_message(me.id, f'Пользователь с именем {user_name} успешно удалён')
        else:
            await client.send_message(me.id, f'Пользователя с именем {user_name} не существует')
    else:
        await client.send_message(me.id, f'Команда должна иметь вид /delete <Имя пользователя>)')


async def add_new_exception(event, me):
    """Добавляет выбранного пользователя в таблицу exceptions. Если пользователь находится в этой таблице фотографии
    от него не сохраняются"""
    user_name = ' '.join(event.message.message.split()[1:])
    if len(user_name) > 0:
        if user_name not in exceptions['user_name'].astype(str).tolist():
            exceptions.loc[len(exceptions)] = [user_name]
            exceptions.to_csv('exceptions.csv', index=False)
            await client.send_message(me.id, f'Фотографии от пользователя {user_name} больше не будут сохраняться')
        else:
            await client.send_message(me.id, 'Этот пользователь уже добавлен')
    else:
        await client.send_message(me.id, 'Неверный формат команды. Используйте: '
                                         '/except <Имя пользователя в контактах>')


async def remove_exception(event, me):
    user_name = ' '.join(event.message.message.split()[1:])
    if len(user_name) > 0:
        if user_name in exceptions['user_name'].astype(str).tolist():
            exceptions.drop(users[users['user_name'] == user_name].index, inplace=True)
            exceptions.to_csv('users.csv', index=False)
            await client.send_message(me.id, f'Пользователь с именем {user_name} успешно удалён из исключений')
        else:
            await client.send_message(me.id, f'Пользователя с именем {user_name} не существует')
    else:
        await client.send_message(me.id, f'Команда должна иметь вид /delete_exception <Имя пользователя>)')


async def get_photo(event, time):
    """Функция скачивает фотографию, отправленную другим пользователем и присваивает ей имя photo<index>"""
    global PHOTO_INDEX
    PHOTO_INDEX += 1
    await client.download_media(event.media, file=f'photos/photo{PHOTO_INDEX}.jpg')
    print(f'[{time}] Фото сохранено как photo{PHOTO_INDEX}.jpg')


async def auto_reply(event, time):
    """Выбирается случайная фотография и отправляется пользователю, приславшему сообщение"""
    photo_to_send = random.choice(photos)
    # Случайная задержка перед отправкой фотографии от 2 до 10 сек
    await sleep(random.randint(2, 10))
    await client.send_file(event.chat_id, f'photos/{photo_to_send}')
    print(f'[{time}] AutoReply: {photo_to_send}')


@client.on(events.NewMessage)
async def message_handler(event):
    """Функция срабатывает, когда кто-то отправил сообщение"""
    current_time = datetime.now().strftime("%H:%M")
    try:
        # Получается информация о владельце
        me = await client.get_me()
        # Если сообщение получено от владельца, разблокирует доступ к командам
        if event.chat_id == me.id:
            if event.message.message.startswith('/add'):
                await add_user(event, me)
            elif event.message.message.startswith('/delete'):
                await remove_user(event, me)
            elif event.message.message.startswith('/except'):
                await add_new_exception(event, me)
            elif event.message.message.startswith('/delete_exception'):
                await remove_exception(event, me)
            elif event.message.message.startswith('/help'):
                await help_command(me)
            elif event.message.message.startswith('/list'):
                await list_command(me)
        # Если сообщения личные
        if event.is_private:
            # Получаем информацию об отправителе
            sender = await event.get_sender()
            # Если это фотография, то скачиваем
            if event.media and event.media.photo and not is_user_in_csv(sender, exceptions):
                await get_photo(event, current_time)
                global photos
                # Обновляем список с фотографиями
                photos = list_files_in_directory('photos')
            elif sender.first_name in users['user_name'].astype(str).tolist():
                print(f'[{current_time}] {sender.first_name}: {event.message.message}')
            # Если пользователь в таблице, то отвечаем ему случайной картинкой
            if is_user_in_csv(sender, users):
                await auto_reply(event, current_time)
    except:
        print(f'[{current_time}] Ошибка')


# Обновляем цикл
with client:
    client.run_until_disconnected()
