import traceback

import sys
from django.contrib import admin
from multiprocessing.connection import Client

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


# Для отображения контактов в даминке компании в БД
class ContactPersonInline(admin.StackedInline):
    model = ContactPerson
    extra = 0
    view_on_site = False
    template = 'admin/edit_inline/stacked_file_person.html'

    # Чтобы выводить по два поля на ширину экрана
    def get_fieldsets(self, request, obj=None):
        old_fields = self.get_fields(request, obj)
        len_old_fields = len(old_fields)
        fields = []
        for i in range(0, len_old_fields, 2):
            fields.append(
                (None, {'fields': (old_fields[i:i+2], )})
            )

        return fields


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
    # Шаблон, на котором добавлено лого компании
    change_form_template = 'admin/custom_change_form_company.html'


# TODO: Для отладки. Потом удалить
@admin.register(ContactPerson)
class ContactPersonAdmin(admin.ModelAdmin):
    pass

# TODO: Для отладки. Потом удалить
@admin.register(OrderCompanyRel)
class OrderCompanyRelAdmin(admin.ModelAdmin):
    readonly_fields = ('document', )

# TODO: Для отладки. Потом удалить
@admin.register(RegisterCompanyRel)
class RegisterCompanyRelAdmin(admin.ModelAdmin):
    readonly_fields = ('document',)

# TODO: Для отладки. Потом удалить
@admin.register(Proxies)
class ProxiesAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'is_banned', 'is_working', 'in_use', 'date_last_used', 'documents_parsed', 'status')


# Для управления парсером. Отправляет запрос на обновление конфига парсеров процессу парсингов
@admin.register(ParserSetting)
class ParserSettingAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'number_gte', 'number_lte', 'proxies_num', 'is_working')

    def save_model(self, request, obj, form, change):
        try:
            socket_path = '/var/www/fips_parser/processor.sock'
            with Client(socket_path) as conn:
                conn.send('self.load_parsers(5)')
        except FileNotFoundError:
            print('save_model Сокет не найден')
        except:
            print('save_model Ошибка подключения')
            traceback.print_exc(file=sys.stdout)
        return super(ParserSettingAdmin, self).save_model(request, obj, form, change)
