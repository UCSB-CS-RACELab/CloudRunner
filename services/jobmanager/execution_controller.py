import os, sys
import uuid, yaml
from datetime import datetime
from base_job import BaseJob, JobConfigurationException
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../'))
from constants import CRConstants
from config_file import CRConfigFile
from utils import utils
from resources.db import CloudDB
from resources.task_queue import TaskQueue


class ExecutionController(object):
    '''
    '''
    LOCAL_OUTPUT_DIR_PATH = os.path.abspath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)),'../../output')
    )
    
    JOB_STATE_RUNNING = CRConstants.JOB_STATE_RUNNING
    JOB_STATE_PENDING = CRConstants.JOB_STATE_PENDING
    JOB_STATE_FAILED = CRConstants.JOB_STATE_FAILED
    JOB_STATE_FINISHED = CRConstants.JOB_STATE_FINISHED
    
    PARAM_INFRA = CRConstants.PARAM_INFRA
    PARAM_CREDENTIALS = CRConstants.PARAM_CREDENTIALS
    PARAM_JOB_NAME = CRConstants.PARAM_JOB_NAME
    PARAM_JOB_TYPE = CRConstants.PARAM_JOB_TYPE
    PARAM_JOB_PARAMS = CRConstants.PARAM_JOB_PARAMS
    PARAM_JOB_PIDS = CRConstants.PARAM_JOB_PIDS
    
    RUN_JOB_REQ_PARAMS = [
        PARAM_INFRA,
        PARAM_JOB_NAME,
        PARAM_JOB_TYPE,
        PARAM_JOB_PARAMS
    ]
    
    QUERY_JOB_REQ_PARAMS = [
        PARAM_INFRA,
        PARAM_JOB_PIDS
    ]
    
    @classmethod
    def available_programs(cls):
        '''
        '''
        return CRConfigFile.available_programs()
    
    @classmethod
    def available_infrastructures_for_program(cls, program):
        '''
        '''
        return CRConfigFile.available_infrastructures_for_program(program)
    
    def run_job(self, params):
        '''
        '''
        result = {}
        
        infrastructure = params[self.PARAM_INFRA]
        job_name = params[self.PARAM_JOB_NAME]
        job_type = params[self.PARAM_JOB_TYPE]
        
        if infrastructure not in self.available_infrastructures_for_program(job_type):
            result = {
                "success": False,
                "reason": "The '{0}' program is not supported on the '{1}' infrastructure.".format(
                    job_type,
                    infrastructure
                )
            }
            return result
        # Add extra needed info to job_params
        job_params = params[self.PARAM_JOB_PARAMS]
        job_params[CRConstants.PARAM_PROG_DIR_PATH] = CRConfigFile.absolute_path_to_program_dir(
            job_type,
            infrastructure
        )
        job_params[CRConstants.PARAM_JOB_TYPE] = job_type
        job_params[CRConstants.PARAM_JOB_NAME] = job_name
        try:
            if infrastructure == "local":
                temp_result = self.__run_local_job(job_params)
                if not temp_result["success"]:
                    result = {
                        "success": False,
                        "reason": temp_result["reason"]
                    }
                    return result
                
                result["pid"] = temp_result["pid"]
                result["output_location"] = temp_result['output_location']
                result["status"] = temp_result["status"]
            else:
                #TODO: This isn't fully implemented or tested
                temp_result = self.__run_cloud_job(job_params)
                result["pid"] = temp_result["celery_task_id"]
                result["db_id"] = temp_result["db_id"]
            #
            result["success"] = True
        except JobConfigurationException, e: #thrown from BaseJob()
            result["success"] = False
            result["reason"] = "The job you submitted was misconfigured: " + str(e)
        utils.log("RunJob exiting with result: {0}".format(result))
        return result
    
    def query_job(self, params):
        '''
        '''
        result = {}
        infrastructure = params[self.PARAM_INFRA]
        if infrastructure == "local":
            pids = params[self.PARAM_JOB_PIDS]
            statuses = self.__query_local_tasks(pids)
            return statuses
        else:
            pass
    
    def __run_local_job(self, params):
        # Create the job
        job = BaseJob(params)
        #result["job"] = job
        # Local jobs can just store output directly in the filesystem
        params["output_location"] = self.LOCAL_OUTPUT_DIR_PATH
        # Make sure we don't wait on it to complete
        params["blocking"] = False
        result = job.run(params)
        return result
    
    def __run_cloud_job(self, params):
        task_queue = TaskQueue()
        # Create DB entry in cloud DB
        db_entry = {
            "status": self.JOB_STATE_PENDING,
            "enqueue_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "message": "Task sent to cloud."
        }
        db_create_params = {
            self.PARAM_INFRA: params[self.PARAM_INFRA],
            self.PARAM_CREDENTIALS: params[self.PARAM_CREDENTIALS],
            CRConstants.PARAM_DB_ENTRY: db_entry
        }
        result = CloudDB.create(db_create_params)
        # Pass DB id to the worker through the task params
        cloud_db_id = result[CRConstants.PARAM_DB_ID]
        params[CRConstants.PARAM_DB_ID] = cloud_db_id
        queue_result = task_queue.enqueue_task(params)
        result = {
            "db_id": cloud_db_id
        }
        result.update(queue_result)
        return result
    
    def __query_local_tasks(self, pids):
        result = {}
        for pid in pids:
            try:
                # This should work on all Linux/Unix systems.
                # Sending '0' signal shouldn't kill the process.
                os.kill(int(pid), 0)
                result[pid] = self.JOB_STATE_RUNNING
            except OSError:
                #TODO: might not have finished successfully...
                result[pid] = self.JOB_STATE_FINISHED
        return result

