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
    need_to_refresh = False

    def __init__(self, verbose=True):
        self.verbose = verbose
        django.setup()
        # from autosearcher.models import AutoSearchTask, AutoSearchTaskItem, OrderDocument, RegisterDocument, Corrector
        from autosearcher.models import AutoSearchTask, OrderDocument, RegisterDocument, Corrector, CorrectorTask, \
            AutoSearchLog
        from autosearcher.admin import get_q_from_queryset
        self.get_q_from_queryset = get_q_from_queryset
        self.AutoSearchTask = AutoSearchTask
        self.OrderDocument = OrderDocument
        self.RegisterDocument = RegisterDocument
        self.Corrector = Corrector
        self.CorrectorTask = CorrectorTask
        self.AutoSearchLog = AutoSearchLog
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

    def process_documents(self, task, documents, f, log_object):
        documents_count = documents.count()
        text = f'Найдено {documents_count} документов'
        print(text)
        f.write(text + '\n')
        log_object.message = (log_object.message or '') + text + '\n'

        if documents.count() == 0:
            return

        # Фильтр корректоров по общему количеству задач
        correctors = self.Corrector.objects.annotate(tasks_count=Count('task')).order_by('tasks_count')
        correctors_count = correctors.count()
        print('Найдено', correctors_count, 'корректоров')

        today = date.today()
        # now = datetime.now()

        correctors_dict = {}
        for corrector in correctors:
            correctors_dict[corrector.id] = {
                'corrector': corrector,
                'name': corrector.user.username,
                'today': corrector.correctortask_set.filter(date_created__gte=today).count(),
                'total': corrector.tasks_count,
                'documents_distributed': 0,
                'done': False
            }
        correctors_ids = sorted(correctors_dict, key=lambda x: correctors_dict[x]['total'])
        documents_distributed = 0
        for i, document in enumerate(documents):
            # Проверяем, что для этого докуента не было создано задачи
            tasks = self.CorrectorTask.objects.filter(document_id=document.id).first()
            if tasks is not None:
                text = f'{i} {document} Уже есть задача'
                print(text)
                f.write(text + '\n')
                # task_already_exists += str(document.number) + ', '
                continue

            # Находим компанию - правообладателя
            company = document.company_set.filter(ordercompanyrel__company_is_holder=True).first()
            sign_char = company.sign_char if company else None
            if sign_char is None:
                text = f'{i} {document} sign_char не определен для компании'
                print(text)
                f.write(text + '\n')
                continue

            # Если код страны определен, то ищем для него подходящего корректора
            all_correctors_done = True
            for corrector_id in correctors_ids:
                corrector = correctors_dict[corrector_id]['corrector']
                # Проверяем наличие кода страны и текущее количество задач
                tasks_today = correctors_dict[corrector.id]['today']
                tasks_total = correctors_dict[corrector.id]['total']

                # Проверяем количество задач, добавленных сегодня
                if tasks_total <= corrector.tasks_max and tasks_today <= corrector.tasks_day_amount:
                    # Проверяем начальную букву в названии компании документа
                    all_correctors_done = False
                    if sign_char in corrector.sign_chars and re.match(r'^[а-я]', company.name, re.I):
                        break
            else:
                if all_correctors_done:
                    text = f'{i} {document} у всех корректоров переполнены списки задач'
                    print(text)
                    f.write(text + '\n')
                    break

                text = f'{i} {document} Нет подходящего корректора {sign_char} '
                print(text)
                f.write(text + '\n')
                continue
            text = f'{i} {document} Корректор найден {corrector} {tasks_total} {tasks_today}'
            print(text)
            f.write(text + '\n')

            # Добавить этому корректору задачу с документом
            task_created = corrector.correctortask_set.create(document_registry=task.registry_type,
                                                              document_id=document.id)
            correctors_dict[corrector.id]['today'] += 1
            correctors_dict[corrector.id]['total'] += 1
            correctors_dict[corrector.id]['documents_distributed'] += 1
            documents_distributed += 1
            correctors_ids = sorted(correctors_dict, key=lambda x: correctors_dict[x]['total'])

        text = f'Распределено документов {documents_distributed}\n'
        text += f'Корректоров {correctors_count}\n'
        for corrector_id, obj in correctors_dict.items():
            text += f'{obj["name"]}: добавлено задач {obj["documents_distributed"]}, \n'
        log_object.message = (log_object.message or '') + text
        print(log_object.message)

        # Обработка задачи из БД

    def process_task(self, task, f, log_object):
        now = datetime.now(tz=timezone.utc)
        delta = now - task.next_action
        print(task.id, delta.total_seconds())
        # Значение должно быть положительным, чтобы сработал триггер
        if delta.total_seconds() >= 0:
            print('Начинаем задачу', task.task_name)
            # Список элементов задачи
            queryset = task.autosearchtaskitem_set.all()

            # Запрос в БД для фильтрации документов
            q = self.get_q_from_queryset(queryset)
            document = self.OrderDocument if task.registry_type == 0 else self.RegisterDocument
            documents = document.objects.filter(q)

            # Распределение документов по корректорам
            self.process_documents(task, documents, f, log_object)

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
            print('Задача', task.task_name, 'завершена')

    # Основной процесс для обработки задач
    def go_processor(self):
        while True:
            if self.need_to_refresh:
                self.load_tasks()
                self.need_to_refresh = False

            for task_id, task in self.tasks.items():
                if not task.is_active:
                    self.need_to_refresh = True
                    continue
                log_object = self.AutoSearchLog(task=task)
                print('Задача', task_id)
                now = datetime.now()
                now_str = now.strftime('%Y-%m-%d_%H-%M-%S')
                filename = 'task_' + str(task.id) + '_' + now_str + '.txt'
                filepath = os.path.join('.', 'media', 'logs')
                if not os.path.exists(filepath):
                    os.makedirs(filepath)
                error_filename = os.path.join(filepath, filename)
                log_file = '/media/logs/' + filename
                log_object.log_file = log_file
                with open(error_filename, 'w') as f:
                    try:
                        self.process_task(task, f, log_object)
                    except:
                        traceback.print_exc(file=f)
                        traceback.print_exc(file=sys.stdout)
                        log_object.is_error = True
                        self.vprint('parser_processor Ошибка парсера', task)
                    finally:
                        log_object.save()

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
