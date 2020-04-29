from django.forms import ModelForm, Form
from django.forms import DateField, CharField, ChoiceField, TextInput, IntegerField, BooleanField

from .models_base import Leaf, Document, DocumentParse, DocumentFile, ServiceItem


class LeafSearchForm(Form):
    name = CharField(required=False, widget=TextInput(
        attrs={
            'filter_method': '__icontains',
        }
    ))


# Форма поиска на странице /admin/registers/documentparse/
class DocumentParseSearchForm(Form):
    order_number_gte = CharField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'order_number',
            'filter_method': '__gte',
        }
    ))

    order_number_lte = CharField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'order_number',
            'filter_method': '__lte',
        }
    ))

    first_order_number_gte = CharField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'first_order_number',
            'filter_method': '__gte',
        }
    ))

    first_order_number_lte = CharField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'first_order_number',
            'filter_method': '__lte',
        }
    ))

    order_register_number_gte = CharField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'order_register_number',
            'filter_method': '__gte',
        }
    ))

    order_register_number_lte = CharField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'order_register_number',
            'filter_method': '__lte',
        }
    ))

    applicant = CharField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'applicant',
            'filter_method': '__icontains',
        }
    ))

    address = CharField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'address',
            'filter_method': '__icontains',
        }
    ))

    copyright_holder = CharField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'copyright_holder',
            'filter_method': '__icontains',
        }
    ))

    patent_atty = CharField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'patent_atty',
            'filter_method': '__icontains',
        }
    ))

    date_refreshed_lte = DateField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'date_refreshed',
            'filter_method': '__lte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))
    date_refreshed_gte = DateField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'date_refreshed',
            'filter_method': '__gte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))

    date_created_lte = DateField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'date_created',
            'filter_method': '__lte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))
    date_created_gte = DateField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'date_created',
            'filter_method': '__gte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))

    date_publish_lte = DateField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'date_publish',
            'filter_method': '__lte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))
    date_publish_gte = DateField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'date_publish',
            'filter_method': '__gte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))

    date_exclusive_lte = DateField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'date_exclusive',
            'filter_method': '__lte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))
    date_exclusive_gte = DateField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'date_exclusive',
            'filter_method': '__gte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))

    date_gos_reg_lte = DateField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'date_gos_reg',
            'filter_method': '__lte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))

    date_gos_reg_gte = DateField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'date_gos_reg',
            'filter_method': '__gte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))

    date_changes_lte = DateField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'date_changes',
            'filter_method': '__lte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))

    date_changes_gte = DateField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'date_changes',
            'filter_method': '__gte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))

    def __init__(self, *args, **kwargs):
        super(DocumentParseSearchForm, self).__init__(*args, **kwargs)
        for key in self.fields:
            self.fields[key].label = fields_dict[key]


class DocumentSearchForm(Form):
    # number = IntegerField(required=False)
    document_exists = BooleanField(required=False)
    document_parsed = BooleanField(required=False)

    date_parsed_lte = DateField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'date_parsed',
            'filter_method': '__lte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))
    date_parsed_gte = DateField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'date_parsed',
            'filter_method': '__gte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))

    order_number_gte = CharField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'documentparse__order_number',
            'filter_method': '__gte',
        }
    ))

    order_number_lte = CharField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'documentparse__order_number',
            'filter_method': '__lte',
            # 'filter_method': '__icontains',
        }
    ))

    first_order_number_gte = CharField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'documentparse__first_order_number',
            'filter_method': '__gte',
        }
    ))

    first_order_number_lte = CharField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'documentparse__first_order_number',
            'filter_method': '__lte',
        }
    ))

    order_register_number_gte = CharField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'documentparse__order_register_number',
            'filter_method': '__gte',
        }
    ))


    order_register_number_lte = CharField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'documentparse__order_register_number',
            'filter_method': '__lte',
        }
    ))

    applicant = CharField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'documentparse__applicant',
            'filter_method': '__icontains',
        }
    ))

    address = CharField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'documentparse__address',
            'filter_method': '__icontains',
        }
    ))

    copyright_holder = CharField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'documentparse__copyright_holder',
            'filter_method': '__icontains',
        }
    ))

    patent_atty = CharField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'documentparse__patent_atty',
            'filter_method': '__icontains',
        }
    ))

    date_refreshed_lte = DateField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'documentparse__date_refreshed',
            'filter_method': '__lte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))
    date_refreshed_gte = DateField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'documentparse__date_refreshed',
            'filter_method': '__gte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))

    date_created_lte = DateField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'documentparse__date_created',
            'filter_method': '__lte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))
    date_created_gte = DateField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'documentparse__date_created',
            'filter_method': '__gte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))

    date_publish_lte = DateField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'documentparse__date_publish',
            'filter_method': '__lte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))
    date_publish_gte = DateField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'documentparse__date_publish',
            'filter_method': '__gte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))

    date_exclusive_lte = DateField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'documentparse__date_exclusive',
            'filter_method': '__lte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))
    date_exclusive_gte = DateField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'documentparse__date_exclusive',
            'filter_method': '__gte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))

    date_gos_reg_lte = DateField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'documentparse__date_gos_reg',
            'filter_method': '__lte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))

    date_gos_reg_gte = DateField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'documentparse__date_gos_reg',
            'filter_method': '__gte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))

    date_changes_lte = DateField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'documentparse__date_changes',
            'filter_method': '__lte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))

    date_changes_gte = DateField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'documentparse__date_changes',
            'filter_method': '__gte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))

    service_items_list = CharField(required=False, widget=TextInput(
        attrs={
            # 'filter_field': 'documentparse__serviceitem_set',
            'filter_method': '__in',
            'placeholder': 'comma separated'
        }
    ))

    documentizv_izv_type = CharField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'izv__izv_type',
            'filter_method': '__icontains'
        }
    ))

    documentizv_address = CharField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'izv__address',
            'filter_method': '__icontains'
        }
    ))

    documentizv_last_copyright_holder = CharField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'izv__last_copyright_holder',
            'filter_method': '__icontains'
        }
    ))

    documentizv_last_copyright_holder_name = CharField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'izv__last_copyright_holder_name',
            'filter_method': '__icontains'
        }
    ))

    documentizv_copyright_holder = CharField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'izv__copyright_holder',
            'filter_method': '__icontains'
        }
    ))

    documentizv_transferor = CharField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'izv__transferor',
            'filter_method': '__icontains'
        }
    ))

    documentizv_contract_type = CharField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'izv__contract_type',
            'filter_method': '__icontains'
        }
    ))

    documentizv_contract_terms = CharField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'izv__contract_terms',
            'filter_method': '__icontains'
        }
    ))

    documentizv_grantor = CharField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'izv__grantor',
            'filter_method': '__icontains'
        }
    ))

    documentizv_granted = CharField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'izv__granted',
            'filter_method': '__icontains'
        }
    ))

    documentizv_licensee = CharField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'izv__licensee',
            'filter_method': '__icontains'
        }
    ))

    documentizv_sublicensee = CharField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'izv__sublicensee',
            'filter_method': '__icontains'
        }
    ))

    documentizv_date_changes_lte = DateField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'izv__date_changes',
            'filter_method': '__lte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))

    documentizv_date_changes_gte = DateField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'izv__date_changes',
            'filter_method': '__gte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))

    documentizv_date_publish_lte = DateField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'izv__date_publish',
            'filter_method': '__lte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))

    documentizv_date_publish_gte = DateField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'izv__date_publish',
            'filter_method': '__gte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))

    documentizv_date_renewal_lte = DateField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'izv__date_renewal',
            'filter_method': '__lte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))

    documentizv_date_renewal_gte = DateField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'izv__date_renewal',
            'filter_method': '__gte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))

    izvitem_key = CharField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'izvitem__key',
            'filter_method': '__icontains'
        }
    ))

    izvitem_date_lte = DateField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'izvitem__date',
            'filter_method': '__lte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))

    izvitem_date_gte = DateField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'izv__date_renewal',
            'filter_method': '__gte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))

    documentizv_service_items_list = CharField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'izv__service_items',
            'filter_method': '__in',
            'placeholder': 'comma separated'
        }
    ))

    def __init__(self, *args, **kwargs):
        super(DocumentSearchForm, self).__init__(*args, **kwargs)
        for key in self.fields:
            self.fields[key].label = fields_dict[key]


fields_dict = {
    'date_refreshed_gte': 'Дата обновления. >= ',
    'date_refreshed_lte': 'Дата обновления. <=',
    'date_parsed_gte': 'Дата парсинга. >=',
    'date_parsed_lte': 'Дата парсинга. <=',
    'date_created_gte': 'Дата поступления заявки. >=',
    'date_created_lte': "Дата поступления заявки. <=",
    'date_publish_gte': "Дата публикации заявки. >= ",
    'date_publish_lte': "Дата публикации заявки. <=",
    'date_gos_reg_gte': "Дата государственной регистрации. >= ",
    'date_gos_reg_lte': "Дата государственной регистрации. <=",
    'date_exclusive_gte': "Дата истечения срока. >= ",
    'date_exclusive_lte': "Дата истечения срока. <=",
    'date_changes_gte': "Дата внесения записи. >= ",
    'date_changes_lte': "Дата внесения записи. <=",

    'applicant': "Заявитель",
    'address': "Адрес для переписки",
    'copyright_holder': "Правообладатель",
    'patent_atty': "Патентный поверенный",
    'order_number_gte': "Номер заявки. >=",
    'order_number_lte': "Номер заявки. <=",
    'first_order_number_gte': "Номер 1-й заявки. >=",
    'first_order_number_lte': "Номер 1-й заявки. <=",
    'order_register_number_gte': "Номер регистрации. >=",
    'order_register_number_lte': "Номер регистрации. <=",
    'document_exists': "Наличие документа",
    'document_parsed': "Документ спарсен",
    'service_items_list': "Классы МКТУ",

    'documentizv_izv_type': "Тип извещения",
    'documentizv_address': "Извещения. Адресс для переписки",
    'documentizv_last_copyright_holder': "Извещения. Прежний правообладатель",
    'documentizv_last_copyright_holder_name': "Извещения. Прежнее наименование",
    'documentizv_copyright_holder': "Извещения. Правообладатель",
    'documentizv_transferor': "Извещения. Передающий права",
    'documentizv_contract_type': "Извещения. Вид договора",
    'documentizv_contract_terms': "Извещения. Условия договора",
    'documentizv_grantor': "Извещения. Предоставляющий право использования",
    'documentizv_granted': "Извещения. Принимающий право использования",
    'documentizv_licensee': "Извещения. Лицензиат",
    'documentizv_sublicensee': "Извещения. Сублицензиат",
    'documentizv_date_changes_lte': "Извещения. Дата внесения записи <=",
    'documentizv_date_changes_gte': "Извещения. Дата внесения записи >=",
    'documentizv_date_publish_lte': "Извещения. Дата публикации <=",
    'documentizv_date_publish_gte': "Извещения. Дата публикации >=",
    'documentizv_date_renewal_lte': "Извещения. Дата продления <=",
    'documentizv_date_renewal_gte': "Извещения. Дата продления >=",
    'documentizv_service_items_list': "Извещения. Классы МКТУ >=",
    'izvitem_key': "Извещения. Другое поле",
    'izvitem_date_lte': "Извещения. Дата в другом поле <=",
    'izvitem_date_gte': "Извещения. Дата в другом поле >=",

}
