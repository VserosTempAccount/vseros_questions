# -*- coding: utf-8 -*-
from time import sleep

from telebot import types
from telebot.apihelper import ApiTelegramException
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import Config

import cryptography as gh
import mariadb
import telebot
import time


key = Config.cypher_key
K = gh.getKeys(key)

sleep(3)
conn = mariadb.connect(
    host=Config.db_host,
    port=Config.db_port,
    username=Config.db_user,
    password=Config.db_passwd,
    database=Config.db_name
)
cursor = conn.cursor()
token = Config.bot_token

bot = telebot.TeleBot(token)


def cypher(plaintext):
    return gh.encrypt(str(plaintext), K)


def decypher(encrypted):
    return gh.decrypt(str(encrypted), K)


def text_shape(text: str):
    return text[:10]


def get_message(msg, uid, from_id):
    uid = uid.replace('\x00', '')
    if len(uid) == 0:
        bot.reply_to(msg, 'Пользователя, которому вы хотите отправить сообщение, не существует.')
        return
    report_button = InlineKeyboardButton('Пожаловаться', callback_data=f'report {from_id} {msg.id}')
    blacklist_button = InlineKeyboardButton('Заблокировать', callback_data=f'block {from_id} {uid} {msg.id}')
    markup = InlineKeyboardMarkup()
    markup.add(report_button, blacklist_button)
    cursor.execute('''SELECT count(*) FROM blacklist WHERE blacked_id = ? AND user_id = ?''', (from_id, uid))
    result = cursor.fetchone()
    if result[0] != 0:
        bot.reply_to(msg, '⛔ Этот пользователь заблокировал вас. Вы не можете отправлять ему сообщения.')
        return
    cursor.execute(f'''SELECT is_banned FROM users WHERE id = {uid}''')
    status = cursor.fetchone()

    # проверка статусов пользователя
    if not status:
        bot.reply_to(msg,
                     'К сожалению, пользователь, которого вы указали, не зарегистрирован в нашем боте. А значит, мы не можем отправить ему ваше сообщение :(')
        return
    elif status[0]:
        bot.reply_to(msg,
                     'К сожалению, пользователь, которого вы указали, заблокирован в нашем боте. А значит, мы не можем отправить ему ваше сообщение :(')
        return

    # отправка текстового сообщения без вложений
    if msg.content_type == 'text':
        if len(msg.text.split()) == 2 and msg.text[:6] == '/start':
            try:
                uid = msg.text.split()[1]
                uid = decypher(uid)
            except ValueError:
                return
            send = bot.send_message(msg.chat.id, "Напиши своё сообщение!")
            bot.register_next_step_handler(send, get_message, uid, msg.from_user.id)
            return
        try:
            temp = bot.send_message(uid, f'У вас новое сообщение!\n\n{msg.text}', reply_markup=markup)
            bot.send_message(uid,
                             f"<a href=\'{Config.bot_url}?start={cypher(msg.from_user.id)}\'><b>(Ответить)</b></a>",
                             parse_mode='HTML')
            # логгирование сообщений
            cursor.execute(
                f'''INSERT INTO message_log (chat_id, message_id, text, have_attach, attach_id, attach_type, fromuser_id) VALUES (?, ?, ?, "0", "NULL", "NULL", ?)''',
                (uid, temp.id, cypher(msg.text), msg.from_user.id))
            conn.commit()
            bot.reply_to(msg, 'Отправили!')
        except BaseException as e:
            bot.reply_to(msg,
                         'К сожалению, пользователь, которого вы указали, не зарегистрирован в нашем боте. А значит, мы не можем отправить ему ваше сообщение :(')
            print(e)

    elif msg.content_type == 'video':
        try:
            if "caption" not in msg.json:
                temp = bot.send_video(uid, msg.video.file_id, caption='У вас новое сообщение!', reply_markup=markup)
                bot.send_message(uid,
                                 f"<a href=\'{Config.bot_url}?start={cypher(msg.from_user.id)}\'><b>(Ответить)</b></a>",
                                 parse_mode='HTML')
                cursor.execute(
                    f'''INSERT INTO message_log (chat_id, message_id, text, have_attach, attach_id, attach_type, fromuser_id) VALUES (?, ?, ?, "1", ?, "video", ?)''',
                    (uid, temp.id, '<БЕЗ ТЕКСТА>', msg.video.file_id, msg.from_user.id))
            else:
                temp = bot.send_video(uid, msg.video.file_id,
                                      caption='У вас новое сообщение!\n\n' + msg.json['caption'],
                                      reply_markup=markup)
                bot.send_message(uid,
                                 f"<a href=\'{Config.bot_url}?start={cypher(msg.from_user.id)}\'><b>(Ответить)</b></a>",
                                 parse_mode='HTML')
                cursor.execute(
                    f'''INSERT INTO message_log (chat_id, message_id, text, have_attach, attach_id, attach_type, fromuser_id) VALUES (?, ?, ?, "1", ?, "video", ?)''',
                    (uid, temp.id, cypher(msg.caption), msg.video.file_id, msg.from_user.id))
            conn.commit()
            bot.reply_to(msg, 'Отправили!')
        except BaseException as e:
            bot.reply_to(msg,
                         'К сожалению, пользователь, которого вы указали, не зарегистрирован в нашем боте. А значит, мы не можем отправить ему ваше сообщение :(')
            print(e)
    elif msg.content_type == 'photo':
        try:
            if "caption" not in msg.json:
                temp = bot.send_photo(uid, msg.photo[len(msg.photo) - 1].file_id, 'У вас новое сообщение!',
                                      reply_markup=markup)
                bot.send_message(uid,
                                 f"<a href=\'{Config.bot_url}?start={cypher(msg.from_user.id)}\'><b>(Ответить)</b></a>",
                                 parse_mode='HTML')
                cursor.execute(
                    f'''INSERT INTO message_log (chat_id, message_id, text, have_attach, attach_id, attach_type, fromuser_id) VALUES (?, ?, ?, "1", ?, "photo", ?)''',
                    (uid, temp.id, '<БЕЗ ТЕКСТА>', msg.photo[len(msg.photo) - 1].file_id, msg.from_user.id))
            else:
                temp = bot.send_photo(uid, msg.photo[len(msg.photo) - 1].file_id,
                                      'У вас новое сообщение!\n\n' + msg.json['caption'], reply_markup=markup)
                bot.send_message(uid,
                                 f"<a href=\'{Config.bot_url}?start={cypher(msg.from_user.id)}\'><b>(Ответить)</b></a>",
                                 parse_mode='HTML')
                cursor.execute(
                    f'''INSERT INTO message_log (chat_id, message_id, text, have_attach, attach_id, attach_type, fromuser_id) VALUES (?, ?, ?, "1", ?, "photo", ?)''',
                    (uid, temp.id, cypher(msg.caption), msg.photo[len(msg.photo) - 1].file_id, msg.from_user.id))
            conn.commit()
            bot.reply_to(msg, 'Отправили!')
        except BaseException as e:
            bot.reply_to(msg,
                         'К сожалению, пользователь, которого вы указали, не зарегистрирован в нашем боте. А значит, мы не можем отправить ему ваше сообщение :(')
            print(e)
    elif msg.content_type == 'document':
        try:
            if "caption" not in msg.json:
                temp = bot.send_document(uid, msg.document.file_id, caption='У вас новое сообщение!',
                                         reply_markup=markup)
                bot.send_message(uid,
                                 f"<a href=\'{Config.bot_url}?start={cypher(msg.from_user.id)}\'><b>(Ответить)</b></a>",
                                 parse_mode='HTML')
                cursor.execute(
                    f'''INSERT INTO message_log (chat_id, message_id, text, have_attach, attach_id, attach_type, fromuser_id) VALUES (?, ?, ?, "1", ?, "document", ?)''',
                    (uid, temp.id, '<БЕЗ ТЕКСТА>', msg.document.file_id, msg.from_user.id))
            else:
                temp = bot.send_document(uid, msg.document.file_id,
                                         caption='У вас новое сообщение!\n\n' + msg.json['caption'],
                                         reply_markup=markup)
                bot.send_message(uid,
                                 f"<a href=\'{Config.bot_url}?start={cypher(msg.from_user.id)}\'><b>(Ответить)</b></a>",
                                 parse_mode='HTML')
                cursor.execute(
                    f'''INSERT INTO message_log (chat_id, message_id, text, have_attach, attach_id, attach_type, fromuser_id) VALUES (?, ?, ?, "1", ?, "document", ?)''',
                    (uid, temp.id, cypher(msg.caption), msg.document.file_id, msg.from_user.id))
            conn.commit()
            bot.reply_to(msg, 'Отправили!')
        except BaseException as e:
            bot.reply_to(msg,
                         'К сожалению, пользователь, которого вы указали, не зарегистрирован в нашем боте. А значит, мы не можем отправить ему ваше сообщение :(')
            print(e)
    elif msg.content_type == 'audio':
        try:
            if "caption" not in msg.json:
                temp = bot.send_audio(uid, msg.audio.file_id, caption='У вас новое сообщение!', reply_markup=markup)
                bot.send_message(uid,
                                 f"<a href=\'{Config.bot_url}?start={cypher(msg.from_user.id)}\'><b>(Ответить)</b></a>",
                                 parse_mode='HTML')
                cursor.execute(
                    f'''INSERT INTO message_log (chat_id, message_id, text, have_attach, attach_id, attach_type, fromuser_id) VALUES (?, ?, ?, "1", ?, "audio", ?)''',
                    (uid, temp.id, '<БЕЗ ТЕКСТА>', msg.audio.file_id, msg.from_user.id))
            else:
                temp = bot.send_audio(uid, msg.audio.file_id,
                                      caption='У вас новое сообщение!\n\n' + msg.json["caption"],
                                      reply_markup=markup)
                bot.send_message(uid,
                                 f"<a href=\'{Config.bot_url}?start={cypher(msg.from_user.id)}\'><b>(Ответить)</b></a>",
                                 parse_mode='HTML')
                cursor.execute(
                    f'''INSERT INTO message_log (chat_id, message_id, text, have_attach, attach_id, attach_type, fromuser_id) VALUES (?, ?, ?, "1", ?, "audio", ?)''',
                    (uid, temp.id, cypher(msg.caption), msg.audio.file_id, msg.from_user.id))
            conn.commit()
            bot.reply_to(msg, 'Отправили!')
        except BaseException as e:
            bot.reply_to(msg,
                         'К сожалению, пользователь, которого вы указали, не зарегистрирован в нашем боте. А значит, мы не можем отправить ему ваше сообщение :(')
            print(e)
    elif msg.content_type == 'voice':
        try:
            if "caption" not in msg.json:
                temp = bot.send_voice(uid, msg.voice.file_id, caption='У вас новое сообщение!', reply_markup=markup)
                bot.send_message(uid,
                                 f"<a href=\'{Config.bot_url}?start={cypher(msg.from_user.id)}\'><b>(Ответить)</b></a>",
                                 parse_mode='HTML')
                cursor.execute(
                    f'''INSERT INTO message_log (chat_id, message_id, text, have_attach, attach_id, attach_type, fromuser_id) VALUES (?, ?, ?, "1", ?, "voice", ?)''',
                    (uid, temp.id, '<БЕЗ ТЕКСТА>', msg.voice.file_id, msg.from_user.id))
            else:
                temp = bot.send_voice(uid, msg.voice.file_id,
                                      caption='У вас новое сообщение!\n\n' + msg.json["caption"],
                                      reply_markup=markup)
                bot.send_message(uid,
                                 f"<a href=\'{Config.bot_url}?start={cypher(msg.from_user.id)}\'><b>(Ответить)</b></a>",
                                 parse_mode='HTML')
                cursor.execute(
                    f'''INSERT INTO message_log (chat_id, message_id, text, have_attach, attach_id, attach_type, fromuser_id) VALUES (?, ?, ?, "1", ?, "voice", ?)''',
                    (uid, temp.id, cypher(msg.caption), msg.voice.file_id, msg.from_user.id))
            conn.commit()
            bot.reply_to(msg, 'Отправили!')
        except BaseException as e:
            bot.reply_to(msg,
                         'К сожалению, пользователь, которого вы указали, не зарегистрирован в нашем боте. А значит, мы не можем отправить ему ваше сообщение :(')
            print(e)


# noinspection PyBroadException
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    # user: report
    if 'report' in call.data:
        approve_button = InlineKeyboardButton('✅ Принять',
                                              callback_data=f"approve {str(call.data).split(' ')[1]} {call.from_user.id}")
        decline_button = InlineKeyboardButton('⛔ Отклонить',
                                              callback_data=f"decline {call.from_user.id} {str(call.data).split(' ')[1]}")
        markup = InlineKeyboardMarkup()
        markup.add(approve_button, decline_button)
        if int(call.from_user.id) == int(str(call.data).split(' ')[1]):
            bot.edit_message_reply_markup(call.message.chat.id, call.message.id)
            bot.answer_callback_query(call.id, "Нельзя подать жалобу на самого себя!")
            return
        bot.send_message(Config.owner_tg_id,
                         f"""🚨 Новый репорт!\nОт: ID — {call.from_user.id}, юзернейм — @{call.from_user.username}\nНа: ID — {str(call.data).split(' ')[1]}\n\n#new_report #id{str(call.data).split(' ')[1]}""",
                         reply_markup=markup)
        bot.forward_message(Config.owner_tg_id, call.message.chat.id, call.message.id)

        cursor.execute('''INSERT INTO blacklist (user_id, blacked_id, message_id) VALUES (?, ?, ?)''',
                       (call.from_user.id, str(call.data).split(' ')[1], str(call.data).split()[2]))
        conn.commit()
        bot.answer_callback_query(call.id, "Вы успешно добавили пользователя в ЧС и подали на него жалобу.")
        bot.edit_message_reply_markup(call.message.chat.id, call.message.id)

    # local blacklist
    elif 'block' in call.data:
        data = str(call.data).split()
        if int(call.from_user.id) == int(str(call.data).split(' ')[1]):
            bot.edit_message_reply_markup(call.message.chat.id, call.message.id)
            bot.answer_callback_query(call.id, "Нельзя заблокировать самого себя!")
            return
        cursor.execute('''INSERT INTO blacklist (user_id, blacked_id, message_id) VALUES (?, ?, ?)''',
                       (data[2], data[1], str(int(data[3]) + 1)))
        conn.commit()
        bot.answer_callback_query(call.id, '✅ Пользователь успешно заблокирован.')
        bot.edit_message_reply_markup(call.message.chat.id, call.message.id)

    # admin: report approve
    elif 'approve' in call.data:
        if call.from_user.id != Config.owner_tg_id:
            return
        from_uid = str(call.data).split(' ')[2]
        to_uid = str(call.data).split(' ')[1]
        cursor.execute(f'UPDATE users SET is_banned = "1" WHERE id = "{to_uid}"')
        conn.commit()
        bot.edit_message_text(
            f"""✅ Закрытый репорт.\nОт: ID — {from_uid}\nНа: ID — {to_uid}\n\nРешение: принять.\n\n#closed_report #id{to_uid}""",
            call.message.chat.id, call.message.id)
        try:
            bot.send_message(to_uid,
                             f'🛑 Вы были заблокированы за нарушение правил пользования ботом. Обжаловать: {Config.owner_tg_tag}')
        except BaseException:
            pass
        try:
            bot.send_message(from_uid, '✅ Ваша жалоба была принята! Пользователь заблокирован в боте.')
        except BaseException:
            pass

    # admin: report decline
    elif 'decline' in call.data:
        if call.from_user.id != Config.owner_tg_id:
            return
        from_uid = str(call.data).split(' ')[1]
        to_uid = str(call.data).split(' ')[2]
        bot.send_message(from_uid, '🛑 Ваша жалоба была отклонена!')
        bot.edit_message_text(
            f"""🚫 Закрытый репорт.\nОт: ID — {from_uid}\nНа: ID — {to_uid}\n\nРешение: отклонить.\n\n#closed_report #id{to_uid}""",
            call.message.chat.id, call.message.id)

    # user agreement accept
    elif call.data == 'accept':
        cursor.execute(f'''UPDATE users SET accepted = "1" WHERE id = "{call.from_user.id}"''')
        conn.commit()
        bot.answer_callback_query(call.id, 'Пользовательское соглашение успешно принято!')
        bot.edit_message_reply_markup(call.message.chat.id, call.message.id)

    # send mail confirmation
    elif 'yes_confirm' in call.data:
        cursor.execute("SELECT id, is_banned FROM users")
        users = cursor.fetchall()
        text = call.message.text[17:-13]
        time_start = time.time()
        counter = 0
        for i in users:
            try:
                bot.send_message(i[0], text=text)
                sleep(0.3)
            except ApiTelegramException:
                if i[1] == 1:
                    continue
                counter += 1
                cursor.execute(f'''DELETE FROM users WHERE id = "{i[0]}"''')
                conn.commit()
        time_end = time.time()
        bot.edit_message_text(
            f"Рассылка отправлена пользователям за {int(time_end - time_start)} секунд. Удалено {counter} неактивных пользователей.",
            call.message.chat.id, call.message.id)
    elif 'no_confirm' == call.data:
        bot.edit_message_text('Рассылка отменена.', call.message.chat.id, call.message.id)


@bot.message_handler(content_types=['text'])
def new_message(message):
    # admin: checkup function
    if '/checkup' == message.text[:8]:
        if message.from_user.id != Config.owner_tg_id:
            return
        cursor.execute(f'''SELECT count(*) FROM users''')
        count1 = cursor.fetchone()[0]
        cursor.execute(f'''DELETE FROM users WHERE accepted = "0"''')
        conn.commit()
        cursor.execute(f'''SELECT count(*) FROM users''')
        count2 = cursor.fetchone()[0]
        row_count = count1 - count2
        bot.send_message(message.chat.id, f'Проверка прошла успешно. Затронуто {row_count} строк(и).')
        return

    # admin: mail send function
    if '/mail' == message.text[:5]:
        if message.from_user.id != Config.owner_tg_id:
            return
        keyboard = InlineKeyboardMarkup()
        confirm = InlineKeyboardButton('✅', callback_data=f'yes_confirm')
        ignore = InlineKeyboardButton('🛑', callback_data=f'no_confirm')
        keyboard.add(confirm)
        keyboard.add(ignore)
        bot.send_message(message.chat.id, f'Текст рассылки:\n\n{message.text[6:]}\n\nОтправляем?',
                         reply_markup=keyboard)
        return

    # admin: unban function
    if '/unban' == message.text[:6]:
        if message.from_user.id != Config.owner_tg_id:
            return
        to_uid = str(message.text).split(' ')[1]
        cursor.execute(f'''UPDATE users SET is_banned = "0" WHERE id = "{to_uid}"''')
        conn.commit()
        bot.send_message(message.chat.id, 'Разбанен.')
        try:
            bot.send_message(to_uid,
                             '✅ Вы были разблокированы администратором бота.')
        except BaseException:
            pass
        return

    # admin: ban function
    if '/ban' == message.text[:4]:
        if message.from_user.id != Config.owner_tg_id:
            return
        to_uid = str(message.text).split(' ')[1]
        cursor.execute(f'''UPDATE users SET is_banned = "1" WHERE id = "{to_uid}"''')
        conn.commit()
        bot.send_message(message.chat.id, 'Забанен.')
        try:
            bot.send_message(to_uid,
                             f'🛑 Вы были заблокированы за нарушение правил пользования ботом. Обжаловать: {Config.owner_tg_tag}')
        except BaseException:
            pass
        return
    cursor.execute(f'''SELECT name, username, is_banned, accepted FROM users WHERE id = "{message.from_user.id}"''')
    dic = cursor.fetchone()
    if not dic:
        cursor.execute(
            f'''INSERT INTO users (name, username, id) VALUES ("{message.from_user.first_name}", "{message.from_user.username}", "{message.from_user.id}")''')
        conn.commit()
    else:
        agree_button = InlineKeyboardButton('✅ Принять', callback_data='accept')
        markup = InlineKeyboardMarkup()
        markup.add(agree_button)
        if dic[2]:
            bot.send_message(message.chat.id,
                             f'🛑 Вы были заблокированы в боте за нарушение правил пользования. Отправка и принятие сообщений недоступны.\n\nОбжаловать: {Config.owner_tg_tag}')
            return
        if dic[3] == 0:
            bot.send_message(message.chat.id,
                             f'🛑 Чтобы пользоваться ботом, нужно принять пользовательское соглашение.\n\nТекст: {Config.user_agreement_link}',
                             reply_markup=markup)
            return
        if dic[0] != message.from_user.first_name:
            cursor.execute(
                f'''UPDATE users SET name = "{message.from_user.first_name}" WHERE id = "{message.from_user.id}"''')
            conn.commit()
        if dic[1] != message.from_user.username:
            cursor.execute(
                f'''UPDATE users SET username = "{message.from_user.username}" WHERE id = "{message.from_user.id}"''')
            conn.commit()

    # first message function
    if "/start" in message.text:
        if " " in message.text:
            try:
                if len(message.text.split()) > 2:
                    bot.send_message(message.chat.id, "Вы указали слишком много ID!")
                    return
                uid = message.text.split()[1]
                uid = decypher(uid)
            except ValueError:
                return
            send = bot.send_message(message.chat.id, "Напиши своё сообщение!")
            bot.register_next_step_handler(send, get_message, uid, message.from_user.id)
        else:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            btn1 = types.KeyboardButton("Получить ссылку")
            btn2 = types.KeyboardButton("Черный список")
            btn3 = types.KeyboardButton("FAQ")
            markup.add(btn1, btn2, btn3)
            bot.reply_to(message,
                         f"Привет\!\n\nЭто — бот для *анонимных* вопросов\.\nБот создан исключительно на некоммерческой основе и не будет рассылать вам рекламу и прочий раздражающий контент\. Однако, вы можете поддержать создателя бота рублём\. Реквизиты: {Config.bank_creds}\.\nДля просмотра ссылки нажмите на кнопку\.\n\nКодер — {Config.owner_tg_tag}",
                         parse_mode='MarkdownV2', reply_markup=markup)
            return

    # show blacklisted message
    elif '/show' == message.text[:5]:
        if len(message.text.split()) < 2:
            bot.send_message(message.from_user.id,
                             'Вы не указали ID сообщения.')
            return
        mid = message.text.split()[1]
        cursor.execute(
            '''SELECT user_id FROM blacklist WHERE message_id = ?''',
            (mid,)
        )
        result = cursor.fetchone()
        if not result or int(result[0]) != int(message.from_user.id):
            if not result:
                bot.send_message(message.from_user.id, 'Такого сообщения нет!')
                return
        cursor.execute(
            '''SELECT text, have_attach, attach_type, attach_id FROM message_log WHERE message_id = ? AND chat_id = ?''',
            (mid, message.from_user.id))
        result = cursor.fetchone()
        if not result:
            bot.send_message(message.from_user.id, 'Такого сообщения нет!')
        else:
            if result[1]:
                if result[2] == 'video':
                    bot.send_video(message.from_user.id, result[3], caption=decypher(result[0]))
                elif result[2] == 'photo':
                    bot.send_photo(message.from_user.id, result[3], caption=decypher(result[0]))
                elif result[2] == 'document':
                    bot.send_document(message.from_user.id, result[3], caption=decypher(result[0]))
                elif result[2] == 'audio':
                    bot.send_audio(message.from_user.id, result[3], caption=decypher(result[0]))
                elif result[2] == 'voice':
                    bot.send_voice(message.from_user.id, result[3], caption=decypher(result[0]))
            else:
                bot.send_message(message.from_user.id, f'Сообщение:\n\n{decypher(result[0])}')

    # remove from blacklist
    elif '/pardon' == message.text[:7]:
        if len(message.text.split()) < 2:
            bot.send_message(message.from_user.id,
                             'Вы не указали ID сообщения.')
            return
        mid = message.text.split()[1]
        cursor.execute('''DELETE FROM blacklist WHERE message_id = ? AND user_id = ?''', (mid, message.from_user.id))
        conn.commit()
        bot.send_message(message.from_user.id,
                         'Если такой человек был заблокирован вами, то теперь он удалён из вашего ЧС.')

    # get link function
    elif message.text == "Получить ссылку":
        bot.send_message(message.chat.id,
                         f"Ссылка для вопросов тебе: {Config.bot_url}?start={cypher(message.from_user.id)}")

    # get blacklist
    elif message.text == "Черный список":
        blacklist = 'Твой ЧС:\n'
        cursor.execute(f'''SELECT blacked_id, message_id FROM blacklist WHERE user_id = "{message.from_user.id}"''')
        result = cursor.fetchall()
        if not result:
            blacklist = 'В твоём ЧС никого нет!'
        else:
            text_array = []
            for i in result:
                try:
                    cursor.execute(
                        f'''SELECT text FROM message_log WHERE chat_id = ? AND fromuser_id = ? AND message_id = ?''',
                        (message.from_user.id, i[0], i[1]))
                    meow = cursor.fetchone()
                    text_array.append(decypher(meow[0]))
                except BaseException:
                    cursor.execute(
                        f'''SELECT text FROM message_log WHERE chat_id = ? AND fromuser_id = ? AND message_id = ?''',
                        (message.from_user.id, i[0], i[1] + 1))
                    meow = cursor.fetchone()
                    text_array.append(decypher(meow[0]))
            text_gen = map(text_shape, text_array)
            final = zip([i[1] for i in result], text_gen)
            for i in final:
                blacklist += f'\nЧеловек с сообщением №{i[0]}. Текст: {i[1]}...'
            blacklist += '\n\nЧтобы посмотреть всё сообщение, введите команду /show <mid>, где <mid> — ID сообщения (они указаны выше).\nЧтобы удалить человека из ЧС, введите команду /pardon <mid>, где <mid> — ID сообщения.'
        bot.send_message(message.chat.id, blacklist)

    elif message.text == "FAQ":
        bot.send_message(message.from_user.id, "**FAQ**\n\n" +

                         "**Q:** Зачем этот бот вообще создан? Есть же другие\!\n" +
                         "**A:** Многим людям хочется получать полностью анонимные, не содержащие рекламу вопросы, которые можно контролировать\. Наш бот предоставляет именно это\.\n\n" +

                         "**Q:** Как я могу быть уверен, что бот полностью анонимизирует сообщение?\n" +
                         "**A:** Мы используем шифрование по ГОСТу, чтобы шифровать ваши идентификаторы и сообщения\. Это шифрование сложно взломать, а перебор займёт слишком много времени что гарантирует безопасность\.\n\n" +

                         "**Q:** В чём отличие кнопок \"Пожаловаться\" и \"Заблокировать\"?\n" +
                         "**A:** Кнопка \"Пожаловаться\" предназначена для случаев, когда заданный вопрос нарушает Пользовательское Соглашение\. После нажатия кнопки ваш репорт будет отправлен администратору, а если он будет одобрен, то автор вопроса больше не сможет писать никому\.\n" +
                         "Кнопка \"Заблокировать\" же предназначена для помещения пользователя в ваш чёрный список\. Он всё так же сможет писать другим, но не вам\. Это предназначено для случаев, когда вопрос не нарушает Соглашения, но вы не хотите его видеть\.\n" +
                         "При этом кнопка \"Пожаловаться\" также отправляет пользователя в ваш личный ЧС\.\n\n"
                         +
                         f"По всем остальным вопросам следует обращаться к {Config.owner_tg_tag}",
                         parse_mode='MarkdownV2')

    # other messages
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton("Получить ссылку")
        btn2 = types.KeyboardButton("Черный список")
        btn3 = types.KeyboardButton("FAQ")
        markup.add(btn1, btn2, btn3)
        bot.reply_to(message,
                     f"Привет\!\n\nЭто — бот для *анонимных* вопросов\.\nБот создан исключительно на некоммерческой основе и не будет рассылать вам рекламу и прочий раздражающий контент\. Однако, вы можете поддержать создателя бота рублём\. Реквизиты: {Config.bank_creds}\.\nДля просмотра ссылки нажмите на кнопку\.\n\nКодер — {Config.owner_tg_tag}",
                     parse_mode='MarkdownV2', reply_markup=markup)
        return


bot.infinity_polling()
