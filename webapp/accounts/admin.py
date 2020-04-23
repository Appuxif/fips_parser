from django.contrib import admin

from .models import UserQuery


@admin.register(UserQuery)
class UserQueryAdmin(admin.ModelAdmin):
    pass
