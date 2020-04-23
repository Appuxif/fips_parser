from django.db import models
from django.contrib.auth.models import User

# Create your models here.


class UserQuery(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    order_document_list = models.CharField(max_length=2000, null=True, blank=True)
    order_document_ordering = models.CharField(max_length=2000, null=True, blank=True)

    register_document_list = models.CharField(max_length=2000, null=True, blank=True)
    register_document_ordering = models.CharField(max_length=2000, null=True, blank=True)

    def __str__(self):
        return self.user.username
