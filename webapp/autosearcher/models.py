from django.db import models
from django.contrib.auth.models import User

from orders.models_base import Document as OrderDocument
from registers.models_base import Document as RegisterDocument


# Список всех полей, по которым возможна фильтрация в документах
filter_field_choices = [
    (None, '-'),
    ('number', 'Номер документа'),
    ('documentparse__applicant', 'Заявитель'),
    ('documentparse__address', 'Адрес для переписки'),
    ('documentparse__copyright_holder', 'Правообладатель'),
    ('documentparse__sign_char', 'Знак, и его хар-ки'),
    ('documentparse__status', 'Статус'),
    ('documentparse__order_type', 'Тип заявки'),
    ('documentparse__patent_atty', 'Патентный поверенный'),
    ('documentparse__order_number', 'Номер заявки'),
    ('documentparse__order_register_number', 'Номер рег-ции'),
    ('documentparse__date_refreshed', 'Дата обновления'),
    ('documentparse__date_created', 'Дата поступ. заявки'),
    ('documentparse__date_publish', 'Дата публ. заявки'),
    ('documentparse__date_exclusive', 'Дата истеч. срока'),
    ('documentparse__first_order_date', 'Дата 1-й заявки'),
    ('documentparse__date_gos_reg', 'Дата гос. рег-ции'),
    ('documentparse__date_changes', 'Дата внесения'),
    ('serviceitem__text', 'Классы МКТУ. Текст'),
    ('izv__izv_type', 'Тип извещения'),
    ('izv__address', 'Извещения. Адресс для переписки'),
    ('izv__last_copyright_holder', 'Извещения. Прежний правообладатель'),
    ('izv__last_copyright_holder_name', 'Извещения. Прежнее наименование'),
    ('izv__copyright_holder', 'Извещения. Правообладатель'),
    ('izv__transferor', 'Извещения. Передающий права'),
    ('izv__contract_type', 'Извещения. Вид договора'),
    ('izv__contract_terms', 'Извещения. Условия договора'),
    ('izv__grantor', 'Извещения. Предоставляющий право использования'),
    ('izv__granted', 'Извещения. Принимающий право использования'),
    ('izv__licensee', 'Извещения. Лицензиат'),
    ('izv__sublicensee', 'Извещения. Сублицензиат'),
    ('izv__date_changes', 'Извещения. Дата внесения записи'),
    ('izv__date_publish', 'Извещения. Дата публикации'),
    ('izv__date_renewal', 'Извещения. Дата продления'),
    ('izvitem__key', 'Извещения. Другое поле'),
    ('izvitem__date', 'Извещения. Дата в другом поле'),
]

filter_method_choices = [
    (None, '-'),
    ('__exact', 'Точное совпадение (чувствительно к регистру)'),
    ('__iexact', 'Точное совпадение (нечувствительно к регистру)'),
    ('__contains', 'Содержит (чувствительно к регистру)'),
    ('__icontains', 'Содержит (нечувствительно к регистру)'),
    ('__in', 'Значения через запятую'),
    ('__gt', 'Строго больше'),
    ('__gte', 'Больше или равно'),
    ('__lt', 'Строго меньше'),
    ('__lte', 'Меньше или равно'),
    ('__startswith', 'Начинается с (чувствительно к регистру)'),
    ('__istartswith', 'Начинается с (нечувствительно к регистру)'),
    ('__endswith', 'Оканчивается на (чувствительно к регистру)'),
    ('__iendswith', 'Оканчивается на (нечувствительно к регистру)'),
]

registry_type_choices = [
    (0, 'orders'),
    (1, 'registers'),
]


# Модель для задачи автопоиска документов и распределения этих документов по корректорам
class AutoSearchTask(models.Model):
    task_name = models.CharField('Имя задачи', max_length=50)
    registry_type = models.IntegerField('Тип реестра для поиска', choices=registry_type_choices, default=0)
    renew_in_days = models.IntegerField('Следующее срабатывание через (дней)', null=True, blank=True)
    renew_in_hours = models.IntegerField('Следующее срабатывание через (часов)', null=True, blank=True)
    next_action = models.DateTimeField('Дата следующего срабатывания', null=True)
    last_launch = models.DateTimeField('Дата предыдущего срабатывания', null=True, blank=True)

    auto_renew = models.BooleanField('Автопродление', default=False)
    is_active = models.BooleanField('Задача активна', default=False)

    def __str__(self):
        return str(self.task_name)

    class Meta:
        verbose_name = "Задача автопоиска"
        verbose_name_plural = "Задачи автопоиска"


# Элемент задачи автопоиска для фильтрации документов
class AutoSearchTaskItem(models.Model):
    autosearchtask = models.ForeignKey(AutoSearchTask, on_delete=models.CASCADE)
    filter_field = models.CharField('Поле для фильтра', max_length=50,
                                    choices=filter_field_choices, null=True, blank=True)
    filter_field_raw = models.CharField('Поле для фильтра', max_length=50, null=True, blank=True)
    filter_method = models.CharField('Метод для фильтрации', max_length=50,
                                     choices=filter_method_choices, null=True, blank=True)
    filter_method_raw = models.CharField('Метод для фильтрации', max_length=50, null=True, blank=True)
    filter_value = models.CharField('Значение для фильтрации', max_length=1000,
                                    help_text='Если дата, то в формате YYYY-MM-DD')
    except_field = models.BooleanField('Кроме', default=False)
    # raw_filter = models.CharField('Полученное выражение для фильтра', max_length=1000)

    def __str__(self):
        return str(self.filter_field or self.filter_field_raw or '') + \
               str(self.filter_method or self.filter_method_raw or '') +\
               "='" + str(self.filter_value) + "'"

    class Meta:
        verbose_name = "Элемент задачи автопоиска"
        verbose_name_plural = "Элементы задач автопоиска"


# Модель для личного кабинета корректора и его настроек
class Corrector(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    sign_chars = models.TextField('Коды стран через запятую', max_length=2000, null=True, blank=True,
                                  help_text='Например: RU,GB,NL')
    company_startswith = models.CharField('Название компании начинается с',
                                          max_length=50, null=True, blank=True, help_text='Например: а-н')
    tasks_day_amount = models.IntegerField('Количество задач в день', default=200, blank=True)
    tasks_max = models.IntegerField('Максимальное количество задач', default=600, blank=True)
    # tasks_today = models.IntegerField('Количество задач, добавленное сегодня', default=0, blank=True)
    score = models.IntegerField('Баллы корректора', default=0, blank=True)
    tasks_done = models.IntegerField('Задач выполнено', default=0, blank=True)
    task_last_added_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField('Корректор активен', default=True,
                                    help_text='Определяет, будет ли корректор участвовать в распределении')
    score_0 = models.SmallIntegerField('Балл за выполнение задачи в тот же день', default=5)
    score_1 = models.SmallIntegerField('Балл за выполнение задачи через день', default=4)
    score_2 = models.SmallIntegerField('Балл за выполнение задачи через два дня', default=3)
    score_3 = models.SmallIntegerField('Балл за выполнение задачи через три и больше дней', default=2)

    def __str__(self):
        return str(self.user.username)

    class Meta:
        verbose_name = 'Корректор'
        verbose_name_plural = 'Корректоры'

    @property
    def tasks_done_amount(self):
        return self.correctortask_set.filter(task_done=True).count()

    @property
    def tasks_not_done_amount(self):
        return self.correctortask_set.filter(task_done=False).count()


# Задача для корректора.
class CorrectorTask(models.Model):
    corrector = models.ForeignKey(Corrector, on_delete=models.CASCADE, related_query_name='task')
    document_registry = models.IntegerField('Тип реестра', choices=registry_type_choices, default=0)
    document_id = models.CharField('ID документа задачи', max_length=30, null=True, blank=True)
    datetime_created = models.DateTimeField('Дата создания задачи', auto_now_add=True)
    date_created = models.DateField('Дата создания задачи', auto_now_add=True)
    date_task_done = models.DateTimeField('Дата завершения задачи', null=True, blank=True)
    task_done = models.BooleanField('Задача завершена', default=False)
    task_cannot_be_done = models.BooleanField('Задача не может быть завершена', default=False)
    note = models.CharField('Примечание', max_length=255, null=True, blank=True)

    def __str__(self):
        return str(self.corrector) + ' ' + str(self.document_registry_name) + ' ' + self.document_number

    class Meta:
        verbose_name = 'Задача корректора'
        verbose_name_plural = 'Задачи корректора'

    def get_absolute_url(self):
        registry = self.document_registry_name
        return f'/admin/{registry}/document/{self.document_id}/change/'

    @property
    def document_number(self):
        Document = OrderDocument if self.document_registry == 0 else RegisterDocument
        doc = Document.objects.get(id=self.document_id)
        return str(doc.number)

    @property
    def document_registry_name(self):
        registry = 'orders'
        for reg in registry_type_choices:
            if reg[0] == self.document_registry:
                registry = reg[1]
        return registry


class AutoSearchLog(models.Model):
    task = models.ForeignKey(AutoSearchTask, on_delete=models.DO_NOTHING, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    is_error = models.BooleanField(default=False)
    log_file = models.CharField(max_length=255, null=True, blank=True)
    message = models.TextField(max_length=10000, null=True, blank=True)

    def __str__(self):
        return 'TaskLog ' + str(self.task.task_name)

    def get_absolute_url(self):
        # if self.is_error:
        return str(self.log_file)
        # return f'/admin/autosearcher/autosearchlog/{self.id}/change/'

    class Meta:
        verbose_name = 'Лог автопоиска'
        verbose_name_plural = 'Логи автопоиска'


# Задача для формирования списка рассылки по расписанию
class MailingTask(models.Model):
    autosearchtask = models.ForeignKey(AutoSearchTask, on_delete=models.CASCADE, verbose_name='Задача Автопоиска')
    renew_in_days = models.IntegerField('Следующее срабатывание через (дней)', null=True, blank=True)
    renew_in_hours = models.IntegerField('Следующее срабатывание через (часов)', null=True, blank=True)
    next_action = models.DateTimeField('Дата следующего срабатывания', null=True)
    last_launch = models.DateTimeField('Дата предыдущего срабатывания', null=True, blank=True)
    categories = models.CharField('Порядок выбора адресатов', max_length=255, null=True, blank=True,
                                  default='DIRECTOR, EXECUTOR, DEFAULT, REPRESENTATIVE',
                                  help_text='DIRECTOR, EXECUTOR, DEFAULT, REPRESENTATIVE')
    auto_renew = models.BooleanField('Автопродление', default=False)
    is_active = models.BooleanField('Задача активна', default=False)

    # distribution_query = models.TextField('Запрос для списка контактов', null=True, blank=True)

    def __str__(self):
        return 'Рассылка для ' + str(self.autosearchtask.task_name)

    class Meta:
        verbose_name = "Задача Списка Рассылок"
        verbose_name_plural = "Задачи Списка Рассылок"


# Элемент таблицы со списками для рассылки
class MailingItem(models.Model):
    # autosearchtask = models.ForeignKey(AutoSearchTask, on_delete=models.CASCADE, verbose_name='Задача Автопоиска')
    mailingtask = models.ForeignKey(MailingTask, on_delete=models.CASCADE, verbose_name='Задача Автопоиска рассылок')
    contactperson_id = models.IntegerField('ID контакта', null=True, blank=True)
    document_id = models.IntegerField('ID документа', null=True, blank=True)
    documentparse_id = models.IntegerField('ID парсинга документа', null=True, blank=True)
    document_image = models.CharField('Ссылка на изображение', max_length=500, null=True, blank=True)
    status = models.CharField('Статус', max_length=50, null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)

    documents_list = models.CharField('Дополнительный список документов', max_length=2000, null=True, blank=True)

    def __str__(self):
        return 'Item ' + str(self.mailingtask)

    class Meta:
        verbose_name = "Элемент списка рассылок"
        verbose_name_plural = "Элементы списка рассылок"
