# Сервис управляет процессами парсинга, перезапускает их при изменении настроек

import multiprocessing as mp
from multiprocessing.connection import Listener

from registers_parser import RegistersParser, REGISTERS_URL
from orders_parser import OrdersParser, ORDERS_URL


# Запуск процессора
def run_processor():
    pass
