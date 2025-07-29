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

### ManagerGPT
---
`ManagerGPT` в папке `managers` — это файл с модулем взаимодействия с YandexGPT Pro. Через него происходит посыл запросов в YandexGPT. При подаче запроса подается два сообщения в GPT:
1) Контекст сообщения. Например, я задал, чтобы нейросеть отвечала только на вопросы ЕГЭ по информатике.
2) Сам запрос пользователя.

