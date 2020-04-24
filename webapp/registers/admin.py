from django.contrib import admin
# from django.contrib.auth.models import User
from django.db.models import Q
# from django_admin_search.admin import AdvancedSearchAdmin

from import_export import resources
from import_export.admin import ExportActionMixin, ExportActionModelAdmin, ExportMixin

from orders.django_admin_search import AdvancedSearchAdmin
from orders.admin import process_buttons, get_export_resource, documentparse_lookup
from .models_base import Leaf, Document, DocumentParse, DocumentFile, ServiceItem, document_parse_dict
from .models import IzvServiceItem, DocumentIzvItem, DocumentIzv
from .forms import LeafSearchForm, DocumentSearchForm, DocumentParseSearchForm, fields_dict
from accounts.models import UserQuery
from interface.models import RegisterContact, RegisterContactPerson


class DocumentParseInLine(admin.StackedInline):
    model = DocumentParse
    extra = 0
    fields = ('status', 'order_type', 'applicant', 'address', 'copyright_holder', 'date_refreshed')
    readonly_fields = fields


class RegisterContactPersonInLine(admin.StackedInline):
    model = RegisterContactPerson
    extra = 0
    fields = ('company_name', 'company_address')
    readonly_fields = ('document', )


class RegisterContactInLine(admin.StackedInline):
    model = RegisterContact
    extra = 0
    fields = ('company_name', 'company_address')
    readonly_fields = ('register', )


@admin.register(Document)
class DocumentAdmin(ExportActionMixin, AdvancedSearchAdmin):
    change_list_template = 'admin/custom_change_list_document.html'
    search_form = DocumentSearchForm

    list_display_static = ['id', 'number', 'url', 'document_exists', 'document_parsed', 'date_parsed']
    list_display = list_display_static + []
    # list_select_related = ('documentparse', )

    # ordering = ('documentparse__date_refreshed', )
    ordering = []
    inlines = [DocumentParseInLine, RegisterContactInLine, RegisterContactPersonInLine]

    fieldsets = (
        (None, {'fields': (('leaf', 'number'),)}),
        (None, {'fields': ('url', )}),
        (None, {'fields': ('document_exists', ('document_parsed', 'date_parsed'), 'order_done')})
    )
    readonly_fields = ('leaf', 'number', 'url', 'document_exists', 'document_parsed', 'date_parsed')
    sortable_by = ()

    # list_filter = ('document_exists', 'document_parsed', 'documentparse__id')

    # Если в переменной list_display появляется кастомное поле для объекта documentparse
    def __getattr__(self, item):
        if item.startswith('documentparse'):
            return documentparse_lookup(item, document_parse_dict)
        return super(DocumentAdmin, self).__getattr__(item)

    # Кастомная обработка страницы /admin/orders/document/
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        request.GET._mutable = True

        # Пользовательские настройки таблицы
        user_query = UserQuery.objects.get_or_create(user=request.user)[0]
        list_display = user_query.register_document_list
        list_display = list_display.split(',') if list_display else self.list_display_static
        ordering = user_query.register_document_ordering
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
        user_query.register_document_list = ','.join(list_display)
        user_query.register_document_ordering = ','.join(ordering)
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
                # queries = ServiceItem.objects.select_related('document').filter(number__in=values)
                # ids = [q.document.id for q in queries]
                # if ids:
                #     return Q(id__in=ids)
                return Q(serviceitem__number__in=values)
        return Q()

    def search_documentizv_service_items_list(self, field, field_value, form_field, request, param_values):
        if field_value and field in param_values:
            values = field_value.split(',')
            if values:
                queries = IzvServiceItem.objects.select_related('document').filter(number__in=values)
                ids = [q.document.id for q in queries]
                if ids:
                    return Q(id__in=ids)
        return Q()


class ServiceItemInLine(admin.StackedInline):
    model = ServiceItem
    exclude = ['document']
    extra = 0


class DocumentFileInLine(admin.StackedInline):
    model = DocumentFile
    exclude = ['document']
    extra = 0


class DocumentIzvInLine(admin.StackedInline):
    model = DocumentIzv
    fields = ('date_publish', )
    # exclude = ['document']
    readonly_fields = fields
    extra = 0


@admin.register(DocumentParse)
# class DocumentParseAdmin(AdvancedSearchAdmin):
class DocumentParseAdmin(admin.ModelAdmin):
    # change_list_template = 'admin/custom_change_list_document.html'
    # search_form = DocumentParseSearchForm

    list_display = ('id', 'order_number', 'order_register_number', 'date_refreshed', 'date_created', 'date_publish', 'date_exclusive')
    exclude = ['document']
    inlines = [ServiceItemInLine, DocumentFileInLine, DocumentIzvInLine]

    # Кастомная обработка страницы /admin/orders/document/
    # def changelist_view(self, request, extra_context=None):
    #     extra_context = extra_context or {}
    #
    #     # Обработка нажатий на кнопки
    #     process_buttons(self, request, [], [])
    #
    #     # extra_context['document_parse_dict'] = document_parse_dict
    #     # extra_context['displayed_list'] = ['field__' + l for l in self.list_display]
    #     # extra_context['ordering_list'] = [
    #     #     [('↓ ' if '-' in order[0] else '↑ ') + document_parse_dict['field__' + order.replace('-', '')]['string'],
    #     #      order.replace('-', '')]
    #     #     for order in ordering
    #     # ]
    #     return super().changelist_view(request, extra_context=extra_context)


class DocumentIzvItemInline(admin.StackedInline):
    model = DocumentIzvItem
    fields = ('full_text', )
    readonly_fields = fields
    extra = 0


@admin.register(DocumentIzv)
class DocumentIzvAdmin(admin.ModelAdmin):
    list_display = ('id', 'document', 'izv_type', 'date_publish')
    exclude = ['document', 'unique_field']
    inlines = [DocumentIzvItemInline]


@admin.register(DocumentIzvItem)
class DocumentIzvAdmin(admin.ModelAdmin):
    list_display = ('id', 'document', 'document_izv', 'key', 'date')
    exclude = ['document']

# class WorkStateRowInLine(admin.TabularInline):
#     model = WorkStateRow
#     fields = ('type', 'key', 'date')
#     readonly_fields = fields
#     exclude = ['document']
#     extra = 0
#
#
# @admin.register(WorkState)
# class WorkStateAdmin(admin.ModelAdmin):
#     list_display = ('id', '__str__', 'document', 'document_parse')
#     exclude = ['document']
#     inlines = [WorkStateRowInLine]
#     select_related = ('document', 'document_parse')


class DocumentInLine(admin.StackedInline):
    model = Document
    extra = 0
    fields = ('url', 'document_exists', 'document_parsed')
    readonly_fields = fields
    ordering = ('number', )


@admin.register(Leaf)
# class LeafAdmin(AdvancedSearchAdmin):
class LeafAdmin(admin.ModelAdmin):
    # search_form = LeafSearchForm
    list_display = ('id', 'name', 'documents')
    exclude = ['a_href_steps']
    inlines = [DocumentInLine]
    # search_fields = ['id', 'name']

    def documents(self, obj):
        return f'{obj.document_set.count()}'
    documents.short_description = 'Количество документов'
