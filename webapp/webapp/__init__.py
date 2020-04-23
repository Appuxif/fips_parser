from config import USE_SQLITE3
if not USE_SQLITE3:
    import pymysql
    pymysql.install_as_MySQLdb()