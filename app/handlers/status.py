import os, subprocess, shlex
import json
from google.appengine.ext import db
from base import BaseHandler
from execution import JobWrapper, LocalJobWrapper, CloudJobWrapper
from constants import CRConstants
from services.jobmanager import ExecutionController
from shared_resources.file_storage import CloudFileStorage

class StatusPage(BaseHandler):
    '''
    '''
    def authentication_required(self):
        return True
    
    def get(self):
        '''
        '''
        context = self.__get_context()
        return self.render_response("status.html", **context)
    
    def post(self):
        '''
        '''
        params = self.request.POST
        action = params["action"]
        if action == "refresh":
            context = self.__get_context()
            return self.render_response("status.html", **context)
        elif action == "delete":
            #TODO: Add support for delete button
            pass
        else:
            pass
    
    def __get_context(self):
        context = {}
        # Local jobs first
        local_jobs_query = LocalJobWrapper.all()
        local_jobs_query.filter("user_id =", self.user.user_id())
        context["local_jobs"] = self.__construct_jobs_list(
            local_jobs_query,
            CRConstants.INFRA_LOCAL
        )
        # Now cloud jobs
        cloud_jobs_query = CloudJobWrapper.all()
        cloud_jobs_query.filter("user_id =", self.user.user_id())
        context["cloud_jobs"] = self.__construct_jobs_list(
            cloud_jobs_query,
            #TODO: Fine for now since only AWS is supported, but we
            #      need all infrastructures displayed somehow.
            CRConstants.INFRA_AWS
        )
        return context
    
    def __construct_jobs_list(self, jobs_query, infrastructure):
        isCloud = infrastructure != CRConstants.INFRA_LOCAL
        jobs_list = {}
        execution_controller = ExecutionController()
        # Run the query and loop through the results
        for job_wrapper in jobs_query.run():
            job = None
            # If the job is already marked as failed or finished, then we don't need to query backend
            if job_wrapper.status in [CRConstants.JOB_STATE_FAILED, CRConstants.JOB_STATE_FINISHED]:
                job = {
                    "name": job_wrapper.name,
                    "type": job_wrapper.job_type,
                    "infrastructure": self.__display_name_for_infra(infrastructure),
                    "status": job_wrapper.status.capitalize()
                }
            # Else we need to query its status and update the GAE DB entry
            else:
                query_params = {
                    CRConstants.PARAM_INFRA: infrastructure,
                    CRConstants.PARAM_CREDENTIALS: self.user.get_credentials(infrastructure),
                    CRConstants.PARAM_JOB_PIDS: [job_wrapper.pid]
                }
                job_status = execution_controller.query_job(query_params)
                # Create the fields needed by the UI
                job = {
                    "name": job_wrapper.name,
                    "type": job_wrapper.job_type,
                    "infrastructure": self.__display_name_for_infra(infrastructure)
                }
                # Check success
                if not job_status["success"]:
                    job["status"] = "Unknown"
                else:
                    if isCloud:
                        job_dict = job_status[job_wrapper.pid]
                        job_wrapper.status = job_dict["status"]
                        if job_wrapper.status == CRConstants.JOB_STATE_FAILED:
                            job_wrapper.exception = job_dict["exception"]
                            job_wrapper.traceback = job_dict["traceback"]
                        elif job_wrapper.status == CRConstants.JOB_STATE_FINISHED:
                            job_wrapper.output_url = job_dict["output_url"]
                        job_wrapper.put()
                        job["status"] = job_wrapper.status.capitalize()
                    else:
                        job_wrapper.status = job_status[job_wrapper.pid]["status"]
                        job_wrapper.put()
                        job["status"] = job_wrapper.status.capitalize()
            
            if job_wrapper.job_type in jobs_list:
                jobs_list[job_wrapper.job_type].append(job)
            else:
                jobs_list[job_wrapper.job_type] = [job]
        # Place them all back into context sorted by job_type
        all_jobs = jobs_list
        jobs_list = []
        for job_type in all_jobs:
            jobs_list += all_jobs[job_type]
        return jobs_list
    
    def __display_name_for_infra(self, infra):
        if infra == CRConstants.INFRA_LOCAL:
            return "Local"
        elif infra == CRConstants.INFRA_AWS:
            return "AWS"
        elif infra == CRConstants.INFRA_EUCA:
            return "Eucalyptus"
        else:
            return "Invalid"

class JobStatusPage(BaseHandler):
    '''
    '''
    OUTPUT_DIR_LOCATION = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "../../output"
    )
    
    def authentication_required(self):
        return True
    
    def get(self):
        '''
        '''
        job_name = self.request.path.split('/')[-1]
        context = self.__get_context(job_name)
        if self.request.get("debug"):
            #TODO: Add support for viewing stdout/stderr and exception info
            context["debug"] = True
        return self.render_response("job_status.html", **context)
    
    def post(self):
        params = self.request.POST
        job_name = self.request.path.split('/')[-1]
        action = params["action"]
        # Make sure we set the Content-Type header for all responses
        self.response.headers['Content-Type'] = 'application/json'
        if action == "pull_local":
            full_path_to_output = params["output_path"]
            output_dir = "/".join(full_path_to_output.split('/')[:-1])
            job_output_dir = full_path_to_output.split('/')[-1]
            url_to_serve_location = "/static/tmp/{0}.tgz".format(job_output_dir)
            full_path_to_serve_location = os.path.abspath(os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..{0}".format(url_to_serve_location)
            ))
            # We want to chdir to the directory that contains the output directory
            # so that the tarball doesnt have a bunch of unnecessary directories
            # in it.
            cwd = os.getcwd()
            os.chdir(output_dir)
            tar_output_string = "tar -zcf {0} {1}".format(
                full_path_to_serve_location,
                job_output_dir
            )
            p = subprocess.Popen(
                shlex.split(tar_output_string),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = p.communicate()
            result = {}
            if p.returncode != 0:
                result['success'] = False
                result['message'] = "The server failed to package up the output data."
            else:
                result['success'] = True
                result['url'] = url_to_serve_location
            # Change working dir back
            os.chdir(cwd)
            return self.response.write(json.dumps(result))
        elif action == "pull_remote":
            job_query = JobWrapper.all()
            job_query.filter("name =", job_name)
            job = job_query.get()
            # Now, just pull the remote file into output directory
            fetch_output_params = {
                CRConstants.PARAM_INFRA: job.infrastructure,
                CRConstants.PARAM_CREDENTIALS: self.user.get_credentials(job.infrastructure),
                CRConstants.PARAM_FILE_URL: job.output_url,
                CRConstants.PARAM_OUTPUT_PATH: self.OUTPUT_DIR_LOCATION
            }
            read_result = CloudFileStorage.read(fetch_output_params)
            if not read_result["success"]:
                result = {
                    "success": False,
                    "message": "The server failed to package up the output data because:\n'{0}'.".format(
                        read_result["reason"]
                    )
                }
                return self.response.write(json.dumps(result))
            #Else we downloaded it successfully
            output_tarball = read_result["output_file_path"]
            cwd = os.getcwd()
            # Unpack the tarball in the output folder
            os.chdir(self.OUTPUT_DIR_LOCATION)
            folder_name = output_tarball.split('/')[-1].split('.')[0]
            output_location = os.path.abspath(
                os.path.join(self.OUTPUT_DIR_LOCATION, folder_name)
            )
            # Try to make the directory that will hold the output.
            try:
                os.mkdir(output_location)
            # If we fail, just let the user know and they can deal
            # with moving the file that's there.
            except OSError, e:
                # Remove the tarball now
                cleanup_string = "rm -rf {0}".format(output_tarball)
                os.system(cleanup_string)
                os.chdir(cwd)
                result = {
                    "success": False,
                    "message": "You already have a file at '{0}' where the job output results are supposed to go.".format(
                        output_location
                    )
                }
                return self.response.write(json.dumps(result))
            #
            untar_string = "tar -zxf {0}".format(output_tarball)
            os.system(untar_string)
            # Remove the tarball now
            cleanup_string = "rm -rf {0}".format(output_tarball)
            os.system(cleanup_string)
            os.chdir(cwd)
            job.output_location = output_location
            job.put()
            result = {
                "success": True
            }
            return self.response.write(json.dumps(result))
        else:
            result = {
                'success': False,
                'message': "Unrecognized action requested: {0}".format(action)
            }
            return self.response.write(json.dumps(result))
    
    def __get_context(self, job_name):
        context = {}
        job_query = JobWrapper.all()
        job_query.filter("name =", job_name)
        job = job_query.get()
        context["job"] = job
        if not job.output_location:
            context["should_pull_remote"] = True
        return context

