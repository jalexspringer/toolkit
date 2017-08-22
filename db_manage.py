import sqlite3


def create_connection(db_file):
    conn = sqlite3.connect(db_file)
    return conn


def create_table(conn, create_table_sql):
    c = conn.cursor()
    c.execute(create_table_sql)


def create_record(conn, record):
    sql = ''' INSERT INTO records VALUES(?,?,?,?,?,?,?)'''
    cur = conn.cursor()
    cur.execute(sql, record)
    conn.commit()
    return cur.lastrowid


def update_record(conn, record):
    sql = "UPDATE records SET orgID='{}' WHERE oppID='{}'".format(record[1], record[0])
    print('SQL QUERY: ', sql)
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()

def resolve_record(conn, jira):
    sql = "UPDATE records SET status='Closed' WHERE jira='{}'".format(jira)
    print('SQL QUERY: ', sql)
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()


def db_init():
    database = "data/records.sql"
    sql_create_records_table = """ CREATE TABLE IF NOT EXISTS records (
                                        account text NOT NULL,
                                        oppID text NOT NULL,
                                        jira text NOT NULL,
                                        orgID text,
                                        owner text NOT NULL,
                                        rep text NOT NULL,
                                        status text NOT NULL
                          ); """

    conn = create_connection(database)
    if conn is not None:
        # create records table
        create_table(conn, sql_create_records_table)
    else:
        print("Error! cannot create the database connection.")


def read_db(conn, locator=False, owner=None, rep=None):
    cur = conn.cursor()
    if locator:
        if len(locator) == 15:
            query = '''SELECT * FROM records WHERE oppID IS ?;'''
        elif len(locator) == 20:
            query = '''SELECT * FROM records WHERE orgID IS ?;'''
        elif locator.startswith('IRO'):
            query = '''SELECT * FROM records WHERE jira IS ?;'''
        else:
            query = '''SELECT * FROM records WHERE account LIKE ?;'''
    elif owner:
            query = '''SELECT * FROM records WHERE owner IS ?;'''
            locator = owner
    elif rep:
            query = '''SELECT * FROM records WHERE rep IS ?;'''
            locator = rep
    else:
            query = '''SELECT * FROM records '''
            cur.execute(query)
            response = {}
            counter = 0
            for r in cur.fetchall():
                response[counter] = r
                counter += 1
            return response
    cur.execute(query, [locator])
    response = {}
    counter = 0
    for r in cur.fetchall():
        response[counter] = r
        counter += 1
    return response
