import json
import re
import sqlite3
from pathlib import Path
from typing import Callable, Dict

import pandas as pd
from langchain.chains.sql_database.prompt import SQL_PROMPTS
from langchain_community.agent_toolkits import (
    create_sql_agent,
    SQLDatabaseToolkit,
)
from langchain_community.callbacks import get_openai_callback
from langchain_community.utilities import SQLDatabase
from langchain_core.output_parsers import PydanticOutputParser
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from chatbot.schemas import GPTModelEnum, GroqModelEnum


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
    # db_info = get_db_info(f"{db_name}")

    agent_executor = create_sql_agent(llm,
                                      toolkit=SQLDatabaseToolkit(db=db, llm=llm),
                                      verbose=True,
                                      agent_executor_kwargs={'return_intermediate_steps': True, 'handle_parsing_errors': True})

    with get_openai_callback() as callback:
        response = agent_executor.invoke(
            {
                "input": f"""
                        {SQL_PROMPTS['mysql'].template}
    
                        Always enclose column names in quotes when utilizing aggregation functions.
                        Always first identify the possible column values used in the database.
                        Never send '```SQL' in the message. Just send the SQL query output.
                        The formatting of the table adheres to the following conventions:
                            -   Spaces have been substituted with underscores.
                            -	All accents have been stripped away.
                            -	All text is in lowercase.
    
                        Question: {question}
    
                         """
            }
        )

        query = response['intermediate_steps'][-1][0].tool_input
        output = response['output']

        return query, output, callback.total_cost


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


def get_llm_instance(model_name: str) -> object:
    gpt_model_value_to_enum = {v.value: k for k, v in GPTModelEnum.__members__.items()}
    groq_model_value_to_enum = {v.value: k for k, v in GroqModelEnum.__members__.items()}

    if model_name in gpt_model_value_to_enum:
        enum_member_name = gpt_model_value_to_enum[model_name]
        model_enum = GPTModelEnum[enum_member_name]
        return ChatOpenAI(model=model_enum.value, max_retries=2)
    elif model_name in groq_model_value_to_enum:
        enum_member_name = groq_model_value_to_enum[model_name]
        model_enum = GroqModelEnum[enum_member_name]
        return ChatGroq(model_name=model_enum.value, timeout=5, max_retries=2)
    else:
        raise ValueError(f"Unsupported model name: {model_name}")
