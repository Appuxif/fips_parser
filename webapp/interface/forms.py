from django import forms


class AddProxyForm(forms.Form):
    proxies = forms.FileField(required=True)


class LogEntrySearchForm(forms.Form):
    username = forms.CharField(required=False, widget=forms.TextInput(
        attrs={
            'filter_field': 'user__username',
        }
    ))
    action_time_gte = forms.DateField(required=False, widget=forms.TextInput(
        attrs={
            'filter_field': 'action_time',
            'filter_method': '__gte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))
    action_time_lte = forms.DateField(required=False, widget=forms.TextInput(
        attrs={
            'filter_field': 'action_time',
            'filter_method': '__lte',
            'data-mask': "0000-00-00",
            'placeholder': 'YYYY-MM-DD'
        }
    ))
    content_type = forms.CharField(required=False, widget=forms.TextInput(
        attrs={
            'filter_field': 'content_type__app_label',
            'placeholder': 'Например: interface'
        }
    ))

    def __init__(self, *args, **kwargs):
        super(LogEntrySearchForm, self).__init__(*args, **kwargs)
        self.fields['username'].label = 'Пользователь'
        self.fields['action_time_gte'].label = 'Время действия >='
        self.fields['action_time_lte'].label = 'Время действия <='
        self.fields['content_type'].label = 'Раздел'

