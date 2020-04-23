from django import forms
from django.contrib.auth.models import User


class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)


class RegForm(forms.ModelForm):
    pass1 = forms.CharField(label='Пароль', widget=forms.PasswordInput)
    pass2 = forms.CharField(label='Повторите пароль', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("username", "first_name", "email")

    def clean_pass2(self):
        cd = self.cleaned_data
        if cd['pass1'] != cd['pass2']:
            raise forms.ValidationError('Пароли не совпадают!')
        return cd['pass2']


class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')
