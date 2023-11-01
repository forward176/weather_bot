import telebot
import requests
import json
import os
import csv
from telebot.types import Message
from datetime import datetime
from settings import TG_key, API_key


bot = telebot.TeleBot(TG_key)


def get_cities():
    cities = []
    with open('data/cities.csv', 'r', encoding='UTF-8') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        next(reader)
        for city, temp in reader:
            temp = float(temp)
            cities.append((temp, city))
    return cities


def top(count,is_higher=True):
    sp = get_cities()
    sp.sort(reverse=is_higher)
    sp  = sp[:count]
    result = ''
    for temp, city in sp:
        stroka = f'{city}: {temp} °C\n'
        result += stroka    
    return result


def custom(first_temp: int, second_temp: int, count: int):
    if first_temp > second_temp:
        first_temp, second_temp = second_temp, first_temp
    sp = get_cities()
    sp.sort()
    result = ''
    for temp, city in sp:
        if first_temp <= temp <= second_temp:
            stroka = f'{city}: {temp} °C\n'
            result += stroka  
            count -= 1 
            if count == 0:
                break 
    if result == '':
        return 'В заданном диапазоне совсем нет городов.'
    if count != 0:
        result += 'Больше городов в заданном диапазоне нет.'
    return result


def record(user, text):
    time_format = datetime.now()
    file_name = f'data/{user}.txt'
    if not os.path.exists(file_name):
        open(file_name, 'w', encoding='UTF-8').close()
    with open(file_name, 'a', encoding='UTF-8') as file:
        file.write(f'{time_format}: {text}\n')
    with open('data/history.txt', 'a', encoding='UTF-8') as file:
        file.write(f'{time_format}: {text}\n')
 

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, 'Привет! Введи название города,чтобы узнать погоду в нем: ')


@bot.message_handler(commands=['help'])
def help(message):
    txt = '/start - запуск бота👋 \n/help - команды ботам.\n/history - общая история запросов.\n/my_history - моя история запросов.\n/low - 10 самых холодных городов.\n/high - 10 самых жарких городов\n/custom - диапозон температур\nНапишите в чат название города для получения информации о погоде.'
    bot.send_message(message.chat.id, txt)


@bot.message_handler(commands=['history'])
def history(message):
    with open('data/history.txt','r',encoding="UTF-8") as f:
        content = f.read().split('\n')[-10:]
    bot.send_message(message.chat.id, '\n'.join(content))


@bot.message_handler(commands=['my_history'])
def send_welcome(message: Message):
    file_name = f'data/{message.from_user.id}.txt'
    if not os.path.exists(file_name):
        bot.send_message(message.chat.id, "Вы пока не делали запросы") 
    else:
        with open(file_name, "r", encoding='UTF-8') as f: 
            content = f.read().split('\n')[-10:]
        bot.send_message(message.chat.id, '\n'.join(content)) 


@bot.message_handler(commands=['custom'])
def low(message: Message):
    bot.send_message(message.chat.id, "Введите от какой температуры: ")
    bot.register_next_step_handler(message, start_custom)


def start_custom(message: Message):
    first_temp = message.text
    if first_temp.isdigit() or first_temp[0] == '-' and first_temp[1:].isdigit():
        bot.send_message(message.chat.id, "Введите до какой температуры: ")
        bot.register_next_step_handler(message, finish_custom, int(first_temp))
    else:
        bot.reply_to(message, 'Введите только число!')  
        bot.register_next_step_handler(message, start_custom)


def finish_custom(message: Message, first_temp):
    second_temp = message.text
    if second_temp.isdigit() or second_temp[0] == '-' and second_temp[1:].isdigit():
        bot.send_message(message.chat.id, "Для какого кол-ва вывести результат? ")
        bot.register_next_step_handler(message, count_custom, first_temp, int(second_temp))
    else:
        bot.reply_to(message, 'Введите только число!')  
        bot.register_next_step_handler(message, finish_custom, first_temp)


def count_custom(message: Message, first_temp, second_temp):
    count = message.text
    if count.isdigit():
        count = int(count)
        if 1 <= count <= 10:
            bot.reply_to(message, custom(first_temp, second_temp, count))
        else:
            bot.reply_to(message, 'Введите число от 1 до 10 включительно')  
            bot.register_next_step_handler(message, count_custom, first_temp, second_temp)
    else:
        bot.reply_to(message, 'Введите только число!')  
        bot.register_next_step_handler(message, count_custom, first_temp, second_temp)


@bot.message_handler(commands=['low'])
def low(message: Message):
    bot.send_message(message.chat.id, "Сколько самых холодных городов вывести?")
    bot.register_next_step_handler(message, next_top_step, is_higher=False)


@bot.message_handler(commands=['high'])
def low(message: Message):
    bot.send_message(message.chat.id, "Сколько самых тёплых городов вывести?")
    bot.register_next_step_handler(message, next_top_step, is_higher=True)


def next_top_step(message: Message, is_higher=False):
    other = message.text.split()
    if len(other) == 1 and other[0].isdigit() and 1 <= int(other[0]) <= 10:
        count = int(other[0])
    else:
        bot.reply_to(message, "Количество может быть от 1 до 10. Устанавливаю колиество 5.")
        count = 5
    bot.send_message(message.chat.id, top(count, is_higher=is_higher))


@bot.message_handler(content_types=['text'])
def text(message: Message):    
    city = message.text.strip().lower()
    res = requests.get(f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_key}&units=metric')    
    if res.status_code == 200:
        parameters_json = json.loads(res.text)
        response = f'Погода в городе {parameters_json["name"]} - \n'
        response += f'  Страна: {parameters_json["sys"]["country"]}\n'
        response += f'  Температура от {parameters_json["main"]["feels_like"]}°С до {parameters_json["main"]["temp_max"]}°С\n'
        response += f'  Температура по ощущениям - {parameters_json["main"]["temp_min"]}°С\n'
        response += f'  Скорость ветра: {parameters_json["wind"]["speed"]} m/s\n'
        response += f'  Атмосферное давление -{parameters_json["main"]["pressure"]}гПа'
        bot.reply_to(message, response)
    else:
        bot.reply_to(message,'Город введен не правильно! Введи название еще раз: ')
    record(message.chat.id,message.text)
    

bot.enable_save_next_step_handlers()
bot.load_next_step_handlers()
print('Бот запущен')
bot.polling(non_stop=True)