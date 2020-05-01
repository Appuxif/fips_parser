import itertools
import os.path
import re
import traceback
from datetime import datetime, timedelta, date

import requests
import json
from time import sleep, monotonic
from random import choice, randint, shuffle

import sys
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, unquote_plus
from multiprocessing import Pool

from myworkers import MyWorkers
from database import DB, insert_into_query, update_by_id_query

# Главная страница
URL = 'https://new.fips.ru'
URL_REG = URL + '/registers-web/'
# РЕЕСТР ЗАЯВОК НА РЕГИСТРАЦИЮ ТОВАРНОГО ЗНАКА И ЗНАКА ОБСЛУЖИВАНИЯ РОССИЙСКОЙ ФЕДЕРАЦИИ
ORDERS_URL = URL_REG + 'action?acName=clickRegister&regName=RUTMAP'
# РЕЕСТР ТОВАРНЫХ ЗНАКОВ И ЗНАКОВ ОБСЛУЖИВАНИЯ РОССИЙСКОЙ ФЕДЕРАЦИИ
REGISTERS_URL = URL_REG + 'action?acName=clickRegister&regName=RUTM'
# Корень реестра
URL_ROOT_PATH = 'action?acName=clickTree&nodeId=0&maxLevel=0'

proxy_list = ['http://52.15.172.134:7778']
# with open('proxy.txt', 'r') as f:
#     proxy_list = ['http://' + line.strip() for line in f.readlines()]
# print(proxy_list)
proxy = surnames = names = countries = cities = regions = forms = None


# Подготавливаем список фамилий, городов и регионов для парсинга
def get_surnames(filename=None):
    filename = filename or 'surnames.txt'
    with open(filename, 'rb') as f:
        s = f.read()
    return s.decode().splitlines()


def get_names():
    return get_surnames('names.txt')


def get_cities(filename=None):
    filename = filename or 'cities.txt'
    with open(filename, 'rb') as f:
        s = f.read()
    s = s.decode().splitlines()
    r = {}
    for l in s:
        l = l.split(';')
        r[l[0]] = {'area': l[1], 'region': l[2]}
    # print(r)
    return r


def get_countries():
    return get_surnames('countries.txt')


# def get_regions():
#     with open('regions.txt', 'rb') as f:
#         s = f.read()
#     s = s.decode().splitlines()
#     r = {}
#     for l in s:
#         l = l.split()
#         city = ' '.join(l[1:])
#         r[l[0]] = city
#     # print(r)
#     return r


def get_forms():
    with open('forms.txt', 'rb') as f:
        s = f.read()
    r = {}
    for l in s.decode().splitlines():
        l = l.split(' - ')
        r[l[0]] = l[1]
    return r
# {'https': 'http://52.15.172.134:7778'}


# Функция рандомно выбирает юзерагент из заготовленного файла
def get_random_useragent(filename='User-Agents.json'):
    with open(filename, 'r') as f:
        user_agents = json.load(f)
    user_agent = choice(user_agents)
    return user_agent['useragent']


def dump_data_to_file(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f)


def load_data_from_file(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    else:
        return None


class Parser:
    documents_in_parsing = []  # Список документов, которые находятся в процессе парсинга
    pools = 0  # Счетчик распараллеленных задач. Для отладки
    workers = None
    workers2 = None
    proxies = []
    proxy_ids = []
    document_parse_query = None  # Для кастомизации запроса документа из БД
    requests_amount = 1
    requests_period = 3

    def __init__(self, url, name='default', verbosity=True):
        self.name = name
        self.verbosity = verbosity
        self.url = url
        self.dbleaf = self.name + '_leaf'
        self.dbdocument = self.name + '_document'
        self.dbdocument_file = self.name + '_documentfile'
        self.dbdocument_parse = self.name + '_documentparse'
        self.dbservice_item = self.name + '_serviceitem'
        self.dbwork_state = self.name + '_workstate'
        self.dbwork_state_row = self.name + '_workstaterow'
        self.dbdocument_izv = self.name + '_documentizv'
        self.dbdocument_izvitem = self.name + '_documentizvitem'
        self.dbdocument_izvserviceitem = self.name + '_izvserviceitem'
        self.dbparserhistory = self.name + '_parserhistory'

    def _print(self, *args, **kwargs):
        if self.verbosity:
            self._lprint(*args, **kwargs)

    def _lprint(self, *args, **kwargs):
        with self.get_workers().lock:
            print(self.name, *args, **kwargs)

    def get_workers(self, number=20):
        if self.workers is None:
            self.workers = MyWorkers(number)
        return self.workers

    def get_workers2(self, number=30):
        if self.workers2 is None:
            self.workers2 = MyWorkers(number)
        return self.workers2

    def session_get(self, session, url, name=''):
        r = session.get(url)
        if r.status_code != 200:
            self._lprint(name, r.status_code, r.reason, url)
            return None
        return r

    # Получение списка всех имеющихся на сайте заявок, сохранение их в базу. Занимает очень продолжительное время
    def get_documents_list(self):
        self._lprint('parsing started')
        self.get_orders_leafs([URL_REG + URL_ROOT_PATH])
        sleep(5)
        self.get_workers()._queue.join()
        self.get_workers2()._queue.join()
        self._lprint('parsing done')
        # dump_data_to_file(self.orders_urls, self.name + '.json')

    # Проверяет новые документы только в первой ветке аккордиона на сайте реестра
    def check_new_documents(self):
        self._lprint('check_new_orders started')
        self.get_first_documents_leaf([URL_REG + URL_ROOT_PATH])

    # Возвращает сессию и объект bs4 для парсинга страницы
    def get_page(self, urls, cookies=None):
        with requests.Session() as session:
            session.headers.update({'User-Agent': get_random_useragent()})
            # Формирование куков
            if cookies is not None:
                session.cookies = cookies.copy()
            else:
                # Из-за особенностей сайта, приходится открывать ссылки таким хитрым образом,
                # чтобы сохранять куки в нужной последовательности
                if self.session_get(session, self.url, 'get_page 1').status_code != 200 or \
                        self.session_get(session, self.url, 'get_page 2').status_code != 200:
                    raise Exception('request is bad', self.url)

            # Последовательный переход по списку ссылок.
            for url in urls:
                c = 0
                while c < 3:
                    c += 1
                    try:
                        r = self.session_get(session, url, 'get_page url')
                        break
                    except requests.exceptions.ConnectionError as err:
                        self._lprint('RETRY:', c, str(err))
                else:
                    r = None
                if not r or r.status_code != 200:
                    self._lprint('request is bad', urls)
                    raise Exception('request is bad', urls)

            return session.cookies.copy(), BeautifulSoup(r.text, 'html.parser')

    # Получение содержимого страницы и парсинг этой страницы. Получение ссылок непосредственно на заявки
    def get_page_and_orders(self, order_leaf, cookies=None):
        # if cookies is None:
        #     # Будет создана новая сессия, для прохода всех ссылок последовательно
        #     urls = order_leaf['a_href_steps']
        # else:
        #     # Для старой сессии достаточно перейти по последней ссылке
        #     urls = [order_leaf['a_href_steps'][-1]]
        urls = order_leaf['a_href_steps']
        # cookies, page = self.get_page(urls, cookies)
        cookies, page = self.get_page(urls)
        self.get_orders_from_page(page, order_leaf)

    # Получение ссылок непосредственно на заявки
    def get_orders_from_page(self, page, leaf_obj):
        # Формируем список документов, которые были найдены ранее и находятся в базе
        with self.get_workers().lock:
            existing_documents = DB().fetchall(
                f"SELECT number FROM {self.dbdocument} WHERE leaf_id = '{leaf_obj['id']}'")

        existing_documents = [str(doc['number']) for doc in existing_documents]
        query = f'INSERT INTO {self.dbdocument} ' \
                '(number, url, document_exists, document_parsed, leaf_id, order_done) ' \
                'VALUES '  # Значения добавятся позднее

        values = []
        tbody = page.find('div', class_="bgtable diapazont").find('table', class_='table')
        # Проход по таблице
        for tr in tbody.find_all('tr'):
            for td in tr.find_all('td'):
                tag_a = td.find('a')
                number = getattr(tag_a, 'text', '')
                # Некоторые ячейки могут быть пустыми (последние)
                # Также пропускаем имеющиеся в базе документы
                if tag_a is None or number in existing_documents:
                    continue

                # if not number.isnumeric():
                #     self._print(leaf_obj['name'], number, 'not numeric')
                #     continue

                a_href = tag_a.get('href')
                url = URL + a_href
                values.append(f"('{number}', '{url}', TRUE, FALSE, '{leaf_obj['id']}', FALSE)")
        self._print(leaf_obj['name'], len(values), 'новых документов')

        if values:
            query += ', '.join(values)
            with self.get_workers().lock:
                DB().executeone(query)

    # Проходится по аккордиону только в самом первом листе. Для поиска новых документов в реестре
    def get_first_documents_leaf(self, urls, cookies=None):
        # cookies, page = self.get_page(urls, cookies)
        cookies, page = self.get_page(urls)
        node = page.find_all(class_='middlenode')[-1]
        li = node.find('li')
        self.process_one_li(li, urls, cookies, self.get_first_documents_leaf, False)

    def process_one_li(self, li, urls, cookies, func, new_thread=True):
        tag_a = li.find('a')
        a_href = tag_a.get('href')
        a_with_img = tag_a.find('img')
        name = li.text.strip()
        if a_with_img:
            # Если в теге a есть img - то это раскрывающийся список, нужно его раскрыть по рекурсии
            self.pools += 1
            # self._print('to pool', self.pools, li.text.strip(), a_href)
            next_urls = urls + [URL_REG + a_href]
            # Новая сессия для нового ответвления в поток
            if new_thread:
                self.get_workers().add_task(func, (next_urls,))
            else:
                func(next_urls)
            return 1
        else:
            # Если в теге a нет img - это последний лист, который содержит ссылки на списки документов
            # Сохранение в БД
            leaf_obj = {'name': f"'{name}'",
                        'a_href_steps': f"'{json.dumps(urls + [URL_REG + a_href])}'",
                        'done': 'FALSE'}
            with self.get_workers().lock:
                exists = DB().fetchone(f"SELECT id FROM {self.dbleaf} WHERE name = {leaf_obj['name']}")
                if exists:
                    leaf_obj['id'] = exists['id']
                    DB().update_row(self.dbleaf, leaf_obj)
                else:
                    leaf_obj['id'] = DB().add_row(self.dbleaf, leaf_obj)
            leaf_obj['a_href_steps'] = urls + [URL_REG + a_href]

            # Получение номеров документов
            if new_thread:
                self.get_workers2().add_task(self.get_page_and_orders, (leaf_obj, cookies))
            else:
                self.get_page_and_orders(leaf_obj, cookies)
            # self._print('saved', leaf_obj['id'], leaf_obj['name'])
        return 0

    # Получение ссылок со списками документов. Проходится по аккордиону и переходит на страницу списка документов
    def get_orders_leafs(self, urls=None, cookies=None):
        urls = urls or []
        # cookies, page = self.get_page(urls, cookies)
        cookies, page = self.get_page(urls)
        # Находим последний раскрытый лист аккордиона на странице
        node = page.find_all(class_='middlenode')[-1]
        li_list = node.find_all('li')
        to_pool = 0
        # Обрабатываем все дочерние теги li
        for li in li_list:
            to_pool += self.process_one_li(li, urls, cookies, self.get_orders_leafs)

        if to_pool != 0:
            self._print('to pool', to_pool, self.pools, node.previous_sibling.previous_sibling.text.strip())

    # Запускает парсинг документов в потоках через доступные в базе прокси.
    def parse_all_documents_in_threads(self, number=1):
        stop_iteration = False
        proxies_in_use = []
        try:
            while True:
                # if self.get_workers(number)._queue.qsize() > 0:
                if len(self.get_workers(number).tasks) >= number - 1:
                    sleep(0.1)
                    continue

                if not self.proxies:
                    self._lprint('Поиск прокси в БД')
                    today = date.today()
                    query = f"SELECT * FROM interface_proxies " \
                            f"WHERE is_banned = FALSE AND is_working = TRUE AND in_use = FALSE " \
                            f"AND (documents_parsed < 990 AND date_last_used = '{today}' " \
                            f"OR date_last_used != '{today}')" \
                            f"LIMIT 1"
                    with self.get_workers().lock:
                        db = DB()
                        try:
                            db.c.execute(query)
                            proxy = db.c.fetchone()
                            if proxy:
                                q = f"UPDATE interface_proxies SET in_use = TRUE WHERE id = '{proxy['id']}'"
                                db.c.execute(q)
                                db.conn.commit()
                        finally:
                            db.c.close()
                            db.conn.close()
                    if proxy is None:
                        # self._lprint('Нет доступных прокси. Ждем окончания потоков или закрытия программы')
                        self._lprint('Нет доступных прокси. Ждем')
                        sleep(30)
                        continue
                        # break
                        # in_use = [f"'{p['id']}'" for p in proxies]

                    proxy = dict(proxy)
                    print(proxy['date_last_used'], today)  # TODO: Delete me
                    if proxy['date_last_used'] != today:
                        proxy['documents_parsed'] = 0

                    in_use = [f"'{proxy['id']}'"]
                    # proxies_in_use.extend(in_use)
                    with self.get_workers().lock:
                        use_proxies(in_use)
                    proxies_in_use.append(in_use)
                self._print('Запуск парсинга с прокси', proxy)
                self.get_workers().add_task(self.start_parse_all_documents, (proxy,), proxy['host'])

            self.get_workers()._queue.join()
            self._lprint('Парсинг окончен')
        finally:
            if proxies_in_use:
                with self.get_workers().lock:
                    release_proxies(proxies_in_use)

    def get_rand_times(self):
        d = self.requests_period/self.requests_amount
        if d < 3:
            d = 3
        s = [d]*self.requests_amount
        for i in range(0, int(len(s) / 2)):
            r = randint(0, int(s[i]) - 3)
            s[i] = s[i] - r
            s[len(s) - 1 - i] = s[len(s) - 1 - i] + r
        shuffle(s)
        return s

    # Начинает новый парсинг информации со страницы с документом из списка документов
    def start_parse_all_documents(self, proxy=None):
        documents_parsed = proxy['documents_parsed'] if proxy else 0
        timer = 0
        rand_times = self.get_rand_times()
        print('rand_times', rand_times)  # TODO: DELETE ME
        rand_times = iter(rand_times)
        while self.start_parse_document(proxy, self.document_parse_query):
            documents_parsed += 1
            if monotonic() - timer > 30:
                q = update_by_id_query('interface_proxies', {'id': f"'{proxy['id']}'",
                                                             'documents_parsed': f"'{documents_parsed}'"})
                DB().executeone(q)

            if documents_parsed > 990:
                break

            try:
                t = next(rand_times)
            except StopIteration:
                rand_times = iter(self.get_rand_times())
                t = next(rand_times)

            timer2 = monotonic()
            while monotonic() - timer2 < t + 1:
                sleep(1)

        release_proxies([f"'{proxy['id']}'"])
        q = update_by_id_query('interface_proxies', {'id': f"'{proxy['id']}'",
                                                    'documents_parsed': f"'{documents_parsed}'"})
        DB().executeone(q)

    # Берет из базы и парсит один непарсенный документ
    def start_parse_document(self, proxy=None, query=None):
        # Блокировка нужна, чтобы не было вероятности парсинга одинаковых документов разными потоками
        with self.get_workers().lock:
            # Берем непарсенную заявку из БД
            if query is None:
                # Берем все документы, для которых не принято решение и сортируем по дате парсинга
                query = f'SELECT id, url, number FROM {self.dbdocument} ' \
                        'WHERE document_exists = TRUE AND order_done = FALSE '
            if len(self.documents_in_parsing) > 0:
                query += f'AND id NOT IN ({", ".join(self.documents_in_parsing)}) '
            query += 'ORDER BY date_parsed, number DESC LIMIT 1'
            document_obj = DB().fetchone(query)
            self.documents_in_parsing.append(f"'{document_obj['id']}'")

        # Если нет документов, прекращаем парсинг
        if document_obj is None:
            return False

        # Если возникают какие-то неучтенные ошибки, то ошибка логируется, в БД создается запись о
        # результате парсинга с ошибкой, записывается путь до файла с логами ошибки
        # Далее документ считается спарсенным и парсер переходит к следующему документу
        try:
            result = self.parse_one_document(dict(document_obj), proxy)
        except:
            result = True
            # Логирование ошибки в файл
            now = datetime.now()
            now_str = now.strftime('%Y-%m-%d_%H-%M-%S')
            filename = self.name + '_' + str(document_obj['number']) + '_' + now_str + '.txt'
            filepath = os.path.join('.', 'media', 'logs')
            if not os.path.exists(filepath):
                os.makedirs(filepath)
            error_filename = os.path.join(filepath, filename)
            error_link = '/media/logs/' + filename
            with open(error_filename, 'w') as f:
                traceback.print_exc(file=f)
            traceback.print_exc(file=sys.stdout)
            print('Ошибка залогирована', error_filename)

            # Запись результата парсинга в БД и отметка документа спарсенным
            with self.get_workers().lock:
                DB().executeone(f"UPDATE {self.dbdocument} SET document_parsed = TRUE, "
                                f"date_parsed = '{date.today()}' "
                                f"WHERE id = '{document_obj['id']}'")
                DB().executeone(f"INSERT INTO {self.dbparserhistory} "
                                f"(document_id, date_created, is_error, error_log_file, message) "
                                f"VALUES ('{document_obj['id']}', '{now}', TRUE, '{error_link}', '')")
        finally:
            self.documents_in_parsing.remove(f"'{document_obj['id']}'")

        return result

    # Парсит одну страницу документа
    def parse_one_document(self, document_obj, proxy=None):
        proxies = None
        if proxy:
            s = [proxy['scheme'], '']
            if proxy.get('user') and proxy.get('password'):
                s = s[:-1] + [proxy['user'], ':', proxy["password"], '@'] + ['/']
            s = ''.join(s[:-1] + [proxy['host'], ':', str(proxy['port'])] + s[-1:])
            if 'http' in proxy['scheme']:
                proxies = {'https': s}
            elif 'socks5' in proxy['scheme']:
                proxies = {'socks5': s}

        self._print(document_obj['number'], 'Парсинг документа', document_obj['url'],
                    proxies, proxy['documents_parsed'] if proxy else None)

        filepath = os.path.join('.', 'media', self.name, str(document_obj['number']))
        filename = os.path.join(filepath, 'page.html')
        url = document_obj['url']
        existence = True
        with requests.Session() as session:
            session.headers.update({'User-Agent': get_random_useragent()})

            # Либо парсим локальный файл # TODO: Для отладки
            if os.path.exists(filename):
                self._print(document_obj['number'], 'Парсим локальный файл')
                with open(filename, 'rb') as f:
                    page_content = f.read()
            # Либо загружаем страницу и проверяем на ошибки
            else:
                counter = 0
                while True:
                    try:
                        r = session.get(url, proxies=proxies, timeout=10)
                    except (requests.exceptions.ProxyError, requests.exceptions.ConnectTimeout) as err:
                        self._print(document_obj['number'], 'Ошибка прокси', str(err), type(err))
                        err = str(err).replace("'", '"')
                        with self.get_workers().lock:

                            DB().executeone(f"UPDATE interface_proxies SET is_working = FALSE, "
                                            f"status = '{'Ошибка прокси ' + err[:200]}'"
                                            f"WHERE id = '{proxy['id']}'")
                        return False

                    if r.status_code != 200:
                        self._lprint(document_obj['number'], 'parse_orders', r.status_code, r.reason, url)
                        return False
                        # existence = True
                        # break
                    text = r.text
                    page_content = r.content

                    if 'Слишком быстрый просмотр документов' in text:
                        self._print(document_obj['number'], text, url)
                    elif 'Превышен допустимый предел' in text:
                        self._print(document_obj['number'], text, url)
                        with self.get_workers().lock:
                            DB().executeone(f"UPDATE interface_proxies SET is_working = FALSE, "
                                            f"status = '{text}'"
                                            f"WHERE id = '{proxy['id']}'")
                        return False

                    elif 'Вы заблокированы' in text:
                        self._print(text, 'Поток закрыт')
                        with self.get_workers().lock:
                            DB().executeone(f"UPDATE interface_proxies SET is_banned = TRUE, "
                                            f"status = '{text}'"
                                            f"WHERE id = '{proxy['id']}'")
                        return False

                    elif 'Документ с данным номером отсутствует' in text:
                        self._lprint(document_obj['number'], text, url)
                        existence = False
                        break
                    else:
                        # self._lprint(text)
                        # TODO: Для отладки
                        # Сохранение файла на диск, для дальнейшего парсинга в будущем
                        # Если потребуется обновление, файл нужно будет удалить
                        os.makedirs(filepath, exist_ok=True)
                        with open(filename, 'wb') as f:
                            f.write(page_content)
                        break

                    counter += 1
                    if counter > 3:
                        self._lprint(document_obj['number'], 'counter exceeded', url)
                        return False
                    self._print(document_obj['number'], 'sleep')
                    sleep(3)

            if existence:
                with self.get_workers().lock:
                    DB().executeone(
                        f"UPDATE {self.dbdocument} SET downloaded_page = '{filename}' WHERE id = '{document_obj['id']}'"
                    )
                self.parse_document_page(page_content, document_obj, session, proxies)
            else:
                with self.get_workers().lock:
                    DB().executeone(f"UPDATE {self.dbdocument} SET document_parsed = TRUE, "
                                    f"date_parsed = '{date.today()}', document_exists = FALSE "
                                    f"WHERE id = '{document_obj['id']}'")
            return True

    # Парсит полученную страницу
    def parse_document_page(self, page_content, document, session, proxies):
        raise Exception('Method not implemented yet')


# Записывает в словарь объект из строки вида "(210) Номер заявки: 123456"
def regex_string(string):
    match = re.match(r'(\((?P<number>.[^)]*)\))*\s*(?P<name>.[^:]*)\s*:*\s*(?P<value>[\s\S]*)', string.strip(),
                     flags=re.MULTILINE)
    if match:
        return match.group('number'), match.group('name'), match.group('value').replace("'", "")
    return None


# Возвращает объект даты из строки вида 01.01.2020
def get_date_from_string(string):
    match = re.match(r'(.*)(?P<value>(?P<day>\d{2})\.(?P<month>\d{2})\.(?P<year>\d{4}))(.*)', string)
    if match:
        match = match.groupdict()
        date_splitted = [int(match['day']), int(match['month']), int(match['year'])]
        return date(date_splitted[2], date_splitted[1], date_splitted[0])
    return None


# Сохраняет загруженный файл в нужное место
def download_file(session, proxies, a, document, self_name):
    direct_url = a.get('href')
    if not direct_url.startswith('http'):
        direct_url = URL + direct_url
    filename = direct_url.split('/')[-1]
    filepath = os.path.join('.', 'media', self_name, str(document['number']))
    if not os.path.exists(filepath):
        os.makedirs(filepath)

    filepath = os.path.join(filepath, filename)
    link = f'/media/{self_name}/{document["number"]}/{filename}'
    # print(direct_url)
    # Если файла нет на диске, то загружаем его
    if not os.path.exists(filepath):
        r = session.get(direct_url, proxies=proxies)
        if r.status_code != 200:
            # print('Файл не был загружен')
            return None
        # filename = os.path.join('.'', 'media', 'files', )
        with open(filepath, 'wb') as f:
            f.write(r.content)
    return direct_url, link


numbers_fields_values_dict = {
    '111': 'order_register_number',  # (111) Номер регистрации
    '210': 'order_number',  # (210) Номер заявки
    '310': 'first_order_number',  # (310) Номер первой заявки
    '330': 'first_order_country_code',  # (330) Код страны подачи первой заявки
    '526': 'unprotected',  # (526) Неохраняемые элементы товарного знака
    '554': 'volumetric',  # (554) Объемный знак
    '550': 'sign_char',  # (550) Указание, относящееся к виду знака, и его характеристики
    '591': 'color',  # (591) Указание цвета или цветового сочетания
    '731': 'applicant',  # (731) Заявитель
    '732': 'copyright_holder',  # (732) Правообладатель
    '740': 'patent_atty',  # (740) Патентный поверенный (полное имя, регистрационный номер, местонахождение)
    '750': 'address'  # (750) Адрес для переписки
}

numbers_fields_dates_dict = {
    '151': 'date_gos_reg',  # (151) Дата государственной регистрации
    '181': 'date_exclusive',  # (181) Дата истечения срока действия исключительного права
    '220': 'date_created',  # (220) Дата подачи заявки
    '320': 'first_order_date',  # (320) Дата подачи заявки
    '450': 'date_publish',  # (450) Дата публикации
    '580': 'date_changes'  # (580) Дата внесения записи в Государственный реестр:
}


# Функция используется для парсинга основной инфомрации со страницы документа
# Сохраняет информацию в словари, которые получает на входе
def parse_main_info(page, document, document_info, document_parse, service_items, session, proxies, self_name, start_izvs=None):
    documentfile_values = []
    serviceitem_values = []
    message = ''

    if start_izvs:
        message += 'Есть извещения. '
        all_p = start_izvs.find_all_previous('p', class_='bib')
    else:
        all_p = page.find_all('p', class_='bib')

    for child in all_p:
        child_text = getattr(child, 'text', '')
        number, name, value = regex_string(child_text) or ("", "", "")

        if number in numbers_fields_values_dict:
            value = re.sub('[-\'{}]', '', value)
            # value = value.replace("'", '"')
            document_parse[numbers_fields_values_dict[number]] = f"'{value}'" if value else 'NULL'

        elif number in numbers_fields_dates_dict:
            date = get_date_from_string(value)
            document_parse[numbers_fields_dates_dict[number]] = f"'{date}'" if date else 'NULL'

        # (511) Классы МКТУ и перечень товаров и/или услуг:
        elif number == '511':
            parsed_service_items = []
            for b in child.find_all('b'):
                line = b.text.split()
                number = line[0]
                parsed_service_items.append(number)
                text = ' '.join(line[1:])
                text = re.sub('[-\'{}]', '', text)
                # print(number, text)
                if number not in service_items:
                    serviceitem_values.append(f"('{document['id']}', {{0}}, '{number}', '{text}')")
            if parsed_service_items:
                document_parse['service_items'] = f"'{', '.join(parsed_service_items)}'"

        # (540) Изображение заявляемого обозначения
        elif number == '540':
            a = child.find('a')
            answer = download_file(session, proxies, a, document, self_name)
            if answer is None:
                message += 'Ошибка загрузки изображения.'
            elif answer:
                direct_url, link = answer
                documentfile_values.append(
                    f"('{document['id']}', {{0}}, 'image', '{direct_url}', '{link}')"
                )

        # Сохраняем неучтенные объекты
        else:
            document_info['unresolved'] = document_info.get('unresolved', '') + ' '.join(child_text.split()) + '\n'

    return message, documentfile_values, serviceitem_values


# Парсит факсимильные файлы со страницы документа
def parse_facsimile(page, document, session, proxies, self_name):
    interface_parsedorderfile_values = []
    message = ''
    p_all = page.find_all('p', class_='bibc')
    for child in p_all:
        child_text = getattr(child, 'text', '')
        if 'Факсимильные изображения' in child_text:
            child = child.next_sibling.next_sibling
            for a in child.find_all('a'):
                answer = download_file(session, proxies, a, document, self_name)
                if answer is None:
                    message = 'Ошибка загрузки факсимального изображения'
                elif answer:
                    direct_url, link = answer
                    interface_parsedorderfile_values.append(
                        f"('{document['id']}', {{0}}, 'facsimile', '{direct_url}', '{link}')"
                    )
    return message, interface_parsedorderfile_values


def use_proxies(ids_list):
    ids = ', '.join(ids_list)
    DB().executeone(f'UPDATE interface_proxies SET in_use = TRUE WHERE id IN ({ids})')


def release_proxies(ids_list=None):
    if ids_list:
        ids = ', '.join(ids_list)
        DB().executeone(f'UPDATE interface_proxies SET in_use = FALSE WHERE id IN ({ids})')
        print("Прокси", ids_list, "освобождены")
    else:
        DB().executeone(f'UPDATE interface_proxies SET in_use = FALSE')
        print("Все прокси освобождены")


def load_proxies_to_db_from_file(filename=None):
    filename = filename or 'proxy_http_ip.txt'
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            proxies = f.readlines()
        values = []
        for proxy in proxies:
            # match = re.match(r'(.*)(?P<value>(?P<day>\d{2})\.(?P<month>\d{2})\.(?P<year>\d{4}))(.*)', proxy)
            match = re.match(r'(?P<scheme>https*://)(?P<host>\d+\.\d+\.\d+\.\d+):(?P<port>\d+)', proxy)
            g = match.groupdict()
            values.append(
                f"('{g['scheme']}', '{g['host']}', '{g['port']}', FALSE, TRUE, FALSE)"
            )
            print(match.groupdict())
        if values:
            q = "INSERT INTO interface_proxies (scheme, host, port, is_banned, is_working, in_use) VALUES "
            q += ', '.join(values)
            print(q)
            DB().executeone(q)
        else:
            print('Не получены значения')
    else:
        print('Файл не найден')


def parse_person_address(applicant_string, item, person):
    item_splitted = re.sub(r'(ГОРОД|город|г\.)', '', item, re.IGNORECASE).strip()
    item_splitted = item_splitted.split()
    applicant_string_lower = applicant_string.lower()
    # Ищем каждое слово среди списка городов

    # Ищем город
    if re.match(r'.*(город|г\.).*', item, re.IGNORECASE):
        person['city'] = re.sub(r'(город |г\.)', '', item, flags=re.IGNORECASE).strip()

    # Ищем край или область
    if re.match(r'.*(край|область|обл).*', item, re.IGNORECASE):
        person['state'] = item.strip()

    # Ищем район
    if re.match(r'.*(район).*', item, re.IGNORECASE):
        person['area'] = item.strip()

    for c in item_splitted:
        # print('city', c)
        c = c.capitalize()

        if re.match(r'.*(поселок|проспект|пркт|улица|ул\.|край|область|обл\.|\d).*', item, re.IGNORECASE) or person.get('city'):
            # print('пропущено', item)
            continue

        # Еще раз пробегаемся по заготовленным городам
        if c in cities:
            if person.get('city') is None:
                person['city'] = c

            # Край/область
            if person.get('state') is None and cities[c]['region']:
                if cities[c]['region'].lower() in applicant_string_lower:
                    person['state'] = cities[c]['region'] or 'NULL'
                else:
                    pass
            # Район
            if person.get('area') is None and cities[c]['area']:
                if cities[c]['area'].lower() in applicant_string_lower:
                    person['area'] = cities[c]['area'] or 'NULL'
                else:
                    pass

    # Поиск по странам
    if item in countries:
        person['country'] = item
    else:
        # Ищем кадое слово среди списка стран
        for c in item_splitted:
            if person.get('country'):
                break
            if c in countries:
                person['country'] = c


def parse_zip_code(applicant_string, person):
    zip_code = re.match(r'.*(?P<zip>\d{6}).*', applicant_string) or \
               re.match(r'.*(?P<zip>\d{5}).*', applicant_string) or \
               re.match(r'.*(?P<zip>\d{4}).*', applicant_string)

    if zip_code:
        zip_code = zip_code.groupdict().get('zip') or 'NULL'
        person['zip'] = zip_code


def parse_applicant(document_parse, type):
    applicant = None
    # Получаем наименование компании из поля document_parse['applicant'] или document_parse['copyright_holder']
    # Нужно искать компанию, либо Имя-Фамилию контакта
    applicant_string = document_parse.get(type)

    if applicant_string:
        applicant = {'company': {}, 'person': {}}
        applicant_string_splitted = applicant_string[1:-1].split(', ')

        # Находим код страны
        sign_char = re.match(r'.*(?P<sign>[A-Z]{2}).*', applicant_string_splitted[0]) or \
                    re.match(r'.*(?P<sign>[A-Z]{2}).*', applicant_string_splitted[-1])
        if sign_char:
            sign_char = sign_char.groupdict().get('sign') or 'NULL'
            applicant['company']['sign_char'] = sign_char
            applicant_string = applicant_string.replace(sign_char, '')
            # print('Код страны', sign_char)

        parse_zip_code(applicant_string, applicant['person'])

        for item in applicant_string_splitted:
            # print('item', item)

            # Ищем известную организационную форму
            # Если найдена форма - это название компании
            if applicant['company'].get('name') is None:
                for form in forms:

                    if form in item:
                        applicant['company']['form'] = forms[form]
                        applicant['company']['name'] = re.sub(r'(^|\s)' + form + r'($|\s)', '', item).strip()
                        applicant_string = applicant_string.replace(item, '')
                        if not applicant['company']['name']:
                            applicant['company']['name'] = applicant_string_splitted[1].strip()
                            applicant_string = applicant_string.replace(applicant_string_splitted[1], '')
                        item = ''

            # Парсим адрес из элементов
            parse_person_address(applicant_string, item, applicant['person'])

            # Если найдена фамилия - то это ФИО контакта
            item_splitted = item.split()
            sur_found = first_found = second_found = middle_found = False

            # if re.match(r'.*(ул\.|г\.|обл\.|д\.|кв\.|\d).*', item):
            if re.match(r'.*(федерация|пркт|проспект|улица|ул\.|город|г\.|область|обл\.|\d).*', item.lower()):
                # print('пропущено', item)
                continue

            # Парсинг ФИО
            for isp in item_splitted:
                isp = isp.capitalize()
                if isp in cities:
                    continue
                if isp in countries:
                    continue
                if isp in surnames:
                    pass
                elif isp[-1] == 'у' and isp[:-1] in surnames:
                    item = re.sub(isp, isp[:-1], item)
                    isp = isp[:-1]
                elif isp[-2:] == 'ой' and isp[:-2] in surnames:
                    item = re.sub(isp, isp[:-2], item)
                    isp = isp[:-2] + 'а'
                else:
                    continue
                if not sur_found:
                    sur_found = True
                    applicant['person']['full_name'] = re.sub('(ИП|Индивидуальный предприниматель)', '',
                                                              item).strip().title()
                    applicant['person']['last_name'] = isp
                    applicant_string = applicant_string.replace(item, '')
                    splitted = applicant['person']['full_name'].replace('.', ' ').split()
                    if isp in splitted:
                        splitted.remove(isp)
                    first_name = splitted[:1]
                    middle_name = splitted[1:]
                    applicant['person']['first_name'] = splitted[:1][0] if splitted[:1] else 'NULL'
                    applicant['person']['middle_name'] = splitted[1:][0] if splitted[1:] else 'NULL'

        applicant_string_splitted = re.sub('[\'(){}]', '', applicant_string).strip().split(', ')
        applicant_string = ', '.join([s for s in applicant_string_splitted if s])
        # print(applicant_string)
        applicant['company']['address'] = applicant_string
        applicant['person']['address'] = applicant_string
        if applicant['person'].get('country') is None and applicant['company'].get('sign_char', 'RU') == 'RU':
            applicant['person']['country'] = 'Россия'

        # Попытка разобрать иностранный адрес
        if applicant['person'].get('city') is None and applicant['company'].get('sign_char', 'RU') != 'RU':
            splitted = applicant['person']['address'].split(', ')
            if applicant['person'].get('country') is None:
                applicant['person']['country'] = splitted[-1]

            if len(splitted) > 2:
                if re.match(r'.*(\d{3,}).*', splitted[-2]):
                    applicant['person']['city'] = splitted[-3]
                else:
                    applicant['person']['city'] = splitted[-2]

    return applicant


def parse_patent_atty(document_parse):
    patent_atty = None
    patent_atty_string = document_parse.get('patent_atty')
    if patent_atty_string:
        patent_atty = {'person': {}}

        parse_zip_code(patent_atty_string, patent_atty['person'])
        splitted = patent_atty_string[1:-1].split(',')
        # Парсинг имени
        if len(splitted) >= 1:
            patent_atty['person']['full_name'] = splitted[0]
            names = splitted[0].split()
            if len(names) >= 1:
                patent_atty['person']['last_name'] = names[0]
            if len(names) >= 2:
                patent_atty['person']['first_name'] = names[1]
            if len(names) >= 3:
                patent_atty['person']['middle_name'] = names[2]
        # Парсинг номера
        if len(splitted) >= 2:
            patent_atty['person']['rep_reg_number'] = splitted[1].strip()

        # Парсинг адреса
        if len(splitted) >= 3:
            patent_atty['person']['rep_correspondence_address'] = ','.join(splitted[2:]).strip()
            # Парсим адрес из элементов
            for item in splitted[2:]:
                parse_person_address(patent_atty_string, item, patent_atty['person'])

    return patent_atty


def parse_correspondence_address(document_parse):
    pass


def get_company_from_db(self, document, document_person):
    company = document_person.get('company')
    name = company.get('name', '')
    if name:
        # Поиск компании по имени в БД
        with self.get_workers().lock:
            company_ = DB().fetchone(f"SELECT id FROM interface_company WHERE name = '{name}'")
        print(company_)  # TODO: deleteme

        # Если компании нет, то создаем новую запись
        if company_ is None:
            # Предварительно подготовить поля для внесения в БД
            company['name'] = f"'{company['name']}'" if company.get('name') else 'NULL'
            company['form'] = f"'{company['form']}'" if company.get('form') else 'NULL'
            company['address'] = f"'{company['address']}'" if company.get('address') else 'NULL'
            company['sign_char'] = f"'{company['sign_char']}'" if company.get('sign_char') else 'NULL'
            with self.get_workers().lock:
                company['id'] = DB().add_row(f"interface_company", company)

            # Дополнительная таблица связей между компанией и документами
            if self.name == 'orders':
                rel_table = 'interface_ordercompanyrel'
                rel_obj = {'company_id': f"'{company['id']}'", 'order_id': f"'{document['id']}'"}
            else:
                rel_table = 'interface_registercompanyrel'
                rel_obj = {'company_id': f"'{company['id']}'", 'register_id': f"'{document['id']}'"}
            # TODO: Этот запрос можно отправить общей кучей.
            with self.get_workers().lock:
                DB().add_row(rel_table, rel_obj)
        # Если компания нашлась, то просто передаем ID
        else:
            company['id'] = company_['id']
        return company
    return None


def parse_contacts_from_documentparse(self, document, document_parse):
    # Парсинг заявителя
    applicant = parse_applicant(document_parse, 'applicant')
    print('applicant', applicant)

    # Парсинг Правообладателя
    copyright_holder = parse_applicant(document_parse, 'copyright_holder')
    print('copyright_holder', copyright_holder)

    # Парсинг патентного поверенного
    patent_atty = parse_patent_atty(document_parse)
    print('patent_atty', patent_atty)

    # Парсинг адреса для переписки
    # correspondence_address = parse_correspondence_address(document_parse)
    correspondence_address = parse_applicant(document_parse, 'address')
    print('correspondence_address', correspondence_address)

    # Ищем компанию в БД
    document_person = applicant or copyright_holder or {}
    company = get_company_from_db(self, document, document_person)

    # Если компания не спарсилась, запись все равно нужно создать в виде Company for document document_parse['number']
    pass


if __name__ == '__main__':
    surnames = get_surnames()
    names = get_names()
    countries = get_countries()
    cities = get_cities()
    forms = get_forms()
    document_parse = {'copyright_holder': "'Унус Сед Лео Лимитед, с/о ШРМ Трастис (БВИ) Лимитед, Тринити Чемберс, П.О. Бокс 4301 Род Таун, Тортола, Британские Виргинские острова VG1110 (VG)'"}
    copyright_holder = parse_applicant(document_parse, 'copyright_holder')
    print('copyright_holder', copyright_holder)
    # print('get_surnames()\n', get_surnames())
    # print('get_names()\n', get_names())
    # print('get_cities()\n', get_cities())
    # print('get_regions()\n', get_regions())
    # p = Parser(REGISTERS_URL, 'registers')
    # p = Parser(URL1, 'orders')
    # p.get_orders()
    # p.check_new_orders()
    # p.start_parse_one_order()
    # p.start_parse_all_orders()
    #
    # # p.orders_urls = load_data_from_file(p.name + '.json')
    # # for url_obj in p.orders_urls:
    # #     print(url_obj)
    # #     urls = url_obj['a_href_steps']
    # #     p.workers.add_task(p.get_page_and_orders_dict, (urls, ))
    #
    # p.workers._queue.join()
    # print(p.orders_urls)
