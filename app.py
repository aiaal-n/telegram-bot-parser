# -*- coding: utf-8 -*-
import os
from bs4 import BeautifulSoup
from datetime import datetime
import telebot
import re
import json
import sqlite3
from urllib import request

base_dir = os.path.dirname(__file__)
host = "http://doska.ykt.ru"
con = sqlite3.connect('db.db', check_same_thread=False, timeout=10)
cur = con.cursor()
try:
    cur.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, username VARCHAR(50), firstName VARCHAR(30), secondName VARCHAR(30), chatId VARCHAR(30), last_post_id INTEGER)')
    con.commit()
except sqlite3.OperationalError:
    None


def getConf():
    f = open(os.path.join(base_dir, 'conf.json'), 'r')
    conf = f.read()
    f.close()
    return json.loads(conf)


bot = telebot.TeleBot(getConf()["token"])

print(bot.get_me())


def log(message, answer):
    try:
        print("\n ------")
        print(datetime.now())
        print("Сообщение от " + str(message.from_user.first_name) + " " + str(
            message.from_user.last_name) + ". id = " + str(message.from_user.id) + ".\nID сообщения - " + str(
            message.message_id) + " Текст - " + str(message.text) + "")
        print("Ответ - " + answer)
    except ValueError:
        pass


# Реагирует на /start, /help, просто отдаёт приветственное сообщение
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_markup = telebot.types.ReplyKeyboardMarkup(True, False)
    user_markup.row('/start', '/send')
    username = message.chat.username
    first_name = message.chat.first_name
    last_name = message.chat.last_name
    chatId = message.chat.id
    cur.execute("SELECT * FROM users WHERE chatId='"+str(chatId)+"'")
    data = cur.fetchone()
    if not data:
        cur.execute('INSERT INTO users (id, username, firstName, secondName, chatId) VALUES(NULL, "'+str(username)+'", "'+str(first_name)+'", "'+str(last_name)+'", "'+str(chatId)+'")')
        con.commit()
    bot.send_message(message.chat.id, "Здравствуйте, я бот парсер обьявлений", reply_markup=user_markup)


@bot.message_handler(commands=['send'])
def send(message):
    answer = 'Отправка сообщений'
    log(message, answer)
    confJson = getConf()
    request.urlopen(host + "/settings?pvt=list").read()
    url = confJson['url']
    page = request.urlopen(host + url).read()
    pages_parse(page, message.chat.id)


def post_parse(post):
    soup = BeautifulSoup(str(post), "html.parser")
    try:
        description = soup.find("div", {"class": "d-post_desc"}).text
    except AttributeError:
        description = "No description"
    try:
        price = soup.find("div", {"class": "d-post_price"}).text
    except AttributeError:
        price = "No price"
    try:
        date = soup.find("span", {"class": "d-post_date"}).text.strip()
    except AttributeError:
        date = "No date"
    try:
        phone = soup.find("span", {"class": "d-post_phone_unmasked"}).text
    except AttributeError:
        phone = "No phone"
    divlink = soup.find("a", {"class": "d-post_link"})
    link = host + divlink["href"]

    return description + "\n" + price + "\n" + phone + "\n" + date + "\n" + link + "\n"


def send_message(content, chatId):
    if not content:
        bot.send_message(chatId, "Список пуст \nНовых записей нет")
    else:
        for cont in reversed(content):
            bot.send_message(chatId, cont)


def pages_parse(page, chatId):
    cur.execute("SELECT * FROM users WHERE chatId='" + str(chatId) + "'")
    data = cur.fetchone()
    last_post_id = data[5]
    soup = BeautifulSoup(page, "html.parser")
    posts = soup.findAll("div", {
        "class": "d-post"
    })
    if last_post_id == '':
        for post in posts:
            m = re.findall('[0-9]+', post["id"])
        last_post_id = m[0]
    maxim = last_post_id
    message = []
    for post in posts:
        m = re.findall('[0-9]+', post["id"])
        post_id = m[0]
        if int(post_id) > int(last_post_id):
            if int(post_id) > int(maxim):
                maxim = post_id
            postContent = post_parse(post)
            message.append(postContent)
    if message is not "":
        send_message(message, chatId)
        cur.execute("UPDATE users SET last_post_id=? WHERE chatId=?", (int(maxim), str(chatId)))
        con.commit()

if __name__ == '__main__':
    bot.polling(none_stop=True)