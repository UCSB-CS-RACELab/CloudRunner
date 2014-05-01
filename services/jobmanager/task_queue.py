import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../'))
from constants import CRConstants

from tasks import CelerySingleton, task

class TaskQueue(object):
    '''
    '''
    TASK_STATE_PENDING = CRConstants.JOB_STATE_PENDING
    
    PARAM_DB_ID = CRConstants.PARAM_DB_ID
    PARAM_TASK_NAME = CRConstants.PARAM_JOB_NAME
    PARAM_INFRA = CRConstants.PARAM_INFRA
    
    ENQUEUE_TASK_REQ_PARAMS = [
        PARAM_DB_ID,
        PARAM_TASK_NAME,
        PARAM_INFRA
    ]
    
    def __init__(self):
        self.celery = CelerySingleton()
    
    def enqueue_task(self, params):
        '''
        '''
        cloud_task = task.delay(params)
        result = {
            "status": self.TASK_STATE_PENDING,
            "task_pid": cloud_task.task_id
        }
        return result
    
    def revoke_task(self):
        '''
        '''
        #TODO
        pass

