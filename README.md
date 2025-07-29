# Проект EgeHelperBot 🤖
Проект нацелен на создание помощника для будущих участников ЕГЭ на базе технологий YandexGPT 5 Pro. Доступно два тарифа `info` и `all`. 
- `info` - бот отвечает на вопросы только на счет ЕГЭ по информатике, лимит запросов 1000
- `all` - бот отвечает на вопросы на все предметы, но в контексте ЕГЭ, лимит запросов 2000
# Структура 📃

```
EgelHelperBot/
│
├── .env                    # Файл с переменными окружения (токены, настройки БД)
├── README.md               # Описание проекта
│
├── admin/                  # Администрирование бота
│   ├── __init__.py        
│   └── console.py          # Консоль администрирования
│
├── bot/                    # Основной модуль бота
│   ├── __init__.py
│   └── tg_bot.py           # Главный файл с логикой бота
│
├── managers/               # Бизнес-логика и управление сервисами
│   ├── __init__.py
│   ├── ManagerGPT.py     
│   └──  dataBase.py
```

### Console
---
`console.py`, расположенный в директории `admin`, предназначен для внесения изменений, обновления тарифного плана и счетчика запросов.

```
import sys
from pathlib import Path
from dateutil.relativedelta import relativedelta

ROOT = Path(__file__).parent.parent  # Если файл на 2 уровня глубже (папка/подпапка/файл)
# ROOT = Path(__file__).parent  # Если файл в корневой папке

# Добавляем путь в sys.path (если его там ещё нет)
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from managers.dataBase import DataBaseManager
from datetime import datetime, timedelta

db = DataBaseManager()

"""
Данная функция предназанчена для админов и способна изменять данные о подписке пользователя
"""
def update_follow(user_id: int)-> str:
    db.query_database(f"update users set follow = 1 where user_id = {user_id};", reg=True)
    curr_date = datetime.now()
    count_month = input("Ежемесячная оплата или до конца учебного? [1/2]>> ")
    if count_month == '1':
        future_date = curr_date  + relativedelta(months=1)
    else:
        future_date = '2026-07-01'
    format_future_date = future_date.strftime('%Y-%m-%d')

    db.query_database(f"update users set data_end = '{format_future_date}' where user_id = {user_id};", reg=True)
    new_tarrif_plan = input("Меняем ли тарифный план ? [y/n]>> ")
    if new_tarrif_plan == 'y':
        new_tarrif = input("На какой тарифный план меняем (info, all) ? >> ")
        db.query_database(f"update users set  tarrif_plan = '{new_tarrif}' where user_id = {user_id};", reg=True)
    
    
   
    db.query_database(f"update users set count_requests = {0} where user_id = {user_id};", reg=True)
    db.query_database(f"update users set overpayment = {0} where user_id = {user_id};", reg=True)



admin_ask = input("Знаете ли вы id пользователя? [y/n] >> ")
if admin_ask == 'n':
    user_name = input('Введите имя пользователя, если оно не пустое>> ')
    user_id = db.query_database(f"select user_id from users where user_name_tg = '{user_name}';", reg=True)
    print(user_id)
else:
    user_id = int(input("Введите id пользователя>>"))
update_follow(user_id)
```

### Tg Bot
---

`tg_bot.py` в директории `bot` — это файл с основным модулем бота, который принимает запросы и команды из самого телеграмм-бота. То есть именно через него устанавливается связь программы и 

 ```
from pathlib import Path
import sys

ROOT = Path(__file__).parent.parent  # Если файл на 2 уровня глубже (папка/подпапка/файл)
# ROOT = Path(__file__).parent  # Если файл в корневой папке

# Добавляем путь в sys.path (если его там ещё нет)
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))


import asyncio
import logging
import json
import re
import os



from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
from aiogram.types import InputFile


from managers.dataBase import DataBaseManager
from managers.ManagerGPT import ManagerYandexGPT





load_dotenv()

TG_BOT_TOKEN = os.getenv('TG_API_BOT')
ADMIN_ID = os.getenv('ADMIN_ID')









bot = Bot(token=TG_BOT_TOKEN)
dp = Dispatcher()
db = DataBaseManager()
yaGPT = ManagerYandexGPT()

def check_id_exists_exists(user_id):
    query = f"SELECT EXISTS(SELECT 1 FROM users WHERE user_id = {user_id})"
    result = db.query_database(query)
    return result[0][0]

def parser_response_gpt(response) -> str:
    """Улучшенный парсер с обработкой всех крайних случаев"""
    # Удаляем лишние пробелы и переносы в начале/конце
    response = response.strip()
    
    # Проверяем баланс скобок (быстрый тест на валидность JSON)
    if response.count('{') != response.count('}'):
        raise ValueError("Несбалансированные скобки в JSON")
    
    # Экранируем только настоящие переносы, не трогая \\n
    fixed_response = re.sub(r'(?<!\\)\n', r'\\n', response)
    
    try:
        data = json.loads(fixed_response)
    except json.JSONDecodeError as e:
        # Пытаемся найти и исправить конкретную проблему
        if "Extra data" in str(e):
            # Обрезаем всё после последней закрывающей скобки
            last_brace = fixed_response.rfind('}')
            if last_brace != -1:
                fixed_response = fixed_response[:last_brace+1]
        
        try:
            data = json.loads(fixed_response)
        except json.JSONDecodeError as final_error:
            # Выводим ошибку и проблемный участок
            error_pos = final_error.pos
            raise ValueError(
                f"Не удалось распарсить JSON. Ошибка: {final_error}\n"
                f"Проблемный участок: {fixed_response[max(0, error_pos-50):error_pos+50]}"
            ) from None
    
    return data["result"]["alternatives"][0]["message"]["text"]

@dp.message(Command("start"))
async def start(message: types.Message):
    

    user_id = message.from_user.id
    user_name = message.from_user.username

    if check_id_exists_exists(user_id):
        await message.answer("👋Привет. Ты уже зарагестрирован. Посмотреть команды - /help.")
        return
    else:
        date_now = datetime.now()
        date_now = date_now.strftime('%Y-%m-%d')
        print(user_id)
        db.query_database(f"insert into users (user_id, user_name_tg, data_register) values ({user_id}, '{user_name}', '{date_now}');", reg=True)
    

    await message.answer("👋 Привет! Я бот-помощник 🤖 для подготовки к ЕГЭ. Работаю на базе одной из самых мощных в России моделей ИИ 'YandexGPT'." \

                "\n Посмотреть команды — /help." \

                "\n Здесь имеются два тарифных плана. Для просмотра набери команду /tarrif." \

                "\n Для регистрации тарифного плана обратись к админу через /support (Обращение писать через пробел после команды)."

                "\n Будь внимателен! Количество запросов ограничено. Задавай вопросы как можно более детально, чтобы получить детальный ответ."

                "\n Также прошу обратить внимание, что ИИ может ошибаться! Рекомендую проверять его ответы.")




@dp.message(Command('help'))
async def start(message: types.Message):
    await message.answer("📃Вот список команд:"
    "\n/tarrif - узнать информацию о тарифах"
    "\n/count_req - узнать сколько осталось запросв и сколько потрачено"
    "\n/ask_info - задать вопрос касаемо ЕГЭ по информатике (Обращение писать через пробел после команды)"
    "\n/ask_all - Задать вопрос касаемо других предметов ЕГЭ (Обращение писать через пробел после команды)"
    "\n/support - предеать обращение об ошибке или пожеланиях (Обращение писать через пробел после команды).")

@dp.message(Command('ask_info'))
async def ask_gpt(message: types.Message):
    mess = message.text
    request =mess.replace('/ask_info', '')
    user_id = message.from_user.id
    
    res = yaGPT.ask_yandex_gpt(request, user_id, tarrif_plan='info')
    result, system_message = res[0], res[1]

    response = parser_response_gpt(result)

    await message.answer(response)
    if system_message:
        await message.answer(system_message)

@dp.message(Command('ask_all'))
async def ask_gpt(message: types.Message):
    mess = message.text
    request =mess.replace('/ask_info', '')
    user_id = message.from_user.id
    
    res = yaGPT.ask_yandex_gpt(request, user_id, tarrif_plan='all')
    result, system_message = res[0], res[1]
    if len(result) == 0:
        await message.reply("❌Произошла ошибка. Пришел пустой ответ от ИИ. Передайте ошибку /support. Прошу прощения за неудобства. Обратитесь чуть позже")
 
    response = parser_response_gpt(result)
    

    await message.reply(response)
    if system_message:
        await message.answer(system_message)

    
@dp.message(Command('tarrif'))

async def tarrif_info(message: types.Message):
    await message.answer("Есть два тарифа:" \
    "\n1) info - это нейросеть, которая будет  отвечать в контексте ЕГЭ по информатике (200 руб/мес, лимит запросов в месяц: 1000)" \
    "\n2) all - нейросеть будет отвечать и по вопросам других предметов ЕГЭ (350 руб/мес, лимит запросов в месяц: 2000)"
    "Лимиты косаются только обращений к нейросети через команды /ask_info или /ask_all. На другие команды не распространяется")

@dp.message(Command('count_req'))

async def count_requests(message: types.Message):
    user_id = message.from_user.id
    try:
        count_req = db.query_database(f"select count_requests from users where user_id = {user_id};")[0][0]
        tarrif_plan = db.query_database(f"select tarrif_plan from users where user_id = {user_id};")[0][0]
        limit = 1000
        if not(count_req) and count_req != 0:
            await message.answer("У вас нет тарифного плана или возникла ошибка. Обратитесь в поддержку /support")
        if tarrif_plan == 'all':
            limit = 2000
        elif tarrif_plan == 'info':
            limit = 1000
        await message.answer(f"У тебя израсходавано: {count_req} из {limit}. \nОсталось: {limit - count_req}")
    except Exception as e:
        await message.answer(f"❌Произошла ошибка: {e}. Передайте ошибку в /support")

@dp.message(Command('support'))
async def support_message(message: types.Message):
    await message.forward(ADMIN_ID)
    await message.answer('✅ Сообщние доставлено!')


@dp.message(Command('video'))

async def send_viseo(message: types.Message):
    user_name = message.from_user.username

    await message.answer("Загружаю видео...")
    try:
        file_path = Path(__file__).resolve()
        root_path = file_path.parent.parent
        print(fr'{root_path}\videos\{user_name}\{message.text.replace('/video', '').replace(' ', '')}.webm')
        video = InputFile(fr'{root_path}\videos\{user_name}\{message.text.replace('/video', '').replace(' ', '')}.webm')
    except Exception as e:
        await message.answer(f"Произшла ошибка: {e}, обратитесь в /support и отправьте ошибку.")


async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())



```

### ManagerGPT
---
`ManagerGPT` в папке `managers` — это файл с модулем взаимодействия с YandexGPT Pro. Через него происходит посыл запросов в YandexGPT. При подаче запроса подается два сообщения в GPT:
1) Контекст сообщения. Например, я задал, чтобы нейросеть отвечала только на вопросы ЕГЭ по информатике.
2) Сам запрос пользователя.

```
from managers.dataBase import DataBaseManager
from dotenv import load_dotenv
from datetime import datetime

import requests
import os

load_dotenv()



db = DataBaseManager()

YANDEX_API_KEY = os.getenv('YANDEX_API_KEY')

YANDEX_GPT_URL = os.getenv('YANDEX_GPT_URL')

class ManagerYandexGPT:
    def __init__(self):
        pass
    
    
    def _check_date(self, date_end):
        date_now = datetime.now()
        date_end = datetime.strptime(str(date_end), "%Y-%m-%d")

        if date_end > date_now:
            return False
        return True
    def _check_limit(self, limit: int, user_count_req: int, user_id: int) -> str:
        if user_count_req > limit:
                user_overpayment += 0.2
                db.query_database(f"update users set overpayment = {user_overpayment} where user_id = {user_id};", reg=True)
                return 'У вас превышен лимит запросов. Теперь каждый новый запрос = 0.2 рубля.'
        elif user_count_req == limit:
            return 'Это ваш был последний запрос. Дальше запросы будет стоить по 0.2 рубля'
        return ''
        

    
    def ask_yandex_gpt(self, request: str, user_id: int, tarrif_plan: str) -> str:
        try:
            user_count_req = db.query_database(f"select count_requests from users where user_id = {user_id};")[0][0]
            user_overpayment = db.query_database(f"select overpayment from users where user_id = {user_id};")[0][0]
            user_date_end = db.query_database(f"select data_end from users where user_id = {user_id};")[0][0]
            user_follow = db.query_database(f"select follow from users where user_id = {user_id};")[0][0]
            user_tarrif_plan = db.query_database(f"select tarrif_plan from users where user_id = {user_id};")[0][0]


            if int(user_follow) == 0 or self._check_date(user_date_end):
                return f'У вас истекла подписка. Обратитесь к @egorbatar. Так же у вас есть переплата: {user_overpayment} рублей'
            system_message = ''
            if user_tarrif_plan == 'all':
                system_message = self._check_limit(2000, user_count_req, user_id)
            
            elif user_tarrif_plan == 'info':
                system_message = self._check_limit(1000, user_count_req, user_id)

            if tarrif_plan == 'rus' and user_tarrif_plan == 'all':
                system_text =  "Ты умный помощник в подготовке к ЕГЭ. Отвечай только в контексте ЕГЭ на вопросы, не по ЕГЭ - не отвечай"
            elif tarrif_plan == 'info' and (user_tarrif_plan == 'all' or user_tarrif_plan == 'info'):
                system_text = "Ты умный помощник в подготовке к ЕГЭ по информатике. Отвечай только на вопросы ЕГЭ по информатике."
            else:
                return 'Ваш тарифный план не соответсвует запросу или у вас не оплачена подписка. Обратитесь к @egorbatar .', user_tarrif_plan
            
            user_count_req += 1
            db.query_database(f"update users set count_requests = {user_count_req} where user_id = {user_id};", reg=True)
            headers = {
                "Authorization": f'Api-Key {YANDEX_API_KEY}'
        }

            promt = {
            "modelUri": "gpt://b1gepobpgb2dkh94rn42/yandexgpt",
            "completionOptions": {
                "stream": False,
                "temperature": 0.6,
                "maxTokens": "2000",
                "reasoningOptions": {
                "mode": "DISABLED"
                }
            },
            "messages": [
                {
                "role": "system",
                "text": system_text
                },
                {
                "role": "user", 
                "text": request
                }
            ]
            }  
            response = requests.post(YANDEX_GPT_URL, headers=headers, json=promt)
            result = response.text
            return result, system_message
        except Exception as e:
            return "❌ Ошибка при исполнении: {e}. Передайте ее в /support. "
         

```

### DataBase
---
`database.py` предназначен для работы с запросами к бд, подключения к бд и получения результатов

```
from dotenv import load_dotenv
import psycopg2
import os
from psycopg2 import OperationalError, InterfaceError, DatabaseError

load_dotenv()

class DataBaseManager:
    def __init__(self):
        self.connection = None
        try:
            self.connection = self._connect()
        except Exception as e:
            print(f"Ошибка при подключении к БД: {e}")
            raise  # Пробрасываем исключение дальше для обработки на уровне приложения

    def _connect(self):
        try:
            connect = psycopg2.connect(
                host=os.getenv('HOST_DB'),
                port=os.getenv('PORT_DB'),
                dbname=os.getenv('DB_NAME'),
                user=os.getenv('USER_DB'),
                password=os.getenv('PASSWORD_DB'), 
                client_encoding=os.getenv('CLIENT_ENCODING_DB')
            )
            print("Успешное подключение к БД")
            return connect
        except OperationalError as e:
            print(f"Ошибка подключения к серверу БД: {e}")
            raise
        except Exception as e:
            print(f"Неизвестная ошибка при подключении: {e}")
            raise

    def query_database(self, query, params=None, fetch_one=False, reg=False):
        if not self.connection:
            raise DatabaseError("Нет подключения к БД")
            
        cursor = None
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
                
            if not reg:
                result = cursor.fetchone() if fetch_one else cursor.fetchall()
                self.connection.commit()
                return result
                
            self.connection.commit()
            return None
            
        except (OperationalError, InterfaceError) as e:
            print(f"Ошибка выполнения запроса: {e}")
            self.connection.rollback()
            raise
        except Exception as e:
            print(f"Неизвестная ошибка при выполнении запроса: {e}")
            self.connection.rollback()
            raise
        finally:
            if cursor:
                cursor.close()

    def close(self):
        try:
            if self.connection and not self.connection.closed:
                self.connection.close()
                print("Соединение с БД закрыто")
        except Exception as e:
            print(f"Ошибка при закрытии соединения: {e}")
            raise

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
```
