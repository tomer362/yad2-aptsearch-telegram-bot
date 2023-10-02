import requests
import time
import hashlib
import pickle
import os
import datetime


BOT_TOKEN = ''
BOT_CHATID = ''

APT_FILE = r'.\yad2_apts.pickle'
BASE_URL = 'https://gw.yad2.co.il/feed-search-legacy/realestate/rent?rooms=2-4&price=4000-6500&priceOnly=1&forceLdLoad=true&city={ct}&page={pg}'
CITIES = [
    5000, # Tel Aviv
    8600 # Ramat Gan
]
MD5 = 0
INFO = 1
LINK = 'https://www.yad2.co.il/item/{id}'

def processPage(page):
    processed_items = []
    for item in page['data']['feed']['feed_items']:
        if 'type' not in item:
            print("OH OH")
        elif item['type'] == 'ad':
            processed_items.append(processItem(item))
    
    return processed_items

def get_field(dicts, field):
    for d in dicts:
        if d['key'] == field:
            return str(d['value'])
    return ''

def processItem(item):
    item_info = {}
    item_info['desc'] = item['search_text']
    item_info['city'] = item['city']
    item_info['street'] = item['row_1']
    item_info['price'] = item['price']
    item_info['id'] = item['id']

    info = item['row_4']
    item_info['rooms'] = get_field(info, 'rooms')
    item_info['floor'] = get_field(info, 'floor')
    item_info['size'] = get_field(info, 'SquareMeter')

    md5 = get_md5(item_info)
    return [md5, item_info]

def get_page_data(pageNumber, city):
    time.sleep(5.5)
    return requests.get(BASE_URL.format(ct=city, pg=pageNumber)).json()

def get_md5(thing):
    return hashlib.md5(str(thing).encode()).hexdigest()

def get_hashes(path):
    if os.path.exists(path):
        with open(path, 'rb') as hashes_inp:
            return pickle.load(hashes_inp)
    else:
        return {}

def get_current():
    current = []
    for city in CITIES:
        first_page = get_page_data(1, city)
        current.extend(processPage(first_page))

        page_count = int(first_page['data']['pagination']['last_page'])
        for pageNumber in range(2, page_count+1):
            page = get_page_data(pageNumber, city)
            current.extend(processPage(page))
    return current

def merge_dicts(dicts):
    all = {}
    for d in dicts:
        all.update(d)
    return all

def telegram_bot_sendtext(bot_message):
   send_text = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={BOT_CHATID}&parse_mode=Markdown&text={bot_message}'
   response = requests.get(send_text)
   return response.json()

def format_message_new(item):
    link = LINK.format(id=item['id'])
    return f'''Address: {item['street']} {item['city']}
Price: {item['price']}
Rooms: {item['rooms']}
Size: {item['size']}
Link: {link}
'''

def format_message_updated(item):
    link = LINK.format(id=item['id'])
    return f'''Address: {item['street']} {item['city']}
Price: {item['price']}
Rooms: {item['rooms']}
Size: {item['size']}
Link: {link}
Updated: True
'''

def send_items_telegram_new(items):
    for id, item in items.items():
        msg = format_message_new(item[INFO])
        telegram_bot_sendtext(msg)

def send_items_telegram_updated(items):
    for id, item in items.items():
        msg = format_message_updated(item[INFO])
        telegram_bot_sendtext(msg)


def main():
    old = get_hashes(APT_FILE)
    current = get_current()
    new = {}
    updated = {}
    for item in current:
        id = item[INFO]['id']
        if id in old.keys():
            if old[id][MD5] != item[MD5]:
                updated[id] = item
        else:
            new[id] = item

    all = merge_dicts([old, new, updated])
    with open(APT_FILE, 'wb') as out:
        pickle.dump(all, out)

    now = str(datetime.datetime.now()).split('.')[0]
    print(f'{now}: New: {len(new)} | Updated: {len(updated)}')

    send_items_telegram_new(new)
    send_items_telegram_updated(updated)


if __name__ == '__main__':
    while True:
        main()
        time.sleep(60 * 15) # Every 15 minutes check for new apartments