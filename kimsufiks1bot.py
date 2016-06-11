#!/usr/bin/env python

import requests
import json
from telegram.ext import Updater, CommandHandler
import time
from collections import Counter
import config

REFERENCE = {"160sk1": "KS-1"}
API_URL = "https://ws.ovh.com/dedicated/r2/ws.dispatcher/getAvailability2"
DATACENTERS = {
    "bhs": "Beauharnois, Canada",
    "gra": "Gravelines, France",
    "rbx": "Roubaix, France",
    "sbg": "Strasbourf, France",
    "par": "Paris, France"
}
INVALID_ZONES = ['unavailable', 'unknown']


def do_request():
    try:
        r = requests.get(API_URL, timeout=10)
    except requests.exceptions.RequestException as e:
        raise e
    response = r.json()['answer']['availability']
    avails = [avail for avail in response if any(ref == avail['reference'] for ref in REFERENCE)]
    return avails


def format_output(total_by_zone):
    output = ""
    for z in total_by_zone:
        c = total_by_zone[z]
        z = z.split('-')[0]
        output += "{} KS-1 server available in {}\n".format(c, DATACENTERS[z])
    return output


def main_loop(bot, _chat_id):
    while True:
        total_by_zone = Counter()
        try:
            response = do_request()
        except requests.exceptions.RequestException as e:
            bot.sendMessage(chat_id=_chat_id, text=e)
        for r in response:
            for zone in r['zones']:
                avail = zone['availability']
                if avail not in INVALID_ZONES:
                    total_by_zone[zone['zone']] += 1
        if total_by_zone:
            output = format_output(total_by_zone)
            bot.sendMessage(chat_id=_chat_id, text=output)
        time.sleep(300)


def start(bot, update):
    bot.sendMessage(chat_id=update.message.chat_id, text="Hello, welcome here !")
    main_loop(bot, update.message.chat_id)

if __name__ == '__main__':
    updater = Updater(token=config.API_KEY)
    dispatcher = updater.dispatcher
    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)
    updater.start_polling()
    updater.idle()
