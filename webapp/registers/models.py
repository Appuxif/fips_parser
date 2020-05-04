from django.db import models
from registers.models_base import DocumentParse, Document


# Извещение в составе документа о регистрации
class DocumentIzv(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE,
                                 related_query_name='izv')
    document_parse = models.ForeignKey(DocumentParse, on_delete=models.CASCADE,
                                       related_query_name='izv')
    # unique_index = models.SmallIntegerField()  # Уникальный идентификатор для группы извещений
    unique_field = models.CharField(max_length=35, unique=True)  # Уникальное поле uuid4, чтобы привязывать связанные объекты
    izv_type = models.CharField('Тип извещения', max_length=500, blank=True)  # Тип извещения - самая первая строчка

    address = models.CharField('Адрес для переписки', max_length=500, null=True, blank=True)
    last_copyright_holder = models.CharField('Прежний правообладатель', max_length=500, null=True, blank=True)
    last_copyright_holder_name = models.CharField('Прежнее наименование правообладателя',
                                                  max_length=500, null=True, blank=True)
    copyright_holder = models.CharField('Правообладатель', max_length=500, null=True, blank=True)
    transferor = models.CharField('Лицо, передающее исключительное право', max_length=500, null=True, blank=True)
    contract_type = models.CharField('Вид договора', max_length=500, null=True, blank=True)
    contract_terms = models.CharField('Указание условий договора', max_length=2000, null=True, blank=True)
    grantor = models.CharField('Лицо, предоставляющее право использования', max_length=500, null=True, blank=True)
    granted = models.CharField('Лицо, которому предоставлено право использования',
                               max_length=500, null=True, blank=True)
    licensee = models.CharField('Лицензиат', max_length=2000, null=True, blank=True)
    sublicensee = models.CharField('Сублицензиат', max_length=2000, null=True, blank=True)
    date_number_changes = models.CharField('Дата и номер государственной регистрации договора',
                                           max_length=100, null=True, blank=True)
    info = models.TextField(max_length=2000, null=True, blank=True)

    date_changes = models.DateField('Дата внесения записи в Государственный реестр', null=True, blank=True)
    date_publish = models.DateField('Дата публикации извещения', null=True, blank=True)
    date_renewal = models.DateField('Дата, до которой продлен срок действия исключительного права', null=True, blank=True)
    date_ended = models.DateField('Дата прекращения правовой охраны', null=True, blank=True)
    service_items = models.CharField('Список МКТУ', max_length=2000, null=True, blank=True)  # Список классов МКТУ через запятую

    class Meta:
        verbose_name = 'Извещение'
        verbose_name_plural = 'Извещения'

    def __str__(self):
        return self.izv_type

    def get_absolute_url(self):
        return f'/admin/registers/documentizv/{self.id}/change/'


# Дополнительная нераспознанная строчка из извещения
class DocumentIzvItem(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE,
                                 related_query_name='izvitem')
    document_izv = models.ForeignKey(DocumentIzv, on_delete=models.CASCADE,
                                     to_field='unique_field', related_query_name='izvitem')
    full_text = models.TextField(null=True)
    key = models.CharField(max_length=2000)
    value = models.TextField(max_length=10000, null=True, blank=True)
    date = models.DateField(null=True, blank=True)  # Если есть дата, она будет распознана

    class Meta:
        verbose_name = 'Элемент извещения'
        verbose_name_plural = 'Элементы извещений'

    def __str__(self):
        return self.key

    def get_absolute_url(self):
        return f'/admin/registers/documentizvitem/{self.id}/change/'


# Дополнительная таблица. Формирует "Классы МКТУ и перечень товаров и услуг"
class IzvServiceItem(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_query_name='izvserviceitem')
    document_izv = models.ForeignKey(DocumentIzv, on_delete=models.CASCADE,
                                     to_field='unique_field', related_query_name='izvserviceitem')
    number = models.CharField('Номер класса', max_length=50)  # Номер класса
    text = models.TextField(max_length=30000)  # Текст класса

    class Meta:
        verbose_name = 'МКТУ извещения'
        verbose_name_plural = 'МКТУ извещений'

    def __str__(self):
        return str(self.number)


class ParserHistory(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True)
    is_error = models.BooleanField(default=False, blank=True)
    error_log_file = models.CharField(max_length=255, null=True, blank=True)
    message = models.TextField(max_length=2000, null=True, blank=True)

    def __str__(self):
        return 'History ' + str(self.document.number)

    def get_absolute_url(self):
        if self.is_error:
            return str(self.error_log_file)
        return f'/admin/registers/parserhistory/{self.id}/change/'
