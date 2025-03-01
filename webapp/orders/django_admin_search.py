# -*- coding: utf-8 -*-
import traceback

import sys
from django.contrib import messages
from django.contrib.admin import ModelAdmin
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError

from django_admin_search import utils
from .forms import fields_dict as f1
from registers.forms import fields_dict as f2

fields_dict = f1.copy()
fields_dict.update(f2)


class AdvancedSearchAdmin(ModelAdmin):
    """
        class to add custom filters in django admin
    """
    change_list_template = 'admin/custom_change_list.html'
    advanced_search_fields = {}
    search_form_data = None
    search_breakable = False

    def get_queryset(self, request):
        """
            override django admin 'get_queryset'
        """
        queryset = super().get_queryset(request)
        # Чтобы результат фильтрации не мешал просматрить документы вне этой фильтрации
        if 'change' in request.path or 'add' in request.path or 'delete' in request.path:
            return queryset

        try:
            return queryset.filter(
                self.advanced_search_query(request)
            )
        except Exception:
            traceback.print_exc(file=sys.stdout)
            messages.add_message(request, messages.ERROR, 'Filter not applied, error has occurred')
            return queryset

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        self.search_form_data = self.search_form(request.GET)
        self.extract_advanced_search_terms(request.GET)
        extra_context['asf'] = self.search_form_data
        extra_context['searching'] = [[fields_dict[s], self.advanced_search_fields[s]]
                                      for s in self.advanced_search_fields if s in fields_dict]
        return super().changelist_view(request, extra_context=extra_context)

    def extract_advanced_search_terms(self, request):
        request._mutable = True  # pylint: disable=W0212

        if self.search_form_data is not None:
            all_none = all([request.get(key) is None for key in self.search_form_data.fields.keys()])
            for key in self.search_form_data.fields.keys():
                temp = request.pop(key, None)
                if temp:
                    self.advanced_search_fields[key] = temp
                elif self.search_breakable and all_none:
                    self.advanced_search_fields[key] = [temp]

        request._mutable = False  # pylint: disable=W0212

    def advanced_search_query(self, request):
        """
            Get form and mount filter query if form is not none
        """
        query = Q()
        param_values = self.advanced_search_fields

        form = self.search_form_data
        if not param_values or form is None:
            return query

        for field, form_field in self.search_form_data.fields.items():
            field_value = param_values[field][0] if field in param_values else None

            # to overide default filter for a sigle field
            if hasattr(self, ('search_' + field)):
                query &= getattr(self, 'search_' + field)(field, field_value,
                                                          form_field, request,
                                                          param_values)
                continue

            if field_value in [None, '']:
                continue

            field_name = form_field.widget.attrs.get('filter_field', field)
            field_filter = field_name + form_field.widget.attrs.get('filter_method', '')

            try:
                field_value = utils.format_data(form_field, field_value)  # format by field type
                query &= Q(**{field_filter: field_value})
            except ValidationError:
                messages.add_message(request, messages.ERROR, _(f"Filter in field `{field_value}` "
                                                                "ignored, because value "
                                                                "`{field_name}` isn't valid"))
                continue
            except Exception:
                messages.add_message(request, messages.ERROR, _(f"Filter in field `{field_name}` "
                                                                "ignored, error has occurred."))
                continue

        return query
