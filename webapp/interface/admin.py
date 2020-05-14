import traceback
import sys
import re
from django.contrib import admin, messages
from multiprocessing.connection import Client
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import User
from datetime import datetime, timezone
from django.db.models import Q, F, Count
import requests
# Все контакты отображаются непосредственно в документе

# from .models import OrderContact, OrderContactPerson, RegisterContact, RegisterContactPerson, ContactPerson, Company
from .models import ContactPerson, Company, RegisterCompanyRel, OrderCompanyRel, \
    ParserSetting, Proxies, EmailApiKey, EmailApiKeyLog
from interface.change_message_utils import construct_change_message
from .forms import AddProxyForm

# from orders.admin import CompanyInline as OrderCompanyInline
# from registers.admin import CompanyInline as RegisterCompanyInline


# @admin.register(OrderContact)
# class OrderContactAdmin(admin.ModelAdmin):
#     readonly_fields = ('order',)


# @admin.register(RegisterContact)
# class RegisterContactAdmin(admin.ModelAdmin):
#     readonly_fields = ('register', )


# @admin.register(OrderContactPerson)
# class OrderContactPersonAdmin(admin.ModelAdmin):
#     readonly_fields = ('document',)


# @admin.register(RegisterContactPerson)
# class RegisterContactPersonAdmin(admin.ModelAdmin):
#     readonly_fields = ('document', )

@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'user', 'content_type', 'action_flag', 'object_repr', 'action_time')
    exclude = ('change_message', )
    readonly_fields = ('__str__', 'user', 'action_time', 'content_type', 'object_id', 'object_repr', 'action_flag')
    search_fields = ('user__username', 'content_type__app_label', 'object_repr')


# Для отображения контактов в даминке компании в БД
class ContactPersonInline(admin.StackedInline):
    model = ContactPerson
    extra = 0
    # view_on_site = False
    template = 'admin/edit_inline/stacked_file_person.html'
    fieldsets = [
        (None, {'fields': ('category', ('job_title'), 'photo',)}),
        (None, {'fields': ('full_name', ('last_name', 'first_name', 'middle_name'),
                           ('gender',), 'bday_date'),
                'description': 'Личные данные'}),
        (None, {'fields': (('email', 'email_verified', 'email_correct'),
                           ('messenger_type', 'messenger_id', 'nick_name'),
                           ('mobile_phone', 'office_phone', 'home_phone', 'fax'),
                           'personal_web',),
                'description': 'Контактные данные'}),
        (None, {'fields': ('office_address', 'zip', ('country', 'state'),
                           ('area', 'city'), ('rep_correspondence_address', 'rep_reg_number')),
                'description': 'Адресные данные'}),
        (None, {'fields': ('date_corrected',)})
    ]
    readonly_fields = ('date_corrected',)

    # Чтобы выводить по два поля на ширину экрана
    # def get_fieldsets(self, request, obj=None):
    #     old_fields = self.get_fields(request, obj)
    #     len_old_fields = len(old_fields)
    #     fields = []
    #     for i in range(0, len_old_fields, 2):
    #         fields.append(
    #             (None, {'fields': (old_fields[i:i+2], )})
    #         )
    #
    #     return fields


# class OrderCompanyInline(admin.StackedInline):
#     model = OrderCompanyRel
#     extra = 0
#     readonly_fields = ('company', 'document')
#     max_num = 5
#
#     def has_add_permission(self, request, obj):
#         return False


# class RegisterCompanyInline(admin.StackedInline):
#     model = RegisterCompanyRel
#     extra = 0
#     readonly_fields = ('company', 'document')
#     max_num = 5
#
#     def has_add_permission(self, request, obj):
#         return False


# Отображение компании в БД
@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    # inlines = [ContactPersonInline, OrderCompanyInline, RegisterCompanyInline]
    inlines = [ContactPersonInline]
    exclude = ('order', 'register')
    list_display = ('__str__', 'sign_char', 'form_correct', 'name_correct', 'address')
    readonly_fields = ('name', 'form', 'date_corrected')
    # Шаблон, на котором добавлено лого компании
    change_form_template = 'admin/custom_change_form_company.html'
    save_on_top = True
    # def save_related(self, request, form, formsets, change):
    # def save_model(self, request, obj, form, change):

    # Кастомное логирование при изменениях в заявках
    def construct_change_message(self, request, form, formsets, add=False):
        change_message = construct_change_message(form, formsets, add)
        return change_message

    def save_related(self, request, form, formsets, change):
        super(CompanyAdmin, self).save_related(request, form, formsets, change)
        for obj in formsets[0].queryset:
            # print(obj, obj.email)
            if obj.email and not obj.email_verified:
                email_verified = verify_email(request, obj)
                obj.save()


class ContactPersonOrderInline(admin.StackedInline):
    model = ContactPerson.order.through
    readonly_fields = ('contactperson', 'document')
    extra = 0
    max_num = 5
    verbose_name = 'Связанный контакт компании (Заявки)'
    verbose_name_plural = 'Связанные контакты компании (Заявки)'

    def view_on_site(self, obj):
        return f'/admin/orders/document/{obj.document_id}/change/'


class ContactPersonRegisterInline(admin.StackedInline):
    model = ContactPerson.register.through
    readonly_fields = ('contactperson', 'document')
    extra = 0
    max_num = 5
    verbose_name = 'Связанный контакт компании (Регистрации)'
    verbose_name_plural = 'Связанные контакты компании (Регистрации)'

    def view_on_site(self, obj):
        return f'/admin/registers/document/{obj.document_id}/change/'


@admin.register(ContactPerson)
class ContactPersonAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'company', 'rep_reg_number')
    exclude = ('order', 'register')
    readonly_fields = ('company', 'date_corrected')
    # inlines = (ContactPersonOrderInline, ContactPersonRegisterInline)
    save_on_top = True
    fieldsets = [
        (None, {'fields': ('company', )}),
        (None, {'fields': ('category', ('job_title',), 'photo',)}),
        (None, {'fields': ('full_name', ('last_name', 'first_name', 'middle_name'),
                           ('gender',), 'bday_date'),
                'description': 'Личные данные'}),
        (None, {'fields': (('email', 'email_verified', 'email_correct'),
                           ('messenger_type', 'messenger_id', 'nick_name'),
                           ('mobile_phone', 'office_phone', 'home_phone', 'fax'),
                           'personal_web',),
                'description': 'Контактные данные'}),
        (None, {'fields': ('office_address', 'zip', ('country', 'state'),
                           ('area', 'city'), ('rep_correspondence_address', 'rep_reg_number')),
                'description': 'Адресные данные'}),
        (None, {'fields': ('date_corrected', )})
    ]

    def save_model(self, request, obj, form, change):
        # try:
        #     corrector = request.user.corrector
        # except User.corrector.RelatedObjectDoesNotExist:
        #     pass
        # Верификация имейла
        if obj.email and not obj.email_verified:
            email_verified = verify_email(request, obj)
        return super(ContactPersonAdmin, self).save_model(request, obj, form, change)

    # Кастомное логирование при изменениях в заявках
    def construct_change_message(self, request, form, formsets, add=False):
        change_message = construct_change_message(form, formsets, add)
        return change_message


# # TODO: Для отладки. Потом удалить
# @admin.register(OrderCompanyRel)
# class OrderCompanyRelAdmin(admin.ModelAdmin):
#     readonly_fields = ('document',)


# # TODO: Для отладки. Потом удалить
# @admin.register(RegisterCompanyRel)
# class RegisterCompanyRelAdmin(admin.ModelAdmin):
#     readonly_fields = ('document',)


@admin.register(Proxies)
class ProxiesAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'is_banned', 'is_working', 'in_use', 'date_last_used', 'documents_parsed',
                    'status', 'errors_in_a_row')
    list_editable = ('is_banned', 'is_working')
    change_list_template = 'admin/custom_change_list_proxies.html'

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        if request.method == 'POST':
            form = AddProxyForm(request.POST, request.FILES)
            if form.is_valid():
                proxies = form.cleaned_data['proxies']
                proxies = proxies.read().splitlines()
                proxies_list = []
                count_before = Proxies.objects.count()
                for proxy in proxies:
                    proxy = proxy.decode()
                    match = re.match(r'(?P<scheme>https?://)(?P<user>.*[^:]):(?P<pass>.*[^@])@'
                                     r'(?P<host>\d+\.\d+\.\d+\.\d+):(?P<port>\d+)', proxy)
                    match = match or re.match(r'(?P<scheme>https*://)(?P<host>\d+\.\d+\.\d+\.\d+):(?P<port>\d+)', proxy)
                    g = match.groupdict()
                    proxies_list.append(Proxies(**g))
                Proxies.objects.bulk_create(proxies_list, ignore_conflicts=True)
                count_after = Proxies.objects.count()
                messages.add_message(request, messages.INFO, f'Получено прокси {len(proxies)}')
                messages.add_message(request, messages.INFO, f'Добавлено новых прокси {count_after - count_before}')
        extra_context['proxy_add_form'] = AddProxyForm()
        return super(ProxiesAdmin, self).changelist_view(request, extra_context)

# Для управления парсером. Отправляет запрос на обновление конфига парсеров процессу парсингов
@admin.register(ParserSetting)
class ParserSettingAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'number_gte', 'number_lte', 'proxies_num', 'documents_parsed', 'is_working')
    list_editable = ('number_gte', 'number_lte', 'proxies_num', 'documents_parsed', 'is_working')

    def save_model(self, request, obj, form, change):
        try:
            socket_path = '/var/www/fips_parser/processor.sock'
            with Client(socket_path) as conn:
                conn.send('self.load_parsers(5)')
        except FileNotFoundError:
            print('ParserSettingAdmin save_model Сокет не найден')
        except:
            print('ParserSettingAdmin save_model Ошибка подключения')
            traceback.print_exc(file=sys.stdout)
        return super(ParserSettingAdmin, self).save_model(request, obj, form, change)


# Модели для API ключей для верификации почты
class EmailApiKeyLogInline(admin.TabularInline):
    model = EmailApiKeyLog
    extra = 0
    readonly_fields = ('api_key', 'date_created', 'email_verified', 'email_is_valid', 'result')
    ordering = ('-date_created', )
    max_num = 20

    def has_add_permission(self, request, obj):
        return False


@admin.register(EmailApiKey)
class EmailApiKeyAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'is_valid')
    inlines = (EmailApiKeyLogInline, )


@admin.register(EmailApiKeyLog)
class EmailApiKeyAdmin(admin.ModelAdmin):
    list_display = ('api_key', 'date_created', 'email_verified', 'email_is_valid')
    readonly_fields = ('api_key', 'date_created', 'email_verified', 'email_is_valid', 'result')


# Дополнительные функции

def verify_email(request, obj, ):
    verify_url = 'http://api.quickemailverification.com/v1/verify?email={}&apikey={}'
    now = datetime.now(tz=timezone.utc)
    today = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)

    api_key = EmailApiKey.objects.filter(is_valid=True)
    # Находим ключи, у которых есть сегодняшние логи
    today_logs_amount = Count('emailapikeylog', filter=Q(emailapikeylog__date_created__gte=today))
    api_key = api_key.annotate(today_logs_amount=today_logs_amount).filter(today_logs_amount__lt=95).first()
    # Если найден свободный API ключ, проводим верификацию
    if api_key:
        # print(api_key.today_logs_amount)
        verify_url = verify_url.format(obj.email, api_key.api_key)
        r = requests.get(verify_url)
        # print(r.headers.get('X-QEV-Remaining-Credits'))
        if r.status_code == 200:
            result = r.json()
            email_is_valid = result['result'] == 'valid'
            if email_is_valid:
                messages.add_message(request, messages.INFO, f'Почта {obj.email} верифицирована')
                obj.email_verified = True
            else:
                messages.add_message(request, messages.ERROR, f'Почта {obj.email} не верифицирована')
            # print(r.json())
            api_key.emailapikeylog_set.create(email_verified=obj.email,
                                              email_is_valid=email_is_valid, result=r.text[:1000])
    else:
        messages.add_message(request, messages.ERROR, 'Нет доступных API ключей для верификации почты')
        EmailApiKeyLog.objects.create(email_verified=obj.email,
                                      email_is_valid=False,
                                      result='Нет доступных API ключей для верификации почты')
    return obj.email_verified
