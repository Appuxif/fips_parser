from django.db import models


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
class DocumentContact(models.Model):
    is_correct = models.BooleanField('Верный контакт')

