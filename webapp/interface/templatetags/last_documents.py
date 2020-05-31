from django import template

from orders.models_base import Document as OrdersDocument
from registers.models_base import Document as RegistersDocument

register = template.Library()


class LastDocumentsNode(template.Node):
    def __init__(self):
        self.orders_count = OrdersDocument.objects.count()
        self.registers_count = RegistersDocument.objects.count()
        self.orders = OrdersDocument.objects.filter(document_parsed=True).order_by('-date_parsed')
        self.orders_parsed = self.orders.count()
        self.registers = RegistersDocument.objects.filter(document_parsed=True).order_by('-date_parsed')
        self.registers_parsed = self.registers.count()

    def __repr__(self):
        return "<GetAdminLog Node>"

    def render(self, context):
        # last_documents_list = list(self.orders[:10]) + list(self.registers[:10])
        # last_documents_list = zip(self.orders[:5], self.registers[:5])
        # context['last_documents_list'] = sorted(last_documents_list, key=lambda x: x.id)
        orders_count = self.orders.count()
        registers_count = self.registers.count()
        # context['last_orders'] = self.orders[:5]
        # context['last_registers'] = self.registers[:5]
        context['orders_percent'] = str(self.orders_parsed) + ' из ' + str(self.orders_count)
        context['registers_percent'] = str(self.registers_parsed) + ' из ' + str(self.registers_count)
        return ''


@register.tag
def get_last_documents(parser, token):
    return LastDocumentsNode()
