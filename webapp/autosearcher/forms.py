# from django.forms import ModelForm, Form, DateField, CharField, ChoiceField, TextInput, IntegerField, BooleanField
from django import forms
from django.forms.utils import ErrorList

from orders.models_base import DocumentParse as OrderDocumentParse
from registers.models_base import DocumentParse as RegisterDocumentParse
from interface.models import ContactPerson, Company


class ContactPersonTaskForm(forms.ModelForm):
    company = forms.IntegerField(required=False, label='ID Компании')
    new_id = forms.IntegerField(required=False, help_text='Для ручного добавления существующего контакта')
    delete = forms.BooleanField(required=False, initial=False, label='Открепить контакт')
    id = forms.HiddenInput()

    class Meta:
        model = ContactPerson
        fields = ('category', 'company', 'full_name', 'last_name', 'first_name',
                  'middle_name', 'home_phone', 'mobile_phone', 'email',
                  'email_verified', 'email_correct', 'id', 'new_id', 'delete')

    def clean(self):
        cleaned_data = super(ContactPersonTaskForm, self).clean()
        company = cleaned_data['company']
        if company:
            cleaned_data['company'] = Company.objects.get(id=company)
            self.instance.company = cleaned_data['company']
        else:
            cleaned_data['company'] = None
        return cleaned_data
