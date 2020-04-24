import itertools
import os.path
import re
from datetime import datetime, timedelta, date

import requests
import json
from time import sleep, monotonic
from random import choice
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
proxy = None


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

    def get_workers2(self, number=20):
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
            if cookies:
                session.cookies = cookies.copy()
            else:
                # Из-за особенностей сайта, приходится открывать ссылки таким хитрым образом,
                # чтобы сохранять куки в нужной последовательности
                if self.session_get(session, self.url, 'get_page 1').status_code != 200 or \
                        self.session_get(session, self.url, 'get_page 2').status_code != 200:
                    return

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
                if not r:
                    self._lprint('request is bad', urls)
                    return

            return session.cookies.copy(), BeautifulSoup(r.text, 'html.parser')

    # Получение содержимого страницы и парсинг этой страницы. Получение ссылок непосредственно на заявки
    def get_page_and_orders(self, order_leaf, cookies=None):
        if cookies is None:
            # Будет создана новая сессия, для прохода всех ссылок последовательно
            urls = order_leaf['a_href_steps']
        else:
            # Для старой сессии достаточно перейти по последней ссылке
            urls = [order_leaf['a_href_steps'][-1]]
        cookies, page = self.get_page(urls, cookies)
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

                if not number.isnumeric():
                    self._print(leaf_obj['name'], number, 'not numeric')
                    continue

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
        cookies, page = self.get_page(urls, cookies)
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
                self.get_workers().add_task(func, (next_urls, cookies))
            else:
                func(next_urls, cookies)
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
        cookies, page = self.get_page(urls, cookies)
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
                if self.get_workers(number)._queue.qsize() >= number:
                    sleep(1)
                    continue

                if not self.proxies:
                    self._lprint('Поиск прокси в БД')
                    with self.get_workers().lock:
                        proxies = DB().fetchall(f"SELECT * FROM interface_proxies "
                                                f"WHERE is_banned = FALSE AND is_working = TRUE AND in_use = FALSE "
                                                f"LIMIT {number}")
                    in_use = [f"'{p['id']}'" for p in proxies]
                    proxies_in_use.extend(in_use)
                    with self.get_workers().lock:
                        use_proxies(in_use)

                    if not proxies:
                        self._lprint('Нет доступных прокси. Ждем окончания потоков или закрытия программы')
                        break
                    self.proxies = [dict(proxy) for proxy in proxies]
                    proxies = iter(self.proxies)
                    stop_iteration = False

                if stop_iteration:
                    continue

                try:
                    proxy = next(proxies)
                except StopIteration:
                    stop_iteration = True
                    continue

                self._print('Запуск парсинга с прокси', proxy)
                self.get_workers().add_task(self.start_parse_all_documents, (proxy,))

            self.get_workers()._queue.join()
            self._lprint('Парсинг окончен')
        finally:
            if proxies_in_use:
                with self.get_workers().lock:
                    release_proxies(proxies_in_use)

    # Начинает новый парсинг информации со страницы с документом из списка документов
    def start_parse_all_documents(self, proxy=None):
        while self.start_parse_document(proxy):
            timer = monotonic()
            while monotonic() - timer < 3:
                sleep(0.1)
        self.proxies.remove(proxy)

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

        return self.parse_one_document(document_obj, proxy)

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

        try:
            document_obj = dict(document_obj)
            self._print(document_obj['number'], 'Парсинг документа', document_obj['url'])
            filepath = os.path.join('.', 'webapp', 'media', self.name, str(document_obj['number']))
            filename = os.path.join(filepath, 'page.html')
            url = document_obj['url']
            session = requests.Session()
            session.headers.update({'User-Agent': get_random_useragent()})
            text = ''
            page_content = None
            existence = True

            # Загружаем страницу и проверяем на ошибки
            if not os.path.exists(filename):
                counter = 0
                while True:
                    try:
                        r = session.get(url, proxies=proxies, timeout=10)
                    except (requests.exceptions.ProxyError, requests.exceptions.ConnectTimeout) as err:
                        self._print(document_obj['number'], 'Ошибка прокси', str(err), type(err))
                        with self.get_workers().lock:
                            DB().executeone(f"UPDATE interface_proxies SET is_working = FALSE, "
                                            f"status = '{'Ошибка прокси ' + str(err)}'"
                                            f"WHERE id = '{proxy['id']}'")
                        return False

                    if r.status_code != 200:
                        self._lprint(document_obj['number'], 'parse_orders', r.status_code, r.reason, url)
                        return False
                        existence = True
                        break
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
            else:
                self._print(document_obj['number'], 'Парсим локальный файл')  # TODO: Временное решение
                with open(filename, 'rb') as f:
                    page_content = f.read()

            if not existence:
                with self.get_workers().lock:
                    DB().executeone(f"UPDATE {self.dbdocument} SET document_exists = FALSE WHERE id = '{document_obj['id']}'")

            else:
                with self.get_workers().lock:
                    DB().executeone(
                        f"UPDATE {self.dbdocument} SET downloaded_page = '{filename}' WHERE id = '{document_obj['id']}'")
                self.parse_document_page(page_content, document_obj, session, proxies)
                return True
        finally:
            self.documents_in_parsing.remove(f"'{document_obj['id']}'")
            session.close()

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
    filename = direct_url.split('/')[-1]
    filepath = os.path.join('.', 'webapp', 'media', self_name, str(document['number']))
    if not os.path.exists(filepath):
        os.makedirs(filepath)

    filepath = os.path.join(filepath, filename)
    link = f'/media/{self_name}/{document["number"]}/{filename}'
    # print(direct_url)
    # Если файла нет на диске, то загружаем его
    if not os.path.exists(filepath):
        if not direct_url.startswith('http'):
            direct_url = URL + direct_url
        r = session.get(direct_url, proxies=proxies)
        if r.status_code != 200:
            # print('Файл не был загружен')
            return None
        # filename = os.path.join('.', 'webapp', 'media', 'files', )
        with open(filepath, 'wb') as f:
            f.write(r.content)
    return direct_url, link


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
        # print(number, name, value)

        # (111) Номер регистрации
        if number == '111':
            document_parse['order_register_number'] = f"'{value}'"

        # (151) Дата государственной регистрации
        elif number == '151':
            date_gos_reg = get_date_from_string(value)
            document_parse['date_gos_reg'] = f"'{date_gos_reg}'" if date_gos_reg else 'NULL'

        # (181) Дата истечения срока действия исключительного права
        elif number == '181':
            date_exclusive = get_date_from_string(value)
            document_parse['date_exclusive'] = f"'{date_exclusive}'" if date_exclusive else 'NULL'

        # (210) Номер заявки
        elif number == '210':
            document_parse['order_number'] = f"'{value}'"

        # (220) Дата подачи заявки
        elif number == '220':
            date_created = get_date_from_string(value)
            document_parse['date_created'] = f"'{date_created}'" if date_created else 'NULL'

        # (310) Номер первой заявки
        elif number == '310':
            document_parse['first_order_number'] = f"'{value}'"

        # (320) Дата подачи заявки
        elif number == '320':
            first_order_date = get_date_from_string(value)
            document_parse['first_order_date'] = f"'{first_order_date}'" if first_order_date else 'NULL'

        # (330) Код страны подачи первой заявки
        elif number == '330':
            document_parse['first_order_country_code'] = f"'{value}'"

        # (450) Дата публикации
        elif number == '450':
            date_publish = get_date_from_string(value)
            document_parse['date_publish'] = f"'{date_publish}'" if date_publish else 'NULL'

        # (511) Классы МКТУ и перечень товаров и/или услуг:
        elif number == '511':
            parsed_service_items = []
            for b in child.find_all('b'):
                line = b.text.split()
                number = line[0]
                parsed_service_items.append(number)
                text = ' '.join(line[1:])
                # print(number, text)
                if number not in service_items:
                    serviceitem_values.append(f"('{document['id']}', {{0}}, '{number}', '{text}')")
            if parsed_service_items:
                document_parse['service_items'] = f"'{', '.join(parsed_service_items)}'"

        # (526) Неохраняемые элементы товарного знака
        elif number == '526':
            document_parse['unprotected'] = f"'{value}'"

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

        # (554) Объемный знак
        elif number == '554':
            document_parse['volumetric'] = f"'{value}'"

        # (550) Указание, относящееся к виду знака, и его характеристики
        elif number == '550':
            document_parse['sign_char'] = f"'{value}'"

        # (580) Дата внесения записи в Государственный реестр:
        elif number == '580':
            date_changes = get_date_from_string(value)
            document_parse['date_changes'] = f"'{date_changes}'" if date_changes else 'NULL'

        # (591) Указание цвета или цветового сочетания
        elif number == '591':
            document_parse['color'] = f"'{value}'"

        # (731) Заявитель
        elif number == '731':
            document_parse['applicant'] = f"'{value}'"

        # (732) Правообладатель
        elif number == '732':
            document_parse['copyright_holder'] = f"'{value}'"

        # (740) Патентный поверенный (полное имя, регистрационный номер, местонахождение)
        elif number == '740':
            document_parse['patent_atty'] = f"'{value}'"

        # (750) Адрес для переписки
        elif number == '750':
            document_parse['address'] = f"'{value}'"

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
    else:
        DB().executeone(f'UPDATE interface_proxies SET in_use = FALSE')


if __name__ == '__main__':
    p = Parser(REGISTERS_URL, 'registers')
    # p = Parser(URL1, 'orders')
    # p.get_orders()
    # p.check_new_orders()
    # p.start_parse_one_order()
    p.start_parse_all_orders()
    #
    # # p.orders_urls = load_data_from_file(p.name + '.json')
    # # for url_obj in p.orders_urls:
    # #     print(url_obj)
    # #     urls = url_obj['a_href_steps']
    # #     p.workers.add_task(p.get_page_and_orders_dict, (urls, ))
    #
    # p.workers._queue.join()
    # print(p.orders_urls)
