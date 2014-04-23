from google.appengine.ext import db
from google.appengine.ext.db import polymodel
from base import BaseHandler
from services.jobmanager import ExecutionController
from constants import CRConstants

class JobWrapper(polymodel.PolyModel):
    '''
    Base DB wrapper for all jobs.
    '''
    user_id = db.StringProperty()
    name = db.StringProperty()
    job_type = db.StringProperty()
    pid = db.StringProperty()
    output_location = db.StringProperty()

class LocalJobWrapper(JobWrapper):
    '''
    DB wrapper for all local jobs.
    '''
    pass

class CloudJobWrapper(JobWrapper):
    '''
    DB wrapper for all cloud jobs.
    '''
    infrastructure = db.StringProperty()
    cloud_db_id = db.StringProperty()

class ExecutionHandler(BaseHandler):
    '''
    '''
    STEP_1_VIEW = "select_job_type.html"
    STEP_2_VIEW = "select_infrastructure.html"
    # STEP_3_VIEW = "{0}.html".format(program_name)
    
    def authentication_required(self):
        return True
    
    def get(self):
        context = {
            "programs": ExecutionController.available_programs()
        }
        return self.render_response(self.STEP_1_VIEW, **context)
    
    def post(self):
        params = self.request.POST
        step = int(params.pop('step'))
        program_name = params.pop('program')
        action = params.pop('action')
        
        if (step == 1):
            # Just pass the program name and available infrastructures on to UI
            context = {
                'program_name': program_name,
                'infrastructures': ExecutionController.available_infrastructures_for_program(program_name)
            }
            return self.render_response(self.STEP_2_VIEW, **context)
        elif (step == 2):
            # Go back to step 1
            if action == "previous":
                return self.get()
            # Else we need to initialize context...
            infrastructure = params['infrastructure']
            context = {
                'program_name': program_name,
                'infrastructures': ExecutionController.available_infrastructures_for_program(program_name),
                'infra': infrastructure
            }
            # ...and make sure the job name is unique
            job_name = params['job_name']
            name_exists = db.GqlQuery("SELECT * FROM JobWrapper WHERE name = :1", job_name).get()
            if name_exists:
                context = {
                    'program_name': program_name,
                    'infrastructures': ExecutionController.available_infrastructures_for_program(program_name),
                    'error_alert': "Job name '{0}' is already in use.".format(job_name)
                }
                return self.render_response(self.STEP_2_VIEW, **context)
            # Ok, now just render the correct page
            context['job_name'] = job_name
            # return self.render_response("input_job_parameters.html", **context)
            return self.render_response("{0}.html".format(program_name), **context)
        elif step == 3:
            # Go back to step 2
            job_name = params.pop('job_name')
            infrastructure = params.pop('infra')
            if action == "previous":
                context = {
                    'program_name': program_name,
                    'job_name': job_name,
                    'infrastructures': ExecutionController.available_infrastructures_for_program(program_name),
                    'infra': infrastructure
                }
                return self.render_response(self.STEP_2_VIEW, **context)
            # Else submit the job
            program_params = {}
            for key in params:
                if params[key]:
                    program_params[key] = params[key]
            # Everything in program_params is a parameter for the program's CLI now
            execution_controller = ExecutionController()
            job_submission_params = {
                CRConstants.PARAM_JOB_NAME: job_name,
                CRConstants.PARAM_INFRA: infrastructure,
                CRConstants.PARAM_JOB_TYPE: program_name,
                CRConstants.PARAM_JOB_PARAMS: program_params
            }
            result = execution_controller.run_job(job_submission_params)
            if result["success"]:
                job_wrapper = LocalJobWrapper(
                    user_id=self.user.user_id(),
                    name=job_name,
                    job_type=program_name,
                    pid=result["pid"],
                    output_location=result["output_location"]
                )
                job_wrapper.put()
                context = {
                    "programs": ExecutionController.available_programs(),
                    "success_alert": "Successfully submitted '{0}' for execution!".format(job_name)
                }
                return self.render_response(self.STEP_1_VIEW, **context)
            else:
                context = {
                    'program_name': program_name,
                    'infra': infrastructure,
                    'job_name': job_name,
                    'error_alert': result["reason"]
                }
                return self.render_response("{0}.html".format(program_name), **context)
        else:
            # Unrecognized
            pass

