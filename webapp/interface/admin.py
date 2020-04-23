from django.contrib import admin
# from .models import Order, OrderLeaf
#
#
# # Для отображения лайков на странице анкеты в админке
# class OrdersInLine(admin.TabularInline):
#     model = Order
#     extra = 0
#     fields = ('name', 'url', 'document_exists', 'document_parsed', )
#     readonly_fields = fields
#
#
# @admin.register(OrderLeaf)
# class OrderLeafAdmin(admin.ModelAdmin):
#     # В списке задач появятся следующие столбцы
#     list_display = ('id', 'name', 'registry_type', 'done')
#     search_fields = ['id', 'name', 'registry_type']
#     exclude = ['a_href_steps']
#     inlines = [OrdersInLine]
#
#
# @admin.register(Order)
# class OrderAdmin(admin.ModelAdmin):
#     # В списке задач появятся следующие столбцы
#     list_display = ('id', 'name', 'url', 'document_exists', 'document_parsed')
#     search_fields = ['id', 'name', 'url']
