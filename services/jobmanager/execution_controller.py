import os, sys
import uuid, yaml
from datetime import datetime
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../'))
from constants import CRConstants
from config_file import CRConfigFile
from utils import utils
from shared_resources.db import CloudDB
from shared_resources.file_storage import CloudFileStorage

from base_job import BaseJob, JobConfigurationException
from task_queue import TaskQueue

class ExecutionController(object):
    '''
    '''
    LOCAL_OUTPUT_DIR_PATH = os.path.abspath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)),'../../output')
    )
    
    INFRA_LOCAL = CRConstants.INFRA_LOCAL
    INFRA_AWS = CRConstants.INFRA_AWS
    
    JOB_STATE_RUNNING = CRConstants.JOB_STATE_RUNNING
    JOB_STATE_PENDING = CRConstants.JOB_STATE_PENDING
    JOB_STATE_FAILED = CRConstants.JOB_STATE_FAILED
    JOB_STATE_FINISHED = CRConstants.JOB_STATE_FINISHED
    
    PARAM_INFRA = CRConstants.PARAM_INFRA
    PARAM_CREDENTIALS = CRConstants.PARAM_CREDENTIALS
    PARAM_REGION = CRConstants.PARAM_REGION
    PARAM_BUCKET_NAME = CRConstants.PARAM_BUCKET_NAME
    PARAM_JOB_NAME = CRConstants.PARAM_JOB_NAME
    PARAM_JOB_TYPE = CRConstants.PARAM_JOB_TYPE
    PARAM_JOB_PARAMS = CRConstants.PARAM_JOB_PARAMS
    PARAM_JOB_PIDS = CRConstants.PARAM_JOB_PIDS
    PARAM_DB_IDS = CRConstants.PARAM_DB_IDS
    PARAM_FILE_URL = CRConstants.PARAM_FILE_URL
    
    # NOTE: PARAM_CREDENTIALS is required unless PARAM_INFRA == INFRA_LOCAL
    RUN_JOB_REQ_PARAMS = [
        PARAM_INFRA,
        PARAM_JOB_NAME,
        PARAM_JOB_TYPE,
        PARAM_JOB_PARAMS
    ]
    # NOTE: PARAM_CREDENTIALS is required unless PARAM_INFRA == INFRA_LOCAL
    QUERY_JOB_REQ_PARAMS = [
        PARAM_INFRA,
        PARAM_JOB_PIDS
    ]
    # NOTE: PARAM_CREDENTIALS is required unless PARAM_INFRA == INFRA_LOCAL
    DELETE_JOB_REQ_PARAMS = [
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
        # Required parameters
        infrastructure = params[self.PARAM_INFRA]
        job_name = params[self.PARAM_JOB_NAME]
        job_type = params[self.PARAM_JOB_TYPE]
        job_params = params[self.PARAM_JOB_PARAMS]
        # Make sure we can actually run the program on this infra
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
        job_params[CRConstants.PARAM_PROG_DIR_PATH] = CRConfigFile.absolute_path_to_program_dir(
            job_type,
            infrastructure
        )
        job_params[self.PARAM_JOB_TYPE] = job_type
        job_params[self.PARAM_JOB_NAME] = job_name
        job_params[self.PARAM_INFRA] = infrastructure
        
        try:
            job = BaseJob(job_params)
        except JobConfigurationException, e:
            result["success"] = False
            result["reason"] = "The job you submitted was misconfigured: " + str(e)
            return result
        
        if infrastructure == self.INFRA_LOCAL:
            temp_result = self.__run_local_job(job)
            if not temp_result["success"]:
                result = {
                    "success": False,
                    "reason": temp_result["reason"]
                }
                return result
            # Else it succeeded
            result["pid"] = temp_result["pid"]
            result["output_location"] = temp_result['output_location']
            result["status"] = temp_result["status"]
            result["exec_str"] = temp_result["exec_str"]
        else:
            job_params[self.PARAM_CREDENTIALS] = params[self.PARAM_CREDENTIALS]
            job_params[self.PARAM_REGION] = CRConfigFile.get_default_region_for_infrastructure(infrastructure)
            job_params[self.PARAM_BUCKET_NAME] = params[self.PARAM_BUCKET_NAME]
            temp_result = self.__run_cloud_job(job_params)
            result.update(temp_result)
        #
        result["success"] = True
        
        utils.log("RunJob exiting with result: {0}".format(result))
        return result
    
    def kill_job(self, params):
        '''
        '''
        #TODO
        pass
    
    def query_job(self, params):
        '''
        '''
        infrastructure = params[self.PARAM_INFRA]
        if infrastructure == self.INFRA_LOCAL:
            pids = params[self.PARAM_JOB_PIDS]
            statuses = self.__query_local_tasks(pids)
            return statuses
        else:
            # db_ids = params[self.PARAM_DB_IDS]
            params[self.PARAM_DB_IDS] = params[self.PARAM_JOB_PIDS]
            params[self.PARAM_REGION] = CRConfigFile.get_default_region_for_infrastructure(infrastructure)
            jobs = CloudDB.get(params)
            return jobs
    
    def delete_job(self, params):
        '''
        '''
        result = {}
        infrastructure = params[self.PARAM_INFRA]
        if infrastructure == self.INFRA_LOCAL:
            # Nothing we need to do for local jobs
            pass
        else:
            # We need to get the DB entries first.
            db_ids = params[self.PARAM_JOB_PIDS]
            params[self.PARAM_DB_IDS] = db_ids
            params[self.PARAM_REGION] = CRConfigFile.get_default_region_for_infrastructure(infrastructure)
            jobs = CloudDB.get(params)
            #TODO: Check this
            jobs.pop('success')
            # First, try to delete all the DB entries
            delete_db_result = CloudDB.delete(params)
            success = delete_db_result.pop("success")
            result["success"] = success
            # If we couldn't delete any of the DB entries, just stop here and return
            # error message.
            if not success:
                result["reason"] = delete_db_result["reason"]
                return result
            # Not all DB entries were necessarily deleted...
            for db_id in delete_db_result:
                result[db_id] = {
                    "success": delete_db_result[db_id]
                }
            utils.log("Result of cloud DB deletion: {0}".format(result))
            # Then, we need to delete all of the file storage tied with these jobs
            utils.log("All jobs: {0}".format(jobs))
            jobs_with_file_storage = [jobs[job] for job in jobs if "output_url" in jobs[job] and jobs[job]["output_url"]]
            utils.log("All jobs with file storage: {0}".format(jobs_with_file_storage))
            for job in jobs_with_file_storage:
                # But if we couldn't delete the DB entry, we shouldn't delete the remote data
                if not result[job["taskid"]]["success"]:
                    utils.log("Not deleting file storage of job '{0}'".format(job["taskid"]))
                    continue
                # Delete remote output
                delete_output_params = {
                    self.PARAM_INFRA: infrastructure,
                    self.PARAM_CREDENTIALS: params[self.PARAM_CREDENTIALS],
                    self.PARAM_FILE_URL: job["output_url"]
                }
                delete_output_result = CloudFileStorage.delete(delete_output_params)
                utils.log("Deleted remote file storage of job '{0}'".format(job["taskid"]))
                result[job["taskid"]]["success"] = delete_output_result["success"]
                if not delete_output_result["success"]:
                    # Pass on the reason and continue to next job
                    result[job["taskid"]]["reason"] = delete_output_result["reason"]
                    continue
        return result
    
    def __run_local_job(self, job):
        # Local jobs can just store output directly in the filesystem
        params = {
            "output_location": self.LOCAL_OUTPUT_DIR_PATH,
            CRConstants.PARAM_BLOCKING: False
        }
        result = job.run(params)
        return result
    
    def __run_cloud_job(self, params):
        # Create DB entry in cloud DB
        db_entry = {
            "status": self.JOB_STATE_PENDING,
            "enqueue_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "message": "Task sent to cloud."
        }
        db_create_params = {
            self.PARAM_INFRA: params[self.PARAM_INFRA],
            self.PARAM_CREDENTIALS: params[self.PARAM_CREDENTIALS],
            self.PARAM_REGION: params[self.PARAM_REGION],
            CRConstants.PARAM_DB_ENTRY: db_entry
        }
        cloud_db_id = CloudDB.create(db_create_params)
        # Pass DB id to the worker through the task params
        params[CRConstants.PARAM_DB_ID] = cloud_db_id
        # Enqueue the task
        task_queue = TaskQueue()
        queue_result = task_queue.enqueue_task(params)
        result = {
            "pid": cloud_db_id,
            "task_id": queue_result["task_pid"]
        }
        return result
    
    def __query_local_tasks(self, pids):
        result = {
            "success": True
        }
        for pid in pids:
            try:
                # This should work on all Linux/Unix systems.
                # Sending '0' signal shouldn't kill the process.
                os.kill(int(pid), 0)
                result[pid] = {
                    "status": self.JOB_STATE_RUNNING
                }
            except OSError:
                #TODO: might not have finished successfully...
                result[pid] = {
                    "status": self.JOB_STATE_FINISHED
                }
        return result

