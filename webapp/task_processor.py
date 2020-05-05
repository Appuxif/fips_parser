from datetime import datetime, timedelta, date, timezone
import django
from django.db.models import Q, Count, F
import os
import sys
import re
import traceback
from time import sleep
import multiprocessing as mp
from multiprocessing.connection import Listener
import threading

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webapp.settings')
alphabet = 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'


# Запускать только в окружении Django
class Processor:
    processes = {}
    tasks = {}
    verbose = False

    def __init__(self, verbose=True):
        self.verbose = verbose
        django.setup()
        # from autosearcher.models import AutoSearchTask, AutoSearchTaskItem, OrderDocument, RegisterDocument, Corrector
        from autosearcher.models import AutoSearchTask, OrderDocument, RegisterDocument, Corrector, CorrectorTask
        from autosearcher.admin import get_q_from_queryset
        self.get_q_from_queryset = get_q_from_queryset
        self.AutoSearchTask = AutoSearchTask
        # self.AutoSearchTaskItem = AutoSearchTaskItem
        self.OrderDocument = OrderDocument
        self.RegisterDocument = RegisterDocument
        self.Corrector = Corrector
        self.CorrectorTask = CorrectorTask
        django.db.close_old_connections()

        self.load_tasks()
        # self.listener = threading.Thread(target=self.listener_thread)
        # self.listener.start()
        self.vprint('Запущен процессор')

    def vprint(self, *args, **kwargs):
        if self.verbose:
            print(*args, **kwargs)

    # Загрузка задач из БД
    def load_tasks(self, sleep_time=0):
        if sleep_time:
            sleep(sleep_time)
        print('Загрузка списка задач из БД')
        self.tasks = {task.id: task for task in self.AutoSearchTask.objects.all() if task.is_active}
        print(self.tasks)

    def process_documents(self, task, documents):
        # Фильтр корректоров по общему количеству задач
        correctors = self.Corrector.objects.annotate(tasks_count=Count('task')).order_by('tasks_count')
        correctors_count = correctors.count()
        print('Найдено', correctors_count, 'корректоров')
        # correctors = list(correctors)
        today = date.today()
        now = datetime.now()
        documents_skipped = 'Документы не распределены:\n'
        sign_chars_not_founded = 'sign_char не определен для:\n'
        task_already_exists = 'Задача уже была создана для:'

        for i, document in enumerate(documents):
            # Проверяем, что для этого докуента не было создано задачи
            tasks = self.CorrectorTask.objects.filter(document_id=document.id).first()
            if tasks is not None:
                print(i, 'Для этого документа уже есть задача. Пропускаем')
                task_already_exists += str(document.number) + '\n'
                continue

            # Находим компанию - правообладателя
            company = document.company_set.filter(ordercompanyrel__company_is_holder=True).first()
            sign_char = company.sign_char if company else None
            if sign_char is None:
                self.vprint('sign_char не определен для', i, document)
                sign_chars_not_founded += str(document.number) + '\n'
                continue

            # Если код страны определен, то ищем для него подходящего корректора
            for corrector in correctors:
                # Проверяем наличие кода страны и текущее количество задач
                if sign_char in corrector.sign_chars and corrector.tasks_count <= corrector.tasks_max:
                    # Проверяем количество задач, добавленных сегодня
                    tasks_today = corrector.correctortask_set.filter(date_created__gte=today).count()
                    if tasks_today <= corrector.tasks_day_amount and re.match(r'^[а-я]', company.name, re.I):
                        # Проверяем начальную букву в названии компании документа
                        break
            else:
                print('Подходящий для документа корректор не найден. Документ пропущен', i, document)
                documents_skipped += str(document.number) + '\n'
                continue

            print('Корректор найден', corrector, corrector.tasks_count, tasks_today)
            # TODO: Добавить этому корректору задачу с документом
            task_created = corrector.correctortask_set.create(document_registry=task.registry_type,
                                                              document_id=document.id)
            print('Задача создана', task_created)

            # corrector = correctors.filter(sign_chars__icontains=sign_char).\
            #     filter(tasks_count__lt=F('tasks_max')).order_by('tasks_count').first()
            # if corrector is None:
            #     self.vprint('Не найден corrector для sign_char', sign_char)
            #     # TODO: Можно пропускать, или отдавать документ случайному корректору
            #     continue

        # Запрашиваем подходящих корректоров

        # Проверяем количество задач на сегодня
        # for corrector in correctors:
        #     # Если дата последнего добавления задачи не равна сегодня, но обнуляем счетчик
        #     if corrector.task_last_added_date.date() != today:
        #         corrector.tasks_today = 0
        # corrector = correctors.filter()
        # for corrector in correctors:
        #     c_documents = documents
        #     # Документы, отфильтрованные для корректора
        #     if ', ' in corrector.sign_chars:
        #         chars = [c for c in corrector.sign_chars.split(', ')]
        #     elif ',' in corrector.sign_chars:
        #         chars = [c for c in corrector.sign_chars.split(',')]
        #     else:
        #         chars = []
        #     if chars:
        #         c_documents = c_documents.filter(person__sign_char__in=chars)
        #         documents = documents.exclude(person__sign_char__in=chars)
        #     for sign in re.findall('[' + corrector.company_startswith.lower() + ']', alphabet):
        #         c_documents = c_documents.filter(person__name__istartswith=sign)
        #         documents = documents.exclude(person__name__istartswith=sign)

    # Обработка задачи из БД
    def process_task(self, task):
        now = datetime.now(tz=timezone.utc)
        delta = now - task.next_action
        print(task.id, delta.total_seconds())
        # Значение должно быть положительным, чтобы сработал триггер
        if delta.total_seconds() >= 0:
            # Список элементов задачи
            queryset = task.autosearchtaskitem_set.all()

            # Запрос в БД для фильтрации документов
            q = self.get_q_from_queryset(queryset)
            document = self.OrderDocument if task.registry_type == 0 else self.RegisterDocument
            documents = document.objects.filter(q)
            print('Найдено', documents.count(), 'документов')

            # Распределение документов по корректорам
            self.process_documents(task, documents)

            # Если задача автообновляемая, то нужно продлить даты до следующего периода
            if task.auto_renew:
                td = timedelta(days=task.renew_in_days or 0, hours=task.renew_in_hours or 0)
                task.next_action += td
                for item in queryset:
                    # Если значение в формате даты, то сдвигаем дату
                    if re.match('\d{4}-\d{2}-\d{2}', item.filter_value):
                        date_ = date.fromisoformat(item.filter_value) + td
                        item.filter_value = date_.strftime('%Y-%m-%d')
                        item.save()
            # Если задача не автообновляемая, то убираем галочку "Задача активна"
            else:
                task.is_active = False

            task.last_launch = now
            task.save()

            # TODO: Добавить в историю задач информацию о результате

    # Основной процесс для обработки задач
    def go_processor(self):
        while True:
            for task_id, task in self.tasks.items():
                if not task.is_active:
                    continue
                print('Задача', task_id)
                try:
                    self.process_task(task)
                except:
                    traceback.print_exc(file=sys.stdout)
                    self.vprint('parser_processor Ошибка парсера', task)

            # for task_id in self.processes:
            #     if task_id not in self.tasks:
            #         self.terminate_process(parser_id)

            sleep(5)

    # В этом потоке будут слушаться запросы от сервера
    def listener_thread(self):
        self.vprint('Запуск листенера')
        socket_path = '/var/www/fips_parser/tasks_processor.sock'
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
                            self.vprint('Ошибка листенера')


if __name__ == '__main__':
    processor = Processor()
    processor.go_processor()
