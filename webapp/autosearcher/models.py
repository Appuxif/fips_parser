from django.db import models


# Список всех полей, по которым возможна фильтрация в документах
filter_field_choices = [
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
    ('documentparse__date_refreshed', 'Дата обновл'),
    ('documentparse__date_created', 'Дата поступ. заявки'),
    ('documentparse__date_publish', 'Дата публ. заявки'),
    ('documentparse__date_exclusive', 'Дата истеч. срока'),
    ('documentparse__first_order_date', 'Дата 1-й заявки'),
    ('documentparse__date_gos_reg', 'Дата гос. рег-ции'),
    ('documentparse__date_changes', 'Дата внесения'),
    ('serviceitem__text', ''),
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


# Модель для задачи автопоиска документов и распределения этих документов по корректорам
class AutoSearchTask(models.Model):
    task_name = models.CharField('Имя задачи', max_length=50)
    registry_type_choices = [
        (0, 'orders'),
        (1, 'registers'),
    ]
    registry_type = models.IntegerField('Тип реестра для поиска', choices=registry_type_choices, default=0)
    renew_in_days = models.IntegerField('Следующее срабатывание через (дней)', null=True, blank=True)
    renew_in_hours = models.IntegerField('Следующее срабатывание через (часов)', null=True, blank=True)
    next_action = models.DateTimeField('Дата следующего срабатывания', null=True)
    last_launch = models.DateTimeField('Дата предыдущего срабатывания')
    auto_renew = models.BooleanField('Автопродление', default=False)

    def __str__(self):
        return str(self.task_name)

    class Meta:
        verbose_name = "Задача автопоиска"
        verbose_name_plural = "Задачи автопоиска"


# Элемент задачи автопоиска для фильтрации документов
class AutoSearchTaskItem(models.Model):
    autosearchtask = models.ForeignKey(AutoSearchTask, on_delete=models.CASCADE)
    filter_field = models.SmallIntegerField('Поле для фильтра', choices=filter_field_choices)
    filter_method = models.CharField('Метод для фильтрации', choices=filter_method_choices)
    filter_value = models.CharField('Значение для фильтрации', max_length=500)
    except_field = models.BooleanField('Кроме', default=False)
    # raw_filter = models.CharField('Полученное выражение для фильтра', max_length=1000)

    def __str__(self):
        return str(self.filter_field) + str(self.filter_method) + '=' + str(self.filter_value)