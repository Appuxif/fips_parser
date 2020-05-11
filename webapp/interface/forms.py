from django import forms


class AddProxyForm(forms.Form):
    proxies = forms.FileField(required=True)