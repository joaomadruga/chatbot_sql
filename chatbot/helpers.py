import re
import sqlite3
from pathlib import Path

import pandas as pd
from langchain.chains.sql_database.prompt import SQL_PROMPTS
from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.utilities import SQLDatabase
from langchain_groq import ChatGroq


def get_db_info(db_path):
    db_info = ""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    for table in tables:
        table_name = table[0]

        query = f"SELECT * FROM {table_name} LIMIT 5;"
        cursor.execute(query)
        first_table_rows = cursor.fetchall()

        column_names = [description[0] for description in cursor.description]

        db_info += f"Table: {table_name}\n"
        db_info += f"Columns: {', '.join(column_names)}\n"

        for index, row in enumerate(first_table_rows):
            db_info += f"ROW {index + 1}: {row}\n"

        db_info += "\n"

    conn.close()
    return db_info


def natural_language_to_sql(question, llm, db_name):
    print(f"Using {llm}")
    db = SQLDatabase.from_uri(f"sqlite:///{db_name}")
    db_info = get_db_info(f"{db_name}")

    agent_executor = create_sql_agent(llm, db=db, verbose=True)
    agent_executor.handle_parsing_errors = True
    response = agent_executor.invoke(
        {
            "input": f"""
                    {SQL_PROMPTS['mysql'].template}

                    Always enclose column names in quotes when utilizing aggregation functions.

                    The formatting of the table adheres to the following conventions:
                        -   Spaces have been substituted with underscores.
                        -	All accents have been stripped away.
                        -	All text is in lowercase.

                    Here is all tables and their first five rows to give you context:

                    {db_info}.

                    Question: {question}

                     """
        }
    )
    return response['output']


def sanitize_table_name(name: str) -> str:
    """Sanitize the table name to avoid SQL injection and unexpected characters."""
    name = re.sub(r'\W+', '_',
                  name)  # Replace any non-alphanumeric character with an underscore
    return name.lower().strip(
        '_')  # Convert to lowercase and strip leading/trailing underscores


def process_csv_to_db(conn: sqlite3.Connection, file_path: str):
    """Transform a .csv file into a SQLite database table."""
    df = pd.read_csv(file_path)
    raw_table_name = Path(file_path).stem
    table_name = sanitize_table_name(raw_table_name)
    df.to_sql(table_name, conn, if_exists='replace', index=False)


def merge_db_files(conn: sqlite3.Connection, db_file: str):
    print(f"Merging database: {db_file}")
    source_conn = sqlite3.connect(db_file)
    source_cursor = source_conn.cursor()
    dest_cursor = conn.cursor()

    for (raw_table_name,) in source_cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table';"):
        table_name = sanitize_table_name(raw_table_name)

        if dest_cursor.execute(
                f"SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
                (table_name,)).fetchone():
            print(f"Replacing existing table: {table_name}")
            dest_cursor.execute(f"DROP TABLE {table_name};")
        else:
            print(f"Adding new table: {table_name}")

        create_table_sql = source_cursor.execute(
            f"SELECT sql FROM sqlite_master WHERE type='table' AND name=?;",
            (raw_table_name,)).fetchone()[0]
        create_table_sql = create_table_sql.replace(raw_table_name, table_name)
        dest_cursor.execute(create_table_sql)

        data = source_cursor.execute(
            f"SELECT * FROM {raw_table_name};").fetchall()
        columns = [col[1] for col in source_cursor.execute(
            f"PRAGMA table_info({raw_table_name});")]
        dest_cursor.executemany(
            f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(['?'] * len(columns))})",
            data)

    conn.commit()
    source_conn.close()
    print(f"Finished merging {db_file} into destination database.")

