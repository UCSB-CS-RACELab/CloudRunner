import os, sys
import subprocess, shlex, yaml
import tempfile
from time import strftime
from workers.factory import CloudWorkerFactory
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../'))
from services.jobmanager.tasks import CelerySingleton
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
    WORKER_SIZE_MEDIUM = CRConstants.WORKER_SIZE_MEDIUM
    
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
    PARAM_IMAGE_ID = CRConstants.PARAM_IMAGE_ID
    PARAM_NUM_VMS = CRConstants.PARAM_NUM_VMS
    PARAM_BLOCKING = CRConstants.PARAM_BLOCKING
    PARAM_WORKER_SIZE = CRConstants.PARAM_WORKER_SIZE
    PARAM_INSTANCE_TYPE = CRConstants.PARAM_INSTANCE_TYPE
    PARAM_QUEUE_HEAD = CRConstants.PARAM_QUEUE_HEAD
    PARAM_WORKER_QUEUE = CRConstants.PARAM_WORKER_QUEUE
    
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
    QUEUEHEAD_KEY_TAG = "queuehead"
    
    @classmethod
    def available_infrastructures(cls):
        return CRConfigFile.available_infrastructures()
    
    def launch_instances(self, params, builder=False):
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
        infrastructure_prefix = "{0}{1}".format(
            self.KEY_PREFIX,
            infrastructure
        )
        if self.PARAM_KEY_NAME not in params:
            params[self.PARAM_KEY_NAME] = "{0}-1".format(
                infrastructure_prefix
            )
        else:
            if not params[self.PARAM_KEY_NAME].startswith(infrastructure_prefix):
                params[self.PARAM_KEY_NAME] = "{0}-{1}".format(
                    infrastructure_prefix,
                    params[self.PARAM_KEY_NAME]
                )
        requested_key_name = params[self.PARAM_KEY_NAME]
        # Make sure security groups are set up
        if self.PARAM_GROUP not in params:
            params[self.PARAM_GROUP] = self.SECURITY_GROUP
        
        # Now try to launch the instances
        vms_requested = int(params[self.PARAM_NUM_VMS])
        if not self.__is_queue_head_running(infrastructure, credentials) and not builder:
            # The first vm we launch needs to be the queue head
            vms_requested = vms_requested - 1
            instance_ids, public_ips, private_ips, key_pair_path = self.__spawn_vms(
                infrastructure,
                1,
                params,
                queue_head=True
            )
            result["key_pair_path"] = key_pair_path
            # If only one VM was requested,
            if vms_requested == 0:
                # Then we need a description of the instance.
                describe_params = {
                    self.PARAM_INFRA: infrastructure,
                    self.PARAM_CREDENTIALS: credentials,
                    self.PARAM_INSTANCE_IDS: instance_ids,
                    self.PARAM_KEY_PREFIX: requested_key_name
                }
                result["status"] = "Finished"
                result["success"] = True
                result["instances"] = self.describe_instances(describe_params)
        # If queue head is running, we can proceed as normal
        #TODO: Remove True when background_thread is added (see TODO in else clause)
        if vms_requested>0:
            if True or params[self.PARAM_BLOCKING]:
                # Synchronous so just call the method directly
                instance_ids, public_ips, private_ips, key_pair_path = self.__spawn_vms(
                    infrastructure,
                    vms_requested,
                    params
                )
                result["key_pair_path"] = key_pair_path
                describe_params = {
                    self.PARAM_INFRA: infrastructure,
                    self.PARAM_CREDENTIALS: credentials,
                    self.PARAM_INSTANCE_IDS: instance_ids,
                    self.PARAM_KEY_PREFIX: requested_key_name
                }
                result["status"] = "Finished"
                result["success"] = True
                result["instances"] = self.describe_instances(describe_params)
            else:
                #TODO: Update GAE SDK and convert main application to a module
                #      with manual scaling so that we can use a background_thread
                #      to asynchronously spawn VMs.
                pass
        #
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
        # Check for key prefix param
        if self.PARAM_KEY_PREFIX in params and params[self.PARAM_KEY_PREFIX]:
            # Make sure it starts with our default prefix
            if not params[self.PARAM_KEY_PREFIX].startswith(self.KEY_PREFIX):
                params[self.PARAM_KEY_PREFIX] = "{0}{1}".format(
                    self.KEY_PREFIX,
                    params[self.PARAM_KEY_PREFIX]
                )
        else:
            params[self.PARAM_KEY_PREFIX] = self.KEY_PREFIX
        return agent.describe_instances(params, params[self.PARAM_KEY_PREFIX])
    
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
    
    def __spawn_vms(self, infrastructure, vms_requested, params, queue_head=False):
        agent = self.__get_agent(infrastructure)
        params[self.PARAM_IMAGE_ID] = self.__get_image_id(infrastructure)
        # Use the right instance size
        if self.PARAM_WORKER_SIZE in params and params[self.PARAM_WORKER_SIZE]:
            params[self.PARAM_INSTANCE_TYPE] = self.__infrastructure_instance_type(
                infrastructure,
                params[self.PARAM_WORKER_SIZE]
            )
        else:
            params[self.PARAM_INSTANCE_TYPE] = self.__infrastructure_instance_type(
                infrastructure,
                self.WORKER_SIZE_TINY
            )
        requested_key_name = params[self.PARAM_KEY_NAME]
        if queue_head:
            # Just set the right parameters and the agent will guarantee
            # the right instance size is used.
            params[self.PARAM_QUEUE_HEAD] = True
            params[self.PARAM_KEY_NAME] += "-{0}".format(self.QUEUEHEAD_KEY_TAG)
        temp_result = agent.configure_instance_security(params)
        security_configured = temp_result["success"]
        key_pair_path = temp_result["absolute_key_path"]
        params["use_spot_instances"] = False
        instance_ids, public_ips, private_ips = agent.run_instances(
            vms_requested,
            params,
            security_configured
        )
        if queue_head:
            params[self.PARAM_KEY_NAME] = requested_key_name
            params[self.PARAM_QUEUE_HEAD] = False
            # Should only be one queuehead launched
            self.__update_celery_config_with_queue_head_ip(public_ips[0])
        return [instance_ids, public_ips, private_ips, key_pair_path]
    
    def __infrastructure_instance_type(self, infra, worker_size):
        if infra == self.INFRA_AWS:
            if worker_size == self.WORKER_SIZE_TINY:
                return "t1.micro"
            elif worker_size == self.WORKER_SIZE_SMALL:
                return "m1.small"
            elif worker_size == self.WORKER_SIZE_MEDIUM:
                return "c3.large"
        else:
            pass
    
    def __infrastructure_running_state(self, infra):
        if infra == self.INFRA_AWS:
            return 'running'
        else:
            pass
    
    def __is_queue_head_running(self, infra, credentials, key_prefix=KEY_PREFIX):
        params = {
            self.PARAM_INFRA: infra,
            self.PARAM_CREDENTIALS: credentials,
            self.PARAM_KEY_PREFIX: key_prefix
        }
        all_vms = self.describe_instances(params)
        if all_vms == None:
            return False
        # Just need one running vm with the QUEUEHEAD_KEY_TAG in the name of the keypair
        for vm in all_vms:
            if vm != None and vm['state'] == self.__infrastructure_running_state(infra) and vm['key_name'].find(self.QUEUEHEAD_KEY_TAG) != -1:
                return True
        return False
    
    def __update_celery_config_with_queue_head_ip(self, queue_head_ip):
            # Write queue_head_ip to file on the appropriate line
            celery_config_filename = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "../jobmanager/celeryconfig.py"
            )
            celery_config_lines = []
            with open(celery_config_filename, 'r') as celery_config_file:
                celery_config_lines = celery_config_file.readlines()
            with open(celery_config_filename, 'w') as celery_config_file:
                for line in celery_config_lines:
                    if line.strip().startswith('BROKER_URL'):
                        celery_config_file.write('BROKER_URL = "amqp://stochss:ucsb@{0}:5672/"\n'.format(queue_head_ip))
                    else:
                        celery_config_file.write(line)
            # Now update the actual Celery app....
            #TODO: Doesnt seem to work in GAE until next request comes in to server
            my_celery = CelerySingleton()
            my_celery.configure()

