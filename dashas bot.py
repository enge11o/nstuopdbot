import telebot
from telebot import types
import datetime
import time
import schedule
import sqlite3
import threading
from flask import Flask

app = Flask(__name__)

# Функция для создания базы данных
def create_database():
    conn = sqlite3.connect('tasks.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            task TEXT,
            due_date TEXT
        )
    ''')
    conn.commit()
    conn.close()

create_database()

token = "YOUR_BOT_TOKEN"
bot = telebot.TeleBot(token)

# Проверка задач на текущую дату
def check_tasks():
    conn = sqlite3.connect('tasks.db')
    cursor = conn.cursor()
    today = datetime.date.today().strftime("%Y-%m-%d")
    cursor.execute("SELECT user_id, task FROM tasks WHERE due_date=?", (today,))
    tasks_to_notify = cursor.fetchall()

    for user_id, task in tasks_to_notify:
        bot.send_message(chat_id=user_id, text=f"Напоминание: вы должны сделать {task}")
        cursor.execute("DELETE FROM tasks WHERE user_id=? AND task=? AND due_date = ?", (user_id, task, today))

    conn.commit()
    conn.close()

schedule.every(1).minutes.do(check_tasks)

def schedule_checker():
    while True:
        schedule.run_pending()
        time.sleep(60)

@bot.message_handler(commands=["start"])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Помощь")
    btn2 = types.KeyboardButton("Добавить задачу")
    btn3 = types.KeyboardButton("Показать список задач")
    markup.add(btn1, btn2, btn3)
    bot.send_message(message.chat.id, text=f"Здравствуйте, {message.from_user.first_name}! Я бот-помощник для организации вашего времени", reply_markup=markup)

@bot.message_handler(content_types=['text'])
def func(message):
    if message.text == "Помощь":
        bot.send_message(message.chat.id, text="Я могу добавлять ваши задачи на любую дату. Просто нажмите кнопку 'Добавить задачу', напишите дату (ГГГГ-ММ-ДД) и задачу через пробел.")
    elif message.text == "Добавить задачу":
        bot.send_message(message.chat.id, text="Введите дату (ГГГГ-ММ-ДД) и задачу через пробел.")
        bot.register_next_step_handler(message, add_task)
    elif message.text == "Показать список задач":
        bot.send_message(message.chat.id, text="Введите дату (ГГГГ-ММ-ДД), на которую хотите посмотреть задачу.")
        bot.register_next_step_handler(message, show)

def add_task(message):
    user_id = message.from_user.id
    command = message.text.split(maxsplit=1)
    if len(command) < 2:
        bot.send_message(message.chat.id, "Неверный формат. Введите дату (ГГГГ-ММ-ДД) и задачу через пробел.")
        return
    due_date, task = command
    try:
        datetime.datetime.strptime(due_date, "%Y-%m-%d").date()
    except ValueError:
        bot.send_message(message.chat.id, "Неверный формат даты. Используйте ГГГГ-ММ-ДД.")
        return
    conn = sqlite3.connect('tasks.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (user_id, task, due_date) VALUES (?, ?, ?)", (user_id, task, due_date))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, f"Задача '{task}' добавлена на {due_date}")

def show(message):
    user_id = message.from_user.id
    date = message.text
    conn = sqlite3.connect('tasks.db')
    cursor = conn.cursor()
    cursor.execute("SELECT task FROM tasks WHERE user_id=? AND due_date=?", (user_id, date))
    tasks = cursor.fetchall()
    conn.close()
    if tasks:
        text = f"Задачи на {date}:\n" + "\n".join(f"- {task[0]}" for task in tasks)
    else:
        text = "Задач на эту дату нет."
    bot.send_message(message.chat.id, text)

# Запускаем планировщик в отдельном потоке
threading.Thread(target=schedule_checker, daemon=True).start()

# Запуск бота в отдельном потоке
threading.Thread(target=lambda: bot.polling(none_stop=True), daemon=True).start()

@app.route("/")
def home():
    return "Бот работает!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
