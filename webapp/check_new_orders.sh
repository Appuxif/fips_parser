cd /var/www/fips_parser/webapp
sh /var/www/fips_parser/venv/bin/python -c "from orders_parser import *; p = OrdersParser(ORDERS_URL, 'orders'); p.check_new_documents()"