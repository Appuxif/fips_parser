from uuid import uuid4

from parser_base import *


class RegistersParser(Parser):
    # Берет из базы и парсит один непарсенный документ
    # def start_parse_document(self, proxy=None, query=None):
    #     query = f'SELECT id, url, number FROM {self.dbdocument} ' \
    #             'WHERE document_exists = TRUE AND order_done = FALSE '
    #     if len(self.documents_in_parsing) > 0:
    #         query += f'AND id NOT IN ({", ".join(self.documents_in_parsing)}) '
    #     # query += 'ORDER BY number LIMIT 1'
    #     query += 'ORDER BY date_parsed, number DESC LIMIT 1'
    #     return super(RegistersParser, self).start_parse_document(proxy, query)

    # Парсит полученную страницу
    def parse_document_page(self, page_content, document, session, proxies):
        page = BeautifulSoup(page_content, 'html.parser')  # Объект страницы для парсинга

        with self.get_workers().lock:
            document_parse = DB().fetchone(
                f"SELECT id, document_id FROM {self.dbdocument_parse} "
                f"WHERE document_id = '{document['id']}' LIMIT 1")
        if document_parse:
            document_parse = dict(document_parse)
            with self.get_workers().lock:
                service_items = DB().fetchall(
                    f"SELECT id, number FROM {self.dbservice_item} "
                    f"WHERE document_parse_id = '{document_parse['id']}'")
                izv_exists_list = DB().fetchall(
                    f"SELECT id, izv_type, date_publish FROM {self.dbdocument_izv} "
                    f"WHERE document_parse_id = '{document_parse['id']}'")
                izv_items_list = DB().fetchall(
                    f"SELECT id, key, value FROM {self.dbdocument_izvitem} "
                    f"WHERE document_id = '{document['id']}'")
                izv_service_items = DB().fetchall(
                    f"SELECT id, number, text FROM {self.dbdocument_izvserviceitem} "
                    f"WHERE document_id = '{document['id']}'")

            izv_unique_list = [izv['izv_type'] + '-' + (izv['date_publish'] or 'NULL') for izv in izv_exists_list]
            service_items = [str(item['number']) for item in service_items]
        else:
            document_parse = {
                'document_id': f"'{document['id']}'"}  # Словарь будет преобразован в запрос к БД на сохранение
            service_items = []
            izv_unique_list = []
        document_info = {}  # Словарь - часть parsed_order
        queries = []  # Список запросов к БД для отправки одной кучей

        # Получение статуса
        status = page.find('tr', class_='Status').text
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

        # Проверка наличия извещений на странице регистрации
        start_izvs = page.find('p', class_='StartIzvs')

        # Строчка с типом заявки/документа
        document_parse['order_type'] = f"'{page.find(id='BibType').text}'"

        # Парсим основную инфомрацию со страницы
        message, documentfile_item, serviceitem_values = \
            parse_main_info(page, document, document_info, document_parse, service_items, session, proxies, self.name, start_izvs)

        if message:
            self._lprint(document['number'], message)
        if document_info.get('unresolved'):
            self._print(document['number'], 'unresolved', document_info['unresolved'])
            document_parse['order_info'] = f"'{document_info['unresolved']}'"

        # Парсим извещения
        izvs_parsed_list = parse_izvs(document, start_izvs)
        izvs_serviceitem_values = []
        documentizvitem_values = []

        # Подготовка запросов в БД, если были собраны извещения
        if izvs_parsed_list:
            print(izv_unique_list)
        for izv in izvs_parsed_list:

            # Проверка по типу извещения и по дате публикации - такая вот уникальная строчка
            if izv.get('izv_type') is None or izv.get('date_publish') is None:
                continue
            parsed_unique = izv['izv_type'][1:-1] + '-' + izv['date_publish'].replace("'", '')
            print(parsed_unique)
            if parsed_unique in izv_unique_list:
                # print('continued')
                continue
            izvs_serviceitem_values.extend(izv.pop('serviceitem_values'))
            documentizvitem_values.extend(izv.pop('documentizvitem_values'))

            self._print(document['number'], 'info:', izv.get('info', 'No info'))
            izv['document_id'] = f"'{document['id']}'"
            izv['document_parse_id'] = '{0}'
            queries.append(insert_into_query(self.dbdocument_izv, izv))

        if izvs_serviceitem_values:
            queries.append(
                f"INSERT INTO {self.dbdocument_izvserviceitem} " +
                f"(document_id, document_izv_id, number, text) " +
                'VALUES ' + ', '.join(izvs_serviceitem_values)
            )

        if documentizvitem_values:
            queries.append(
                f"INSERT INTO {self.dbdocument_izvitem} " +
                f"(document_id, document_izv_id, full_text, key, value, date) " +
                'VALUES ' + ', '.join(documentizvitem_values)
            )

        # Парсим факсимильные изображения
        message, values = parse_facsimile(page, document, session, proxies, self.name)
        documentfile_item.extend(values)
        if message:
            self._lprint(document['number'], message)

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

        # Отмечаем, что документ был спарсен
        order_query = f"UPDATE {self.dbdocument} SET document_parsed = TRUE, date_parsed = '{date.today()}' "
        status_lower = status.lower()
        if 'прекратил действие' in status_lower:
            order_query += ', order_done = TRUE '
        order_query += f"WHERE id = '{document['id']}'"
        queries.append(order_query)

        # Сохраняем или обновляем парсинг документа
        with self.get_workers().lock:
            # exists = DB().fetchone(f"SELECT id FROM {self.dbdocument_parse} "
            #                        f"WHERE document_id = '{document['id']}' LIMIT 1")
            # if exists is None:
            if document_parse.get('id') is None:
                document_parse['id'] = f"'{DB().add_row(self.dbdocument_parse, document_parse)}'"
            else:
                # document_parse['id'] = f"'{exists['id']}'"
                DB().executeone(update_by_id_query(self.dbdocument_parse, document_parse))

        queries = list(map(lambda x: x.format(document_parse['id']), queries))

        with self.get_workers().lock:
            DB().executemany(queries, verbose=False)


# Парсинг извещений на странице документа регистрации
def parse_izvs(document, start_izvs):
    izvs_list = []
    if start_izvs:
        izv_i = -1
        sib = start_izvs
        title_parsed = False
        while sib:
            sib = sib.next_sibling
            if sib is None or sib.name is None:
                continue

            if sib.name == 'hr':
                if izv_i > -1:
                    sib_prev = sib.previous_sibling.previous_sibling
                    sib_text = getattr(sib_prev, 'text', '').strip()
                    # Дата публикации извещения
                    date_publish = get_date_from_string(sib_text)
                    izvs_list[izv_i]['date_publish'] = f"'{date_publish}'" if date_publish else 'NULL'
                izv_i += 1
                izvs_list.append({'unique_field': f"'{str(uuid4()).replace('-', '')}'",
                                  'serviceitem_values': [],
                                  'documentizvitem_values': []})
                title_parsed = False
            elif sib.name == 'p':
                sib_text = ' '.join(getattr(sib, 'text', '').split())

                if not title_parsed:
                    title_parsed = True
                    izvs_list[izv_i]['izv_type'] = f"'{sib_text}'"
                    continue

                number, name, value = regex_string(sib_text) or ("", "", "")

                if not number and not name and not value:
                    continue

                # (141) Дата прекращения правовой охраны
                if number == '141':
                    date_ended = get_date_from_string(value)
                    izvs_list[izv_i]['date_ended'] = f"'{date_ended}'" if date_ended else 'NULL'
                # (186) Дата, до которой продлен срок действия исключительного права
                elif number == "186":
                    date_renewal = get_date_from_string(value)
                    izvs_list[izv_i]['date_renewal'] = f"'{date_renewal}'" if date_renewal else 'NULL'
                # (511) Классы МКТУ и перечень товаров и/или услуг:
                elif number == '511':
                    service_items = []
                    for b in sib.find_all('b'):
                        line = b.text.split()
                        number = line[0]
                        service_items.append(number)
                        text = ' '.join(line[1:])

                        unique_field = izvs_list[izv_i]['unique_field']
                        izvs_list[izv_i]['serviceitem_values'].append(f"('{document['id']}', {unique_field}, '{number}', '{text}')")
                    if service_items:
                        izvs_list[izv_i]['service_items'] = f"'{', '.join(service_items)}'"
                # (580) Дата внесения записи в Государственный реестр
                elif number == "580":
                    date_changes = get_date_from_string(value)
                    izvs_list[izv_i]['date_changes'] = f"'{date_changes}'" if date_changes else 'NULL'
                # (732) Правообладатель
                elif number == "732":
                    izvs_list[izv_i]['copyright_holder'] = f"'{value}'"
                # (750) Адрес для переписки
                elif number == "750":
                    izvs_list[izv_i]['address'] = f"'{value}'"
                # (770) Прежний правообладатель
                elif number == "770":
                    izvs_list[izv_i]['last_copyright_holder'] = f"'{value}'"
                # (771) Прежнее наименование/имя правообладателя
                elif number == "771":
                    izvs_list[izv_i]['last_copyright_holder_name'] = f"'{value}'"
                # (791) Лицензиат:
                elif number == "791":
                    izvs_list[izv_i]['licensee'] = f"'{value}'"
                # (793) Указание условий договора:
                elif number == "793":
                    izvs_list[izv_i]['contract_terms'] = f"'{value}'"
                # Сублицензиат
                elif 'Сублицензиат' in sib_text:
                    izvs_list[izv_i]['sublicensee'] = f"'{value}'"
                # Вид договора
                elif 'Вид договора' in sib_text:
                    izvs_list[izv_i]['contract_type'] = f"'{value}'"
                # Лицо, передающее исключительное право
                elif 'Лицо, передающее' in sib_text:
                    izvs_list[izv_i]['transferor'] = f"'{value}'"
                # Лицо, передающее исключительное право
                elif 'Лицо, предоставляющее право использования' in sib_text:
                    izvs_list[izv_i]['grantor'] = f"'{value}'"
                # Лицо, передающее исключительное право
                elif 'Лицо, которому предоставлено право использования' in sib_text:
                    izvs_list[izv_i]['granted'] = f"'{value}'"
                # # Дата и номер государственной регистрации договора
                # elif 'Дата и номер' in sib_text:
                #     izvs_list[izv_i]['date_number_changes'] = f"'{value}'"
                elif 'Опубликовано' in sib_text or 'Дата публикации' in sib_text:
                    pass
                else:
                    # Тут обрабатываем неучтенные строчки
                    unique_field = izvs_list[izv_i]['unique_field']
                    date = get_date_from_string(value)
                    date = f"'{date}'" if date else 'NULL'
                    izvs_list[izv_i]['documentizvitem_values'].append(
                        f"('{document['id']}', {unique_field}, '{sib_text}', '{name}', '{value}', {date})"
                    )
    return izvs_list[:-1]


def start_parse_all_documents():
    p = RegistersParser(REGISTERS_URL, 'registers')
    p.start_parse_all_documents()


if __name__ == '__main__':
    release_proxies()
    p = RegistersParser(REGISTERS_URL, 'registers')
    # p.check_new_documents()
    # p.get_documents_list()
    # p.start_parse_document()
    # p.start_parse_all_documents()
    p.parse_all_documents_in_threads(1)

# python -s 'from register_parser import RegistersParser; p = RegistersParser(REGISTERS_URL, 'registers'); p.parse_all_documents_in_threads(5)'
