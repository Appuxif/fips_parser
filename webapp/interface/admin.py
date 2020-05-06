import traceback
import sys
from django.contrib import admin, messages
from multiprocessing.connection import Client
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import User
from datetime import datetime, timezone
from django.db.models import F
import requests
# Все контакты отображаются непосредственно в документе

# from .models import OrderContact, OrderContactPerson, RegisterContact, RegisterContactPerson, ContactPerson, Company
from .models import ContactPerson, Company, RegisterCompanyRel, OrderCompanyRel, \
    ParserSetting, Proxies, EmailApiKey, EmailApiKeyLog
from interface.change_message_utils import construct_change_message

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
    readonly_fields = ( '__str__', 'user', 'action_time', 'content_type', 'object_id', 'object_repr', 'action_flag')


# Для отображения контактов в даминке компании в БД
class ContactPersonInline(admin.StackedInline):
    model = ContactPerson
    extra = 0
    view_on_site = False
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


class OrderCompanyInline(admin.StackedInline):
    model = OrderCompanyRel
    extra = 0
    readonly_fields = ('company', 'document')

    def has_add_permission(self, request, obj):
        return False


class RegisterCompanyInline(admin.StackedInline):
    model = RegisterCompanyRel
    extra = 0
    readonly_fields = ('company', 'document')

    def has_add_permission(self, request, obj):
        return False


# Отображение компании в БД
@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    inlines = [ContactPersonInline, OrderCompanyInline, RegisterCompanyInline]
    exclude = ('order', 'register')
    list_display = ('__str__', 'sign_char', 'form', 'form_correct', 'name', 'name_correct', 'address')
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


class ContactPersonOrderInline(admin.StackedInline):
    model = ContactPerson.order.through
    readonly_fields = ('contactperson', 'document')
    extra = 0

    verbose_name = 'Связанный контакт компании (Заявки)'
    verbose_name_plural = 'Связанные контакты компании (Заявки)'

    def view_on_site(self, obj):
        return f'/admin/orders/document/{obj.document_id}/change/'


class ContactPersonRegisterInline(admin.StackedInline):
    model = ContactPerson.register.through
    readonly_fields = ('contactperson', 'document')
    extra = 0

    verbose_name = 'Связанный контакт компании (Регистрации)'
    verbose_name_plural = 'Связанные контакты компании (Регистрации)'

    def view_on_site(self, obj):
        return f'/admin/registers/document/{obj.document_id}/change/'


@admin.register(ContactPerson)
class ContactPersonAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'company', 'rep_reg_number')
    exclude = ('order', 'register')
    readonly_fields = ('company', 'date_corrected')
    inlines = (ContactPersonOrderInline, ContactPersonRegisterInline)
    save_on_top = True
    fieldsets = [
        (None, {'fields': ('company', )}),
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
        (None, {'fields': ('date_corrected', )})
    ]

    def save_model(self, request, obj, form, change):
        # super(ContactPersonAdmin, self).save_model(request, obj, form, change)
        try:
            corrector = request.user.corrector
        except User.corrector.RelatedObjectDoesNotExist:
            pass
        # verify_url = 'http://api.quickemailverification.com/v1/verify?email={}&apikey={}'
        # # Верификация имейла
        # if obj.email and not obj.email_verified:
        #     now = datetime.now(tz=timezone.utc)
        #     today = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        #     api_key = EmailApiKey.objects.filter(is_valid=True)
        #     # Находим ключи, у которых есть сегодняшние логи
        #     api_key = api_key.filter(emailapikeylog__date_created__gte=today)
        #     # Если есть такие ключи, проверяем количество использований
        #     if api_key.count() != 0:
        #         api_key = api_key.filter(emailapikeylog__uses_amount__lt=F('emailapikeylog__max_amount'))
        #     api_key = api_key.first()
        #     if api_key:
        #         verify_url = verify_url.format(obj.email, api_key.api_key)
        #         r = requests.get(verify_url)
        #         print(r)
        #         log = e.emailapikeylog_set.get_or_create()
        #     else:
        #         messages.add_message(request, messages.ERROR, 'Нет доступных API ключей для верификации почты')


        obj.save()

    # Кастомное логирование при изменениях в заявках
    def construct_change_message(self, request, form, formsets, add=False):
        change_message = construct_change_message(form, formsets, add)
        return change_message


# TODO: Для отладки. Потом удалить
@admin.register(OrderCompanyRel)
class OrderCompanyRelAdmin(admin.ModelAdmin):
    readonly_fields = ('document',)


# TODO: Для отладки. Потом удалить
@admin.register(RegisterCompanyRel)
class RegisterCompanyRelAdmin(admin.ModelAdmin):
    readonly_fields = ('document',)


# TODO: Для отладки. Потом удалить
@admin.register(Proxies)
class ProxiesAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'is_banned', 'is_working', 'in_use', 'date_last_used', 'documents_parsed', 'status')
    list_editable = ('is_banned', 'is_working', 'in_use', 'status')


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
class EmailApiKeyLogInline(admin.StackedInline):
    model = EmailApiKeyLog
    extra = 0
    readonly_fields = ('api_key', 'date_created', 'uses_amount')

    def has_add_permission(self, request, obj):
        return False


@admin.register(EmailApiKey)
class EmailApiKeyAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'is_valid')
    inlines = (EmailApiKeyLogInline, )
