#!/usr/bin/env python

"""
This script runs a telegram bot that checks the kimsufi servers availability for users that ask for it.

I took inspiration from ncrocfer's code (https://github.com/ncrocfer/kimsufi-availability) to use and parse
OVH's API.

Author : Gil Brechbühler
"""

import requests
from telegram.ext import Updater, CommandHandler
from collections import Counter
import re
import config

REFERENCE = {
    "160sk1": "KS-1",
    "160sk2": "KS-2A",
    "160sk21": "KS-2B",
    "160sk23": "KS-2D",
    "161sk2": "KS-2E",
    "160sk3": "KS-3A",
    "160sk31": "KS-3B",
    "160sk32": "KS-3C",
    "160sk4": "KS-4A",
    "160sk42": "KS-4C",
    "160sk5": "KS-5"
}
API_URL = "https://ws.ovh.com/dedicated/r2/ws.dispatcher/getAvailability2"
DATACENTERS = {
    "bhs": "Beauharnois, Canada",
    "gra": "Gravelines, France",
    "rbx": "Roubaix, France",
    "sbg": "Strasbourf, France",
    "par": "Paris, France"
}
INVALID_ZONES = ['unavailable', 'unknown']

users_queries = dict()
users_chatid = dict()

WELCOME = "Hello \o/. Please read the help : \n"
HELP = "/check <server name> to check the availability of <server name> every five minutes.\n" \
       "/uncheck <server name> to stop checking the availibility of <server name>.\n\n" \
       "Example :\n" \
       "    /check KS-1A (also works in lower case)\n" \
       "    /uncheck KS-1A (also work in lower case too)\n" \
       "You can add multiple servers to the check by using /check with different <server_name> values."

job_queue = None


def do_request(query):
    try:
        r = requests.get(API_URL, timeout=10)
    except requests.exceptions.RequestException as e:
        raise e
    response = r.json()['answer']['availability']
    search = {k: v for k, v in REFERENCE.items() if v in query}
    avails = [avail for avail in response if any(ref == avail['reference'] for ref in search)]
    return avails


def format_output(total_by_zone, ref):
    output = ""
    for z in total_by_zone:
        c = total_by_zone[z]
        z = z.split('-')[0]
        output += "{} {} server available in {}\n".format(c, ref, DATACENTERS[z])
    return output


def check_avails_loop(bot):
    for user_id, query in users_queries.items():
        output = ""
        total_by_zone = Counter()
        if not query:
            continue
        chat_id = users_chatid[user_id]
        try:
            response = do_request(query)
        except requests.exceptions.RequestException as e:
            bot.sendMessage(chat_id=chat_id, text=e)
        for r in response:
            ref = REFERENCE[r['reference']]
            for zone in r['zones']:
                avail = zone['availability']
                if avail not in INVALID_ZONES:
                    total_by_zone[zone['zone']] += 1
            if total_by_zone:
                output += format_output(total_by_zone, ref)
        if output:
            bot.sendMessage(chat_id=chat_id, text=output)


def remove_cmd_from_message(text):
    return re.sub(r'/\w+\s', '', text)


def alarm(bot, user_id):
    check_avails_loop(bot, user_id)


def check(bot, update):
    text = update.message.text
    user_id = update.message.from_user.id
    chat_id = users_chatid[user_id]
    text = remove_cmd_from_message(text)
    text = text.upper()
    if text in REFERENCE.values():
        users_queries[user_id].append(text)
        bot.sendMessage(chat_id=chat_id, text="Adding {} to the list of servers to check for you".format(text))
    else:
        bot.sendMessage(chat_id=chat_id, text="'{}' not referenced in my database. I can't query its availability, sorry :)".format(text))


def uncheck(bot, update):
    text = update.message.text
    user_id = update.message.from_user.id
    chat_id = users_chatid[user_id]
    text = remove_cmd_from_message(text)
    text = text.upper()
    if text in REFERENCE.values():
        users_queries[user_id].remove(text)
        bot.sendMessage(chat_id=chat_id, text="Removing {} from the list of servers to check for you".format(text))
    else:
        bot.sendMessage(chat_id=chat_id, text="'{}' not in the list of servers to check.".format(text))


def start(bot, update):
    bot.sendMessage(chat_id=update.message.chat_id, text=WELCOME)
    bot.sendMessage(chat_id=update.message.chat_id, text=HELP)
    users_chatid[update.message.from_user.id] = update.message.chat_id
    users_queries[update.message.from_user.id] = []


def help(bot, update):
    bot.sendMessage(chat_id=update.message.chat_id, text=HELP)


if __name__ == '__main__':
    updater = Updater(token=config.TOKEN)
    job_queue = updater.job_queue
    dispatcher = updater.dispatcher
    start_handler = CommandHandler('start', start)
    help_hanlder = CommandHandler('help', help)
    check_handler = CommandHandler('check', check)
    uncheck_handler = CommandHandler('uncheck', uncheck)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(help_hanlder)
    dispatcher.add_handler(check_handler)
    dispatcher.add_handler(uncheck_handler)
    job_queue.put(check_avails_loop, 300)
    updater.start_polling()
    updater.idle()
