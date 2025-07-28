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
         


