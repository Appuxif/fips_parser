# Сервис управляет процессами парсинга, перезапускает их при изменении настроек

import multiprocessing as mp
import traceback
from multiprocessing.connection import Listener
import threading
import os

import sys
from time import sleep

from registers_parser import RegistersParser, REGISTERS_URL, start_parse_all_documents as start_registers_parser
from orders_parser import OrdersParser, ORDERS_URL, start_parse_all_documents as start_orders_parser, release_proxies
from database import DB

processes = {}


class Processor:
    parsers_processes = {}
    parsers = {}
    release_proxies = False

    def __init__(self, verbose=True):
        self.verbose = verbose
        self.listener = threading.Thread(target=self.listener_thread, daemon=True)
        self.listener.start()
        self.load_parsers()
        self.vprint('Запущен процессор')

    def load_parsers(self, sleep_time=None):
        if sleep_time:
            sleep(sleep_time)
        self.parsers = {p['id']: p for p in DB().fetchall('SELECT * FROM interface_parsersetting')}
        self.vprint('Загружены парсеры')
        for parser_id, parser in self.parsers.items():
            self.vprint(parser)
        self.release_proxies = True

    def vprint(self, *args, **kwargs):
        if self.verbose:
            print(*args, **kwargs)

    def terminate_process(self, parser_id):
        process = self.parsers_processes.pop(parser_id)
        process.terminate()
        self.vprint('Закрыт процесс', process)

    def terminate_all_processes(self):
        while self.parsers_processes:
        # for parser_id, process in self.parsers_processes.items():
            ids = list(self.parsers_processes.keys())
            if not ids:
                break
            parser_id = ids[0]
            self.terminate_process(parser_id)

    # Основной процесс для запуска парсеров
    def go_processor(self):
        while True:
            if self.release_proxies:
                release_proxies()
                self.terminate_all_processes()
                self.release_proxies = False

            for parser_id, parser in self.parsers.items():
                try:
                    self.process_parser(parser)
                except:
                    traceback.print_exc(file=sys.stdout)
                    self.vprint('parser_processor Ошибка парсера', parser)
            for parser_id in self.parsers_processes:
                if parser_id not in self.parsers:
                    self.terminate_process(parser_id)

            sleep(5)

    # Обработка парсеров. Запуск и перезапуск
    def process_parser(self, parser):
        # Если процесс уже был запущен, проверяем его состояние
        process = self.parsers_processes.get(parser['id'])
        if parser['is_working']:
            if process and not process.is_alive():
                self.parsers_processes.pop(parser['id'])
                self.vprint('Процесс не запущен, удаляю из списка для перезапуска', process)
                process = None
            if process is None:
                self.start_new_parser(parser)
        else:
            if process and process.is_alive():
                process.terminate()
                self.vprint('Процесс остановлен', process)
            if process and not process.is_alive():
                self.parsers_processes.pop(parser['id'])
                self.vprint('Процесс удален из списка', process)

    def start_new_parser(self, parser):
        target = start_orders_parser if parser['type'] == 0 else start_registers_parser
        dbdocument = 'orders_document' if parser['type'] == 0 else 'registers_document'

        query = f"SELECT id, url, number FROM {dbdocument} " \
                f"WHERE document_exists = TRUE AND order_done = FALSE "
        if parser['number_gte'] and parser['number_gte'].isnumeric():
            query += f"AND number >= {parser['number_gte']} "
        if parser['number_lte'] and parser['number_lte'].isnumeric():
            query += f"AND number <= {parser['number_lte']} "
        process = mp.Process(
            target=target,
            args=(parser['proxies_num'], query, parser['requests_period'], parser['requests_amount']),
            daemon=True
        )
        process.start()
        self.parsers_processes[parser['id']] = process

    # В этом потоке будут слушаться запросы от сервера
    def listener_thread(self):
        self.vprint('Запуск листенера')
        socket_path = '/var/www/fips_parser/processor.sock'
        if os.path.exists(socket_path):
            os.remove(socket_path)

        with Listener(socket_path) as listener:
            while True:
                with listener.accept() as conn:
                    self.vprint('connection accepted', listener.last_accepted)
                    while True:
                        try:
                            accepted = conn.recv()
                            self.vprint('Получен запрос', accepted)
                            exec(accepted)
                        except KeyboardInterrupt:
                            self.vprint('KeyboardInterrupt')
                            return
                        except EOFError:
                            break
                        except Exception as err:
                            traceback.print_exc(file=sys.stdout)
                            print('Ошибка листенера')


if __name__ == '__main__':
    processor = Processor()
    processor.go_processor()
