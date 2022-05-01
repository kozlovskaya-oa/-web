# импортируем библиотеки
from flask import Flask, request
import logging
from waitress import serve
import csv
import random
import requests

import json

app = Flask(__name__)


# Устанавливаем уровень логирования
logging.basicConfig(level=logging.INFO)

sessionStorage = {}

# список с положительными вартиантами ответов
YES = [
    "хорошо",
    "да",
    "конечно",
    "давай",
    "ок",
    "с радостью"
]

# список с отрицательными вартиантами ответов
NO = [
    "нет",
    "не хочу",
    "откажусь",
    "отказываюсь",
    "не хочу",
    "не",
    "не надо"
]

ARTISTS = {
    "леонардо да винчи": "leonardo.csv",
    "сандро боттичелли": "sandro.csv",
    "рафаэль санти": "raphael.csv",
    "микеланджело буонаротти": "michelangelo.csv",
    "рафаэле санти": "raphael.csv"
}


with open('/home/kozlovskayaoa/mysite/where_picture.csv', encoding="utf8") as csvfile:
    WHERE = (list(csv.reader(csvfile, delimiter=':', quotechar='"')))


@app.route('/post', methods=['POST'])
# Функция получает тело запроса и возвращает ответ.
# Внутри функции доступен request.json - это JSON,
# который отправила нам Алиса в запросе POST
def main():
    logging.info(f'Request: {request.json!r}')

    # Начинаем формировать ответ, согласно документации
    # мы собираем словарь, который потом при помощи
    # библиотеки json преобразуем в JSON и отдадим Алисе
    response = {
        'session': request.json['session'],
        'version': request.json['version'],
        'response': {
            'end_session': False
        }
    }

    # непосредственно за ведение диалога
    handle_dialog(request.json, response)

    logging.info(f'Response:  {response!r}')

    # Преобразовываем в JSON и возвращаем
    return json.dumps(response)


def get_adr(place):
    try:
        url = "https://geocode-maps.yandex.ru/1.x/"
        params = {
            "apikey": "40d1649f-0493-4b70-98ba-98533de7710b",
            'geocode': place,
            'format': 'json'
        }
        data = requests.get(url, params).json()
        # все отличие тут, мы получаем имя страны
        return data['response']['GeoObjectCollection'][
            'featureMember'][0]['GeoObject']['metaDataProperty'][
            'GeocoderMetaData']["text"]
    except Exception as e:
        return e


def where_picture(name):
    place = "Извините, я не знаю, где находится эта картина"
    pic = ""
    dat = [x for x in WHERE if x[0] in name]
    if dat:
        place = get_adr(dat[0][1])
        return place
    return place


def random_fact(name):
    file = False
    for elem in ARTISTS:
        if elem in name:
            file = ARTISTS[elem]
    if file:
        with open(f"/home/kozlovskayaoa/mysite/{file}", mode="r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter=":")
            data = random.choice([str(x[1]) for x in reader])
            # находим случайный факт о художнике
            return data
    return f"я не знаю фактов об этом художнике"


def get_first_name(req):
    # перебираем сущности
    for entity in req['request']['nlu']['entities']:
        # находим сущность с типом 'YANDEX.FIO'
        if entity['type'] == 'YANDEX.FIO':
            # Если есть сущность с ключом 'first_name',
            # то возвращаем ее значение.
            # Во всех остальных случаях возвращаем None.
            return entity['value'].get('first_name', None)


def get_suggests(user_id):
    sessionStorage[user_id]['suggests'] = [
                "Что такое эпоха возрождения?",
                "Что ты умеешь?",
                "Мини-игра",
                "где находится картина рождение венеры?",
                "рандомный факт о леонардо да винчи"
            ]
    session = sessionStorage[user_id]
    suggests = [
        {'title': suggest, 'hide': True}
        for suggest in session['suggests']
    ]

    return suggests


def handle_dialog(req, res):
    user_id = req['session']['user_id']

    if req['session']['new']:

        res['response']['text'] = \
            'Привет, это навык, посвященный художникам итальянской эпохи возражденияы! Назови свое имя!'
        # создаем словарь в который в будущем положим имя пользователя
        sessionStorage[user_id] = {
            'first_name': None
        }
        return

        # если пользователь не новый, то попадаем сюда.
        # если поле имени пустое, то это говорит о том,
        # что пользователь еще не представился.
    if sessionStorage[user_id]['first_name'] is None:
        # в последнем его сообщение ищем имя.
        first_name = get_first_name(req)
        if first_name is None:
            res['response']['text'] = \
                    'Мне кажется, я тебя не поняла, повтори пожалуйста свое имя'
            # если нашли, то приветствуем пользователя.
            return
        else:
            sessionStorage[user_id]['first_name'] = first_name
            res['response']["text"] = "Приятно познакомиться!"
            # Получим подсказки
            sessionStorage[user_id]['guessed'] = []
            sessionStorage[user_id]['game_started'] = False
            sessionStorage[user_id]['is_answering'] = False
            sessionStorage[user_id]['continue'] = False
            res['response']['buttons'] = get_suggests(user_id)
            return

    elif "что ты умеешь" in req['request']['original_utterance'].lower():
        dt = ["1. мини игра 'угадай картину'",
              "2. случайный факт о художнике",
              "3. где находится картина?",
              "4. что такое эпоха возрождения?"]
        res['response']['text'] = "\n".join(dt)
        res['response']['buttons'] = get_suggests(user_id)
        return

    elif "что такое" in req['request']['original_utterance'].lower():
        f = open("/home/kozlovskayaoa/mysite/renessans.txt", "rt", encoding="utf-8")
        data = [x.rstrip() for x in f.readlines()]
        res['response']['text'] = "\n".join(data)
        res['response']['buttons'] = get_suggests(user_id)
        return

    elif "факт" in req['request']['original_utterance'].lower():
        fact = random_fact(req['request']['original_utterance'].lower())
        res['response']['text'] = fact
        res['response']['buttons'] = get_suggests(user_id)
        return

    elif "где находится картина" in req['request']['original_utterance'].lower():
        pic = " ".join(req['request']["nlu"]["tokens"]).split("где находится картина")[-1]
        res['response']['text'] = where_picture(pic)
        res['response']['buttons'] = get_suggests(user_id)
        return

    elif "угадай картину" in req['request']['original_utterance'].lower() or\
            "мини-игра" in req['request']['original_utterance'].lower():
        res = game(res, user_id)
        return

    elif sessionStorage[user_id]['game_started'] is True:
        if sessionStorage[user_id]['is_answering'] is True:
            if sessionStorage[user_id]['cur_answ']["name"] in req['request']['original_utterance'].lower():
                res['response']['text'] = \
                    f'Правильно, {str(sessionStorage[user_id]["first_name"]).capitalize()}! Вы большой молодец! Продолжить игру?'
                sessionStorage[user_id]['is_answering'] = False
                sessionStorage[user_id]['continue'] = True
                return
            elif sessionStorage[user_id]['cur_answ']["name"] == "джоконда":
                if "мона лиза" in req['request']['original_utterance'].lower():
                    res['response']['text'] = \
                        f'Правильно, {str(sessionStorage[user_id]["first_name"]).capitalize()}! Вы большой молодец! Продолжить игру?'
                    sessionStorage[user_id]['is_answering'] = False
                    sessionStorage[user_id]['continue'] = True
                    return

            elif sessionStorage[user_id]['try'] == 1:
                res['response']['text'] = \
                    f"Неверно. Подсказка: {sessionStorage[user_id]['cur_answ']['fact']}"
                sessionStorage[user_id]['try'] = 2

            elif sessionStorage[user_id]['try'] == 2:
                res['response']['text'] = \
                    f"Неверно. Автором этой картины является {sessionStorage[user_id]['cur_answ']['artist']}"
                sessionStorage[user_id]['try'] = 3
                return

            elif sessionStorage[user_id]['try'] == 3:
                res['response']['text'] = \
                    f"Неверно, это {str(sessionStorage[user_id]['cur_answ']['name']).capitalize()}, продолжить игру?"
                sessionStorage[user_id]['continue'] = True
                sessionStorage[user_id]['is_answering'] = False
                return

        elif sessionStorage[user_id]['continue'] is True:
            if req['request']['original_utterance'].lower() in YES:
                res = game(res, user_id)
                sessionStorage[user_id]['continue'] = False
                return

            elif req['request']['original_utterance'].lower() in NO:
                res['response']['text'] = f"Ладно"
                res['response']['buttons'] = get_suggests(user_id)
                sessionStorage[user_id]['game_started'] = False
                sessionStorage[user_id]['guessed'] = []
                sessionStorage[user_id]['is_answering'] = False
                sessionStorage[user_id]['continue'] = False
                return

            else:
                res['response']['text'] = "я не совсем поняла, что вы сказали"
                return

    else:
        res['response']['text'] = "Извините, я не совсем поняла ваш запрос"
        res['response']['buttons'] = get_suggests(user_id)
        return


def game(res, user_id):
    if len(sessionStorage[user_id]['guessed']) == 11:
        res['response']['text'] = 'Вы угадали все картины'
        res['response']['buttons'] = get_suggests(user_id)
        sessionStorage[user_id]['game_started'] = False
        sessionStorage[user_id]['guessed'] = []
        sessionStorage[user_id]['is_answering'] = False
        sessionStorage[user_id]['continue'] = False
    else:
        with open('/home/kozlovskayaoa/mysite/guess_pic.csv', encoding="utf8") as csvfile:
            reader = csv.DictReader(csvfile, delimiter=':', quotechar='"')
            data = [x for x in reader]
            sessionStorage[user_id]['cur_answ'] = random.choice(data)
            while sessionStorage[user_id]['cur_answ']["id"] in sessionStorage[user_id]['guessed']:
                sessionStorage[user_id]['cur_answ'] = random.choice(data)
        res['response']['card'] = {}
        res['response']['card']['type'] = 'BigImage'
        res['response']['card']['title'] = 'Что это за картина?'
        res['response']['card']['image_id'] = sessionStorage[user_id]['cur_answ']["ind"]
        res['response']['text'] = 'Тогда сыграем!'
        sessionStorage[user_id]['guessed'].append(sessionStorage[user_id]['cur_answ']["id"])
        sessionStorage[user_id]['game_started'] = True
        sessionStorage[user_id]['is_answering'] = True
        sessionStorage[user_id]['try'] = 1
        return res


if __name__ == '__main__':
    serve(app)