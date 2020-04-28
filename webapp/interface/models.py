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


# # TODO: Наверное, придется удалить
# # Таблица контактов, присваеваемых к документу
# class OrderContact(models.Model):
#     order = models.ForeignKey(OrderDocument, on_delete=models.DO_NOTHING, related_query_name='contact')
#     company_name = models.CharField('Наименование компании', max_length=255, null=True, blank=True)
#     company_address = models.CharField('Адрес компании', max_length=255, null=True, blank=True)
#
#     def __str__(self):
#         return 'Contact ' + str(self.id) + ' for order ' + str(self.order.number)
#
#     def get_absolute_url(self):
#         return f'/admin/interface/ordercontact/{self.id}/change/'
#
#     class Meta:
#         verbose_name = 'Контакт заявки'
#         verbose_name_plural = 'Контакты заявок'


# # TODO: Наверное, придется удалить
# # Таблица контактов, присваеваемых к документу
# class RegisterContact(models.Model):
#     register = models.ForeignKey(RegisterDocument, on_delete=models.DO_NOTHING, related_query_name='contact')
#     company_name = models.CharField('Наименование компании', max_length=255, null=True, blank=True)
#     company_address = models.CharField('Адрес компании', max_length=255, null=True, blank=True)
#
#     def __str__(self):
#         return 'Contact ' + str(self.id) + ' for register ' + str(self.register.number)
#
#     def get_absolute_url(self):
#         return f'/admin/interface/registercontact/{self.id}/change/'
#
#     class Meta:
#         verbose_name = 'Контакт регистрации'
#         verbose_name_plural = 'Контакты регистраций'


class Company(models.Model):
    company_name = models.CharField('Наименование компании', max_length=255, null=True, blank=True)
    company_address = models.CharField('Адрес компании', max_length=255, null=True, blank=True)
    company_web = models.CharField(max_length=100, null=True, blank=True)
    company_form = models.CharField(max_length=50, null=True, blank=True)  # ! # Организационная форма ООО

    # order = models.ManyToManyField(OrderDocument, related_query_name='person',
    #                                blank=True, through='OrderCompanyRel')
    # register = models.ManyToManyField(RegisterDocument, related_query_name='person',
    #                                   blank=True, through='RegisterCompanyRel')

    def __str__(self):
        return str(self.company_name)

    def get_absolute_url(self):
        return f'/admin/interface/company/{self.id}/change/'

    class Meta:
        verbose_name = 'Компания'
        verbose_name_plural = 'Компании'


class OrderCompanyRel(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    order = models.ForeignKey(OrderDocument, on_delete=models.CASCADE, null=True)

    class Meta:
        verbose_name = 'Связь Заявка-Компания'
        verbose_name_plural = 'Связи Заявка-Компания'


class RegisterCompanyRel(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    register = models.ForeignKey(RegisterDocument, on_delete=models.CASCADE, null=True)

    class Meta:
        verbose_name = 'Связь Регистрация-Компания'
        verbose_name_plural = 'Связи Регистрация-Компания'


class ContactPerson(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_query_name='person')

    category = models.CharField(max_length=50, default='DEFAULT')  # DEFAULT или REPRESENTATIVE (поверенный)

    email = models.CharField('Электронная почта', max_length=255, null=True, blank=True)  #
    full_name = models.CharField('Полное имя', max_length=255, null=True, blank=True)  #
    first_name = models.CharField('Имя', max_length=50, null=True, blank=True)
    middle_name = models.CharField('Отчество', max_length=50, null=True, blank=True)
    last_name = models.CharField('Фамилия', max_length=50, null=True, blank=True)
    nick_name = models.CharField('Никнейм', max_length=50, null=True, blank=True)
    gender = models.CharField('Пол', max_length=10, null=True, blank=True)
    job_title = models.CharField('Должность', max_length=50, null=True, blank=True)

    # company_name = models.CharField('Наименование комании', max_length=100, null=True, blank=True)  # #
    # company_form = models.CharField(max_length=50, null=True, blank=True)  # ! # Организационная форма ООО
    # company_web = models.CharField(max_length=100, null=True, blank=True)

    personal_web = models.CharField(max_length=150, null=True, blank=True)
    office_address = models.CharField(max_length=100, null=True, blank=True)  # ! #
    home_phone = models.CharField('Домашний телефон', max_length=25, null=True, blank=True)
    office_phone = models.CharField('Оффисный телефон', max_length=25, null=True, blank=True)
    mobile_phone = models.CharField('Мобильный телефон', max_length=25, null=True, blank=True)
    messenger_id = models.CharField(max_length=25, null=True, blank=True)
    messenger_type = models.CharField(max_length=25, null=True, blank=True)
    fax = models.CharField(max_length=25, null=True, blank=True)
    city = models.CharField('Город', max_length=50, null=True, blank=True)  # ! #
    zip = models.IntegerField('Индекс', null=True, blank=True)  # ! #
    area = models.CharField(max_length=50, null=True, blank=True)  # ! #
    state = models.CharField(max_length=50, null=True, blank=True)  # ! #
    country = models.CharField(max_length=50, null=True, blank=True)  # ! #

    rep_reg_number = models.CharField(max_length=20, null=True, blank=True)
    rep_correspondence_address = models.CharField(max_length=255, null=True, blank=True)  # ! #


    def __str__(self):
        return 'Контакт ' + str(self.id) + ' компании ' + str(self.company)

    def get_absolute_url(self):
        return f'/admin/interface/contactperson/{self.id}/change/'

    class Meta:
        verbose_name = 'Представитель заявки'
        verbose_name_plural = 'Представители заявок'
        indexes = [
            models.Index(fields=['id']),
            models.Index(fields=['email']),
            models.Index(fields=['full_name']),
            # models.Index(fields=['company_name']),
        ]


# # TODO: Наверное, придется удалить
# class OrderContactPerson(models.Model):
#     document = models.ForeignKey(OrderDocument, on_delete=models.CASCADE, related_query_name='person')
#     category = models.CharField(max_length=50, default='DEFAULT')  # DEFAULT или REPRESENTATIVE (поверенный)
#
#     email = models.CharField('Электронная почта', max_length=255, null=True, blank=True)  #
#     full_name = models.CharField('Полное имя', max_length=255, null=True, blank=True)  #
#     first_name = models.CharField('Имя', max_length=50, null=True, blank=True)
#     middle_name = models.CharField('Отчество', max_length=50, null=True, blank=True)
#     last_name = models.CharField('Фамилия', max_length=50, null=True, blank=True)
#     nick_name = models.CharField('Никнейм', max_length=50, null=True, blank=True)
#     gender = models.CharField('Пол', max_length=10, null=True, blank=True)
#     job_title = models.CharField('Должность', max_length=50, null=True, blank=True)
#
#     company_name = models.CharField('Наименование комании', max_length=100, null=True, blank=True)  # #
#     company_form = models.CharField(max_length=50, null=True, blank=True)  # ! # Организационная форма ООО
#     company_web = models.CharField(max_length=100, null=True, blank=True)
#
#     personal_web = models.CharField(max_length=150, null=True, blank=True)
#     office_address = models.CharField(max_length=100, null=True, blank=True)  # ! #
#     home_phone = models.CharField('Домашний телефон', max_length=25, null=True, blank=True)
#     office_phone = models.CharField('Оффисный телефон', max_length=25, null=True, blank=True)
#     mobile_phone = models.CharField('Мобильный телефон', max_length=25, null=True, blank=True)
#     messenger_id = models.CharField(max_length=25, null=True, blank=True)
#     messenger_type = models.CharField(max_length=25, null=True, blank=True)
#     fax = models.CharField(max_length=25, null=True, blank=True)
#     city = models.CharField('Город', max_length=50, null=True, blank=True)  # ! #
#     zip = models.IntegerField('Индекс', null=True, blank=True)  # ! #
#     area = models.CharField(max_length=50, null=True, blank=True)  # ! #
#     state = models.CharField(max_length=50, null=True, blank=True)  # ! #
#     country = models.CharField(max_length=50, null=True, blank=True)  # ! #
#
#     # rep_full_name = models.CharField(max_length=255, null=True, blank=True)  # #
#     rep_reg_number = models.CharField(max_length=20, null=True, blank=True)  # ! #
#     # rep_company_name = models.CharField(max_length=100, null=True, blank=True)  # ! #
#     # rep_company_form = models.CharField(max_length=50, null=True, blank=True)  # ! #
#     # rep_company_web = models.CharField(max_length=100, null=True, blank=True)
#     # rep_personal_web = models.CharField(max_length=150, null=True, blank=True)
#     rep_correspondence_address = models.CharField(max_length=255, null=True, blank=True)  # ! #
#
#     # rep_office_address = models.CharField(max_length=100, null=True, blank=True)  # ! #
#     # rep_home_phone = models.CharField(max_length=25, null=True, blank=True)
#     # rep_office_phone = models.CharField(max_length=25, null=True, blank=True)
#     # rep_mobile_phone = models.CharField(max_length=25, null=True, blank=True)
#     # rep_messenger_id = models.CharField(max_length=25, null=True, blank=True)
#     # rep_messenger_type = models.CharField(max_length=25, null=True, blank=True)
#     # rep_fax = models.CharField(max_length=25, null=True, blank=True)
#     # rep_city = models.CharField(max_length=50, null=True, blank=True)  # ! #
#     # rep_zip = models.IntegerField(null=True, blank=True)  # ! #
#     # rep_area = models.CharField(max_length=50, null=True, blank=True)  # ! #
#     # rep_state = models.CharField(max_length=50, null=True, blank=True)  # ! #
#     # rep_country = models.CharField(max_length=50, null=True, blank=True)  # ! #
#
#     def __str__(self):
#         return 'Person ' + str(self.id) + ' for order ' + str(self.document)
#
#     def get_absolute_url(self):
#         return f'/admin/interface/ordercontactperson/{self.id}/change/'
#
#     class Meta:
#         verbose_name = 'Представитель заявки'
#         verbose_name_plural = 'Представители заявок'
#         indexes = [
#             models.Index(fields=['id']),
#             models.Index(fields=['email']),
#             models.Index(fields=['full_name']),
#             models.Index(fields=['company_name']),
#             # models.Index(fields=['rep_full_name']),
#         ]


# # TODO: Наверное, придется удалить
# class RegisterContactPerson(models.Model):
#     document = models.ForeignKey(RegisterDocument, on_delete=models.CASCADE, related_query_name='person')
#     category = models.CharField(max_length=50, default='DEFAULT')  # DEFAULT или REPRESENTATIVE (поверенный)
#
#     email = models.CharField('Электронная почта', max_length=255, null=True, blank=True)  #
#     full_name = models.CharField('Полное имя', max_length=255, null=True, blank=True)  #
#     first_name = models.CharField('Имя', max_length=50, null=True, blank=True)
#     middle_name = models.CharField('Отчество', max_length=50, null=True, blank=True)
#     last_name = models.CharField('Фамилия', max_length=50, null=True, blank=True)
#     nick_name = models.CharField('Никнейм', max_length=50, null=True, blank=True)
#     gender = models.CharField('Пол', max_length=10, null=True, blank=True)
#     job_title = models.CharField('Должность', max_length=50, null=True, blank=True)
#
#     company_name = models.CharField('Наименование комании', max_length=100, null=True, blank=True)  # #
#     company_form = models.CharField(max_length=50, null=True, blank=True)  # ! # Организационная форма ООО
#     company_web = models.CharField(max_length=100, null=True, blank=True)
#
#     personal_web = models.CharField(max_length=150, null=True, blank=True)
#     office_address = models.CharField(max_length=100, null=True, blank=True)  # ! #
#     home_phone = models.CharField('Домашний телефон', max_length=25, null=True, blank=True)
#     office_phone = models.CharField('Оффисный телефон', max_length=25, null=True, blank=True)
#     mobile_phone = models.CharField('Мобильный телефон', max_length=25, null=True, blank=True)
#     messenger_id = models.CharField(max_length=25, null=True, blank=True)
#     messenger_type = models.CharField(max_length=25, null=True, blank=True)
#     fax = models.CharField(max_length=25, null=True, blank=True)
#     city = models.CharField('Город', max_length=50, null=True, blank=True)  # ! #
#     zip = models.IntegerField('Индекс', null=True, blank=True)  # ! #
#     area = models.CharField(max_length=50, null=True, blank=True)  # ! #
#     state = models.CharField(max_length=50, null=True, blank=True)  # ! #
#     country = models.CharField(max_length=50, null=True, blank=True)  # ! #
#
#     # rep_full_name = models.CharField(max_length=255, null=True, blank=True)  # #
#     rep_reg_number = models.CharField(max_length=20, null=True, blank=True)  # ! #
#     # rep_company_name = models.CharField(max_length=100, null=True, blank=True)  # ! #
#     # rep_company_form = models.CharField(max_length=50, null=True, blank=True)  # ! #
#     # rep_company_web = models.CharField(max_length=100, null=True, blank=True)
#     # rep_personal_web = models.CharField(max_length=150, null=True, blank=True)
#     rep_correspondence_address = models.CharField(max_length=255, null=True, blank=True)  # ! #
#     # rep_office_address = models.CharField(max_length=100, null=True, blank=True)  # ! #
#     # rep_home_phone = models.CharField(max_length=25, null=True, blank=True)
#     # rep_office_phone = models.CharField(max_length=25, null=True, blank=True)
#     # rep_mobile_phone = models.CharField(max_length=25, null=True, blank=True)
#     # rep_messenger_id = models.CharField(max_length=25, null=True, blank=True)
#     # rep_messenger_type = models.CharField(max_length=25, null=True, blank=True)
#     # rep_fax = models.CharField(max_length=25, null=True, blank=True)
#     # rep_city = models.CharField(max_length=50, null=True, blank=True)  # ! #
#     # rep_zip = models.IntegerField(null=True, blank=True)  # ! #
#     # rep_area = models.CharField(max_length=50, null=True, blank=True)  # ! #
#     # rep_state = models.CharField(max_length=50, null=True, blank=True)  # ! #
#     # rep_country = models.CharField(max_length=50, null=True, blank=True)  # ! #
#
#     def __str__(self):
#         return 'Person ' + str(self.id) + ' for register ' + str(self.document)
#
#     def get_absolute_url(self):
#         return f'/admin/interface/registercontactperson/{self.id}/change/'
#
#     class Meta:
#         verbose_name = 'Представитель регистрации'
#         verbose_name_plural = 'Представители регистраций'
#         indexes = [
#             models.Index(fields=['id']),
#             models.Index(fields=['email']),
#             models.Index(fields=['full_name']),
#             models.Index(fields=['company_name']),
#             # models.Index(fields=['rep_full_name']),
#         ]