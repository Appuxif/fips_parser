from django.forms import ModelForm, Form
from django.forms import DateField, CharField, ChoiceField, TextInput, IntegerField, BooleanField
from interface.models import ContactPerson


from .models_base import Leaf, Document, DocumentParse, DocumentFile, ServiceItem
income_choices = [
    (0, None),
    (1, 'Запрос об уточнении перечня товаров и/или услуг'),
    (2, 'Запрос формальной экспертизы'),
    (3, 'Запрос экспертизы заявленного обозначения'),
    (4, 'Напоминание о необходимости уплаты пошлин'),
    (5, 'Письмо о высылке копий'),
    (6, 'Письмо о пошлине'),
    (7, 'Письмо о соответствии перечня товаров и/или услуг требованиям Кодекса'),
    (8, 'Письмо о том, что пошлина не учтена'),
    (9, 'Письмо об отказе в высылке копий'),
    (10, 'Письмо об уточнении адреса'),
    (11, 'Письмо об учете пошлины'),
    (12, 'Письмо по вопросам делопроизводства'),
    (13, 'Письмо произвольной формы'),
    (14, 'Решение о признании заявки отозванной'),
    (15, 'Решение о принятии заявки к рассмотрению'),
    (16, 'Решение о регистрации'),
    (17, 'Решение об изменении наименования заявителя'),
    (18, 'Решение об отказе в регистрации'),
    (19, 'Уведомление о представлении документов'),
    (20, 'Уведомление о принятии к сведению заявления об отзыве'),
    (21, 'Уведомление о результатах проверки пошлины'),
    (22, 'Уведомление о результатах проверки соответствия'),
    (23, 'Уведомление об отказе в  удовлетворении ходатайства'),
    (24, 'Уведомление об отказе в совершении юр. действия'),
    (25, 'Уведомление об отказе в удовлетворении просьбы'),
    (26, 'Уведомление об удовлетворении просьбы'),
    (27, 'Уведомление об удовлетворении ходатайства'),
]

outcome_choices = [
    (0, None),
    (1, 'Ходатайство о преобразовании заявки'),
    (2, 'Возврат почтового отправления'),
    (3, 'Доверенность'),
    (4, 'Дополнительные материалы'),
    (5, 'Досрочное прекращение доверенности'),
    (6, 'Заявление о внесении изменений в документы заявки'),
    (7, 'Заявление о внесении исправлений'),
    (8, 'Заявление о внесении исправлений в документы заявки'),
    (9, 'Заявление об изменении наименования заявителя'),
    (10, 'Заявление об изменении сведений о заявителе в случае передачи или перехода права'),
    (11, 'Комплект заявочной документации'),
    (12, 'Копия первой заявки'),
    (13, 'Корреспонденция, поступившая по факсу'),
    (14, 'Корреспонденция, поступившая через личный кабинет и требующая представления оригинала документа'),
    (15, 'Обращение'),
    (16, 'Перевод документов'),
    (17, 'Письмо для ответа'),
    (18, 'Письмо для ответа на контроле дирекции'),
    (19, 'Письмо, не требующее ответа'),
    (20, 'Платежный документ'),
    (21, 'Просьба заявителя об отзыве заявки'),
    (22, 'Просьба о установлении выставочного приоритета'),
    (23, 'Просьба об установлении конвенционного приоритета'),
    (24, 'Просьба об установлении приоритета выделенной заявки'),
    (25, 'Ходатайство о ведении переписки через личный кабинет'),
    (26, 'Ходатайство о внесении изменений в адрес'),
    (27, 'Ходатайство о возврате пошлины'),
    (28, 'Ходатайство о восстановлении пропущенного срока'),
    (29, 'Ходатайство о зачете пошлины'),
    (30, 'Ходатайство о продлении установленного срока'),
]


class ContactPersonAddForm(ModelForm):
    contactperson_new_id = IntegerField(help_text="Для ручного добавления контакта", required=False)
    contactperson = CharField(required=False)

    class Meta:
        model = ContactPerson.order.through
        fields = ('contactperson', 'contactperson_new_id')

    def clean(self):
        cleaned_data = super(ContactPersonAddForm, self).clean()
        contactperson_new = cleaned_data['contactperson_new_id']
        if contactperson_new:
            cleaned_data['contactperson'] = ContactPerson.objects.get(id=contactperson_new)
            self.instance.contactperson = cleaned_data['contactperson']
        return cleaned_data


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

    # income_value = CharField(required=False, widget=TextInput(
    #     attrs={
    #         # 'filter_field': 'documentparse__serviceitem_set',
    #         'filter_method': '__icontains',
    #         # 'placeholder': 'comma separated'
    #     }
    # ))
    income_value = ChoiceField(required=False, choices=income_choices, initial=None)

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

    # outcome_value = CharField(required=False, widget=TextInput(
    #     attrs={
    #         # 'filter_field': 'documentparse__serviceitem_set',
    #         'filter_method': '__icontains',
    #         # 'placeholder': 'comma separated'
    #     }
    # ))

    outcome_value = ChoiceField(required=False, choices=outcome_choices, initial=None)

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
