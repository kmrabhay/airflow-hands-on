from airflow.models import DAG
from datetime import datetime
from airflow.providers.sqlite.operators.sqlite import SqliteOperator
from airflow.providers.http.sensors.http import HttpSensor
from airflow.providers.http.operators.http import SimpleHttpOperator
import json
from airflow.operators.python import PythonOperator
from pandas import json_normalize
from airflow.operators.bash import BashOperator

default_args ={
        'start_date':datetime(2022, 2, 23),
}


def _processing_user(ti):
        users =  ti.xcom_pull(task_ids=['extracting_user'])
        print("------->>>>", users)
        if not len(users) or "result"  not in str(users):
                raise ValueError("User is empty!")
        user =  users[0]['results'][0]
        if user['name']['last'] is None:
                user['name']['last']  ='Kumar'
        processed_user = json_normalize({
                'firstname':user['name']['first'],
                'lastname':user['name']['last'],
                'country':user['location']['country'],
                'username':user['login']['username'],
                'password':user['login']['password'],
                'email': user['email']
        })

        processed_user.to_csv('/home/abhay/airflow/processed_user.csv', index=None, header=False)

with DAG("user_processing", schedule_interval='@daily', 
             default_args=default_args,
            catchup=True) as dag:

        #Define the task/operator
        creating_table = SqliteOperator(
                task_id='creating_table',
                sqlite_conn_id='db_sqlite',
                sql='''
                        CREATE TABLE IF NOT EXISTS users(
                                firstname TEXT NOT NULL,
                                lastname TEXT NOT NULL,
                                country TEXT NOT NULL,
                                username TEXT NOT NULL,
                                password TEXT NOT NULL ,
                                email TEXT NOT NULL PRIMARY KEY
                        );
                '''


        )


        is_api_available =  HttpSensor(
                task_id='is_api_available',
                http_conn_id='user_api',
                endpoint='api/'
        )
        
        extracting_user = SimpleHttpOperator(
                task_id='extracting_user',
                http_conn_id='user_api',
                endpoint='api/',
                method='GET',
                response_filter= lambda response: json.loads(response.text),
                log_response=True

        )


        processing_user =  PythonOperator(
                task_id='processing_user',
                python_callable=_processing_user
        )


        storing_user =  BashOperator(
                task_id='storing_user',
                bash_command="echo -e .separator"+"\n.import /home/abhay/airflow/processed_user.csv users" "| sqlite3 /home/abhay/airflow/airflow.db"
        )


        creating_table >> is_api_available >> extracting_user >> processing_user >> storing_user