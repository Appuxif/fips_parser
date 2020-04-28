from django.contrib import admin


# Все контакты отображаются непосредственно в документе

# from .models import OrderContact, OrderContactPerson, RegisterContact, RegisterContactPerson, ContactPerson, Company
from .models import ContactPerson, Company, RegisterCompanyRel, OrderCompanyRel
from orders.admin import CompanyInline as OrderCompanyInline
from registers.admin import CompanyInline as RegisterCompanyInline


# @admin.register(OrderContact)
# class OrderContactAdmin(admin.ModelAdmin):
#     readonly_fields = ('order',)


# @admin.register(RegisterContact)
# class RegisterContactAdmin(admin.ModelAdmin):
#     readonly_fields = ('register', )


# @admin.register(OrderContactPerson)
# class OrderContactPersonAdmin(admin.ModelAdmin):
#     readonly_fields = ('document',)


# @admin.register(RegisterContactPerson)
# class RegisterContactPersonAdmin(admin.ModelAdmin):
#     readonly_fields = ('document', )


# Для отображения контактов в даминке компании в БД
class ContactPersonInline(admin.StackedInline):
    model = ContactPerson
    extra = 0
    view_on_site = False


# Отображение компании в БД
@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    inlines = [ContactPersonInline, OrderCompanyInline, RegisterCompanyInline]
    exclude = ('order', 'register')


# TODO: Для отладки. Потом удалить
@admin.register(ContactPerson)
class ContactPersonAdmin(admin.ModelAdmin):
    pass

# TODO: Для отладки. Потом удалить
@admin.register(OrderCompanyRel)
class OrderCompanyRelAdmin(admin.ModelAdmin):
    pass

# TODO: Для отладки. Потом удалить
@admin.register(RegisterCompanyRel)
class RegisterCompanyRelAdmin(admin.ModelAdmin):
    pass
