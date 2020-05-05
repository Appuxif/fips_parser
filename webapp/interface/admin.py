import traceback
import sys
from django.contrib import admin
from multiprocessing.connection import Client
from django.contrib.admin.models import LogEntry
# Все контакты отображаются непосредственно в документе

# from .models import OrderContact, OrderContactPerson, RegisterContact, RegisterContactPerson, ContactPerson, Company
from .models import ContactPerson, Company, RegisterCompanyRel, OrderCompanyRel, ParserSetting, Proxies


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
    ]
    # readonly_fields = ('company',)

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
    readonly_fields = ('name', 'form')
    # Шаблон, на котором добавлено лого компании
    change_form_template = 'admin/custom_change_form_company.html'


# TODO: Для отладки. Потом удалить
@admin.register(ContactPerson)
class ContactPersonAdmin(admin.ModelAdmin):
    pass


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
