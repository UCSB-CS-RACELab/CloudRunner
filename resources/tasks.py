import sys, os
file_dir_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(file_dir_path, '../lib/celery'))
sys.path.append(os.path.join(file_dir_path, '../lib/kombu'))
sys.path.append(os.path.join(file_dir_path, '../lib/amqp'))
sys.path.append(os.path.join(file_dir_path, '../lib/billiard'))
sys.path.append(os.path.join(file_dir_path, '../lib/anyjson'))
from celery import Celery, group
sys.path.append(os.path.join(file_dir_path, '../'))
from constants import CRConstants

import celeryconfig

class CelerySingleton(object):
    '''
    Singleton class by Duncan Booth.
    Multiple object variables refers to the same object.
    http://web.archive.org/web/20090619190842/http://www.suttoncourtenay.org.uk/duncan/accu/pythonpatterns.html#singleton-and-the-borg
    '''
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = object.__new__(cls)
            cls._instance.celery_app = Celery('tasks')
        return cls._instance
    
    def configure(self):
        reload(celeryconfig)
        self.celery_app.config_from_object('resources.celeryconfig')

celery_singleton = CelerySingleton()
celery_singleton.configure()

@celery_singleton.celery_app.task(name='tasks.task')
def task(params):
    '''
    '''
    job_name = params[CRConstants.PARAM_JOB_NAME]
    infrastructure = params[CRConstants.PARAM_INFRA]
    command_string = params[CRConstants.PARAM_COMMAND_STR]
    db_id = params[CRConstants.PARAM_DB_ID]
    #

