from django.contrib import admin
# from django.contrib.auth.models import User
from django.db.models import Q
# from django_admin_search.admin import AdvancedSearchAdmin

from import_export import resources
from import_export.admin import ExportActionMixin, ExportActionModelAdmin, ExportMixin

from .django_admin_search import AdvancedSearchAdmin
from .models_base import Leaf, Document, DocumentParse, DocumentFile, ServiceItem, document_parse_dict
from .models import WorkState, WorkStateRow
from .forms import LeafSearchForm, DocumentSearchForm, fields_dict
from accounts.models import UserQuery
# from interface.models import OrderContact, OrderContactPerson
from interface.models import ContactPerson, Company
from interface.change_message_utils import construct_change_message

admin.site.site_header = 'Администрирование'


class DocumentParseInLine(admin.StackedInline):
    model = DocumentParse
    extra = 0
    fields = ('status', 'order_type', 'applicant', 'address', 'copyright_holder', 'patent_atty', 'date_refreshed')
    readonly_fields = fields


class DocumentFileInLine(admin.StackedInline):
    model = DocumentFile
    fields = ('name', 'direct_url', 'link')
    readonly_fields = fields
    extra = 0
    template = 'admin/edit_inline/stacked_file.html'


# class OrderContactPersonInLine(admin.StackedInline):
#     model = OrderContactPerson
#     extra = 0
#     readonly_fields = ('document', )
#     view_on_site = False


class CompanyInline(admin.StackedInline):
    model = Company.order.through
    extra = 0
    view_on_site = False


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


@admin.register(Document)
class DocumentAdmin(ExportActionMixin, AdvancedSearchAdmin):
    change_list_template = 'admin/custom_change_list_document.html'
    search_form = DocumentSearchForm

    list_display_static = ['id', 'number', 'url', 'document_exists', 'document_parsed', 'date_parsed']
    list_display = list_display_static + []
    # list_select_related = ('documentparse', )

    # ordering = ('documentparse__date_refreshed', )
    ordering = []
    inlines = [DocumentParseInLine, DocumentFileInLine, WorkStateInLine,
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
                queries = ServiceItem.objects.select_related('document').filter(number__in=values)
                ids = [q.document.id for q in queries]
                if ids:
                    return Q(id__in=ids)
        return Q()

    def search_income_value(self, field, field_value, form_field, request, param_values):
        if field_value and field in param_values or 'income_date_gte' in param_values or 'income_date_lte' in param_values:
            queries = WorkStateRow.objects.select_related('document').filter(type='income')
            if field in param_values:
                queries = queries.filter(key__icontains=field_value)
            if 'income_date_gte' in param_values:
                value = param_values['income_date_gte'][0]
                queries = queries.filter(date__gte=value)
            if 'income_date_lte' in param_values:
                value = param_values['income_date_lte'][0]
                queries = queries.filter(date__lte=value)
            ids = [q.document.id for q in queries]
            if ids:
                return Q(id__in=ids)
        return Q()

    def search_outcome_value(self, field, field_value, form_field, request, param_values):
        if field_value and field in param_values or 'outcome_date_gte' in param_values or 'outcome_date_lte' in param_values:
            queries = WorkStateRow.objects.select_related('document').filter(type='outcome')
            if field in param_values:
                queries = queries.filter(key__icontains=field_value)
            if 'outcome_date_gte' in param_values:
                value = param_values['outcome_date_gte'][0]
                queries = queries.filter(date__gte=value)
            if 'outcome_date_lte' in param_values:
                value = param_values['outcome_date_lte'][0]
                queries = queries.filter(date__lte=value)
            ids = [q.document.id for q in queries]
            if ids:
                return Q(id__in=ids)
        return Q()

    def search_income_date_gte(self, field, field_value, form_field, request, param_values):
        return Q()
    def search_income_date_lte(self, field, field_value, form_field, request, param_values):
        return Q()
    def search_outcome_date_gte(self, field, field_value, form_field, request, param_values):
        return Q()
    def search_outcome_date_lte(self, field, field_value, form_field, request, param_values):
        return Q()


class ServiceItemInLine(admin.TabularInline):
    model = ServiceItem
    fields = ('text', )
    readonly_fields = fields
    extra = 0


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


@admin.register(WorkState)
class WorkStateAdmin(admin.ModelAdmin):
    list_display = ('id', '__str__', 'document', 'document_parse')
    exclude = ['document']
    inlines = [WorkStateRowInLine]
    select_related = ('document', 'document_parse')


class DocumentInLine(admin.StackedInline):
    model = Document
    extra = 0
    fields = ('url', 'document_exists', 'document_parsed')
    readonly_fields = fields
    ordering = ('number', )


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


# Функции ################################################################

# Добавляет логику выдачи дополнительных столбцов для связанных объектов
def documentparse_lookup(item, document_parse_dict):
    keys = item.split('__')[1:]
    def func(obj):
        object = obj.documentparse
        for k in keys:
            if object is None:
                break
            object = getattr(object, k, None)
        str_type = str(type(object))
        if str_type == "<class 'function'>" or str_type == "<class 'method'>":
            return object()
        return object
    func.short_description = document_parse_dict['field__' + item]['string']
    return func


# Генерация класса "ресурсов" для формирования файла экспорта
def get_export_resource(model, fields, document_parse_dict):
    resource_class = resources.ModelResource

    # Некоторые столбцы неизбежно придется пропускать, так как они несут информативный характер
    attrs = {'model': model, 'fields': tuple((f for f in fields if '_set' not in f))}
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
