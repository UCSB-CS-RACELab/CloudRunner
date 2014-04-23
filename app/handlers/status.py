import os, subprocess, shlex
import json
from google.appengine.ext import db
from base import BaseHandler
from execution import JobWrapper, LocalJobWrapper
from constants import CRConstants
from services.jobmanager import ExecutionController

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
        #TODO: Add support for delete button
        params = self.request.POST
        action = params["action"]
        if action == "refresh":
            context = self.__get_context()
            return self.render_response("status.html", **context)
        elif action == "delete":
            pass
        else:
            pass
    
    def __get_context(self):
        context = {
            "local_jobs": {}
        }
        execution_controller = ExecutionController()
        local_jobs_query = LocalJobWrapper.all()
        local_jobs_query.filter("user_id =", self.user.user_id())
        for local_job_wrapper in local_jobs_query.run():
            query_params = {
                CRConstants.PARAM_INFRA: "local",
                CRConstants.PARAM_JOB_PIDS: [local_job_wrapper.pid]
            }
            job_status = execution_controller.query_job(query_params)
            # Create the fields needed by the UI
            local_job = {
                "name": local_job_wrapper.name,
                "type": local_job_wrapper.job_type,
                "status": job_status[local_job_wrapper.pid].capitalize(),
                "infrastructure": "Local"
            }
            if local_job_wrapper.job_type in context["local_jobs"]:
                context["local_jobs"][local_job_wrapper.job_type].append(local_job)
            else:
                context["local_jobs"][local_job_wrapper.job_type] = [local_job]
        all_local = context["local_jobs"]
        context["local_jobs"] = []
        for job_type in all_local:
            context["local_jobs"] += all_local[job_type]
        return context

class JobStatusPage(BaseHandler):
    '''
    '''
    def authentication_required(self):
        return True
    
    def get(self):
        '''
        '''
        #TODO: Implement
        job_name = self.request.path.split('/')[-1]
        context = self.__get_context(job_name)
        return self.render_response("job_status.html", **context)
    
    def post(self):
        #TODO: Implement for downloading remote data
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
            pass
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
        return context

