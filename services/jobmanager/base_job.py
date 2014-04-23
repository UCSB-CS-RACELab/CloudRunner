import os, sys
import subprocess, shlex
import yaml
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../'))
from constants import CRConstants

global output_param
output_param = "out-dir"

class JobConfigurationException(Exception):
    '''
    This exception is raised when a job is misconfigured, e.g. missing some
    required parameters.
    '''
    def __init__(self, msg):
      Exception.__init__(self, msg)

class BaseJob(object):
    '''
    The base job class that all other job classes must inherit from. A single
     instance of the job class should encapsulate an entire unit of parallelizable
     work, such that parallelization can be achieved simply by running multiple 
     concurrent jobs.
    '''
    # All YAML job configuration files should be in the app/backend/jobs directory. 
    CONFIG_FILES_DIRECTORY = os.path.abspath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../programs_yaml')
    )
    # Required parameters to initialize a new job.
    REQUIRED_INIT_PARAMS = [
        CRConstants.PARAM_JOB_TYPE,
        CRConstants.PARAM_JOB_NAME,
        # CRConstants.PARAM_INFRA,
        CRConstants.PARAM_PROG_DIR_PATH
        # CRConstants.PARAM_YAML_DIR
    ]
    # Required keys to be present in the YAML config file
    REQUIRED_YAML_PARAMS = CRConstants.REQUIRED_PROGRAM_YAML_KEYS
    # Required parameters to run any job.
    REQUIRED_RUN_PARAMS = [
        'output_location',
        CRConstants.PARAM_BLOCKING
    ]
    
    def __init__(self, params):
        '''
        This method constructs a new job from params, a dictionary of parameters.
        The params dictionary must contain the keys specified in REQUIRED_INIT_PARAMS,
         as well as any of the required parameters of the job.
        If there are any file parameters being passed to the job, then self.execution_string
         will not be completely valid until after the run() method is called.
        '''
        # Assert general required params
        self.__assert_required_parameters(params, self.REQUIRED_INIT_PARAMS)
        job_type = params[CRConstants.PARAM_JOB_TYPE]
        job_name = params[CRConstants.PARAM_JOB_NAME]
        # Output directory will use job_name
        self.output_dir = '{0}'.format(job_name)
        # Grab the job-specific required params from the YAML file
        job_config = yaml.load(
            open('{0}/{1}.yaml'.format(self.CONFIG_FILES_DIRECTORY, job_type), 'r')
        )
        print "\njob_config:", job_config, "\n"
        # All YAML files need to have some parameters specified
        self.__assert_required_parameters(job_config, self.REQUIRED_YAML_PARAMS, is_dict=True)
        self.parameter_prefix = job_config[CRConstants.KEY_PARAM_PREFIX]
        self.parameter_suffix = job_config[CRConstants.KEY_PARAM_SUFFIX]
        # The execution string will start off with the name of the executable
        executable = job_config[CRConstants.KEY_EXECUTABLE][CRConstants.KEY_EXEC_NAME]
        self.execution_string = "{0}/{1}".format(
            params[CRConstants.PARAM_PROG_DIR_PATH],
            executable
        )
        # Next come the required parameters...
        required_file_params = job_config[CRConstants.KEY_REQ_FILE]
        required_value_params = job_config[CRConstants.KEY_REQ_VALUE]
        self.__assert_required_parameters(
            params,
            [file_param[CRConstants.KEY_FILE_NAME] for file_param in required_file_params]+required_value_params
        )
        # File parameters need to be saved for later because we have to write them to a file first
        # and we want to include them in the output directory
        self.input_files = {}
        for required_file in required_file_params:
            param_name = required_file[CRConstants.KEY_FILE_NAME]
            file_extension = required_file[CRConstants.KEY_FILE_EXTENSION]
            file_name = '{0}-{1}.{2}'.format(job_name, param_name, file_extension)
            file_contents = params[param_name]
            self.input_files[param_name] = (file_name, file_contents)
        # Value parameters are easy...
        self.__add_value_params_to_execution_string(params, required_value_params)
        # Now the optional parameters...
        if CRConstants.KEY_OPT_FILE in job_config:
            optional_file_params = job_config[CRConstants.KEY_OPT_FILE]
            for optional_file in optional_file_params:
                param_name = optional_file[CRConstants.KEY_FILE_NAME]
                if param_name in params:
                    file_extension = optional_file[CRConstants.KEY_FILE_EXTENSION]
                    file_name = '{0}-{1}.{2}'.format(job_name, param_name, file_extension)
                    file_contents = params[param_name]
                    self.input_files[param_name] = (file_name, file_contents)
        
        if CRConstants.KEY_OPT_VALUE in job_config:
            optional_value_params = job_config[CRConstants.KEY_OPT_VALUE]
            self.__add_value_params_to_execution_string(params, optional_value_params, optional=True)
        if CRConstants.KEY_OPT_BOOL in job_config:
            optional_bool_params = job_config[CRConstants.KEY_OPT_BOOL]
            self.__add_bool_params_to_execution_string(params, optional_bool_params)
        print "\n" + self.execution_string + "\n"
    
    def run(self, params):
        '''
        This method runs the actual job based off params, a dictionary of parameters. The
         params dictionary must contain the following keys:
         - output_location: Specifies where the output directory should be created.
         - executable_location: Specifies where to find the executable for the job.
         - blocking: Specifies whether the job should run synchronously or not.
        Returns a dictionary containing the result of running the job.
        '''
        self.__assert_required_parameters(params, self.REQUIRED_RUN_PARAMS)
        success = self.__create_output_dir(params['output_location'])
        if not success:
            result = {
                "success": False,
                "reason": "Couldn't create output directory in specified location: {0}".format(params['output_location'])
            }
            return result
            
        result = {
            "output_location": self.output_location
        }
        stdout = "{0}/stdout".format(self.output_location)
        stderr = "{0}/stderr".format(self.output_location)
        result["stdout_path"] = stdout
        result["stderr_path"] = stderr
        p = subprocess.Popen(
            shlex.split(self.execution_string),
            stdin=subprocess.PIPE,
            stdout=open(stdout, 'w'),
            stderr=open(stderr, 'w')
        )
        if params['blocking']:
            #TODO: Actually implement this
            stdout, stderr = p.communicate()
        else:
            #TODO: What else should be returned?
            result["pid"] = str(p.pid)
            result["status"] = CRConstants.JOB_STATE_RUNNING
        
        result["success"] = True
        return result
    
    def __assert_required_parameters(self, params, required_params, is_dict=False):
        '''
        @param params         : A dictionary of parameters to be verified.
        @param required_params: A list of required parameters whose inclusion should be asserted.
        '''
        print "Asserting required parameters:", required_params
        missing_params = []
        for param in required_params:
            if param not in params or params[param] is None:
                missing_params.append(param)
            # If is_dict == True, then required_params is actually a dictionary
            # Need to assert all of the sub_params too
            if is_dict and not missing_params:
                required_sub_params = required_params[param]
                sub_params = params[param]
                for sub_param in required_sub_params:
                    if sub_params and type(sub_params) is list and type(sub_params[0]) is dict:
                        for item in sub_params:
                            if sub_param not in item or item[sub_param] is None:
                                missing_params.append("{0}[{1}]".format(param, sub_param))
                    else:
                        if sub_param not in sub_params or sub_params[sub_param] is None:
                            missing_params.append("{0}[{1}]".format(param, sub_param))
        # Now make sure none were missing
        if len(missing_params) > 0:
            if len(missing_params) == 1:
                raise JobConfigurationException('missing required parameter: ' + missing_params[0])
            else:
                raise JobConfigurationException('missing required parameters: ' + str(missing_params))
        return True
    
    def __add_value_params_to_execution_string(self, params, keys, optional=False):
        '''
        @param params  : The dictionary containing (param, value) mappings.
        @param keys    : The list of possible parameter names.
        @param optional: If True, the parameter names in keys are considered optional.
        '''
        for key in keys:
            if optional:
                if key in params:
                    self.execution_string += " {0}{1}{2}{3}".format(self.parameter_prefix, key,
                                                                    self.parameter_suffix, params[key])
            else: #not optional
                self.execution_string += " {0}{1}{2}{3}".format(self.parameter_prefix, key,
                                                                    self.parameter_suffix, params[key])
    
    def __add_bool_params_to_execution_string(self, params, keys):
        '''
        @param params: The dictionary containing (param, value) mappings. Value is ignored.
        @param keys  : The list of possible parameter names.
        '''
        for key in keys:
            if key in params:
                self.execution_string += " {0}{1}".format(self.parameter_prefix, key)
    
    def __create_output_dir(self, reference_path):
        '''
        Utility method for creating the output directory. If this method returns True,
         self.output_location gets assigned to the absolute path to the output results.
        This method also creates all input files and adds them to self.execution_string.
        @param reference_path: The location where the jobs output directory should be created.
        @returns True if the output directory and all input files were created successfully, 
                 False otherwise.
        '''
        self.output_location = "{0}/{1}".format(reference_path, self.output_dir)
        create_output_dir_str = "mkdir -p {0}".format(self.output_location)
        if os.system(create_output_dir_str) != 0:
            self.output_location = None
            return False
        # TODO: output_param is a global for now, could just be another thing to specify in YAML file??
        self.__add_value_params_to_execution_string({output_param: self.output_location+'/result'},
                                                    [output_param])
        for param_name in self.input_files:
            file_name = self.input_files[param_name][0]
            file_contents = self.input_files[param_name][1]
            file_name = "{0}/{1}".format(self.output_location, file_name)
            fh = open(file_name, 'w')
            fh.write(file_contents)
            fh.close()
            self.__add_value_params_to_execution_string({param_name: file_name},
                                                        [param_name])
        return True


if __name__ == "__main__":
    path_to_sample_model = os.path.dirname(os.path.abspath(__file__))+'/../../../StochKit/models/examples/dimer_decay.xml'
    model_file = open(path_to_sample_model, 'r')
    stochkit_job_creation_params = {
        'job_type': 'Testing-ssa',
        'job_name': 'IAmUnique',
        # 'executable': 'ssa',
        'model': ''.join(model_file.readlines()),
        'time': 1000,
        'realizations': 10,
        'force': True,
        'intervals': int(1000/0.1)
    }
    model_file.close()
    stochkit_job = BaseJob(stochkit_job_creation_params)
    stochkit_job_run_params = {
        'output_location': os.path.dirname(os.path.abspath(__file__))+'/../../output',
        'executable_location': os.path.dirname(os.path.abspath(__file__))+'/../../../StochKit',
        'blocking': False
    }
    result = stochkit_job.run(stochkit_job_run_params)
    print "Result of running job:", result, "\n"
    print "Final execution string:", stochkit_job.execution_string, "\n"
    print "Success"