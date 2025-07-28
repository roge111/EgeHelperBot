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
# res = '{"result":{"alternatives":[{"message":{"role":"assistant","text":"Первая задача ЕГЭ по информатике обычно проверяет базовые знания и умение работать с информацией. Для успешного решения необходимо внимательно прочитать условие задачи, понять, какие данные даны, и определить, какой результат нужно получить.\n\nВот общий подход к решению первой задачи:\n\n1. **Внимательно прочитайте условие задачи.** Определите, какие данные вам даны и что требуется найти.\n2. **Подумайте, какие знания и навыки могут понадобиться для решения задачи.** Это могут быть знания о системах счисления, логических операциях, алгоритмах и т. д.\n3. **Попробуйте решить задачу на бумаге, используя известные вам методы и алгоритмы.** Если задача связана с логическими операциями, постройте таблицу истинности. Если задача на системы счисления, переведите числа в нужную систему и выполните необходимые операции.\n4. **Проверьте своё решение.** Убедитесь, что вы правильно поняли условие задачи и что ваш ответ соответствует требуемому результату.\n5. **Запишите ответ в нужном формате.**\n\nЕсли у вас есть конкретные вопросы по первой задаче или вам нужна помощь с определённым типом задач, пожалуйста, уточните ваш запрос."},"status":"ALTERNATIVE_STATUS_FINAL"}],"usage":{"inputTextTokens":"33","completionTokens":"216","totalTokens":"249","completionTokensDetails":{"reasoningTokens":"0"}},"modelVersion":"09.02.2025"}}'

# print(parser_response_gpt(res))