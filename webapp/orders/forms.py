from django.forms import ModelForm, Form
from django.forms import DateField, CharField, ChoiceField, TextInput, IntegerField, BooleanField

from .models_base import Leaf, Document, DocumentParse, DocumentFile, ServiceItem


class LeafSearchForm(Form):
    name = CharField(required=False, widget=TextInput(
        attrs={
            'filter_method': '__icontains',
        }
    ))


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

    service_items_values = CharField(required=False, widget=TextInput(
        attrs={
            'filter_field': 'serviceitem__text',
            'filter_method': '__icontains',
            # 'placeholder': 'comma separated'
        }
    ))

    # work_state_value = CharField(required=False, widget=TextInput(
    #     attrs={
    #         # 'filter_field': 'documentparse__serviceitem_set',
    #         'filter_method': '__icontains',
    #         # 'placeholder': 'comma separated'
    #     }
    # ))
    #
    # work_state_date_gte = DateField(required=False, widget=TextInput(
    #     attrs={
    #         # 'filter_field': 'documentparse__date_gos_reg',
    #         'filter_method': '__gte',
    #         'data-mask': "0000-00-00",
    #         'placeholder': 'YYYY-MM-DD'
    #     }
    # ))
    #
    # work_state_date_lte = DateField(required=False, widget=TextInput(
    #     attrs={
    #         # 'filter_field': 'documentparse__date_gos_reg',
    #         'filter_method': '__gte',
    #         'data-mask': "0000-00-00",
    #         'placeholder': 'YYYY-MM-DD'
    #     }
    # ))

    income_value = CharField(required=False, widget=TextInput(
        attrs={
            # 'filter_field': 'documentparse__serviceitem_set',
            'filter_method': '__icontains',
            # 'placeholder': 'comma separated'
        }
    ))

    income_date_gte = DateField(required=False, widget=TextInput(
        attrs={
            # 'filter_field': 'documentparse__date_gos_reg',
            'filter_method': '__gte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))

    income_date_lte = DateField(required=False, widget=TextInput(
        attrs={
            # 'filter_field': 'documentparse__date_gos_reg',
            'filter_method': '__lte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))

    outcome_value = CharField(required=False, widget=TextInput(
        attrs={
            # 'filter_field': 'documentparse__serviceitem_set',
            'filter_method': '__icontains',
            # 'placeholder': 'comma separated'
        }
    ))

    outcome_date_gte = DateField(required=False, widget=TextInput(
        attrs={
            # 'filter_field': 'documentparse__date_gos_reg',
            'filter_method': '__gte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))

    outcome_date_lte = DateField(required=False, widget=TextInput(
        attrs={
            # 'filter_field': 'documentparse__date_gos_reg',
            'filter_method': '__lte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
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
    'service_items_values': "Классы МКТУ. Текст",

    'income_value': "Вх. корреспонденция",
    'income_date_gte': "Вх. корреспонденция >=",
    'income_date_lte': "Вх. корреспонденция <=",
    'outcome_value': "Исх. корреспонденция",
    'outcome_date_gte': "Исх. корреспонденция. Дата >=",
    'outcome_date_lte': "Исх. корреспонденция. Дата <=",

}
