import sys
from django.contrib import admin
# from django.contrib.auth.models import User
from django.db.models import Q
# from django_admin_search.admin import AdvancedSearchAdmin
from django.urls import reverse

from import_export import resources
from import_export.admin import ExportActionMixin, ExportActionModelAdmin, ExportMixin

from .django_admin_search import AdvancedSearchAdmin
from .models_base import Leaf, Document, DocumentParse, DocumentFile, ServiceItem, document_parse_dict
from .models import WorkState, WorkStateRow, ParserHistory
from .forms import LeafSearchForm, DocumentSearchForm, fields_dict, income_choices, outcome_choices
from accounts.models import UserQuery
# from interface.models import OrderContact, OrderContactPerson
from interface.models import ContactPerson, Company, OrderCompanyRel
from interface.change_message_utils import construct_change_message

admin.site.site_header = 'Администрирование'


class DocumentParseInLine(admin.StackedInline):
    model = DocumentParse
    extra = 0
    fields = ('status', 'order_type', 'applicant', 'address', 'copyright_holder', 'patent_atty', 'date_refreshed')
    readonly_fields = fields

    def has_add_permission(self, request, obj):
        return False


class DocumentFileInLine(admin.StackedInline):
    model = DocumentFile
    fields = ('name', 'direct_url', 'link')
    readonly_fields = fields
    extra = 0
    template = 'admin/edit_inline/stacked_file.html'

    def has_add_permission(self, request, obj):
        return False


# class OrderContactPersonInLine(admin.StackedInline):
#     model = OrderContactPerson
#     extra = 0
#     readonly_fields = ('document', )
#     view_on_site = False


class CompanyInline(admin.StackedInline):
    # Такой же есть в interface\admin.py
    model = OrderCompanyRel
    # model = Document.company_set.rel.through
    extra = 0
    readonly_fields = ('company', 'order')

    def view_on_site(self, obj):
        return f'/admin/interface/company/{obj.id}/change/'

    # def has_add_permission(self, request, obj):
    #     return False


# class OrderContactInLine(admin.StackedInline):
#     model = OrderContact
#     extra = 0
#     fields = ('company_name', 'company_address')
#     readonly_fields = ('order', )
#     view_on_site = False


class WorkStateInLine(admin.TabularInline):
    model = WorkState
    fields = ['income', 'outcome']
    readonly_fields = fields
    extra = 0

    def has_add_permission(self, request, obj):
        return False


class ServiceItemInLine(admin.TabularInline):
    model = ServiceItem
    fields = ('text', )
    readonly_fields = fields
    extra = 0

    def has_add_permission(self, request, obj):
        return False


@admin.register(Document)
class DocumentAdmin(ExportActionMixin, AdvancedSearchAdmin):
    change_list_template = 'admin/custom_change_list_document.html'
    search_form = DocumentSearchForm

    list_display_static = ['id', 'number', 'url', 'document_exists', 'document_parsed', 'date_parsed']
    list_display = list_display_static + []
    # list_select_related = ('documentparse', )

    # ordering = ('documentparse__date_refreshed', )
    ordering = []
    inlines = [DocumentParseInLine, ServiceItemInLine, DocumentFileInLine, WorkStateInLine,
               # OrderContactInLine, OrderContactPersonInLine]
               # OrderContactPersonInLine]  # TODO: Удалить OrderContactPersonInLine
               CompanyInline]

    fieldsets = (
        (None, {'fields': (('leaf', 'number'),)}),
        (None, {'fields': ('url', )}),
        (None, {'fields': ('document_exists', ('document_parsed', 'date_parsed'), 'order_done')}),
    )
    readonly_fields = ('leaf', 'number', 'url', 'document_exists', 'document_parsed', 'date_parsed')

    sortable_by = ()

    # list_filter = ('document_exists', 'document_parsed', 'documentparse__id')

    # Если в переменной list_display появляется кастомное поле для объекта documentparse
    def __getattr__(self, item):
        if item.startswith('documentparse'):
            return documentparse_lookup(item, document_parse_dict)
        return super(DocumentAdmin, self).__getattr__(item)

    # Кастомное логирование при изменениях в заявках
    def construct_change_message(self, request, form, formsets, add=False):
        change_message = construct_change_message(form, formsets, add)
        return change_message

    # Кастомная обработка страницы /admin/orders/document/
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        request.GET._mutable = True

        # Пользовательские настройки таблицы
        user_query = UserQuery.objects.get_or_create(user=request.user)[0]
        list_display = user_query.order_document_list
        list_display = list_display.split(',') if list_display else self.list_display_static
        ordering = user_query.order_document_ordering
        ordering = ordering.split(',') if ordering else []
        # ordering = []
        # list_display = []

        # Подстройка экспорта таблицы
        action = request.POST.get('action')
        if action and action == 'export_admin_action':
            self.resource_class = get_export_resource(self.model, list_display, document_parse_dict)

        # Обработка нажатий на кнопки
        if request.method == 'POST':
            process_buttons(self, request, list_display, ordering, document_parse_dict)

        request.GET._mutable = False
        self.list_display = list_display
        self.ordering = ordering
        user_query.order_document_list = ','.join(list_display)
        user_query.order_document_ordering = ','.join(ordering)
        user_query.save()
        extra_context['document_parse_dict'] = document_parse_dict
        extra_context['displayed_list'] = {'field__' + l: document_parse_dict['field__' + l] for l in self.list_display}
        extra_context['ordering_list'] = [
            [('↓ ' if '-' in order[0] else '↑ ') + document_parse_dict['field__' + order.replace('-', '')]['string'],
             order.replace('-', '')]
            for order in ordering
        ]
        return super().changelist_view(request, extra_context=extra_context)

    def search_service_items_list(self, field, field_value, form_field, request, param_values):
        if field_value and field in param_values:
            values = field_value.split(',')
            if values:
                return Q(serviceitem__number__in=values)
        return Q()

    def search_income_value(self, field, field_value, form_field, request, param_values):
        field_value = ([v[1] for v in income_choices if str(v[0]) == field_value] or [None])[0]
        if field_value and field in param_values:
            return Q(workstaterow__type='income') & Q(workstaterow__key__icontains=field_value)
        return Q()

    def search_outcome_value(self, field, field_value, form_field, request, param_values):
        field_value = ([v[1] for v in income_choices if str(v[0]) == field_value] or [None])[0]
        if field_value and field in param_values:
            return Q(workstaterow__type='outcome') & Q(workstaterow__key__icontains=field_value)
        return Q()

    def search_income_date_gte(self, field, field_value, form_field, request, param_values):
        if field_value and field in param_values:
            return Q(workstaterow__type='income') & Q(workstaterow__date__gte=field_value)
        return Q()

    def search_income_date_lte(self, field, field_value, form_field, request, param_values):
        if field_value and field in param_values:
            return Q(workstaterow__type='income') & Q(workstaterow__date__lte=field_value)
        return Q()

    def search_outcome_date_gte(self, field, field_value, form_field, request, param_values):
        if field_value and field in param_values:
            return Q(workstaterow__type='outcome') & Q(workstaterow__date__gte=field_value)
        return Q()

    def search_outcome_date_lte(self, field, field_value, form_field, request, param_values):
        if field_value and field in param_values:
            return Q(workstaterow__type='outcome') & Q(workstaterow__date__lte=field_value)
        return Q()


@admin.register(DocumentParse)
class DocumentParseAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'order_number', 'order_register_number', 'date_refreshed',
        'date_created', 'date_publish', 'date_exclusive'
    )
    exclude = ['document']
    inlines = [ServiceItemInLine, DocumentFileInLine, WorkStateInLine]

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.opts.local_fields]


class WorkStateRowInLine(admin.TabularInline):
    model = WorkStateRow
    fields = ('type', 'key', 'date')
    readonly_fields = fields
    exclude = ['document']
    extra = 0

    def has_add_permission(self, request, obj):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(WorkState)
class WorkStateAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('id', '__str__', 'document', 'document_parse')
    exclude = ('document', )
    fields = ('document_parse', ('income', 'outcome'))
    readonly_fields = ('document_parse', 'income', 'outcome')
    inlines = [WorkStateRowInLine]
    # select_related = ('document', 'document_parse')


class DocumentInLine(admin.StackedInline):
    model = Document
    extra = 0
    fields = ('url', 'document_exists', 'document_parsed')
    readonly_fields = fields
    ordering = ('number', )

    def has_add_permission(self, request, obj):
        return False


@admin.register(Leaf)
class LeafAdmin(AdvancedSearchAdmin):
    search_form = LeafSearchForm
    list_display = ('id', 'name', 'documents')
    exclude = ['a_href_steps']
    inlines = [DocumentInLine]
    # search_fields = ['id', 'name']

    def documents(self, obj):
        return f'{obj.document_set.count()}'
    documents.short_description = 'Количество документов'


@admin.register(ParserHistory)
class ParserHistoryAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'is_error', 'date_created')
    exclude = ('document',)

# Функции ################################################################

# Добавляет логику выдачи дополнительных столбцов для связанных объектов
def documentparse_lookup(item, document_parse_dict):
    keys = item.split('__')[1:]
    def func(obj):
        object = obj.documentparse
        for k in keys:
            if object is None:
                break
            # Только для отображения ссылок изображений
            if k == 'links':
                # object = '\n'.join([o.link for o in object.filter(name="image").first()])
                object = object.filter(name="image").first()
                if object:
                    # <a href="{{ inline_admin_form.original.link }}" target="_blank"><img src="{{ inline_admin_form.original.link }}" alt="file" width="150px"></a>
                    object = f'{object.link}'
                    # object = f'<a href="{object.link}" target="_blank"><img src="{object.link}" alt="file" width="100px"></a>'
            else:
                object = getattr(object, k, None)
        str_type = str(type(object))
        if callable(object) or str_type == "<class 'function'>" or str_type == "<class 'method'>":
            return object()
        return object
    func.short_description = document_parse_dict['field__' + item]['string']
    return func


# Генерация класса "ресурсов" для формирования файла экспорта
def get_export_resource(model, fields, document_parse_dict):
    resource_class = resources.ModelResource

    # Некоторые столбцы неизбежно придется пропускать, так как они несут информативный характер
    attrs = {'model': model, 'fields': tuple([f for f in fields if '_set' not in f])}
    Meta = type(str('Meta'), (object,), attrs)

    class_name = model.__name__ + str('Resource')
    class_attrs = {
        'Meta': Meta,
    }
    metaclass = resources.ModelDeclarativeMetaclass(class_name, (resource_class,), class_attrs)

    # Объявление имен столбцов
    for f in metaclass.fields:
        metaclass.fields[f].column_name = document_parse_dict['field__' + f]['string']
    return metaclass


# Обработка нажатий на кнопки на странице /admin/orders/document/
def process_buttons(self, request, list_display, ordering, document_parse_dict):
    list_display_ordered = []
    apply_cols_pressed = 'apply_cols' in request.POST
    # Обработка поступаемых данных в POST запросе
    for key in list(request.POST.keys()):
        if key == 'clear_table':
            list_display.clear()
            list_display.extend(getattr(self, 'list_display_static', []) + [])
            ordering.clear()
            break
        elif key == 'clear_search':
            self.advanced_search_fields = {}
        elif key == 'clear_ordering':
            ordering.clear()
        elif key.startswith('del_'):
            num = int(key.split('_')[1])
            try:
                list_display.pop(num)
            except IndexError:
                pass
        elif key.startswith('col_'):
            num = int(key.split('_')[1])
            value = list_display[num]
            if value in ordering:
                ordering.remove(value)
                ordering.append('-' + value)
            elif '-' + value in ordering:
                ordering.remove('-' + value)
                ordering.append(value)
            else:
                if document_parse_dict['field__' + value]['ordering']:
                    ordering.append('-' + value)
        elif key == 'apply_cols':
            list_display.clear()
        # Подготовка столбцов для вывода на странице, если нажата кнопка
        elif apply_cols_pressed and key.startswith('field__'):
            value = key.split('field__')[1]
            if value not in list_display:
                list_display_ordered.append((value, int(request.POST[key])))
        # Подготовка порядка сортировки столбцов таблицы
        elif key.startswith('ordering__'):
            value = key.split('ordering__')[1]
            if value in ordering:
                ordering.remove(value)
            elif '-' + value in ordering:
                ordering.remove('-' + value)
    list_display_ordered = sorted(list_display_ordered, key=lambda x: x[1])
    # print(list_display_ordered)
    list_display.extend([x[0] for x in list_display_ordered])
