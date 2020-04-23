import traceback
import pymysql
import sqlite3
import os.path
import sys

from config import DBHOST, DBNAME, DBPASS, DBUSERNAME, USE_SQLITE3


def insert_into_query(table_name, row, replace=False):
    insert = 'REPLACE' if replace else 'INSERT'
    fields = []
    values = []
    for key in row:
        fields.append(key)
        values.append(f"{row[key]}")
    return f"{insert} INTO {table_name} ({', '.join(fields)}) VALUES ({', '.join(values)})"


def update_by_id_query(table_name, row):
    query = f'UPDATE {table_name} SET '
    queries = [f"{key} = {row[key] if row[key] is not None else 'NULL'}" for key in row if key != 'id']
    query += ', '.join(queries)
    query += f" WHERE id = {row['id']}"
    return query


class DB:
    def __init__(self):
        if USE_SQLITE3:
            self.conn = sqlite3.connect(os.path.join('.', 'webapp', 'db.sqlite3'))
            self.conn.row_factory = sqlite3.Row
            self.c = self.conn.cursor()
        else:
            self.conn = pymysql.connect(DBHOST, DBUSERNAME, DBPASS, DBNAME, charset="utf8",
                                        use_unicode=True, cursorclass=pymysql.cursors.DictCursor)
            self.c = self.conn.cursor()

    def executeone(self, query):
        try:
            self.c.execute(query)
            self.conn.commit()
            return self.c.lastrowid
        finally:
            self.c.close()
            self.conn.close()

    def executemany(self, queries, verbose=False):
        try:
            for query in queries:
                if verbose:
                    print(query, '\n')
                try:
                    self.c.execute(query)
                except Exception as err:
                    traceback.print_exc(file=sys.stdout)
                    print(query)
                    return
            self.conn.commit()
            return self.c.lastrowid
        finally:
            self.c.close()
            self.conn.close()

    def fetchone(self, query):
        try:
            self.c.execute(query)
            return self.c.fetchone()
        finally:
            self.c.close()
            self.conn.close()

    def fetchall(self, query):
        try:
            self.c.execute(query)
            return self.c.fetchall()
        finally:
            self.c.close()
            self.conn.close()

    def db_create(self, table_name, lis):
        # query = f'CREATE TABLE IF NOT EXISTS {table_name} ({" VARCHAR(1000),".join(lis)} VARCHAR(1000))'
        query = f'CREATE TABLE IF NOT EXISTS {table_name} ({", ".join(lis)})'
        self.executeone(query)

    def add_row(self, table_name, row):
        # row is dict!
        query = insert_into_query(table_name, row)
        return self.executeone(query)

    def update_row(self, table_name, row):
        # row is dict!
        query = update_by_id_query(table_name, row)
        return self.executeone(query)

