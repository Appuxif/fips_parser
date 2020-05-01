cd /var/www/fips_parser/webapp
sudo ../venv/bin/python -c "from orders_parser import *; p = OrdersParser(ORDERS_URL, 'orders'); p.check_new_documents()"