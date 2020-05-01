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
    documents_parsed = models.IntegerField(default=0, null=True, blank=True)
    date_last_used = models.DateField(auto_now=True)

    def __str__(self):
        s = [str(self.scheme), '']
        if self.user and self.password:
            s = s[:-1] + [str(self.user), ':', str(self.password), '@'] + ['/']
        s = s[:-1] + [str(self.host), ':', str(self.port)] + s[-1:]
        return ''.join(s)


def company_logo_path(instance, filename):
    return 'company_{0}/logo.jpg'.format(instance.id)


class Company(models.Model):
    name = models.CharField('Наименование компании', max_length=255, null=True, blank=True)
    name_latin = models.CharField('Наименование компании латинское', max_length=255, null=True, blank=True)
    address = models.CharField('Адрес компании', max_length=255, null=True, blank=True)
    address_latin = models.CharField('Адрес компании латинский', max_length=255, null=True, blank=True)
    sign_char = models.CharField('Код страны', max_length=5, null=True, blank=True)
    web = models.CharField(max_length=100, null=True, blank=True)
    form = models.CharField(max_length=50, null=True, blank=True)  # ! # Организационная форма ООО

    order = models.ManyToManyField(OrderDocument, related_query_name='person',
                                   blank=True, through='OrderCompanyRel')
    register = models.ManyToManyField(RegisterDocument, related_query_name='person',
                                      blank=True, through='RegisterCompanyRel')

    logo = models.ImageField('Логотип компании', upload_to=company_logo_path, null=True, blank=True)

    def __str__(self):
        return str(self.name)

    def get_absolute_url(self):
        return f'/admin/interface/company/{self.id}/change/'

    class Meta:
        verbose_name = 'Компания'
        verbose_name_plural = 'Компании'
        indexes = [
            models.Index(fields=['form']),
        ]


class OrderCompanyRel(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    order = models.ForeignKey(OrderDocument, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return str(self.id)

    def get_absolute_url(self):
        return f'/admin/orders/document/{self.order.id}/change/'

    class Meta:
        verbose_name = 'Связанная Компания'
        verbose_name_plural = 'Связанные Компании'


class RegisterCompanyRel(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    register = models.ForeignKey(RegisterDocument, on_delete=models.CASCADE, null=True)

    def __str__(self):
        # return str(self.register) + ' - ' + str(self.company)
        return str(self.id)

    def get_absolute_url(self):
        return f'/admin/registers/document/{self.register.id}/change/'

    class Meta:
        verbose_name = 'Связанная Компания'
        verbose_name_plural = 'Связанные Компании'


def person_photo_path(instance, filename):
    return 'company_{0}/person_{1}/photo.jpg'.format(instance.company.id, instance.id)


class ContactPerson(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_query_name='person')

    category = models.CharField(max_length=50, default='DEFAULT')  # DEFAULT или REPRESENTATIVE (поверенный)

    email = models.CharField('Электронная почта', max_length=255, null=True, blank=True)  #
    email_verified = models.BooleanField('Почта верифицирована', default=False)
    email_correct = models.BooleanField('Почта корректна', default=True)

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
    city = models.CharField('Город', max_length=255, null=True, blank=True)  # ! #
    zip = models.IntegerField('Индекс', null=True, blank=True)  # ! #
    area = models.CharField(max_length=255, null=True, blank=True)  # ! #
    state = models.CharField(max_length=255, null=True, blank=True)  # ! #
    country = models.CharField(max_length=255, null=True, blank=True)  # ! #

    rep_reg_number = models.CharField(max_length=255, null=True, blank=True)
    rep_correspondence_address = models.CharField(max_length=255, null=True, blank=True)  # ! #

    photo = models.ImageField('Персональное фото', upload_to=person_photo_path, null=True, blank=True)
    bday_date = models.DateField('День рождения', null=True, blank=True)

    def __str__(self):
        return 'Контакт ' + str(self.id) + ' компании ' + str(self.company)

    def get_absolute_url(self):
        return f'/admin/interface/contactperson/{self.id}/change/'

    class Meta:
        verbose_name = 'Представитель компании'
        verbose_name_plural = 'Представители компаний'
        indexes = [
            models.Index(fields=['id']),
            models.Index(fields=['email']),
            models.Index(fields=['full_name'])
        ]


# Таблица с настройками парсера. Парсеров всего два: orders и registers
class ParserSetting(models.Model):
    type_choices = [
        (0, 'orders'),
        (1, 'registers')
    ]
    type = models.SmallIntegerField('Тип парсера', choices=type_choices)  # orders или registers

    source_choices = [
        (0, 'fips.ru'),
        (1, 'new.fips.ru')
    ]
    source = models.SmallIntegerField(choices=source_choices)

    # date_gte = models.DateField('С даты')
    # date_lte = models.DateField('По дату')

    requests_period = models.IntegerField('Период запросов (сек)', default=3)
    requests_amount = models.IntegerField('Количество запросов за период', default=1)

    number_gte = models.CharField('С номера', max_length=20, null=True, blank=True)  # 2020706000
    number_lte = models.CharField('По номер', max_length=20, null=True, blank=True)  # 2020706099

    proxies_num = models.IntegerField('Количество используемых прокси')
    is_working = models.BooleanField('Парсер запущен')

    def __str__(self):
        type = 'orders' if self.type == 0 else 'registers'
        return 'Настройки для ' + type + ' ' + str(self.id)
