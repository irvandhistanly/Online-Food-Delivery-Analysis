'''
Irvandhi Stanly Winata
HCK - 013

Objective: This python file is intended to create DAG that automates the process of loading, fetching, cleaning, and uploading data between different systems (CSV files, PostgreSQL, 
and Elasticsearch) as part of a data processing pipeline. Each task in the DAG performs a specific step in the pipeline, helping to streamline and automate the data workflow.
'''

from airflow.models import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from sqlalchemy import create_engine
import pandas as pd
from elasticsearch import Elasticsearch

# Define default arguments for the DAG
default_args = {
    'owner': 'Stanly', 
    'start_date': datetime(2024, 3, 20, 6, 30), # Start date of the DAG
    'retries': 1, # Number of retries for failed tasks
    'retry_delay': timedelta(minutes=10), # Delay between retries
}

def load_csv_to_database():
    '''
    Function to load data from CSV to PostgreSQL.

    Expected Output:
        This function reads data from a CSV file named 'P2M3_Irvandhi_Stanly_data_raw.csv' located in the '/opt/airflow/dags/' directory. 
        It then connects to a PostgreSQL database named 'airflow_m3' and uploads the data to a table named 'table_m3'.
    '''
    database = "airflow"
    username = "airflow"
    password = "airflow"
    host = "postgres"
    postgres_url = f"postgresql+psycopg2://{username}:{password}@{host}/{database}" # Making a PostgreSQL URL connection
    engine = create_engine(postgres_url) # Using the URL to create a connection to SQLAlchemy
    conn = engine.connect() # Creating a connection to the database
    df = pd.read_csv('/opt/airflow/dags/P2M3_Irvandhi_Stanly_data_raw.csv') # Reading data from CSV
    df.to_sql('table_m3', conn, index=False, if_exists='replace') # Writing data to PostgreSQL table

def fetch_data_from_database():
    '''
    Function to fetch data from PostgreSQL.

    Expected Output:
        This function connects to a PostgreSQL database named 'airflow_m3' and retrieves all data from the 'table_m3' table.
        It then saves the retrieved data to a CSV file named 'P2M3_Irvandhi_Stanly_data_new.csv' in the '/opt/airflow/dags/' directory.
    '''
    database = "airflow"
    username = "airflow"
    password = "airflow"
    host = "postgres"
    postgres_url = f"postgresql+psycopg2://{username}:{password}@{host}/{database}"
    engine = create_engine(postgres_url)
    conn = engine.connect()
    df = pd.read_sql_query("select * from table_m3", conn) # Retrieving data from PostgreSQL table
    df.to_csv('/opt/airflow/dags/P2M3_Irvandhi_Stanly_data_new.csv', sep=',', index=False)

def clean_data(): 
    '''
    Function to clean data.

    Expected Output:
        This function reads data from a CSV file named 'P2M3_Irvandhi_Stanly_data_new.csv' located in the '/opt/airflow/dags/' directory. It performs data cleaning 
        operations, which include removing duplicates, converting column names to lowercase, replacing spaces with underscores, removing unnecessary characters from 
        column names, removing leading and trailing white spaces, and dropping unnecessary column. The cleaned data is then saved to a new CSV file named 'P2M3_Irvandhi_Stanly_data_clean.csv'.
    '''
    data = pd.read_csv("/opt/airflow/dags/P2M3_Irvandhi_Stanly_data_new.csv")
    data['id'] = range(1, len(data) + 1)  # Add a new column 'id' for unique identifiaction
    # Rearrange columns to place 'id' as the leftmost column
    columns = list(data.columns)
    columns.insert(0, columns.pop(columns.index('id')))
    data = data[columns]
    data.dropna(inplace=True) # Dropping rows with missing values
    data.drop_duplicates(inplace=True) # Dropping duplicate rows
    data.columns = data.columns.str.lower()  # Convert all letters to lowercase
    data.columns = data.columns.str.replace(' ', '_')  # Replace spaces with underscores
    data.columns = data.columns.str.replace('[^\w\s]', '')  # Remove unnecessary characters
    data.columns = data.columns.str.strip()  # Remove leading and trailing spaces/tabs in column names
    data.drop('unnamed_12', axis=1, inplace=True) # Dropping excess unnamed column
    data.to_csv('/opt/airflow/dags/P2M3_Irvandhi_Stanly_data_clean.csv', index=False)

def upload_to_elasticsearch():
    '''
    Function to upload data to Elasticsearch.

    Expected Output:
        This function reads data from a CSV file named 'P2M3_Irvandhi_Stanly_data_clean.csv' located in the '/opt/airflow/dags/' directory.
        It connects to an Elasticsearch server running at 'http://elasticsearch:9200' and uploads each row of the cleaned data as a document to the 'table' index.
        It prints the response from Elasticsearch for each document uploaded.
    '''
    es = Elasticsearch("http://elasticsearch:9200") # Creating Elasticsearch client
    df = pd.read_csv('/opt/airflow/dags/P2M3_Irvandhi_Stanly_data_clean.csv')
    for i, r in df.iterrows():  # Iterating over each row in the DataFrame
        doc = r.to_dict()  # Converting the row to a dictionary
        res = es.index(index="table_milestone", id=i+1, body=doc)  # Indexing the document in Elasticsearch
        print(f"Response from Elasticsearch: {res}")  # Printing the response from Elasticsearch

with DAG(
    "P2M3_Stanly_DAG", # Project name
    description='Milestone 3 DAG by Stanly',
    schedule_interval='30 6 * * *', # Scheduling every day at 06:30
    default_args=default_args, 
    catchup=False
) as dag:
    # Step 1: Loading CSV to Database
    load_csv_task = PythonOperator(
        task_id='load_csv_to_database',
        python_callable=load_csv_to_database)
    
    # Step 2: Fetching Data from Database
    fetch_data_task = PythonOperator(
        task_id='fetch_data_from_database',
        python_callable=fetch_data_from_database)
    
    # Step 3: Cleaning Data
    clean_data_task = PythonOperator(
        task_id='clean_data',
        python_callable=clean_data)

    # Step 4: Uploading Data to Elasticsearch
    upload_data_to_elastic_task = PythonOperator(
        task_id='upload_to_elasticsearch',
        python_callable=upload_to_elasticsearch)


    # DAG workflow
    load_csv_task >> fetch_data_task >> clean_data_task >> upload_data_to_elastic_task
