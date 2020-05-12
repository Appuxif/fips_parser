from django.db import models
from orders.models_base import Document as OrderDocument
from registers.models_base import Document as RegisterDocument

contact_categories = [
    ('DEFAULT', 'Общий'),
    ('DIRECTOR', 'Руководитель'),
    ('EXECUTOR', 'Исполнитель'),
    ('REPRESENTATIVE', 'Патентный поверенный'),
]


# Объект прокси
class Proxies(models.Model):
    scheme = models.CharField(max_length=10, default='http://', blank=True)
    user = models.CharField(max_length=100, null=True, blank=True)
    password = models.CharField(max_length=100, null=True, blank=True)
    host = models.CharField(max_length=100, unique=True)
    port = models.PositiveIntegerField()

    is_banned = models.BooleanField(default=False)
    is_working = models.BooleanField(default=True)
    in_use = models.BooleanField(default=False)
    status = models.CharField(max_length=255, null=True, blank=True)
    documents_parsed = models.IntegerField(default=0, null=True, blank=True)
    date_last_used = models.DateField(auto_now=True)

    def __str__(self):
        s = [str(self.scheme), '']
        if self.user and self.password:
            s = s[:-1] + [str(self.user), ':', str(self.password), '@'] + ['/']
        s = s[:-1] + [str(self.host), ':', str(self.port)] + s[-1:]
        return ''.join(s)

    class Meta:
        unique_together = ['host', 'port']


def company_logo_path(instance, filename):
    return 'company_{0}/logo.jpg'.format(instance.id)


class Company(models.Model):
    form = models.CharField('Орг. форма', max_length=50, null=True, blank=True)  # ! # Организационная форма ООО
    form_correct = models.CharField('Орг. форма', max_length=50, null=True, blank=True)
    name = models.CharField('Наименование компании', max_length=255, blank=True)
    name_correct = models.CharField('Наименование компании', max_length=255, null=True, blank=True)
    name_latin = models.CharField('Наименование компании латинское', max_length=255, null=True, blank=True)
    address = models.CharField('Адрес компании', max_length=1000, null=True, blank=True)
    address_latin = models.CharField('Адрес компании латинский', max_length=1000, null=True, blank=True)
    sign_char = models.CharField('Код страны', max_length=5, null=True, blank=True)
    web = models.CharField('WEB', max_length=100, null=True, blank=True)
    inn = models.CharField('ИНН', max_length=100, null=True, blank=True)
    kpp = models.CharField('КПП', max_length=100, null=True, blank=True)
    ogrn = models.CharField('ОГРН', max_length=100, null=True, blank=True)

    order = models.ManyToManyField(OrderDocument, related_query_name='company',
                                   blank=True, through='OrderCompanyRel')
    register = models.ManyToManyField(RegisterDocument, related_query_name='company',
                                      blank=True, through='RegisterCompanyRel')

    logo = models.ImageField('Логотип компании', upload_to=company_logo_path, null=True, blank=True)

    date_corrected = models.DateField('Дата последней корректировки', auto_now=True, null=True, blank=True)

    def __str__(self):
        return str(self.form_correct or self.form or '') + ' ' + str(self.name_correct or self.name or '')

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
    company_is_holder = models.BooleanField('Правообладатель', default=False)
    document = models.ForeignKey(OrderDocument, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return str(self.id)

    def get_absolute_url(self):
        return f'/admin/orders/document/{self.document.id}/change/'

    class Meta:
        verbose_name = 'Связанная Компания (Заявки)'
        verbose_name_plural = 'Связанные Компании (Заявки)'


class RegisterCompanyRel(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    company_is_holder = models.BooleanField(default=False)
    document = models.ForeignKey(RegisterDocument, on_delete=models.CASCADE, null=True)

    def __str__(self):
        # return str(self.register) + ' - ' + str(self.company)
        return str(self.id)

    def get_absolute_url(self):
        return f'/admin/registers/document/{self.document.id}/change/'

    class Meta:
        verbose_name = 'Связанная Компания (Регистрации)'
        verbose_name_plural = 'Связанные Компании (Регистрации)'


def person_photo_path(instance, filename):
    return 'company_{0}/person_{1}/photo.jpg'.format(instance.company.id, instance.id)


class ContactPerson(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_query_name='person',
                                verbose_name='Компания', null=True, blank=True)  ##

    category = models.CharField('Категория', max_length=50, default='DEFAULT', choices=contact_categories)  # DEFAULT или REPRESENTATIVE (поверенный) ##

    email = models.CharField('Электронная почта', max_length=255, null=True, blank=True)  # ##
    email_verified = models.BooleanField('Почта верифицирована', default=False)  ##
    email_correct = models.BooleanField('Почта корректна', default=True)  ##

    full_name = models.CharField('Полное имя', max_length=255, null=True, blank=True)  # ##
    first_name = models.CharField('Имя', max_length=50, null=True, blank=True)  ##
    middle_name = models.CharField('Отчество', max_length=50, null=True, blank=True)  ##
    last_name = models.CharField('Фамилия', max_length=50, null=True, blank=True)  ##
    nick_name = models.CharField('Никнейм', max_length=50, null=True, blank=True)  ##
    gender_choices = [
        (0, '-'),
        (1, 'М'),
        (2, 'Ж')
    ]
    gender = models.SmallIntegerField('Пол', choices=gender_choices, default=0)  ##
    job_title = models.CharField('Должность', max_length=50, null=True, blank=True)  ##

    # company_name = models.CharField('Наименование комании', max_length=100, null=True, blank=True)  # #
    # company_form = models.CharField(max_length=50, null=True, blank=True)  # ! # Организационная форма ООО
    # company_web = models.CharField(max_length=100, null=True, blank=True)

    personal_web = models.CharField('Персональный сайт', max_length=150, null=True, blank=True)  ##
    office_address = models.CharField('Адрес офиса', max_length=1000, null=True, blank=True)  # ! #  ##
    home_phone = models.CharField('Домашний телефон', max_length=25, null=True, blank=True)  ##
    office_phone = models.CharField('Оффисный телефон', max_length=25, null=True, blank=True)  ##
    mobile_phone = models.CharField('Мобильный телефон', max_length=25, null=True, blank=True)  ##
    messenger_id = models.CharField('ID в мессенджере', max_length=25, null=True, blank=True)  ##
    messenger_type = models.CharField('Мессенджер', max_length=25, null=True, blank=True)  ##
    fax = models.CharField('Факс', max_length=25, null=True, blank=True)  ##
    city = models.CharField('Город', max_length=255, null=True, blank=True)  # ! #  ##
    zip = models.IntegerField('Индекс', null=True, blank=True)  # ! #  ##
    area = models.CharField('Район', max_length=255, null=True, blank=True)  # ! #  ##
    state = models.CharField('Область', max_length=255, null=True, blank=True)  # ! #  ##
    country = models.CharField('Страна', max_length=255, null=True, blank=True)  # ! #  ##

    rep_reg_number = models.CharField('Рег номер поверенного', max_length=255, null=True, blank=True)  ##
    rep_correspondence_address = models.CharField('Адрес для корреспонденции поверенного', max_length=255, null=True, blank=True)  # ! #  ##

    photo = models.ImageField('Персональное фото', upload_to=person_photo_path, null=True, blank=True)  ##
    bday_date = models.DateField('День рождения', null=True, blank=True)  ##

    order = models.ManyToManyField(OrderDocument, related_query_name='person', blank=True)
    register = models.ManyToManyField(RegisterDocument, related_query_name='person', blank=True)

    date_corrected = models.DateField('Дата последней корректировки', auto_now=True, null=True, blank=True)

    def __str__(self):
        if self.full_name:
            return str(self.full_name) + ' ' + str(self.id)
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
    documents_parsed = models.IntegerField('Количество документов на один прокси', default=990)
    requests_period = models.IntegerField('Период запросов (сек)', default=3)
    requests_amount = models.IntegerField('Количество запросов за период', default=1)

    number_gte = models.CharField('С номера', max_length=20, null=True, blank=True)  # 2020706000
    number_lte = models.CharField('По номер', max_length=20, null=True, blank=True)  # 2020706099

    proxies_num = models.IntegerField('Количество используемых прокси')
    is_working = models.BooleanField('Парсер запущен')

    def __str__(self):
        type = 'orders' if self.type == 0 else 'registers'
        return 'Настройки для ' + type + ' ' + str(self.id)


# Таблица для API ключей для верификации почты
class EmailApiKey(models.Model):
    api_key = models.CharField('API Ключ', max_length=100)
    is_valid = models.BooleanField(default=True)

    def __str__(self):
        return str(self.api_key)

    class Meta:
        verbose_name = 'API ключ'
        verbose_name_plural = 'API ключи'


# Записи использования API ключа
class EmailApiKeyLog(models.Model):
    api_key = models.ForeignKey(EmailApiKey, on_delete=models.CASCADE, null=True)
    date_created = models.DateTimeField('Дата создания', auto_now_add=True)
    email_verified = models.CharField('Верифицируемый имейл', max_length=255, null=True)
    email_is_valid = models.BooleanField('Валидация успешна')
    result = models.TextField('Результат верификации', max_length=1000)

    def __str__(self):
        return str(self.api_key)

    class Meta:
        verbose_name = 'Использование API ключа'
        verbose_name_plural = 'Использование API ключей'

    def get_absolute_url(self):
        return f'/admin/interface/emailapikeylog/{self.id}/change/'

