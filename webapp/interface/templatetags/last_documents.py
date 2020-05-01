from django import template

from orders.models_base import Document as OrdersDocument
from registers.models_base import Document as RegistersDocument

register = template.Library()


class LastDocumentsNode(template.Node):
    def __init__(self, orders, registers):
        self.orders, self.registers = orders, registers

    def __repr__(self):
        return "<GetAdminLog Node>"

    def render(self, context):
        # last_documents_list = list(self.orders[:10]) + list(self.registers[:10])
        # last_documents_list = zip(self.orders[:5], self.registers[:5])
        # context['last_documents_list'] = sorted(last_documents_list, key=lambda x: x.id)
        context['last_orders'] = self.orders[:5]
        context['last_registers'] = self.registers[:5]
        return ''


@register.tag
def get_last_documents(parser, token):
    orders = OrdersDocument.objects.filter(document_parsed=True).order_by('-id')
    registers = RegistersDocument.objects.filter(document_parsed=True).order_by('-id')
    return LastDocumentsNode(orders, registers)
