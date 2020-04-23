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

from .models_base import Leaf, Document, DocumentParse, DocumentFile, ServiceItem
from .models import DocumentIzv

# Create your views here.


# class IndexView(LoginRequiredMixin, View):
#     def get(self, request, *args, **kwargs):
#         dict_to_str = {
#             'site_header': 'Таблица'
#         }
#         return render(request, 'orders/index.html', dict_to_str)


class IndexView(LoginRequiredMixin, ListView):
    model = Document
    # queryset = TodoItem.objects.all()
    context_object_name = 'tasks'
    template_name = 'tasks/list.html'
    slug_field = 'tags'

    # Изменено на 136 шаге
    def get_queryset(self):
        qs = super().get_queryset()
        u = self.request.user
        slug = self.kwargs.get('slug')
        if slug is None:
            return qs.filter(owner=u)
        return qs.filter(owner=u).filter(tags__slug__in=[slug])

    # Добавлено на 136 шаге
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_tasks = super().get_queryset()
        tags = set()

        for task in user_tasks:
            tags.update(task.tags.all())
        context['tags'] = sorted(tags)
        context['tag'] = Tag.objects.filter(slug=self.kwargs.get('slug')).first()
        return context