import sqlite3
import pandas as pd

def execute_sql_query(sql_query, db_name="database.db"):
    conn = sqlite3.connect(db_name)
    result = pd.read_sql(sql_query, conn)
    conn.close()
    return result

def get_table_schema(db_name="database.db", table_name="dataset"):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name} LIMIT 0")
    schema = [description[0] for description in cursor.description]
    conn.close()
    return schema