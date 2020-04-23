from django.shortcuts import redirect, render, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q, Count
from django.core.mail import send_mail
from django.conf import settings
from django.views.generic import (
    ListView,
    TemplateView,
    CreateView,
    DeleteView,
    UpdateView,
    DetailView,
)
from django.views import View
from django.urls import reverse, reverse_lazy

# Create your views here.


# class IndexView(LoginRequiredMixin, View):
class IndexView(View):
    def get(self, request, *args, **kwargs):
        # dict_to_str = {
        #     'site_header': 'Таблица'
        # }
        # return render(request, 'interface/index.html', dict_to_str)
        return redirect('admin/')
