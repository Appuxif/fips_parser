from django.db import models
from orders.models_base import DocumentParse, Document


# Состояние делопроизводства
class WorkState(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    document_parse = models.OneToOneField(DocumentParse, on_delete=models.CASCADE)
    income = models.TextField('Входящая корреспонденция', max_length=2000, null=True)  # Полный текст входящей корреспонденции
    outcome = models.TextField('Исходящая корреспонденция', max_length=2000, null=True)  # Полный текст исходящей корреспонденции

    class Meta:
        verbose_name = 'Делопроизводство'
        verbose_name_plural = 'Делопроизводство'

    def __str__(self):
        return 'For ' + str(self.document_parse.id) + ' ' + str(self.document_parse.order_number)

    def get_absolute_url(self):
        return f'/admin/orders/workstate/{self.id}/change/'


# Строчка из таблицы делопроизводства
class WorkStateRow(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    workstate = models.ForeignKey(WorkState, on_delete=models.CASCADE)
    type = models.CharField('Тип строки делопроизводства', max_length=20)  # 0-income or 1-outcome
    key = models.CharField('Наименование', max_length=200)  # Первый столбец: Наименование строки
    date = models.DateField('Дата наименования', null=True)  # Второй столбец: Дата

    class Meta:
        verbose_name = 'Строка из делопроизводства'
        verbose_name_plural = 'Строки из делопроизводства'

    def __str__(self):
        return 'For ' + str(self.workstate.id)
