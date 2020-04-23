# Общие модели для orders и registers
from django.db import models


# Лист раскрывающегося аккордиона на сайте со списком заявок
class Leaf(models.Model):
    name = models.CharField(max_length=50, unique=True)  # Имя в виде 2013742400 - 2013742499
    a_href_steps = models.TextField(max_length=1000)  # Список урлов для перехода к списку документов. JSON объект
    done = models.BooleanField(default=False)  # TRUE - Если в этой ветке нет обновляемых документов

    def __str__(self):
        return str(self.name)

    class Meta:
        verbose_name = 'Список документов'
        verbose_name_plural = '2 Списки документов'


# Документ в составе листа
class Document(models.Model):
    leaf = models.ForeignKey(Leaf, on_delete=models.CASCADE)  # ID листа, в состав которого входил документ

    number = models.IntegerField('Номер документа')  # Идентификатор документа в реестре в виде 2013742400
    url = models.URLField('Ссылка', max_length=200)  # Ссылка на документ
    document_exists = models.BooleanField('Наличие документа', default=True)  # False - если документа нет в реестре
    document_parsed = models.BooleanField('Документ спарсен', default=False)  # False - если документ не был спарсен
    order_done = models.BooleanField('Не обновлять', default=False)  # True - если документ не обновляемый
    downloaded_page = models.CharField('Сохраненная на диске страница',
                                       max_length=200, null=True)  # Скачанная страница документа
    date_parsed = models.DateField('Дата парсинга', null=True)

    class Meta:
        verbose_name = 'Документ'
        verbose_name_plural = '1 Документы'

    def __str__(self):
        return str(self.number)

    def get_absolute_url(self):
        return f'/admin/orders/document/{self.id}/change/'


# Напарсенная информация документа
class DocumentParse(models.Model):
    document = models.OneToOneField(Document, on_delete=models.CASCADE)  # ID документа, из таблицы Order

    applicant = models.CharField('Заявитель', max_length=500, null=True)  # Заявитель документа
    address = models.CharField('Адрес для переписки', max_length=500, null=True)  # Аддрес заявителя
    copyright_holder = models.CharField('Правообладатель', max_length=500, null=True)  # Правообладатель
    sign_char = models.CharField('Указание, относящееся к виду знака, и его характеристики', max_length=500, null=True)  # Характеристики знака

    status = models.CharField('Статус', max_length=200)  # Спарсенный статус документа
    order_type = models.CharField('Тип', max_length=200)  # Тип документа (реестра) BibType
    patent_atty = models.CharField('Патентный поверенный', max_length=200, null=True)
    color = models.CharField('Цветовое сочетание', max_length=200, null=True)

    order_number = models.IntegerField('Номер заявки', null=True)  # Номер документа в реестре
    first_order_number = models.CharField('Номер первой заявки', max_length=20, null=True)  # Номер первой заявки
    order_register_number = models.IntegerField('Номер регистрации', null=True)  # Номер документа в реестре
    first_order_country_code = models.CharField('Код страны подачи первой заявки', max_length=10, null=True)  # Код страны подачи первой заявки
    volumetric = models.CharField('Объемный знак', max_length=50, null=True)  # Объемный знак
    unprotected = models.CharField('Неохраняемые элементы товарного знака', max_length=255, null=True)  # Неохраняемые элементы товарного знака

    date_refreshed = models.DateField('Дата обновления', null=True)  # Дата обновления документа. Парсится из статуса
    date_created = models.DateField('Дата поступления заявки', null=True)  # Дата поступления документа
    date_publish = models.DateField('Дата публикации заявки', null=True)  # Дата принятия решение по заявке
    date_exclusive = models.DateField('Дата истечения срока действия исключительного права', null=True)  # Дата истечения срока действия исключительного права
    first_order_date = models.DateField('Дата подачи первой заявки', null=True)  # Дата подачи первой заявки
    date_gos_reg = models.DateField('Дата государственной регистрации', null=True)  # Дата государственной регистрации
    date_changes = models.DateField('Дата внесения записи в Государственный реестр', null=True)

    order_info = models.TextField('Информация', max_length=2000, null=True)  # Другая напарсенная информация в виде JSON
    service_items = models.CharField(max_length=2000, null=True)  # Список классов МКТУ через запятую

    class Meta:
        verbose_name = 'Парсинг документа'
        verbose_name_plural = '3 Парсинг документов'

    def __str__(self):
        return str(self.id)

    def get_absolute_url(self):
        return f'/admin/orders/documentparse/{self.id}/change/'


# Дополнительная таблица. Формирует "Классы МКТУ и перечень товаров и услуг"
class ServiceItem(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_query_name='serviceitem')
    document_parse = models.ForeignKey(DocumentParse, on_delete=models.CASCADE,
                                       related_query_name='serviceitem')  # ID парсинга документа
    number = models.CharField('Номер класса', max_length=5)  # Номер класса
    text = models.TextField(max_length=30000)  # Текст класса

    class Meta:
        verbose_name = 'МКТУ элемент'
        verbose_name_plural = 'МКТУ элементы'

    def __str__(self):
        return str(self.number)


# 'Факсимильные изображения' и другие файлы, прикрепленные к документу
class DocumentFile(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    document_parse = models.ForeignKey(DocumentParse, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    direct_url = models.URLField('Прямая ссылка', max_length=200)
    link = models.URLField('Ссылка', max_length=200, unique=True)

    class Meta:
        verbose_name = 'Прикрепленный файл'
        verbose_name_plural = 'Прикрепленные файлы'

    def __str__(self):
        return str(self.document_parse.id)

    def get_absolute_url(self):
        return self.link


document_parse_dict = {
    'field__id': {'string': 'ID документа', 'ordering': True, 'chosen': False},
    'field__number': {'string': 'Номер Документа', 'ordering': True, 'chosen': False},
    'field__url': {'string': 'Ссылка на документ', 'ordering': True, 'chosen': False},
    'field__document_exists': {'string': 'Наличие документа', 'ordering': True, 'chosen': False},
    'field__document_parsed': {'string': 'Документ спарсен', 'ordering': True, 'chosen': False},
    'field__date_parsed': {'string': 'Дата парсинга', 'ordering': True, 'chosen': False},
    'field__documentparse__id': {'string': 'ID', 'ordering': True, 'chosen': False},
    'field__documentparse__applicant': {'string': 'Заявитель', 'ordering': True, 'chosen': False},
    'field__documentparse__address': {'string': 'Адрес для переписки', 'ordering': True, 'chosen': False},
    'field__documentparse__copyright_holder': {'string': 'Правообладатель', 'ordering': True, 'chosen': False},
    'field__documentparse__sign_char': {'string': 'Знак, и его хар-ки', 'ordering': True, 'chosen': False},
    'field__documentparse__status': {'string': 'Статус', 'ordering': True, 'chosen': False},
    'field__documentparse__order_type': {'string': 'Тип заявки', 'ordering': True, 'chosen': False},
    'field__documentparse__patent_atty': {'string': 'Патентный поверенный', 'ordering': True, 'chosen': False},
    'field__documentparse__color': {'string': 'Цветовое сочетание', 'ordering': True, 'chosen': False},
    'field__documentparse__order_number': {'string': 'Номер заявки', 'ordering': True, 'chosen': False},
    'field__documentparse__first_order_number': {'string': 'Номер 1-й заявки', 'ordering': True, 'chosen': False},
    'field__documentparse__order_register_number': {'string': 'Номер рег-ции', 'ordering': True, 'chosen': False},
    'field__documentparse__first_order_country_code': {'string': 'Код страны 1-й з.', 'ordering': True, 'chosen': False},
    'field__documentparse__volumetric': {'string': 'Объемный знак', 'ordering': True, 'chosen': False},
    'field__documentparse__unprotected': {'string': 'Неохраняемые эл-ты', 'ordering': True, 'chosen': False},
    'field__documentparse__date_refreshed': {'string': 'Дата обновл.', 'ordering': True, 'chosen': False},
    'field__documentparse__date_created': {'string': 'Дата поступ. заявки', 'ordering': True, 'chosen': False},
    'field__documentparse__date_publish': {'string': 'Дата публ. заявки', 'ordering': True, 'chosen': False},
    'field__documentparse__date_exclusive': {'string': 'Дата истеч. срока', 'ordering': True, 'chosen': False},
    'field__documentparse__first_order_date': {'string': 'Дата 1-й заявки', 'ordering': True, 'chosen': False},
    'field__documentparse__date_gos_reg': {'string': 'Дата гос. рег-ции', 'ordering': True, 'chosen': False},
    'field__documentparse__date_changes': {'string': 'Дата внесения', 'ordering': True, 'chosen': False},
    'field__documentparse__order_info': {'string': 'Доп. информация', 'ordering': True, 'chosen': False},
    'field__documentparse__service_items': {'string': 'Классы МКТУ', 'ordering': True, 'chosen': False},
    'field__documentparse__documentfile_set__count': {'string': 'К-во документов', 'ordering': False},
    'field__documentparse__workstate__income': {'string': 'Вх. Корресп.', 'ordering': True, 'chosen': False},
    'field__documentparse__workstate__outcome': {'string': 'Исх. Корресп.', 'ordering': True, 'chosen': False},
}
