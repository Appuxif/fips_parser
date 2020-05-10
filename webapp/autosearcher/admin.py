import traceback
import sys
from datetime import datetime, timezone, date, timedelta
from django.db import connection
from django.contrib import admin, messages
from django.db.models import Q, Count, FilteredRelation
from django.contrib.auth.models import User
from django.contrib.admin.models import LogEntry, ContentType
from multiprocessing.connection import Client

from .models import AutoSearchTask, AutoSearchTaskItem, \
    OrderDocument, RegisterDocument, \
    Corrector, CorrectorTask, AutoSearchLog, \
    MailingTask, MailingItem
# from interface.models import OrderDocument, RegisterDocument,
# from orders.models_base import Document as OrderDocument
# from registers.models_base import Document as RegisterDocument


document_dict = {0: OrderDocument,
                 1: RegisterDocument}


# Составляет запрос для фильтрации элементов из БД, используя элементы задачи
def get_q_from_queryset(queryset):
    q = Q()
    for item in queryset:
        # Подготовка значений для составления фильтра
        filter_field = item.filter_field_raw or item.filter_field or ''
        filter_method = item.filter_method_raw or item.filter_method or ''
        filter_value_lower = item.filter_value.lower()
        if 'false' in filter_value_lower:
            filter_value = False
        elif 'true' in filter_value_lower:
            filter_value = True
        else:
            filter_value = item.filter_value

        if filter_method == '__in':
            if ', ' in item.filter_value:
                filter_value = [it for it in filter_value.split(', ')]
            else:
                filter_value = [it for it in filter_value.split(',')]

        # Получение фильтра
        if item.except_field:
            q &= ~Q(**{filter_field + filter_method: filter_value})
        else:
            q &= Q(**{filter_field + filter_method: filter_value})
    return q


# Генерирует запрос в БД в зависимости от элементов задачи
def get_task_queryset(form, formsets):
    q = Q()
    for formset in formsets:
        q &= get_q_from_queryset(formset.queryset)
    if form.cleaned_data['registry_type'] == 0:
        Document = OrderDocument
    else:
        Document = RegisterDocument
    return Document.objects.filter(q)


class AutoSearchTaskItemInline(admin.StackedInline):
    model = AutoSearchTaskItem
    # exclude = ('tasks_today', )
    extra = 0
    fields = (('filter_field', 'filter_field_raw'),
              ('filter_method', 'filter_method_raw'),
              ('filter_value', 'except_field'))


class AutoSearchLogInline(admin.TabularInline):
    model = AutoSearchLog
    extra = 0
    readonly_fields = ('is_error', 'log_file', 'message', 'date_created')
    ordering = ('-date_created', )
    max_num = 3

    def get_queryset(self, request):
        queryset = super(AutoSearchLogInline, self).get_queryset(request)
        first = queryset.first()
        if first:
            return queryset.filter(id__gte=first.id - 2)
        return queryset

    def has_add_permission(self, request, obj):
        return False


@admin.register(AutoSearchTask)
class AutoSearchTaskAdmin(admin.ModelAdmin):
    inlines = (AutoSearchTaskItemInline, AutoSearchLogInline)
    list_display = ('__str__', 'registry_type', 'next_action', 'last_launch', 'auto_renew', 'is_active')
    save_on_top = True
    readonly_fields = ('documents_count', 'actual_query')

    my_queryset = None

    # Подсчитывает количество документов по заданным фильтрам
    def documents_count(self, obj):
        q = Q()
        q &= get_q_from_queryset(obj.autosearchtaskitem_set.all())
        self.my_queryset = q
        Document = document_dict[obj.registry_type]
        return Document.objects.filter(q).count()
    documents_count.short_description = "Найдено документов"

    # Построение запроса для получения списка в AMS
    def actual_query(self, obj):
        q = self.my_queryset
        if q is None:
            return ''
        Document = document_dict[obj.registry_type]
        # f = FilteredRelation('workstaterow', condition=Q(workstaterow__date__gte='2020-04-27') & Q(workstaterow__date__lte='2020-05-01'))
        # qq = Document.objects.filter(q).annotate(date=f)
        # print(qq.first().date)
        return Document.objects.filter(q).query
    actual_query.short_description = 'SQL'

    # def save_related(self, request, form, formsets, change):
    #     super(AutoSearchTaskAdmin, self).save_related(request, form, formsets, change)
    #     queryset = get_task_queryset(form, formsets[:1])
    #     # TODO: Подгрузка таблицы с контактами
    #     # print(queryset.annotate(name='person__full_name').filter(person__full_name__isnull=False).query)
    #     # print(queryset.prefetch_related('contactperson_set').filter(person__full_name__isnull=False).query)
    #     c = queryset.count()
    #     messages.add_message(request, messages.INFO, 'Найдено ' + str(c) + ' документов')

    def save_model(self, request, obj, form, change):
        if obj.is_active:
            try:
                socket_path = '/var/www/fips_parser/tasks_processor.sock'
                with Client(socket_path) as conn:
                    conn.send('self.load_tasks(5)')
            except FileNotFoundError:
                print('AutoSearchTaskAdmin save_model Сокет не найден')
            except:
                print('AutoSearchTaskAdmin save_model Ошибка подключения')
                traceback.print_exc(file=sys.stdout)
        return super(AutoSearchTaskAdmin, self).save_model(request, obj, form, change)


# class CorrectorTaskInline(admin.StackedInline):
class CorrectorTaskInline(admin.TabularInline):
    model = CorrectorTask
    extra = 0
    readonly_fields = ('datetime_created', 'date_created')
    ordering = ('date_task_done', 'datetime_created')
    max_num = 30
    fields = ('document_registry', 'document_id', 'date_created', 'task_done', 'date_task_done')

    # def view_on_site(self, obj):
    #     return f'/admin/autosearcher/contactperson/{obj.contactperson_id}/change/'


@admin.register(Corrector)
class CorrectorAdmin(admin.ModelAdmin):
    # inlines = (CorrectorTaskInline, )  # TODO: Может стоит убрать
    save_on_top = True
    fields = ('user', 'sign_chars', 'company_startswith', 'tasks_day_amount', 'tasks_max', 'score', 'tasks_done_amount')
    readonly_fields = ('tasks_done_amount', )

    def tasks_done_amount(self, obj):
        return obj.tasks_done_amount
    tasks_done_amount.short_description = 'Количество выполненных задач'


@admin.register(CorrectorTask)
class CorrectorTaskAdmin(admin.ModelAdmin):
    readonly_fields = ('note', 'corrector', 'document_registry', 'document_id', 'datetime_created',
                       'date_created', 'date_task_done', )
    list_display = ('__str__', 'corrector', 'document_registry', 'document_id',
                    'task_done', 'date_created')
    save_on_top = True

    def get_queryset(self, request):
        qs = super(CorrectorTaskAdmin, self).get_queryset(request)
        try:
            qs = qs.filter(corrector_id=request.user.corrector.id)
        except User.corrector.RelatedObjectDoesNotExist:
            pass
        return qs

    def save_model(self, request, obj, form, change):
        # super(CorrectorTaskAdmin, self).save_model(request, obj, form, change)
        try:
            corrector = request.user.corrector
        except User.corrector.RelatedObjectDoesNotExist:
            corrector = None
        # TODO: Добавить проверку менеждера
        # Проверка выполнения задачи при сохранени объекта
        if obj.task_done and obj.corrector == corrector:
            # Определяем БД для документов
            Document = OrderDocument if obj.document_registry == 0 else RegisterDocument
            # Получаем документ из задания
            doc = Document.objects.get(id=obj.document_id)
            print(doc)
            print(doc.company_set.all())

            corrector_logs = LogEntry.objects.filter(user_id=corrector.user.id)
            now = datetime.now(tz=timezone.utc)
            today = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)

            # Проверяем все компании документа на корректировку
            company_corrected = True
            for company in doc.company_set.all():
                # Ищем изменения в компании от этого пользователя в логах
                company_content_type = ContentType.objects.get(model='company')
                company_corrector_logs = corrector_logs.filter(content_type_id=company_content_type.id)
                company_corrector_logs = company_corrector_logs.filter(object_id=company.id)
                company_corrector_logs = company_corrector_logs.filter(action_time__gte=obj.datetime_created)
                if len(company_corrector_logs) == 0:
                    company_corrected = False
                    messages.add_message(request, messages.ERROR, f'Компания {company} не была откорректирована')
                # print('company_corrector_logs', company_corrector_logs)
                # print('company.date_corrected', company.date_corrected)

            print(doc.contactperson_set.all())
            # Проверяем все контакты компании на корректировку
            person_corrected = True
            for person in doc.contactperson_set.all():
                # Ищем изменения в контакте от этого пользователя в логах
                person_content_type = ContentType.objects.get(model='contactperson')
                person_corrector_logs = corrector_logs.filter(content_type_id=person_content_type.id)
                person_corrector_logs = person_corrector_logs.filter(object_id=person.id)
                person_corrector_logs = person_corrector_logs.filter(action_time__gte=obj.datetime_created)
                if len(person_corrector_logs) == 0:
                    company_corrected = False
                    messages.add_message(request, messages.ERROR, f'Контакт {person} не был откорректирован')
                # print('company_corrector_logs', person_corrector_logs)
                # print('company.date_corrected', person.date_corrected)

            if person_corrected and company_corrected:
                messages.add_message(request, messages.INFO, f'Задача выполнена')
                obj.save()
                corrector.score += 5
                corrector.tasks_done += 1
            else:
                messages.add_message(request, messages.ERROR, f'Задача не выполнена')


@admin.register(AutoSearchLog)
class AutoSearchLogAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'is_error', 'date_created')
    readonly_fields = ('task', 'is_error', 'log_file', 'message', 'date_created')


@admin.register(MailingTask)
class MailingTaskAdmin(admin.ModelAdmin):
    list_display = ('autosearchtask', 'next_action', 'last_launch', 'auto_renew', 'is_active')
    readonly_fields = ('actual_query', 'contacts_amount', 'documents_count')

    get_ams_query = None

    # Построение запроса для получения списка в AMS
    def actual_query(self, obj):
        q = self.get_ams_query or get_ams_query(obj, join_document=True, join_documentparse=True)
        self.get_ams_query = q
        # Проверка получившегося запроса.
        with connection.cursor() as cur:
            cur.execute(q + ' LIMIT 1')
            # rows = cur.fetchone()
            # print(cur.description)
        # print(rows)
        return q
    actual_query.short_description = 'Запрос для получения списка в AMS'

    def contacts_amount(self, obj):
        q = get_ams_query(obj, 'count(*) as amount', True, True)
        with connection.cursor() as cur:
            cur.execute(q)
            row = cur.fetchone()
        return row[0]
    contacts_amount.short_description = 'Найдено контактов'

    # Подсчитывает количество документов по заданным фильтрам
    def documents_count(self, obj):
        return AutoSearchTaskAdmin.documents_count(self, obj.autosearchtask)
    documents_count.short_description = "Найдено документов"

    def save_model(self, request, obj, form, change):
        if obj.is_active:
            try:
                socket_path = '/var/www/fips_parser/tasks_processor.sock'
                with Client(socket_path) as conn:
                    conn.send('self.load_tasks(5)')
            except FileNotFoundError:
                print('MailingTaskAdmin save_model Сокет не найден')
            except:
                print('MailingTaskAdmin save_model Ошибка подключения')
                traceback.print_exc(file=sys.stdout)
        return super(MailingTaskAdmin, self).save_model(request, obj, form, change)


# TODO: Для отладки
@admin.register(MailingItem)
class MailingItemAdmin(admin.ModelAdmin):
    list_display = ('mailingtask', 'contactperson_id', 'document_id', 'documentparse_id', )


# Получение запроса
def get_ams_query(obj, selected=None, join_document=False, join_documentparse=False):
    queryset = obj.mailingitem_set.all()

    selected = selected or 't2.id, t2.email, t2.full_name, t2.last_name, t2.first_name, t2.middle_name'
    joined = f' LEFT JOIN interface_contactperson t2 ON t1.contactperson_id = t2.id'
    table = 'orders' if obj.autosearchtask.registry_type == 0 else 'registers'

    # Если есть запросы, включающие ID документа,
    if join_document and queryset.filter(document_id__isnull=False).exists():
        selected += ', t3.*'
        joined += f' LEFT JOIN {table}_document t3 ON t1.document_id = t3.id'

    # Если есть запросы, включающие ID парсинга документа
    if join_documentparse and queryset.filter(documentparse_id__isnull=False).exists():
        selected += ', t4.*'
        joined += f' LEFT JOIN {table}_documentparse t4 ON t1.documentparse_id = t4.id'

    q = f'SELECT {selected} FROM autosearcher_mailingitem t1'
    q += joined
    q += f" WHERE t1.mailingtask_id = '{obj.id}'"
    return q
