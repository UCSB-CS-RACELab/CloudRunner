import os, sys
import subprocess, shlex, yaml
import tempfile
from time import strftime
from workers.factory import CloudWorkerFactory
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../'))
from constants import CRConstants
from config_file import CRConfigFile

class InvalidInfrastructureError(Exception):
    pass

class CloudManager(object):
    '''
    '''
    INFRA_AWS = CRConstants.INFRA_AWS
    
    WORKER_SIZE_TINY = CRConstants.WORKER_SIZE_TINY
    WORKER_SIZE_SMALL = CRConstants.WORKER_SIZE_SMALL
    
    PARAM_INFRA = CRConstants.PARAM_INFRA
    PARAM_REGION = CRConstants.PARAM_REGION
    PARAM_CREDENTIALS = CRConstants.PARAM_CREDENTIALS
    PARAM_CREDS_PUBLIC = CRConstants.PARAM_CREDS_PUBLIC
    PARAM_CREDS_PRIVATE = CRConstants.PARAM_CREDS_PRIVATE
    PARAM_KEY_NAME = CRConstants.PARAM_KEY_NAME
    PARAM_KEY_PREFIX = CRConstants.PARAM_KEY_PREFIX
    PARAM_GROUP = CRConstants.PARAM_GROUP
    PARAM_INSTANCE_IDS = CRConstants.PARAM_INSTANCE_IDS
    PARAM_INSTANCE_ID = CRConstants.PARAM_INSTANCE_ID
    PARAM_NUM_VMS = CRConstants.PARAM_NUM_VMS
    PARAM_BLOCKING = CRConstants.PARAM_BLOCKING
    PARAM_WORKER_SIZE = CRConstants.PARAM_WORKER_SIZE
    
    LAUNCH_INSTANCES_REQ_PARAMS = [
        PARAM_INFRA,
        PARAM_CREDENTIALS,
        PARAM_NUM_VMS,
        PARAM_BLOCKING
    ]
    
    TERMINATE_INSTANCES_REQ_PARAMS = [
        PARAM_INFRA,
        PARAM_CREDENTIALS,
        PARAM_INSTANCE_IDS,
        PARAM_BLOCKING
    ]
    
    DESCRIBE_INSTANCES_REQ_PARAMS = [
        PARAM_INFRA,
        PARAM_CREDENTIALS
    ]
    
    CREATE_IMAGE_REQ_PARAMS = [
        PARAM_INFRA,
        PARAM_CREDENTIALS,
        PARAM_INSTANCE_ID
    ]
    
    VALIDATE_CREDS_REQ_PARAMS = [
        PARAM_INFRA,
        PARAM_CREDENTIALS
    ]
    
    SECURITY_GROUP = "cloudrunner"
    KEY_PREFIX = "cloudrunner-key-pair-"
    
    @classmethod
    def available_infrastructures(cls):
        return CRConfigFile.available_infrastructures()
    
    def launch_instances(self, params):
        '''
        '''
        result = {}
        # Get the agent
        infrastructure = params[self.PARAM_INFRA]
        credentials = params[self.PARAM_CREDENTIALS]
        agent = self.__get_agent(infrastructure)
        # Check for region parameter and use default if not there
        if self.PARAM_REGION not in params or not params[self.PARAM_REGION]:
            params[self.PARAM_REGION] = CRConfigFile.get_default_region_for_infrastructure(infrastructure)
        # Make sure key name has infrastructure in it as well...
        if self.PARAM_KEY_NAME not in params:
            params[self.PARAM_KEY_NAME] = "{0}{1}-1".format(
                self.KEY_PREFIX,
                infrastructure
            )
        else:
            params[self.PARAM_KEY_NAME] = "{0}{1}-{2}".format(
                self.KEY_PREFIX,
                infrastructure,
                params[self.PARAM_KEY_NAME]
            )
        # Make sure security groups are set up
        if self.PARAM_GROUP not in params:
            params[self.PARAM_GROUP] = self.SECURITY_GROUP
        temp_result = agent.configure_instance_security(params)
        security_configured = temp_result["success"]
        result["key_pair_path"] = temp_result["absolute_key_path"]
        # Now try to launch the instances
        #TODO: Remove True when background_thread is added (see TODO in else clause)
        if True or params[self.PARAM_BLOCKING]:
            # Synchronous so just call the method directly
            params["image_id"] = self.__get_image_id(infrastructure)
            # Use the right instance size
            if self.PARAM_WORKER_SIZE in params and params[self.PARAM_WORKER_SIZE]:
                params["instance_type"] = self.__infrastructure_instance_type(
                    infrastructure,
                    params[self.PARAM_WORKER_SIZE]
                )
            else:
                params["instance_type"] = self.__infrastructure_instance_type(
                    infrastructure,
                    self.WORKER_SIZE_TINY
                )
            # params["instance_type"] = "m1.small"#"t1.micro"
            params["use_spot_instances"] = False
            instance_ids, public_ips, private_ips = agent.run_instances(
                int(params[self.PARAM_NUM_VMS]),
                params,
                security_configured
            )
            # Now we need a description of the instances
            describe_params = {
                self.PARAM_INFRA: infrastructure,
                self.PARAM_CREDENTIALS: credentials,
                self.PARAM_INSTANCE_IDS: instance_ids
            }
            result["status"] = "Finished"
            result["success"] = True
            result["instances"] = self.describe_instances(describe_params)
        else:
            #TODO: Update GAE SDK and convert main application to a module
            #      with manual scaling so that we can use a background_thread
            #      to asynchronously spawn VMs.
            pass
        return result
    
    def terminate_instances(self, params):
        '''
        '''
        result = {}
        # Get the agent
        infrastructure = params[self.PARAM_INFRA]
        credentials = params[self.PARAM_CREDENTIALS]
        agent = self.__get_agent(infrastructure)
        # Check for region parameter and use default if not there
        if self.PARAM_REGION not in params or not params[self.PARAM_REGION]:
            params[self.PARAM_REGION] = CRConfigFile.get_default_region_for_infrastructure(infrastructure)
        # Check for key prefix param and prefix with cloudrunner's prefix if needed
        if self.PARAM_KEY_PREFIX in params:
            params[self.PARAM_KEY_PREFIX] = "{0}{1}-{2}".format(
                self.KEY_PREFIX,
                infrastructure,
                params[self.PARAM_KEY_PREFIX]
            )
        else:
            params[self.PARAM_KEY_PREFIX] = "{0}{1}".format(
                self.KEY_PREFIX,
                infrastructure
            )
        
        if params[self.PARAM_BLOCKING]:
            terminate_result = agent.terminate_instances(params)
            result['success'] = terminate_result
        else:
            #TODO: Update GAE SDK and convert main application to a module
            #      with manual scaling so that we can use a background_thread
            #      to asynchronously kill VMs.
            pass
        return result
    
    def describe_instances(self, params):
        '''
        '''
        # Get the agent
        infrastructure = params[self.PARAM_INFRA]
        agent = self.__get_agent(infrastructure)
        # Check for region parameter and use default if not there
        if self.PARAM_REGION not in params or not params[self.PARAM_REGION]:
            params[self.PARAM_REGION] = CRConfigFile.get_default_region_for_infrastructure(infrastructure)
        return agent.describe_instances(params, self.KEY_PREFIX)
    
    def create_image(self, params):
        '''
        '''
        result = {}
        # Get the agent
        infrastructure = params[self.PARAM_INFRA]
        agent = self.__get_agent(infrastructure)
    	month = strftime("%b")
    	day = strftime("%d")
        hour = strftime("%l").strip()
        minute = strftime("%M")
        am_or_pm = strftime("%p")
        params[agent.PARAM_IMAGE_NAME] = "CloudRunner-Worker-{0}{1}-{2}.{3}{4}".format(
            month,
            day,
            hour,
            minute,
            am_or_pm
        )
        # Check for region parameter and use default if not there
        if self.PARAM_REGION not in params or not params[self.PARAM_REGION]:
            params[self.PARAM_REGION] = CRConfigFile.get_default_region_for_infrastructure(infrastructure)
        image_id = agent.make_image(params, params[self.PARAM_INSTANCE_ID])
        result["image_id"] = str(image_id)
        return result
    
    def validate_credentials(self, params):
        '''
        '''
        infrastructure = params[self.PARAM_INFRA]
        credentials = params[self.PARAM_CREDENTIALS]
        # Get the agent
        infrastructure = params[self.PARAM_INFRA]
        return self.__get_agent(infrastructure).validate_credentials(credentials)
    
    def __get_agent(self, infrastructure):
        try:
            return CloudWorkerFactory().create_agent(infrastructure)
        except NameError, e:
            if str(e).startswith("Unrecognized infrastructure"):
                raise InvalidInfrastructureError(str(e))
            raise e
    
    def __get_image_id(self, infrastructure):
        return CRConfigFile.get_image_id(infrastructure)
    
    def __infrastructure_instance_type(self, infra, worker_size):
        if infra == self.INFRA_AWS:
            if worker_size == self.WORKER_SIZE_TINY:
                return "t1.micro"
            elif worker_size == self.WORKER_SIZE_SMALL:
                return "m1.small"
        else:
            pass

