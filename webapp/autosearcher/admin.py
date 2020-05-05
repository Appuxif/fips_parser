import traceback

import sys
from django.contrib import admin, messages
from django.db.models import Q
from multiprocessing.connection import Client

from .models import AutoSearchTask, AutoSearchTaskItem, OrderDocument, RegisterDocument, Corrector, CorrectorTask
# from interface.models import OrderDocument, RegisterDocument,
# from orders.models_base import Document as OrderDocument
# from registers.models_base import Document as RegisterDocument

# Register your models here.


def get_q_from_queryset(queryset):
    q = Q()
    for item in queryset:
        if item.filter_method == '__in':
            if ', ' in item.filter_value:
                item.filter_value = [it for it in item.filter_value.split(', ')]
            else:
                item.filter_value = [it for it in item.filter_value.split(',')]
        filter_field = item.filter_field_raw or item.filter_field
        filter_method = item.filter_method_raw or item.filter_method
        if item.except_field:
            q &= ~Q(**{filter_field + filter_method: item.filter_value})
        else:
            q &= Q(**{filter_field + filter_method: item.filter_value})
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


@admin.register(AutoSearchTask)
class AutoSearchTaskAdmin(admin.ModelAdmin):
    inlines = (AutoSearchTaskItemInline, )
    list_display = ('__str__', 'registry_type', 'next_action', 'last_launch', 'auto_renew')

    def save_related(self, request, form, formsets, change):
        super(AutoSearchTaskAdmin, self).save_related(request, form, formsets, change)
        queryset = get_task_queryset(form, formsets)
        c = queryset.count()
        messages.add_message(request, messages.INFO, 'Найдено ' + str(c) + ' документов')

    def save_model(self, request, obj, form, change):
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


class CorrectorTaskInline(admin.StackedInline):
    model = CorrectorTask
    extra = 0
    readonly_fields = ('datetime_created', 'date_created')
    # def has_add_permission(self, request, obj):
    #     return False


@admin.register(Corrector)
class CorrectorAdmin(admin.ModelAdmin):
    inlines = (CorrectorTaskInline, )
