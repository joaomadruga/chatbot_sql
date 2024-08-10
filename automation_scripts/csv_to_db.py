import os
import sqlite3
import pandas as pd

# Caminho da pasta onde os arquivos .csv estão localizados
caminho_dos_csv = './new_csv'

# Conexão com o banco de dados SQLite
conn = sqlite3.connect('../dbs/game_sales.db')

# Itera sobre os arquivos .csv na pasta
for arquivo in os.listdir(caminho_dos_csv):
    if arquivo.endswith('.csv'):
        caminho_completo = os.path.join(caminho_dos_csv, arquivo)

        # Lê o arquivo .csv em um DataFrame do pandas
        df = pd.read_csv(caminho_completo)

        # Extrai o nome do arquivo sem a extensão para usar como nome da tabela
        nome_tabela = os.path.splitext(arquivo)[0].lower().replace(' ', '_')
        print(nome_tabela)

        # Insere os dados no banco de dados
        df.to_sql(nome_tabela, conn, if_exists='replace', index=False)

# Fecha a conexão com o banco de dados
conn.close()