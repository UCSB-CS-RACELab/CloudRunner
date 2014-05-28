from datetime import datetime
import sys, os, traceback
FILE_DIR_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(FILE_DIR_PATH, '../../lib/celery'))
sys.path.append(os.path.join(FILE_DIR_PATH, '../../lib/kombu'))
sys.path.append(os.path.join(FILE_DIR_PATH, '../../lib/amqp'))
sys.path.append(os.path.join(FILE_DIR_PATH, '../../lib/billiard'))
sys.path.append(os.path.join(FILE_DIR_PATH, '../../lib/anyjson'))
sys.path.append(os.path.join(FILE_DIR_PATH, '../../lib/pytz'))
from celery import Celery, group
sys.path.append(os.path.join(FILE_DIR_PATH, '../../'))
from constants import CRConstants
from shared_resources.db import CloudDB
from shared_resources.file_storage import CloudFileStorage

from base_job import BaseJob
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
        self.celery_app.config_from_object('services.jobmanager.celeryconfig')

celery_singleton = CelerySingleton()
celery_singleton.configure()
celery = celery_singleton.celery_app

def update_db_entry(infrastructure, credentials, region, db_id, data):
    db_entry_dict = {
        db_id: data
    }
    put_params = {
        CRConstants.PARAM_INFRA: infrastructure,
        CRConstants.PARAM_CREDENTIALS: credentials,
        CRConstants.PARAM_REGION: region,
        CRConstants.PARAM_DB_ENTRIES: db_entry_dict
    }
    CloudDB.put(put_params)

def send_to_s3(infrastructure, credentials, region, bucket_name, file_path):
    put_params = {
        CRConstants.PARAM_INFRA: infrastructure,
        CRConstants.PARAM_CREDENTIALS: credentials,
        CRConstants.PARAM_REGION: region,
        CRConstants.PARAM_FILE_PATH: file_path,
        CRConstants.PARAM_BUCKET_NAME: bucket_name
    }
    return CloudFileStorage.write(put_params)

def tar_output(path_to_output_dir):
    cwd = os.getcwd()
    output_path_segments = path_to_output_dir.split('/')
    path_to_output_parent_dir = "/".join(output_path_segments[:-1])
    output_dir = output_path_segments[-1]
    print "cd {0}".format(path_to_output_parent_dir)
    os.chdir(path_to_output_parent_dir)
    tar_output_string = "tar -zcf {0}.tgz {0}".format(output_dir)
    print tar_output_string
    os.system(tar_output_string)
    # os.path.abspath relative to current working dir
    tarball_path = os.path.abspath("{0}.tgz".format(output_dir))
    print "cd {0}".format(cwd)
    os.chdir(cwd)
    return tarball_path

@celery.task(name='tasks.task')
def task(params):
    '''
    '''
    try:
        start_time = datetime.now()
        job_name = params[CRConstants.PARAM_JOB_NAME]
        infrastructure = params[CRConstants.PARAM_INFRA]
        credentials = params[CRConstants.PARAM_CREDENTIALS]
        region = params[CRConstants.PARAM_REGION]
        db_id = params[CRConstants.PARAM_DB_ID]
        bucket_name = params[CRConstants.PARAM_BUCKET_NAME]
        print "Remote task picked up by worker."
        print "Job name:", job_name, "Infrastructure:", infrastructure, "DB ID:", db_id
        data = {
            "status": CRConstants.JOB_STATE_RUNNING,
            "start_time": start_time.strftime('%Y-%m-%d %H:%M:%S'),
            "message": "Task executing in the cloud."
        }
        update_db_entry(
            infrastructure,
            credentials,
            region,
            db_id,
            data
        )
        job = BaseJob(params)
        # Just put all of the output in a folder in the current working dir
        # so we can easily tar it up / remove it when done
        remote_output_location = os.getcwd()
        run_params = {
            CRConstants.PARAM_BLOCKING: True,
            'output_location': remote_output_location
        }
        result = job.run(run_params, verbose=True)
        if not result["success"]:
            reason = result["reason"]
            print "Job failed to run because: '{0}'".format(reason)
            data = {
                "status": CRConstants.JOB_STATE_FAILED,
                "message": reason
            }
            update_db_entry(
                infrastructure,
                credentials,
                region,
                db_id,
                data
            )
            return
        elif result["status"] == CRConstants.JOB_STATE_FAILED:
            print "The job was able to run, but execution failed."
            # Data in output folder might be useful, at least the stdout/stderr
            output_dir_path = result["output_location"]
            output_tar_file_path = tar_output(output_dir_path)
            s3_result = send_to_s3(
                infrastructure,
                credentials,
                region,
                bucket_name,
                output_tar_file_path
            )
            cleanup_string = "rm -rf {0} {1}".format(output_dir_path, output_tar_file_path)
            print cleanup_string
            os.system(cleanup_string)
            data = {
                "status": CRConstants.JOB_STATE_FAILED,
                "message": "The program failed during execution.",
                "output_url": s3_result["output_url"],
                "bucket_name": s3_result["bucket_name"]
            }
            update_db_entry(
                infrastructure,
                credentials,
                region,
                db_id,
                data
            )
            return
        #else result["status"] == CRConstants.JOB_STATE_FINISHED
        print "The job finished executing successfully."
        output_dir_path = result["output_location"]
        output_tar_file_path = tar_output(output_dir_path)
        s3_result = send_to_s3(
            infrastructure,
            credentials,
            region,
            bucket_name,
            output_tar_file_path
        )
        cleanup_string = "rm -rf {0} {1}".format(output_dir_path, output_tar_file_path)
        print cleanup_string
        os.system(cleanup_string)
        total_time = datetime.now() - start_time
        data = {
            "status": CRConstants.JOB_STATE_FINISHED,
            "message": "The program finished executing successfully.",
            "output_url": s3_result["output_url"],
            "bucket_name": s3_result["bucket_name"],
            "cloud_execution_time": total_time.total_seconds(),
            #TODO: Update worker image w/ new cloudrunner
            "exec_str": result["exec_str"]
        }
        update_db_entry(
            infrastructure,
            credentials,
            region,
            db_id,
            data
        )
        return
    except Exception as e:
        print "Worker failed with exception:"
        print str(e)
        print traceback.format_exc()
        data = {
            "status": CRConstants.JOB_STATE_FAILED,
            "exception": str(e),
            "traceback": traceback.format_exc()
        }
        update_db_entry(
            infrastructure,
            credentials,
            region,
            db_id,
            data
        )        
        return

