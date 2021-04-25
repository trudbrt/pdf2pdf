from contextlib import closing as contextlib_closing
import sqlite3 as sql
import time

from .params import Cols, Paths


class Db(object):

    db_uri = Paths.DB_PATH
    local_table = None
    shared_table = 'hq'

    create_table_template = f'CREATE TABLE IF NOT EXISTS {{}} ({Cols.ARTTEXT1} TEXT, {Cols.ARTTEXT2} TEXT, {Cols.ARTNR} INTEGER, {Cols.PREIS} REAL, {Cols.DATUM} INTEGER)'
    read_from_table_template = f'SELECT {Cols.ARTTEXT1}, {Cols.ARTTEXT2} FROM {{}} WHERE {Cols.ARTNR} = ?'
    write_to_table_template = f'INSERT OR IGNORE INTO {{}} ({Cols.ARTNR}, {Cols.ARTTEXT1}, {Cols.ARTTEXT2}, {Cols.PREIS}, {Cols.DATUM}) VALUES (?, ?, ?, ?, ?)'
    update_table_template = f'UPDATE {{}} SET {Cols.ARTTEXT1} = ?, {Cols.ARTTEXT2} = ?, {Cols.PREIS} = ?, {Cols.DATUM} = ? WHERE {Cols.ARTNR} = ?'


def setup_local_table(filnr=None):
    try:
        with contextlib_closing(sql.connect(Db.db_uri, uri=True)) as conn:
            if filnr:
                with contextlib_closing(conn.cursor()) as cur:
                    cur.execute(Db.create_table_template.format(filnr))
                    Db.local_table = filnr
        return True
    except sql.OperationalError:
        print('Keine Verbindung zur Datenbank möglich!')

def read_from_db_decorator(func):
    def read_from_db_wrapper(*args, db_search=None, r=None, 
            sanitize=False, **kwargs):
        if not db_search or not r:
            return func(*args, **kwargs)
        obj, df_dict, *args = args
        queries = [Db.read_from_table_template.format(i) for i 
                in (Db.local_table, Db.shared_table) if i]
        with contextlib_closing(sql.connect(Db.db_uri, uri=True)) as conn:
            with contextlib_closing(conn.cursor()) as cur:
                for i in r:
                    artnr = df_dict[Cols.ARTNR][i]
                    for query in queries:
                        row = cur.execute(query, (artnr,)).fetchone()
                        if row:
                            df_dict[Cols.ARTTEXT1][i], df_dict[Cols.ARTTEXT2][i] = row
        if sanitize:
            for i in r:
                if not df_dict[Cols.ARTTEXT1][i] and not df_dict[Cols.ARTTEXT2][i] and not df_dict[Cols.PREIS][i]:
                    print(f'{df_dict[Cols.ARTNR][i]} nicht gefunden!')
                    for key in df_dict.keys():
                        df_dict[key].pop(i)
        return func(obj, df_dict, *args, **kwargs)
    return read_from_db_wrapper

def write_to_db_decorator(func):
    def write_to_db_wrapper(*args, db_search=None, **kwargs):
        if not db_search or not Db.local_table:
            return func(*args, **kwargs)
        obj, df_dict, *args = args
        write = Db.write_to_table_template.format(Db.local_table)
        update = Db.update_table_template.format(Db.local_table)
        with contextlib_closing(sql.connect(Db.db_uri, uri=True)) as conn:
            with contextlib_closing(conn.cursor()) as cur:
                for i in range(max(map(len, df_dict.values()))):
                    cur.execute(write, (df_dict[Cols.ARTNR][i], df_dict[Cols.ARTTEXT1][i], 
                        df_dict[Cols.ARTTEXT2][i], df_dict[Cols.PREIS][i],int(time.time())))
                    cur.execute(update, (df_dict[Cols.ARTTEXT1][i], df_dict[Cols.ARTTEXT2][i], 
                        df_dict[Cols.PREIS][i], int(time.time()), df_dict[Cols.ARTNR][i]))
                conn.commit()
        return func(obj, *args, df_dict=df_dict, **kwargs)
    return write_to_db_wrapper
