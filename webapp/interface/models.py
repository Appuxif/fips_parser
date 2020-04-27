from django.db import models
from orders.models_base import Document as OrderDocument
from registers.models_base import Document as RegisterDocument


# Объект прокси
class Proxies(models.Model):
    scheme = models.CharField(max_length=10, default='http://')
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
        return 'Contact ' + str(self.id) + ' for order ' + str(self.order.number)

    def get_absolute_url(self):
        return f'/admin/interface/ordercontact/{self.id}/change/'

    class Meta:
        verbose_name = 'Контакт заявки'
        verbose_name_plural = 'Контакты заявок'


# Таблица контактов, присваеваемых к документу
class RegisterContact(models.Model):
    register = models.ForeignKey(RegisterDocument, on_delete=models.DO_NOTHING, related_query_name='contact')
    company_name = models.CharField('Наименование компании', max_length=255, null=True, blank=True)
    company_address = models.CharField('Адрес компании', max_length=255, null=True, blank=True)

    def __str__(self):
        return 'Contact ' + str(self.id) + ' for register ' + str(self.register.number)

    def get_absolute_url(self):
        return f'/admin/interface/registercontact/{self.id}/change/'

    class Meta:
        verbose_name = 'Контакт регистрации'
        verbose_name_plural = 'Контакты регистраций'


class OrderContactPerson(models.Model):
    document = models.ForeignKey(OrderDocument, on_delete=models.CASCADE, related_query_name='person')
    name = models.CharField('Персональные данные контактного лица', max_length=255, null=True, blank=True)
    address = models.CharField('Адрес контактного лица', max_length=2000, null=True, blank=True)
    position = models.CharField('Должность контактного лица', max_length=255, null=True, blank=True)
    tel = models.CharField('Номер телефона', max_length=255, null=True, blank=True)
    email = models.CharField('Электронная почта', max_length=255, null=True, blank=True)

    def __str__(self):
        return 'Person ' + str(self.id) + ' for order ' + str(self.document)

    def get_absolute_url(self):
        return f'/admin/interface/ordercontactperson/{self.id}/change/'

    class Meta:
        verbose_name = 'Представитель заявки'
        verbose_name_plural = 'Представители заявок'


class RegisterContactPerson(models.Model):
    document = models.ForeignKey(RegisterDocument, on_delete=models.CASCADE, related_query_name='person')
    name = models.CharField('Персональные данные контактного лица', max_length=255, null=True, blank=True)
    address = models.CharField('Адрес контактного лица', max_length=2000, null=True, blank=True)
    position = models.CharField('Должность контактного лица', max_length=255, null=True, blank=True)
    tel = models.CharField('Номер телефона', max_length=255, null=True, blank=True)
    email = models.CharField('Электронная почта', max_length=255, null=True, blank=True)

    def __str__(self):
        return 'Person ' + str(self.id) + ' for register ' + str(self.document)

    def get_absolute_url(self):
        return f'/admin/interface/registercontactperson/{self.id}/change/'

    class Meta:
        verbose_name = 'Представитель регистрации'
        verbose_name_plural = 'Представители регистраций'
