cd /var/www/fips_parser/webapp
sudo ../venv/bin/python -c "from registers_parser import *; p = RegistersParser(REGISTERS_URL, 'registers'); p.check_new_documents()"