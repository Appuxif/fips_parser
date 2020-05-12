import traceback
import sys
from datetime import datetime, timezone, date, timedelta
from time import sleep

from django.db import connection
from django.contrib import admin, messages
from django.db.models import Q, Count, FilteredRelation
from django.contrib.auth.models import User
from django.contrib.admin.models import LogEntry, ContentType
from django.forms import modelform_factory, modelformset_factory
from multiprocessing.connection import Client

from .models import AutoSearchTask, AutoSearchTaskItem, \
    OrderDocument, RegisterDocument, \
    Corrector, CorrectorTask, AutoSearchLog, \
    MailingTask, MailingItem
from interface.models import ContactPerson, Company
# from .forms import OrderDocumentParseForm, RegisterDocumentParseForm, \
#     OrderDocumentParse, RegisterDocumentParse
from .forms import OrderDocumentParse, RegisterDocumentParse, ContactPersonTaskForm, CompanyForm, ContactFormset
from interface.change_message_utils import construct_change_message
from interface.admin import verify_email
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
    save_as = True
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
        # if obj.is_active:
        try:
            socket_path = '/var/www/fips_parser/tasks_processor.sock'
            with Client(socket_path) as conn:
                # conn.send('self.load_tasks(5)')
                conn.send('self.need_to_refresh=True')
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
    fields = ('user', 'sign_chars', 'company_startswith', 'tasks_day_amount', 'tasks_max',
              'score', 'tasks_done_amount', 'tasks_not_done_amount', 'is_active')
    readonly_fields = ('tasks_done_amount', 'tasks_not_done_amount')
    list_display = ('__str__', 'tasks_day_amount', 'tasks_max', 'tasks_done_amount',
                    'tasks_not_done_amount', 'is_active')

    def tasks_done_amount(self, obj):
        return obj.tasks_done_amount
    tasks_done_amount.short_description = 'Количество выполненных задач'

    def tasks_not_done_amount(self, obj):
        return obj.tasks_not_done_amount
    tasks_not_done_amount.short_description = 'Количество невыполненных задач'


@admin.register(CorrectorTask)
class CorrectorTaskAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'datetime_created', 'date_task_done', 'task_done', 'task_cannot_be_done')
    fields = ('document_number', 'datetime_created', 'date_task_done', 'task_cannot_be_done')
    readonly_fields = ('note', 'datetime_created', 'date_task_done', 'document_number')
    # save_on_top = True
    view_on_site = False
    change_form_template = 'admin/custom_change_form_autosearchtask.html'

    def document_number(self, obj):
        return obj.document_number
    document_number.short_description = 'Номер документа'

    # Кастомный функционал страницы
    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        # Поиск объектов, связанных с этой задачей
        task = CorrectorTask.objects.get(id=object_id)
        if task.document_registry == 0:
            Document = OrderDocument
            DocumentParse = OrderDocumentParse
            filter_type = 'order'
        else:
            Document = RegisterDocument
            DocumentParse = RegisterDocumentParse
            filter_type = 'register'
        document = Document.objects.get(id=task.document_id)

        company_filter = {filter_type + '__id': document.id,
                          filter_type + 'companyrel__company_is_holder': True}
        # Кастомные формы объектов
        DocumentParseForm = modelform_factory(DocumentParse, fields=('applicant', 'address', 'copyright_holder', 'patent_atty'))

        company = Company.objects.filter(**company_filter).first()

        # Проверяем у документа наличие прикрепленных контактов
        # TODO: Временное решение
        if document.contactperson_set.count() == 0:
            # Если контактов нет, то добавляем контакты из компании-правообладателя
            for p in company.contactperson_set.all():
                document.contactperson_set.add(p)
            if document.documentparse.patent_atty:
                document.document_parsed = False
                document.order_done = False
                document.date_parsed = None
                document.save()
                sleep(5)

        # Размещение изображений и факсимильных файлов
        link = document.documentfile_set.filter(name='image').first()
        if link:
            extra_context['document_image'] = link.link
        files = document.documentfile_set.exclude(name='image')
        if files.exists():
            extra_context['document_files'] = [f.link for f in files.all()]

        # Если был POST запрос, то нужно сохранить кастомные формы
        if request.method == 'POST':
            # print(request.POST)
            if request.POST.get('_continue', '') == 'Сохранить Компанию':
                company_form = CompanyForm(request.POST, request.FILES, instance=company)
                if company_form.is_valid():
                    company = company_form.save()
                    # Логируем изменения
                    change_message = construct_change_message(company_form, [], False)
                    logs = self.log_change(request, company, change_message)

            if request.POST.get('_continue', '') == 'Сохранить Контакты':
                contact_formset = ContactFormset(request.POST, request.FILES)
                # print(contact_formset.is_valid())
                email_verified = False
                for i, form in enumerate(contact_formset.forms):
                    # print(form.has_changed())
                    # print(form.cleaned_data)
                    if form.has_changed():
                        form_is_valid = form.is_valid()
                        person = form.cleaned_data.get(f'id')
                        delete = form.cleaned_data['delete']
                        # print(person)
                        # При откреплении контакта от документа
                        if delete and person:
                            document.contactperson_set.remove(person)
                            # Логируем изменения
                            change_message = []
                            # change_message = construct_change_message(form, [], False)
                            change_message.append({
                                'changed': {
                                    'name': 'Связь Контакт - Документ',
                                    'object': str(person),
                                    'fields': ['unpinned Contact ' + str(person.id)]
                                }
                            })
                            logs = self.log_change(request, document, change_message)
                            # print('logs', logs)
                            continue

                        # Если контакт был отредактирован
                        if person and form_is_valid:
                            person = form.save()
                            if person.email and not person.email_verified:
                                email_verified = verify_email(request, person)
                                person.save()
                            # Логируем изменения
                            change_message = construct_change_message(form, [], False)
                            self.log_change(request, form.instance, change_message)
                            continue

                        # При прикреплении уже существующего контакта к документу
                        new_id = form.cleaned_data['new_id']
                        if new_id:
                            person = ContactPerson.objects.get(id=new_id)
                            document.contactperson_set.add(person)
                            # Логируем изменения
                            change_message = []
                            # change_message = construct_change_message(form, [], False)
                            change_message.append({
                                'changed': {
                                    'name': 'Связь Контакт - Документ',
                                    'object': str(person),
                                    'fields': ['pinned Contact ' + str(person.id)]
                                }
                            })
                            logs = self.log_change(request, document, change_message)
                            # print('logs', logs)
                            continue

                        # При создании нового контакта
                        if form_is_valid and form.cleaned_data.get('full_name'):
                            person = form.save()
                            document.contactperson_set.add(person)
                            if person.email and not person.email_verified:
                                email_verified = verify_email(request, person)
                                person.save()
                            # Логируем изменения
                            change_message = []
                            change_message.append({
                                'changed': {
                                    'name': 'Связь Контакт - Документ',
                                    'object': str(person),
                                    'fields': ['pinned Contact ' + str(person.id)]
                                }
                            })
                            logs = self.log_change(request, document, change_message)
                            # print('logs 1', logs)
                            change_message = construct_change_message(form, [], False)
                            logs = self.log_addition(request, person, change_message)
                            # print('logs 2', logs)

                # Если почта была верифицирована, то задача считается завершенной, начисляем балл за задачу
                if email_verified:
                    class FakeForm:
                        cleaned_data = {}
                        pass
                    f = FakeForm()
                    f.cleaned_data['task_done'] = True
                    make_task_done(f, task)
                    task.save()
                    corrector_add_score(request, task)
        elif request.method == 'GET':
            pass

        contact_formset_filter = {filter_type + '__id': document.id}

        extra_context['document_form'] = DocumentParseForm(instance=document.documentparse)
        extra_context['company_form'] = CompanyForm(request.POST or None, instance=company)
        extra_context['company'] = company
        contactpersons = ContactPerson.objects.filter(**contact_formset_filter)
        contactpersons_initial = [{'company': company.id, filter_type: document, 'company_id': company.id}]*(contactpersons.count() + 1)
        extra_context['contact_formset'] = ContactFormset(queryset=contactpersons.all(),
                                                          initial=contactpersons_initial)

        # print('document', document)
        # print('company', company)
        # print('contact_formset', extra_context['contact_formset'])
        return super(CorrectorTaskAdmin, self).change_view(request, object_id, form_url, extra_context)

    # Отображение задач только для текущего корректора. Если в задачи зайдет не корректор, то буду
    # отображены все возможные задачи
    def get_queryset(self, request):
        qs = super(CorrectorTaskAdmin, self).get_queryset(request)
        try:
            qs = qs.filter(corrector_id=request.user.corrector.id)
        except User.corrector.RelatedObjectDoesNotExist:
            pass
        return qs

    def save_model(self, request, obj, form, change):
        make_task_done(form, obj)
        super(CorrectorTaskAdmin, self).save_model(request, obj, form, change)
        corrector_add_score(request, obj)
        # TODO: Добавить проверку менеждера
        # Проверка выполнения задачи при сохранени объекта
        # if obj.task_done and obj.corrector == corrector:
        #     # Определяем БД для документов
        #     Document = OrderDocument if obj.document_registry == 0 else RegisterDocument
        #     # Получаем документ из задания
        #     doc = Document.objects.get(id=obj.document_id)
        #     # print(doc)
        #     # print(doc.company_set.all())
        #
        #     corrector_logs = LogEntry.objects.filter(user_id=corrector.user.id)
        #     now = datetime.now(tz=timezone.utc)
        #     today = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        #
        #     # Проверяем все компании документа на корректировку
        #     company_corrected = True
        #     for company in doc.company_set.all():
        #         # Ищем изменения в компании от этого пользователя в логах
        #         company_content_type = ContentType.objects.get(model='company')
        #         company_corrector_logs = corrector_logs.filter(content_type_id=company_content_type.id)
        #         company_corrector_logs = company_corrector_logs.filter(object_id=company.id)
        #         company_corrector_logs = company_corrector_logs.filter(action_time__gte=obj.datetime_created)
        #         if len(company_corrector_logs) == 0:
        #             company_corrected = False
        #             messages.add_message(request, messages.ERROR, f'Компания {company} не была откорректирована')
        #         # print('company_corrector_logs', company_corrector_logs)
        #         # print('company.date_corrected', company.date_corrected)
        #
        #     # print(doc.contactperson_set.all())
        #     # Проверяем все контакты компании на корректировку
        #     person_corrected = True
        #     for person in doc.contactperson_set.all():
        #         # Ищем изменения в контакте от этого пользователя в логах
        #         person_content_type = ContentType.objects.get(model='contactperson')
        #         person_corrector_logs = corrector_logs.filter(content_type_id=person_content_type.id)
        #         person_corrector_logs = person_corrector_logs.filter(object_id=person.id)
        #         person_corrector_logs = person_corrector_logs.filter(action_time__gte=obj.datetime_created)
        #         if len(person_corrector_logs) == 0:
        #             company_corrected = False
        #             messages.add_message(request, messages.ERROR, f'Контакт {person} не был откорректирован')
        #         # print('company_corrector_logs', person_corrector_logs)
        #         # print('company.date_corrected', person.date_corrected)
        #
        #     if person_corrected and company_corrected:
        #         messages.add_message(request, messages.INFO, f'Задача выполнена')
        #         obj.task_done = True
        #         corrector.score += 5
        #         corrector.tasks_done += 1
        #     else:
        #         obj.task_done = False
        #         messages.add_message(request, messages.ERROR, f'Задача не выполнена')
        #     obj.save()


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
        # if obj.is_active:
        try:
            socket_path = '/var/www/fips_parser/tasks_processor.sock'
            with Client(socket_path) as conn:
                # conn.send('self.load_tasks(5)')
                conn.send('self.need_to_refresh=True')
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

    # selected = selected or 't1.id, t1.document_image, t2.id, t2.email, t2.full_name, ' \
    #                        't2.last_name, t2.first_name, t2.middle_name'
    selected = selected or 't1.id, t1.document_image, t2.*'
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


def make_task_done(form, obj):
    today = datetime.now(tz=timezone.utc)
    obj_task_done = form.cleaned_data.get('task_done')
    obj_date_task_done = obj.date_task_done
    if obj_task_done and obj_date_task_done is None:
        obj.date_task_done = today
    obj.task_done = True


def corrector_add_score(request, obj):
    try:
        user = request.user
        corrector = user.corrector
        if obj.task_done and obj.date_task_done is None:
            today = datetime.now(tz=timezone.utc)
            delta = today - obj.datetime_created
            add_score = 5 - delta.days if delta.days < 3 else 2
            corrector.score += add_score
            corrector.save()
            messages.add_message(request, messages.INFO, f'Начислено баллов {add_score}')
            # user.save()
    except User.corrector.RelatedObjectDoesNotExist:
        pass
