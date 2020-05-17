import itertools
import os.path
import re
import traceback
from datetime import datetime, timedelta, date, timezone

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

# Поля для get_or_create_person
person_fields = ['full_name', 'first_name', 'middle_name', 'last_name', 'office_address', 'rep_correspondence_address',
                 'city', 'zip', 'area', 'state', 'country', ]


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
    # Параетры, определяющие частоту парсинга документов
    requests_amount = 1
    requests_period = 3
    parser_source = 'new.fips.ru'
    # Для фильтрации парсинга документов
    document_parse_query = None  # Для кастомизации запроса документа из БД
    # number_gte = None
    # number_lte = None
    documents_parsed = 990  # Количество документов на один прокси

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
        timer = 0
        try:
            while True:
                # if self.get_workers(number)._queue.qsize() > 0:
                if len(self.get_workers(number).tasks) >= number:
                    sleep(0.1)
                    continue

                if not self.proxies:
                    # self._lprint('Поиск прокси в БД')
                    # now = datetime.now(tz=timezone.utc)
                    # today = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
                    today = date.today()
                    # two_days_ago = today - timedelta(days=2)
                    query = f"SELECT * FROM interface_proxies " \
                            f"WHERE is_banned = FALSE AND is_working = TRUE AND in_use = FALSE " \
                            f"AND (documents_parsed < {self.documents_parsed} AND date_last_used = '{today}' " \
                            f"OR date_last_used < '{today}') AND datetime_delayed < NOW()" \
                            f"LIMIT 1"
                    with self.get_workers().lock:
                        db = DB()
                        try:
                            db.c.execute(query)
                            proxy = db.c.fetchone()
                            if proxy:
                                q = f"UPDATE interface_proxies " \
                                    f"SET in_use = TRUE, date_last_used = CURDATE(), status = NULL " \
                                    f"WHERE id = '{proxy['id']}'"
                                db.c.execute(q)
                                db.conn.commit()
                        finally:
                            db.c.close()
                            db.conn.close()
                    if proxy is None:
                        # self._lprint('Нет доступных прокси. Ждем окончания потоков или закрытия программы')
                        if monotonic() - timer > 3600:
                            self._lprint('Нет доступных прокси. Ждем')
                            timer = monotonic()
                        sleep(60)
                        continue
                        # break
                        # in_use = [f"'{p['id']}'" for p in proxies]

                    proxy = dict(proxy)
                    proxy['in_use'] = 1
                    proxy['status'] = ''
                    proxy['datetime_delayed'] = None  # Если будет ошибка, сюда подставится дата
                    # print(today, proxy['date_last_used'])
                    # print(two_days_ago, proxy['date_last_used'])
                    if proxy['date_last_used'] < today:
                        proxy['documents_parsed'] = 0
                    proxy['date_last_used'] = 'CURDATE()'

                    in_use = [f"'{proxy['id']}'"]
                    # proxies_in_use.extend(in_use)
                    # with self.get_workers().lock:
                    #     use_proxies(in_use)
                    proxies_in_use.append(in_use)
                self._print('Запуск парсинга с прокси', proxy['host'], proxy['port'])
                self.get_workers().add_task(self.start_parse_all_documents, (proxy,), proxy['host'])
                sleep(1)

            self.get_workers()._queue.join()
            self._lprint('Парсинг окончен')
        finally:
            if proxies_in_use:
                with self.get_workers().lock:
                    release_proxies(proxies_in_use)

    def get_rand_times(self):
        d = self.requests_period / self.requests_amount
        if d < 3:
            d = 3
        s = [d] * self.requests_amount
        for i in range(0, int(len(s) / 2)):
            r = randint(0, int(s[i]) - 3)
            s[i] = s[i] - r
            s[len(s) - 1 - i] = s[len(s) - 1 - i] + r
        shuffle(s)
        return s

    # Начинает новый парсинг информации со страницы с документом из списка документов
    def start_parse_all_documents(self, proxy=None):
        # documents_parsed = proxy['documents_parsed'] if proxy else 0
        timer = 0
        rand_times = self.get_rand_times()
        rand_times = iter(rand_times)
        while self.start_parse_document(proxy):
            if proxy:
                # proxy['documents_parsed'] += 1
                if proxy['errors_in_a_row']:
                    proxy['errors_in_a_row'] = 0
                # Сохранение данных о прокси раз в минуту
                if monotonic() - timer > 60:
                    proxy_to_db = {'id': f"'{proxy['id']}'", 'date_last_used': proxy['date_last_used'],
                                   'documents_parsed': f"'{proxy['documents_parsed']}'",
                                   'in_use': proxy['in_use'], 'is_working': proxy['is_working'],
                                   'is_banned': proxy['is_banned'],
                                   'errors_in_a_row': f"'{proxy['errors_in_a_row']}'",  #
                                   'status': f"'{proxy['status']}'" if proxy['status'] else 'NULL'}
                    DB().update_row('interface_proxies', proxy_to_db)
                    timer = monotonic()

                # При достижении дневного лимита использования прокси цикл прерывается
                if proxy['documents_parsed'] >= self.documents_parsed:
                    proxy['errors_in_a_row'] = 0  # Счетчик ошибок подряд обнуляется
                    break

            try:
                t = next(rand_times)
            except StopIteration:
                rand_times = iter(self.get_rand_times())
                t = next(rand_times)

            timer2 = monotonic()
            while monotonic() - timer2 < t + 1:
                sleep(1)

        # В некотрых случая не нужно освобождать прокси
        if proxy.get('need_to_release_proxy', True):
            proxy['in_use'] = 0

        proxy_to_db = {'id': f"'{proxy['id']}'", 'date_last_used': proxy['date_last_used'],
                       'documents_parsed': f"'{proxy['documents_parsed']}'",
                       'in_use': proxy['in_use'], 'is_working': proxy['is_working'],
                       'is_banned': proxy['is_banned'],
                       'errors_in_a_row': f"'{proxy['errors_in_a_row']}'",  #
                       'status': f"'{proxy['status']}'" if proxy['status'] else 'NULL'}

        # Если воникла ошибка и была установлена дата задержки использования прокси
        # Изначально proxy['datetime_delayed'] = None
        if proxy['datetime_delayed']:
            proxy_to_db['datetime_delayed'] = proxy['datetime_delayed']

        DB().update_row('interface_proxies', proxy_to_db)

    # Берет из базы и парсит один непарсенный документ
    def start_parse_document(self, proxy=None):
        query = self.document_parse_query
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

        # Если is_error == TRUE или message не пустой, то результат парсинга логируется в БД
        history = {'message': '', 'is_error': 'FALSE',
                   'document_id': f"'{document_obj['id']}'",
                   'date_created': 'NOW()', }

        # Если возникают какие-то неучтенные ошибки, то ошибка логируется, в БД создается запись о
        # результате парсинга с ошибкой, записывается путь до файла с логами ошибки
        # Далее документ считается спарсенным и парсер переходит к следующему документу
        try:
            result = self.parse_one_document(dict(document_obj), history, proxy)
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
            self._print('Ошибка для', document_obj['number'], ' залогирована', error_filename)
            history['error_log_file'] = f"'{error_link}'"
            history['is_error'] = 'TRUE'
            # Запись результата парсинга в БД и отметка документа спарсенным
            with self.get_workers().lock:
                DB().executeone(f"UPDATE {self.dbdocument} SET document_parsed = TRUE, date_parsed = NOW() "
                                f"WHERE id = '{document_obj['id']}'")
        finally:
            self.documents_in_parsing.remove(f"'{document_obj['id']}'")
            if history['is_error'] == 'TRUE' or history['message']:
                history['message'] = history['message'].replace("'", '"')
                history['message'] = f"'{history['message']}'" if history['message'] else 'NULL'
                self._print('Лог парсинга для', document_obj['number'], ' сохранен в БД\n')
                self._print(history)
                with self.get_workers().lock:
                    DB().add_row(self.dbparserhistory, history)

        return result

    # Парсит одну страницу документа
    def parse_one_document(self, document_obj, history, proxy=None):
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

        # Замена домена, если надо
        if self.parser_source == 'fips.ru':
            document_obj['url'] = document_obj['url'].replace('new.fips.ru', 'fips.ru')
        elif 'new.fips.ru' not in document_obj['url']:
            document_obj['url'] = document_obj['url'].replace('fips.ru', 'new.fips.ru')

        self._print(document_obj['number'], 'Парсинг документа', document_obj['url'],
                    proxies, proxy['documents_parsed'] if proxy else None)

        filepath = os.path.join('.', 'media', self.name, str(document_obj['number']))
        filename = os.path.join(filepath, 'page.html')
        url = document_obj['url']
        existence = True
        with requests.Session() as session:
            session.headers.update({'User-Agent': get_random_useragent()})

            # # Либо парсим локальный файл # TODO: Для отладки
            if os.path.exists(filename):
                self._print(document_obj['number'], 'Парсим локальный файл')
                with open(filename, 'rb') as f:
                    page_content = f.read()
            # Либо загружаем страницу и проверяем на ошибки
            else:
                counter = 0
                while True:
                    try:
                        r = session.get(url, proxies=proxies, timeout=30)
                        # Если парсинг был удачным, то прибавляем единицу в статистику прокси
                        if proxy:
                            proxy['documents_parsed'] += 1
                    except requests.exceptions.ReadTimeout:
                        self._print(document_obj['number'], 'Нет ответа от сервера!')
                        sleep(5)
                        return True
                    except (requests.exceptions.ProxyError, requests.exceptions.ConnectTimeout) as err:
                        self._print(document_obj['number'], 'Ошибка прокси', str(err), type(err))
                        err = str(err).replace("'", '"')
                        # with self.get_workers().lock:
                        # Если возникает ошибка, увеличиваем счетчик ошибок на 1
                        history['message'] += f'Ошибка прокси {proxy["id"]}\n'
                        proxy['status'] = 'Ошибка прокси ' + err[:200]
                        proxy['errors_in_a_row'] += 1
                        proxy['datetime_delayed'] = f"ADDDATE(NOW(), INTERVAL {proxy['errors_in_a_row']} HOUR)"
                        # proxy['documents_parsed'] += 1000000
                        # Если ошибок 5, то отмечаем прокси как нерабочий
                        if proxy['errors_in_a_row'] >= 5:
                            proxy['is_working'] = 'FALSE'
                        return False
                    if r.status_code == 502:
                        self._lprint(document_obj['number'], 'ошибка сервера', r.status_code, r.reason, url)
                        sleep(5)
                        return True
                    elif r.status_code != 200:
                        self._lprint(document_obj['number'], 'parse_orders', r.status_code, r.reason, url)
                        return False
                        # existence = True
                        # break
                    text = r.text
                    page_content = r.content

                    if 'Слишком быстрый просмотр документов' in text:
                        self._print(document_obj['number'], text, url)
                        proxy['in_use'] = 1
                        # Прокси не нужно освобождать
                        proxy['need_to_release_proxy'] = False
                        return False
                    elif 'Превышен допустимый предел' in text:
                        self._print(document_obj['number'], text, url)
                        history['message'] += f'Превышен предел прокси {proxy["id"]}\n'
                        proxy['status'] = text
                        proxy['documents_parsed'] += 1000000
                        return False

                    elif 'Вы заблокированы' in text:
                        self._print(text, 'Поток закрыт')
                        history['message'] += f'Блокировка прокси {proxy["id"]}\n'
                        proxy['status'] = text
                        # proxy['is_banned'] = 'TRUE'
                        # Следующее использование прокси через 31 день
                        proxy['datetime_delayed'] = f"ADDDATE(NOW(), 31)"
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
                        history['message'] += f'counter exceeded\n'
                        self._lprint(document_obj['number'], 'counter exceeded', url)
                        return False
                    self._print(document_obj['number'], 'sleep')
                    sleep(3)

            if existence:
                with self.get_workers().lock:
                    DB().executeone(
                        f"UPDATE {self.dbdocument} SET downloaded_page = '{filename}' WHERE id = '{document_obj['id']}'"
                    )
                self.parse_document_page(page_content, document_obj, session, proxies, history)
            else:
                with self.get_workers().lock:
                    DB().executeone(f"UPDATE {self.dbdocument} SET document_parsed = TRUE, "
                                    # f"date_parsed = '{date.today()}', document_exists = FALSE "
                                    f"date_parsed = NOW(), document_exists = FALSE "
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
        if date_splitted[1] == 2 and date_splitted[0] >= 29:
            date_splitted[0] = 28
        try:
            date_ = date(date_splitted[2], date_splitted[1], date_splitted[0])
        except ValueError as err:
            # Некоторые даты в документах введены неверно. Например, 30.02.2019 или 31.04.2010 или 31.13.2001
            err_str = str(err)
            if 'month must be in' in err_str:
                if date_splitted[1] > 12:
                    date_splitted[1] = 12
                elif date_splitted[1] < 1:
                    date_splitted[1] = 1
            elif 'day is out of range for month' in err_str:
                # Чтобы не проверять каждый год по отдельности, запостулируем, что в феврале всегда 28 дней.
                if date_splitted[1] == 2 and date_splitted[0] > 28:
                    date_splitted[0] = 28
                elif date_splitted[0] > 30:
                    date_splitted[0] = 30
                elif date_splitted[0] < 1:
                    date_splitted[0] = 1
            else:
                raise err
            date_ = date(date_splitted[2], date_splitted[1], date_splitted[0])
        return date_
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
        try:
            r = session.get(direct_url, proxies=proxies)
        except:
            return None
        if r.status_code != 200:
            # print('Файл не был загружен')
            return None
        # filename = os.path.join('.'', 'media', 'files', )
        with open(filepath, 'wb') as f:
            f.write(r.content)
    return direct_url, link


# Номера, встречаемые в документах, и соответствующие им столбцы в БД (строчки)
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

# Номера, встречаемые в документах, и соответствующие им столбцы в БД (даты)
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
def parse_main_info(page, document, document_info, document_parse, service_items, session, proxies, self_name,
                    start_izvs=None):
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
            value = re.sub('[\'{}]', '', value)
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
            if len(child_text.replace(',', '').strip()) > 10:
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


# Ставит значение in_use в положение True для прокси с указанными ID в списке
def use_proxies(ids_list):
    ids = ', '.join(ids_list)
    DB().executeone(f'UPDATE interface_proxies SET in_use = TRUE WHERE id IN ({ids})')


# Ставит значение in_use в положение False для прокси с указанными ID в списке
def release_proxies(ids_list=None):
    if ids_list:
        ids = ', '.join(ids_list)
        DB().executeone(f'UPDATE interface_proxies SET in_use = FALSE WHERE id IN ({ids})')
        print("Прокси", ids_list, "освобождены")
    else:
        DB().executeone(f'UPDATE interface_proxies SET in_use = FALSE')
        print("Все прокси освобождены")


# Загружает список прокси из файла в БД. Не нужная функция, так как в интерфейсе реализован более удобный метод
def load_proxies_to_db_from_file(filename=None):
    filename = filename or 'proxy_http_ip.txt'
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            proxies = f.readlines()
        values = []
        for proxy in proxies:
            # match = re.match(r'(.*)(?P<value>(?P<day>\d{2})\.(?P<month>\d{2})\.(?P<year>\d{4}))(.*)', proxy)
            match = re.match(r'(?P<scheme>https?://)(?P<user>.*[^:]):(?P<pass>.*[^@])@'
                             r'(?P<host>\d+\.\d+\.\d+\.\d+):(?P<port>\d+)', proxy)
            match = match or re.match(r'(?P<scheme>https*://)(?P<host>\d+\.\d+\.\d+\.\d+):(?P<port>\d+)', proxy)
            g = match.groupdict()
            scheme = f"'{g['scheme']}'" if g.get('scheme') else 'NULL'
            user = f"'{g['user']}'" if g.get('user') else 'NULL'
            password = f"'{g['pass']}'" if g.get('pass') else 'NULL'
            host = f"'{g['host']}'" if g.get('host') else 'NULL'
            port = f"'{g['port']}'" if g.get('port') else 'NULL'
            values.append(f"({scheme}, {user}, {password}, {host}, {port}, FALSE, TRUE, FALSE)")
            print(match.groupdict())
        if values:
            q = "INSERT INTO interface_proxies (scheme, user, password, host, port, is_banned, is_working, in_use) " \
                "VALUES "
            q += ', '.join(values)
            print(q)
            DB().executeone(q)
        else:
            print('Не получены значения')
    else:
        print('Файл не найден')


# Разбирает адрес на составляющие
def parse_person_address(applicant_string, item, person):
    item_splitted = re.sub(r'(ГОРОД|город|г\.)', '', item, re.IGNORECASE).strip()
    item_splitted = item_splitted.split()
    applicant_string_lower = applicant_string.lower()
    # Ищем каждое слово среди списка городов

    # Ищем город
    if person.get('city') is None:
        if re.match(r'(^город\s|\sгород$|.*г\..*)', item, re.IGNORECASE):
            person['city'] = re.sub(r'(город |г\.)', '', item, flags=re.IGNORECASE).strip()

    # Ищем край или область
    if person.get('state') is None:
        if re.match(r'.*(край|область|обл|республика).*', item, re.IGNORECASE):
            person['state'] = item.strip()

    # Ищем район
    if person.get('area') is None:
        if re.match(r'.*(район).*', item, re.IGNORECASE):
            person['area'] = item.strip()

    for c in item_splitted:
        # print('city', c)
        c = c.capitalize()

        # Исключаем слова, которых не должно быть в Городе
        if re.match(r'.*(республика|поселок|площадь|проспект|пркт|пр-кт|улица|ул\.|край|область|обл\.|\d).*', item,
                    re.IGNORECASE) or person.get('city'):
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
        # Ищем каждое слово среди списка стран
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
    applicant = {}
    # Получаем наименование компании из поля document_parse['applicant'] или document_parse['copyright_holder']
    # Нужно искать компанию, либо Имя-Фамилию контакта
    applicant_string = document_parse.get(type, '')[1:-1]

    if applicant_string:
        is_sng = False  # Документ принадлежит странам СНГ
        applicant = {'company': {}, 'person': {}}
        applicant_string_splitted = applicant_string.split(', ')

        # Находим код страны
        sign_char = re.match(r'.*(?P<sign>[A-Z]{2}).*', applicant_string_splitted[0]) or \
                    re.match(r'.*(?P<sign>[A-Z]{2}).*', applicant_string_splitted[-1])
        if sign_char:
            sign_char = sign_char.groupdict().get('sign') or 'NULL'
            applicant['company']['sign_char'] = sign_char
            applicant_string = applicant_string.replace(sign_char, '')
            # print('Код страны', sign_char)
            if sign_char.lower() in 'AZ,АM,BY,GE,KG,KZ,MD,RU,TJ,TM,UA,UZ'.lower():
                is_sng = True
        else:
            is_sng = True

        parse_zip_code(applicant_string, applicant['person'])

        company_part = ''
        if is_sng:
            # spltd = re.split(r', \d{6}', applicant_string)
            mtchd = re.match(r'(.*), \d{6}', applicant_string)
            if mtchd and mtchd.group(1):
                # company_part = spltd[0]
                company_part = applicant_string[:mtchd.end(1)]
                # applicant_string = spltd[1]
                applicant_string = applicant_string[mtchd.end(1):]
                applicant_string_splitted = applicant_string.split(', ')
            # applicant['company']['address'] = spltd[1]
        elif sign_char:
            if sign_char not in applicant_string_splitted[0]:
                company_part = applicant_string_splitted[0]
                applicant_string_splitted[0] = ''
                # address_part = spltd[1]
            elif len(applicant_string_splitted) > 1:
                company_part = applicant_string_splitted[1]
                applicant_string_splitted[0] = ''
                applicant_string_splitted[1] = ''
        else:
            company_part = ''

        # print('applicant_string', applicant_string)
        if company_part:
            # print('company_part', company_part)
            company_part_splitted = re.sub('[\'{}]', '', company_part).strip().split(', ')
            company_part = ', '.join([s for s in company_part_splitted if s])
            applicant['company']['full_name'] = company_part
            applicant['company']['name'] = company_part
            applicant['company']['form'] = ''
            # print('company_part', company_part)
            # print('applicant_string', applicant_string)
            # applicant_string.replace(company_part, '')
            # print('applicant_string', applicant_string)

            for form in forms:
                if form in company_part:
                    applicant['company']['form'] = forms[form]
                    if is_sng:
                        company_name = re.sub(r'(^|\s)' + form + r'($|\s)', '', company_part).strip()
                        company_name = re.sub(', ', '', company_name).strip()
                        applicant['company']['name'] = company_name
                    else:
                        applicant['company']['name'] = company_part.strip()
                    applicant['company']['name'] = re.sub(r'(["«»\'{}])', '', applicant['company']['name'])

                    if forms[form] == 'ИП':
                        applicant_string_splitted = applicant_string_splitted + [applicant['company']['name']]
                    break
            else:
                if is_sng:
                    # applicant['person']['full_name'] = applicant['company']['full_name']
                    # applicant['company']['form'] = 'ИП'
                    applicant_string_splitted = applicant_string_splitted + [applicant['company']['name']]
                if applicant['company'].get('name') is None and applicant['company'].get('full_name') is not None:
                    applicant['company']['form'] = ''
                    applicant['company']['name'] = applicant['company']['full_name']
            #         print('company_part', form, company_part)

        for i, item in enumerate(applicant_string_splitted):
            if not item:
                continue
            # print('item', item)

            # Ищем известную организационную форму
            # Если найдена форма - это название компании
            # Это повторный поиск, если не было произведено разбиение (чаще для адреса переписки)
            if applicant['company'].get('name') is None:
                for form in forms:
                    if form in item:
                        mtchd = re.match(r'(.*)' + form + r'(.[^()]*)', item)
                        # mtchd = re.match(r'(.*)' + form + r'(.[^()]*)', item)
                        if mtchd is None:
                            continue
                        applicant['company']['full_name'] = item[mtchd.end(1):mtchd.end(2)].strip()
                        applicant['company']['form'] = forms[form]
                        # applicant['company']['name'] = re.sub(r'(^|\s)' + form + r'($|\s)', '', item).strip()
                        applicant['company']['name'] = mtchd.group(2).strip()
                        # applicant_string = applicant_string.replace(item, '')
                        # Для определения имени некоторых иностранных компаний
                        if not applicant['company']['name']:
                            index = i - 1
                            if i > 0:
                                index = i - 1
                            elif len(applicant_string_splitted) > 1:
                                index = 1
                            else:
                                index = 0
                            applicant['company']['name'] = applicant_string_splitted[index].strip()
                            # applicant_string = applicant_string.replace(applicant_string_splitted[1], '')
                        item = ''
                        applicant['company']['name'] = re.sub(r'(["«»\'{}])', '', applicant['company']['name'])
                        break

            # Парсим адрес из элементов
            parse_person_address(applicant_string, item, applicant['person'])

            # Дальше поиск ФИО
            if not is_sng:
                continue

            if (applicant['person'].get('first_name') and applicant['person'].get('last_name') and
                    applicant['person'].get('middle_name')):
                continue

            if applicant['person'].get('full_name'):
                item_splitted = applicant['person']['full_name'].split()
            else:
                item = re.sub('для ', '', item, re.I)
                item_splitted = item.split()

            if len(item_splitted) <= 1 or len(item_splitted) >= 4:
                continue

            # if re.match(r'.*(ул\.|г\.|обл\.|д\.|кв\.|\d).*', item):
            if re.match(
                    r'.*(\.|район|край|федерация|республика|корпус|пр.|пркт|пр-кт|пр-д|проспект|улица'
                    r'|ул\.|город|г\.|область|обл\.|\d|[a-z]|").*',
                    item.lower()):
                # print('пропущено', item)
                continue

            sur_found = first_found = second_found = middle_found = False
            # Парсинг ФИО
            for isp in item_splitted:
                if not sur_found and not first_found:
                    isp = isp.capitalize()
                    # if isp in cities or isp in countries:
                    #     continue
                    if isp in surnames:
                        # applicant_string = applicant_string.replace(item, '')
                        sur_found = True
                    elif isp[-1] == 'у' and isp[:-1] in surnames:
                        # applicant_string = applicant_string.replace(item, '')
                        item = re.sub(isp, isp[:-1], item)
                        isp = isp[:-1]
                        sur_found = True
                    elif isp[-2:] == 'ой' and isp[:-2] in surnames:
                        # applicant_string = applicant_string.replace(item, '')
                        item = re.sub(isp, isp[:-2] + 'а', item)
                        isp = isp[:-2] + 'а'
                        sur_found = True
                    elif isp in names:
                        first_found = True
                    else:
                        continue
                    full_name = re.sub('(ИП|Индивидуальный предприниматель)', '', item).strip().title()
                    if sur_found:
                        last_name = isp
                        splitted = full_name.replace('.', ' ').split()
                        if isp in splitted:
                            splitted.remove(isp)
                        first_name = splitted[:1][0] if splitted[:1] else None
                        middle_name = splitted[1:][0] if splitted[1:] else None
                    elif first_found:
                        first_name = isp
                        splitted = full_name.replace('.', ' ').split()
                        if isp in splitted:
                            splitted.remove(isp)
                        last_name = splitted[:1][0] if splitted[:1] else None
                        middle_name = splitted[1:][0] if splitted[1:] else None
                    else:
                        first_name = middle_name = last_name = ''
                    if first_name and len(first_name) == 1 or middle_name and len(middle_name) == 1:
                        continue
                    applicant['person']['full_name'] = full_name
                    applicant['person']['last_name'] = last_name
                    applicant['person']['first_name'] = first_name
                    applicant['person']['middle_name'] = middle_name
                    if not applicant['company'].get('form', ''):
                        applicant['company']['form'] = 'ИП'

        applicant_string_splitted = re.sub('[\'(){}]', '', applicant_string).strip().split(', ')
        applicant_string = ', '.join([s for s in applicant_string_splitted if s])
        # print(applicant_string)
        if applicant['company'].get('address') is None:
            applicant['company']['address'] = applicant_string
        applicant['person']['office_address'] = applicant_string
        if applicant['person'].get('country') is None and applicant['company'].get('sign_char', 'RU') == 'RU':
            applicant['person']['country'] = 'Россия'

        # Попытка разобрать иностранный адрес
        if applicant['person'].get('city') is None and applicant['company'].get('sign_char', 'RU') != 'RU':
            splitted = applicant['person']['office_address'].split(', ')
            if applicant['person'].get('country') is None:
                applicant['person']['country'] = splitted[-1]

            if len(splitted) > 2:
                if re.match(r'.*(\d{3,}).*', splitted[-2]):
                    applicant['person']['city'] = splitted[-3]
                else:
                    applicant['person']['city'] = splitted[-2]

    return applicant


def parse_patent_atty(document_parse):
    patent_atty = {}
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
            # patent_atty['person']['rep_correspondence_address'] = ','.join(splitted[2:]).strip()
            patent_atty['person']['office_address'] = ','.join(splitted[2:]).strip()
            # Парсим адрес из элементов
            for item in splitted[2:]:
                parse_person_address(patent_atty_string, item, patent_atty['person'])

    return patent_atty


def get_or_create_company(self, document, document_person, save_anyway=True, make_holder=False):
    company = document_person.get('company', {})
    name = company.get('name')
    # Если имя не найдено, то нужно проверить ФИО и сохранить как ИП
    if name is None and save_anyway:
        full_name = document_person.get('person', {}).get('full_name', '')
        if full_name:
            name = full_name
            company['form'] = 'ИП'
        else:
            name = f"Company for {self.name} {document['number']}"
        # name = full_name if full_name else f"Company for {self.name} {document['number']}"
    elif name is None and not save_anyway:
        return {}
    form = company.get('form', '')
    sign_char = company.get('sign_char')

    # Поиск компании по имени в БД
    q = f"SELECT id FROM interface_company WHERE name = '{name}'"
    if form:
        q += f" AND form = '{form}'"
    if sign_char:
        q += f" AND sign_char = '{sign_char}'"
    q += ' LIMIT 1'
    with self.get_workers().lock:
        company_ = DB().fetchone(q)

        # Попытка найти компанию по адресу
        if company_ is None:
            address = company.get('address')
            q = f"SELECT id FROM interface_company WHERE address = '{address}'"
            if form:
                q += f" AND form = '{form}'"
            if sign_char:
                q += f" AND sign_char = '{sign_char}'"
            q += ' LIMIT 1'
        # with self.get_workers().lock:
            company_ = DB().fetchone(q)

        # Если компании нет, то создаем новую запись
        if company_ is None:
            # Предварительно подготовить поля для внесения в БД
            company['full_name'] = f"'{company['full_name']}'" if company.get('full_name') else 'NULL'
            company['name'] = f"'{name}'"
            company['name_correct'] = company['name']
            company['form'] = f"'{company['form']}'" if company.get('form') else 'NULL'
            company['form_correct'] = company['form']
            company['address'] = f"'{company['address']}'" if company.get('address') else 'NULL'
            company['sign_char'] = f"'{company['sign_char']}'" if company.get('sign_char') else 'NULL'
            company['date_corrected'] = 'NULL'
            # with self.get_workers().lock:
            company['id'] = DB().add_row(f"interface_company", company)
        # Если компания нашлась, то просто передаем ID
        else:
            company['id'] = company_['id']

    # Проверяем дополнительную таблицу связей между компанией и документами
    rel_obj = {'company_id': f"'{company['id']}'", 'document_id': f"'{document['id']}'",
               'company_is_holder': 'FALSE'}
    rel_table = 'interface_ordercompanyrel' if self.name == 'orders' else 'interface_registercompanyrel'

    with self.get_workers().lock:
        rel_ = DB().fetchone(f"SELECT id FROM {rel_table} "
                             f"WHERE company_id = '{company['id']}' AND document_id = '{document['id']}'")
        if rel_ is None:
        # with self.get_workers().lock:
            # Если надо переопределить правообладателя
            if make_holder:
                DB().executeone(f"UPDATE {rel_table} SET company_is_holder = FALSE "
                                f"WHERE document_id = '{document['id']}'")
                rel_obj['company_is_holder'] = 'TRUE'
            rel_obj['id'] = DB().add_row(rel_table, rel_obj)
        else:
            rel_obj['id'] = rel_['id']

    return company
    # return None


def get_or_create_person(self, document, document_person, company=None):
    company = company or {}
    person = document_person.get('person', {})
    full_name = person.get('full_name', '')
    if full_name:
        # Поиск контакта для данной компании по имени в БД
        if person.get('rep_reg_number'):  # rep_reg_number - уникальный номер патентного поверенного
            q = f"SELECT id FROM interface_contactperson WHERE rep_reg_number = '{person['rep_reg_number']}'"
        elif company and company.get('id'):
            q = f"SELECT id FROM interface_contactperson " \
                f"WHERE full_name = '{full_name}' AND company_id = '{company['id']}'"
        else:
            return None
        q += ' LIMIT 1'
        with self.get_workers().lock:
            person_ = DB().fetchone(q)

            # Если контакта нет, то создаем новую запись
            if person_ is None:
                # Предварительно подготовить поля для внесения в БД
                for f in person_fields:
                    if f in person:
                        person[f] = f"'{person[f]}'"
                person['gender'] = "'0'"
                if 'rep_reg_number' in person:
                    person['rep_reg_number'] = f"'{person['rep_reg_number']}'"
                    person['category'] = "'REPRESENTATIVE'"
                elif company and company.get('form') == 'ИП':
                    person['category'] = "'DIRECTOR'"
                else:
                    person['category'] = "'DEFAULT'"
                person['company_id'] = f"'{company['id']}'" if company and company.get('id') else 'NULL'
                person['email_verified'] = 'FALSE'
                person['email_correct'] = 'TRUE'
                person['date_corrected'] = 'NULL'

            # with self.get_workers().lock:
                person['id'] = DB().add_row(f"interface_contactperson", person)
            # Если контакт нашелся, то просто передаем ID
            else:
                person['id'] = person_['id']

        # Проверяем дополнительную таблицу связей между контактами и документами
        rel_obj = {'contactperson_id': f"'{person['id']}'", 'document_id': f"'{document['id']}'"}
        rel_table = 'interface_contactperson_order' if self.name == 'orders' else 'interface_contactperson_register'

        with self.get_workers().lock:
            rel_ = DB().fetchone(f"SELECT id FROM {rel_table} "
                                 f"WHERE contactperson_id = '{person['id']}' AND document_id = '{document['id']}'")
            if rel_ is None:
                # with self.get_workers().lock:
                rel_obj['id'] = DB().add_row(rel_table, rel_obj)
            else:
                rel_obj['id'] = rel_['id']

        return person
    return None


# Парсинг компаний и представителей в полученных данных документа
def parse_contacts_from_documentparse(self, document, document_parse, history):
    # Парсинг заявителя
    applicant = parse_applicant(document_parse, 'applicant')

    # Парсинг Правообладателя
    copyright_holder = parse_applicant(document_parse, 'copyright_holder')

    document_person = applicant or copyright_holder or None
    # Если нет заявителя или правообладателя, но не надо создавать компанию
    if document_person is None:
        return

    # Парсинг патентного поверенного
    patent_atty = parse_patent_atty(document_parse)
    if document_parse.get('address'):
        if patent_atty:
            patent_atty['person']['rep_correspondence_address'] = document_parse['address'][1:-1]
        else:
            document_person['person']['rep_correspondence_address'] = document_parse['address'][1:-1]

    # Парсинг адреса для переписки
    correspondence_address = parse_applicant(document_parse, 'address')

    # Ищем компанию-правообладателя в БД
    company = get_or_create_company(self, document, document_person, False, make_holder=True)
    person = get_or_create_person(self, document, document_person, company)

    # Ищем компанию в БД для патентного поверенного
    pat_company = get_or_create_company(self, document, correspondence_address, False)

    # Если патентная компания не определена, то
    # регистрируем патентного поверенного без компании
    # if pat_company:
    #     pat_person_company = pat_company
    # else:
    #     # history['message'] += 'Имя патентной компании не найдено\n'
    #     # pat_person_company = company
    #     pat_person_company = None
    pat_person_company = pat_company
    # Если есть патентный поверенный, то сохраняем его в БД
    if patent_atty:
        pat_person = get_or_create_person(self, document, patent_atty, pat_person_company)
    # Если патентного поверенного нет, то ищем иного исполнителя в адресе для коррекспонденции
    else:
        pat_person = get_or_create_person(self, document, correspondence_address, pat_person_company)
    # print('pat_person', pat_person)


if __name__ == '__main__':
    surnames = get_surnames()
    names = get_names()
    countries = get_countries()
    cities = get_cities()
    forms = get_forms()
    document_parse = {
        'copyright_holder': "'Унус Сед Лео Лимитед, с/о ШРМ Трастис (БВИ) Лимитед, Тринити Чемберс, П.О. Бокс 4301 Род Таун, Тортола, Британские Виргинские острова VG1110 (VG)'"}
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
