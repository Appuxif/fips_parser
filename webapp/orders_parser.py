from parser_base import *
import parser_base
# proxy = surnames = names = cities = regions = None


class OrdersParser(Parser):
    # Парсит полученную страницу
    def parse_document_page(self, page_content, document, session, proxies):
        page = BeautifulSoup(page_content, 'html.parser')  # Объект страницы для парсинга

        work_state_row_items = []
        with self.get_workers().lock:
            document_parse = DB().fetchone(
                f"SELECT id, document_id FROM {self.dbdocument_parse} "
                f"WHERE document_id = '{document['id']}' LIMIT 1")
        if document_parse:
            document_parse = dict(document_parse)
            with self.get_workers().lock:
                service_items = DB().fetchall(
                    f"SELECT number FROM {self.dbservice_item} "
                    f"WHERE document_parse_id = '{document_parse['id']}'")
                work_state_item = DB().fetchone(
                    f"SELECT id FROM {self.dbwork_state} "
                    f"WHERE document_parse_id = '{document_parse['id']}'")
                if work_state_item:
                    id = work_state_item['id']
                    work_state_row_items = DB().fetchall(
                        f"SELECT * FROM {self.dbwork_state_row} "
                        f"WHERE workstate_id = '{id}'")
            service_items = [str(item['number']) for item in service_items]
        else:
            document_parse = {
                'document_id': f"'{document['id']}'"}  # Словарь будет преобразован в запрос к БД на сохранение
            service_items = []
            work_state_item = None
        documentfile_item = []
        serviceitem_values = []
        document_info = {}  # Словарь - часть parsed_order
        queries = []  # Список запросов к БД для отправки одной кучей

        # Получение статуса
        status = page.find('tr', class_='Status').text
        status = re.sub('(Статус|Статус:|Статус: )', '', status)
        status = ' '.join(status.split())
        document_parse['status'] = f"'{status}'"

        # Парсинг даты из статуса
        date_refreshed = get_date_from_string(status)
        if date_refreshed:
            document_parse['date_refreshed'] = f"'{date_refreshed}'"
            d = date.today() - date_refreshed
        else:
            self._print(document['number'], 'Не найдена дата в статусе')
            with self.get_workers().lock:
                DB().executeone(f"UPDATE {self.dbdocument} SET document_exists = FALSE WHERE id = '{document['id']}'")
            return

        # Строчка с типом заявки/документа
        document_parse['order_type'] = f"'{page.find(id='BibType').text}'"

        # Парсим основную инфомрацию со страницы
        message, documentfile_item, serviceitem_values = \
            parse_main_info(page, document, document_info, document_parse, service_items, session, proxies, self.name)

        if message:
            self._lprint(document['number'], message)
        if document_info.get('unresolved'):
            self._print(document['number'], 'unresolved', document_info['unresolved'])
            document_parse['order_info'] = f"'{document_info['unresolved']}'"

        # Парсим факсимильные изображения
        message, values = parse_facsimile(page, document, session, proxies, self.name)
        documentfile_item.extend(values)
        if message:
            self._lprint(document['number'], message)

        # Парсим делопроизводство
        work_state, work_state_rows = parse_workstate(page)

        # Отмечаем, что документ был спарсен
        # Если два года не обновлялось, то можно считать закрытой, страница будет доступна на диске
        order_query = f"UPDATE {self.dbdocument} SET document_parsed = TRUE, date_parsed = '{date.today()}' "
        status_lower = status.lower()
        if d.days > 730 or work_state.get('reg_decision') is not None or 'принято решение' in status_lower or\
                'регистрация товарного знака' in status_lower:
            order_query += ', order_done = TRUE '
        order_query += f"WHERE id = '{document['id']}'"
        queries.append(order_query)

        # Получаем контакты из спарсенной информации
        # parse_contacts_from_documentparse(document_parse)
        # return
        # Сохраняем или обновляем парсинг документа
        with self.get_workers().lock:
            if document_parse.get('id') is None:
                document_parse['id'] = f"'{DB().add_row(self.dbdocument_parse, document_parse)}'"
            else:
                DB().executeone(update_by_id_query(self.dbdocument_parse, document_parse))

        if documentfile_item:
            queries.append(
                f"REPLACE INTO {self.dbdocument_file} (document_id, document_parse_id, name, direct_url, link) " +
                'VALUES ' + ', '.join(documentfile_item)
            )

        if serviceitem_values:
            queries.append(
                f"INSERT INTO {self.dbservice_item} (document_id, document_parse_id, number, text) " +
                'VALUES ' + ', '.join(serviceitem_values)
            )

        # Собираем запрос на сохраненение делопроизводства
        if work_state:
            with self.get_workers().lock:
                queries.extend(prepare_work_state_query(work_state_item, work_state, self.dbwork_state, document, document_parse['id']))
            # На этом этапе work_state['id'] уже определен
            queries.extend(get_work_state_queries(work_state_rows, work_state_row_items,
                                                  self.dbwork_state_row, work_state['id'], document))

        # Форматируем запросы. Подставляем ID парсинга документа
        queries = list(map(lambda x: x.format(document_parse['id']), queries))

        with self.get_workers().lock:
            DB().executemany(queries, verbose=False)


# Подготовка запроса на обновление, либо сохранение объекта в БД
def prepare_work_state_query(work_state_item, work_state, dbwork_state, document, document_parse_id):
    if work_state_item:
        # Если запись имеется в БД, то подготавляиваем запрос на обновление
        work_state['id'] = f"'{work_state_item['id']}'"
        q = update_by_id_query(dbwork_state, work_state)
        return [q]
    else:
        # Если в БД нет записи, то сохраняем и получаем ID
        work_state['document_id'] = f"'{document['id']}'"
        work_state['document_parse_id'] = document_parse_id
        id = DB().add_row(dbwork_state, work_state)
        work_state['id'] = f"'{id}'"
    return []


# Подготавливает список запросов на сохраненение делопроизводства
def get_work_state_queries(work_state_rows, work_state_row_items, dbwork_state_row, workstate_id, document):
    values = []
    # Сохраняем строчки из таблицы делопроизводства в соответствующую таблицу
    keys = {row['key'] + '-' + (str(row['date']) if row['date'] else 'NULL'): row['id'] for row in work_state_row_items}
    for row in work_state_rows:
        id = keys.get(row['key'] + '-' + (str(row['date']) if row['date'] else 'NULL'))
        if id is None:
            date = f"'{row['date']}'" if row['date'] else 'NULL'
            values.append(f"('{row['type']}', '{row['key']}', {date}, {workstate_id}, '{document['id']}')")
        # else:
        #     print(row['key'] + '-' + (str(row['date']) if row['date'] else 'NULL'))
    if values:
        q = f"INSERT INTO {dbwork_state_row} (type, `key`, date, workstate_id, document_id) VALUES "
        q += ', '.join(values)
        return [q]
    return []


# Парсинг делопроизводства со страницы документа заявки
def parse_workstate(page):
    # Делопроизводство
    work_state = {}
    obj_list = []
    delo = page.find(id="delo")
    if delo:
        # Всего две таблицы: исходящая и входящая корреспонденции
        all_table = delo.find_all('table')
        fileds = ['income', 'outcome']
        for i, td in enumerate(all_table):
            all_tr = td.find_all('tr')
            obj = "'"
            for tr in all_tr[1:]:
                all_td = tr.find_all('td')
                col_1_text = all_td[0].text.strip()
                col_2_text = all_td[1].text.strip()
                obj += f"{col_1_text}\t{col_2_text}\n"
                obj_list.append({
                    'type': fileds[i],
                    'key': col_1_text,
                    'date': get_date_from_string(col_2_text)
                })
            obj += "'"
            work_state[fileds[i]] = obj
    return work_state, obj_list


def start_parse_all_documents():
    global surnames, names, cities, regions
    parser_base.surnames = get_surnames()
    parser_base.names = get_names()
    parser_base.cities = get_cities()
    # regions = get_regions()
    parser_base.forms = get_forms()
    p = OrdersParser(ORDERS_URL, 'orders')
    p.start_parse_all_documents()


if __name__ == '__main__':
    # start_parse_all_documents()
    release_proxies()
    p = OrdersParser(ORDERS_URL, 'orders')
    # p.check_new_documents()
    # p.get_documents_list()
    p.start_parse_document()
    # p.start_parse_all_documents()
    # p.parse_all_documents_in_threads()

# python -c "from orders_parser import *; p = OrdersParser(ORDERS_URL, 'orders'); p.get_documents_list()"
# python -c "from orders_parser import *; release_proxies(); p = OrdersParser(ORDERS_URL, 'orders'); p.parse_all_documents_in_threads(20)"
# python -c "from orders_parser import *; p = OrdersParser(ORDERS_URL, 'orders'); p.parse_all_documents_in_threads(50)"
