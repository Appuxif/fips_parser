from django.db import models
from orders.models_base import Document as OrderDocument
from registers.models_base import Document as RegisterDocument


# Объект прокси
class Proxies(models.Model):
    scheme = models.CharField(max_length=10)
    user = models.CharField(max_length=100, null=True)
    password = models.CharField(max_length=100, null=True)
    host = models.CharField(max_length=100)
    port = models.PositiveIntegerField()
    is_banned = models.BooleanField(default=False)
    is_working = models.BooleanField(default=True)
    in_use = models.BooleanField(default=False)
    status = models.CharField(max_length=255, null=True)

    def __str__(self):
        s = [str(self.scheme), '']
        if self.user and self.password:
            s = s[:-1] + [str(self.user), ':', str(self.password), '@'] + ['/']
        s = s[:-1] + [str(self.host), ':', str(self.port)] + s[-1:]
        return ''.join(s)


# Таблица контактов, присваеваемых к документу
class OrderContact(models.Model):
    order = models.ForeignKey(OrderDocument, on_delete=models.DO_NOTHING, related_query_name='contact')
    company_name = models.CharField('Наименование компании', max_length=255, null=True, blank=True)
    company_address = models.CharField('Адрес компании', max_length=255, null=True, blank=True)

    def __str__(self):
        return 'Contact for ' + str(self.order.number)


# Таблица контактов, присваеваемых к документу
class RegisterContact(models.Model):
    register = models.ForeignKey(RegisterDocument, on_delete=models.DO_NOTHING, related_query_name='contact')
    company_name = models.CharField('Наименование компании', max_length=255, null=True, blank=True)
    company_address = models.CharField('Адрес компании', max_length=255, null=True, blank=True)

    def __str__(self):
        return 'Contact for ' + str(self.register.number)


class OrderContactPerson(models.Model):
    order_contact = models.ForeignKey(OrderDocument, on_delete=models.CASCADE, related_query_name='person')
    name = models.CharField('Персональные данные контактного лица', max_length=255, null=True, blank=True)
    address = models.CharField('Адрес контактного лица', max_length=255, null=True, blank=True)
    position = models.CharField('Должность контактного лица', max_length=255, null=True, blank=True)
    tel = models.CharField('Номер телефона', max_length=255, null=True, blank=True)
    email = models.CharField('Электронная почта', max_length=255, null=True, blank=True)

    def __str__(self):
        return self.order_contact


class RegisterContactPerson(models.Model):
    register_contact = models.ForeignKey(OrderDocument, on_delete=models.CASCADE, related_query_name='person')
    name = models.CharField('Персональные данные контактного лица', max_length=255, null=True, blank=True)
    address = models.CharField('Адрес контактного лица', max_length=255, null=True, blank=True)
    position = models.CharField('Должность контактного лица', max_length=255, null=True, blank=True)
    tel = models.CharField('Номер телефона', max_length=255, null=True, blank=True)
    email = models.CharField('Электронная почта', max_length=255, null=True, blank=True)

    def __str__(self):
        return self.register_contact
