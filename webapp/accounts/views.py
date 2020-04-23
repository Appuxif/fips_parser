from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.views import View

from .forms import LoginForm, RegForm, UserEditForm


class LoginView(View):
    def post(self, request, *args, **kwargs):
        form = LoginForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            user = authenticate(
                request,
                username=cd['username'],
                password=cd['password']
            )
            if user is None:
                return HttpResponse('Неправльный логин и/или пароль!')
            if not user.is_active:
                return HttpResponse('Ваш аккаунт заблокирован.')
            login(request, user)
            return HttpResponse('Добро пожаловать! Успешный вход.')
        return render(request, 'accounts/login.html', {'form': form})

    def get(self, request, *args, **kwargs):
        form = LoginForm()
        return render(request, 'accounts/login.html', {'form': form})


def register(request):
    form = RegForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            new_user = form.save(commit=False)
            new_user.set_password(form.cleaned_data["pass1"])
            new_user.save()
            return render(request, 'accounts/registration_complete.html', {'new_user': new_user})
    return render(request, 'accounts/register.html', {'user_form': form})


@login_required
def edit(request):
    if request.method == "POST":
        user_form = UserEditForm(instance=request.user, data=request.POST)
        if user_form.is_valid():
            user_form.save()
    else:
        user_form = UserEditForm(instance=request.user)

    return render(request, 'accounts/edit.html', {'user_form': user_form})

