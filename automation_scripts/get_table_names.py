import sqlite3

# Connect to the SQLite database
conn = sqlite3.connect('database.db')

# Create a cursor object
cursor = conn.cursor()

# Execute the query to get all table names
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")

# Fetch all results (table names)
tables = cursor.fetchall()

# Print each table name
for table in tables:
    print(table[0])

# Close the connection
conn.close()