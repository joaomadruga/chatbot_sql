import os
import sqlite3

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


def natural_language_to_sql(question):
    DB_NAME = "dbs/olimpic_medals.db"
    llm = ChatGroq(model_name="llama3-70b-8192")
    db = SQLDatabase.from_uri(f"sqlite:///{DB_NAME}")
    db_info = get_db_info(f"{DB_NAME}")

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
    return response
