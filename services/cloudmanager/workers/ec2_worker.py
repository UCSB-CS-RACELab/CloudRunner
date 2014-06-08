import sys,os,traceback
import datetime, time, uuid
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../lib/boto'))
import boto.ec2
from boto.exception import EC2ResponseError
from boto.ec2.cloudwatch import MetricAlarm
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))
from utils import utils
from constants import CRConstants
from base_worker import BaseWorker, WorkerConfigurationException, WorkerRuntimeException

__author__ = 'hiranya, anand, chris'
__email__ = 'hiranya@appscale.com, anand@cs.ucsb.edu, chris@horukmail.com'

class EC2Worker(BaseWorker):
    """
    EC2 infrastructure agent class which can be used to spawn and terminate
    VMs in an EC2 based environment.
    """

    # The maximum amount of time, in seconds, that we are willing to wait for
    # a virtual machine to start up, from the initial run-instances request.
    # Setting this value is a bit of an art, but we choose the value below
    # because our image is roughly 10GB in size, and if Eucalyptus doesn't
    # have the image cached, it could take half an hour to get our image
    # started.
    MAX_VM_CREATION_TIME = 1200

    # The amount of time that run_instances waits between each describe-instances
    # request. Setting this value too low can cause Eucalyptus to interpret
    # requests as replay attacks.
    SLEEP_TIME = 20

    PARAM_REGION = CRConstants.PARAM_REGION
    PARAM_CREDENTIALS = CRConstants.PARAM_CREDENTIALS
    PARAM_CREDS_PUBLIC = CRConstants.PARAM_CREDS_PUBLIC
    PARAM_CREDS_PRIVATE = CRConstants.PARAM_CREDS_PRIVATE
    PARAM_GROUP = CRConstants.PARAM_GROUP
    PARAM_IMAGE_ID = CRConstants.PARAM_IMAGE_ID
    PARAM_IMAGE_NAME = CRConstants.PARAM_IMAGE_NAME
    PARAM_INSTANCE_TYPE = CRConstants.PARAM_INSTANCE_TYPE
    PARAM_KEYNAME = CRConstants.PARAM_KEY_NAME
    PARAM_KEY_PREFIX = CRConstants.PARAM_KEY_PREFIX
    PARAM_INSTANCE_IDS = CRConstants.PARAM_INSTANCE_IDS
    PARAM_INSTANCE_ID = CRConstants.PARAM_INSTANCE_ID
    PARAM_WORKER_QUEUE = CRConstants.PARAM_WORKER_QUEUE
    PARAM_QUEUE_HEAD = CRConstants.PARAM_QUEUE_HEAD
    PARAM_SPOT = CRConstants.PARAM_SPOT
    PARAM_SPOT_PRICE = CRConstants.PARAM_SPOT_PRICE

    REQUIRED_EC2_MAKE_IMAGE_PARAMS = (
        PARAM_REGION,
        PARAM_CREDENTIALS,
        PARAM_INSTANCE_ID,
        PARAM_IMAGE_NAME
    )
    
    REQUIRED_EC2_RUN_INSTANCES_PARAMS = (
        PARAM_REGION,
        PARAM_CREDENTIALS,
        PARAM_GROUP,
        PARAM_IMAGE_ID,
        PARAM_INSTANCE_TYPE,
        PARAM_KEYNAME,
        PARAM_SPOT
    )

    REQUIRED_EC2_TERMINATE_INSTANCES_PARAMS = (
        PARAM_REGION,
        PARAM_CREDENTIALS,
        PARAM_INSTANCE_IDS
    )

    DESCRIBE_INSTANCES_RETRY_COUNT = 3
    
    FILE_NAME = "ec2_agent.py"

    def configure_instance_security(self, parameters):
        """
        Setup EC2 security keys and groups. Required input values are read from
        the parameters dictionary. More specifically, this method expects to
        find a 'keyname' parameter and a 'group' parameter in the parameters
        dictionary. Using these provided values, this method will create a new
        EC2 key-pair and a security group. Security group will be granted permissions
        to access any port on the instantiated VMs. (Also see documentation for the
        BaseAgent class)

        Args:
        parameters  A dictionary of parameters
        """
        keyname = parameters[self.PARAM_KEYNAME]
        #keyname = "cloudrunner-keypair"
        group = parameters[self.PARAM_GROUP]
        #group = "cloudrunner-security-group"
        key_path = '{0}.key'.format(keyname)
        ssh_key = os.path.abspath(key_path)
        utils.log(
            'About to spawn EC2 instances - Expecting to find a key at {0}'.format(ssh_key)
        )
        try:
            conn = self.open_connection(parameters)
            if os.path.exists(ssh_key):
                utils.log('SSH keys found in the local system - Not initializing EC2 security')
            else:
                utils.log('Creating key pair: ' + keyname)
                key_pair = conn.create_key_pair(keyname)
                utils.write_key_file(ssh_key, key_pair.material)

            security_groups = conn.get_all_security_groups()
            group_exists = False
            for security_group in security_groups:
                if security_group.name == group:
                    group_exists = True
                    break
            if not group_exists:
                utils.log('Creating security group: ' + group)
                newgroup = conn.create_security_group(group, 'CloudRunner security group')
                newgroup.authorize('tcp', 22, 22, '0.0.0.0/0')
                newgroup.authorize('tcp', 5672, 5672, '0.0.0.0/0')
                newgroup.authorize('tcp', 6379, 6379, '0.0.0.0/0')
                newgroup.authorize('tcp', 11211, 11211, '0.0.0.0/0')
                newgroup.authorize('tcp', 55672, 55672, '0.0.0.0/0')
            result = {
                'success': True,
                'absolute_key_path': ssh_key
            }
            return result
        except EC2ResponseError as exception:
            self.handle_failure(
                'EC2 response error while initializing security: {0}'.format(exception.error_message)
            )
        except Exception as exception:
            self.handle_failure(
                'Error while initializing EC2 security: {0}'.format(exception.message)
            )

    def assert_required_parameters(self, parameters, operation):
        """
        Assert that all the parameters required for the EC2 agent are in place.
        (Also see documentation for the BaseAgent class)

        Args:
        parameters  A dictionary of parameters
        operation   Operations to be invoked using the above parameters
        """
        required_params = ()
        if operation == BaseAgent.OPERATION_RUN:
            required_params = self.REQUIRED_EC2_RUN_INSTANCES_PARAMS
        elif operation == BaseAgent.OPERATION_TERMINATE:
            required_params = self.REQUIRED_EC2_TERMINATE_INSTANCES_PARAMS

        for param in required_params:
            if not utils.has_parameter(param, parameters):
                raise AgentConfigurationException('no ' + param)
    
    def describe_instances_old(self, parameters):
        """
        Retrieves the list of running instances that have been instantiated using a
        particular EC2 keyname. The target keyname is read from the input parameter
        map. (Also see documentation for the BaseAgent class)

        Args:
        parameters  A dictionary containing the 'keyname' parameter

        Returns:
        A tuple of the form (public_ips, private_ips, instances) where each
        member is a list.
        """
        instance_ids = []
        public_ips = []
        private_ips = []

        conn = self.open_connection(parameters)
        reservations = conn.get_all_instances()
        instances = [i for r in reservations for i in r.instances]
        utils.log("Looking for instances with key = {0}".format(parameters[self.PARAM_KEYNAME]))
        for i in instances:
            if i.state == 'running' and i.key_name == parameters[self.PARAM_KEYNAME]:
                instance_ids.append(i.id)
                public_ips.append(i.public_dns_name)
                private_ips.append(i.private_dns_name)
        return public_ips, private_ips, instance_ids
    
    def describe_instances(self, parameters, prefix=''):
        """
        Retrieves the list of running instances that have been instantiated.
        The target keyname is read from the input parameter map. (Also see
        documentation for the BaseAgent class)

        Args:
        parameters  A dictionary containing the 'keyname' parameter

        Returns:
        A list of dictionaries, each one representing a running instance.
        """
        conn = self.open_connection(parameters)
        reservations = conn.get_all_instances()
        instanceList = []
        instances = [i for r in reservations for i in r.instances if i.state == 'running']
        instance_ids = []
        if self.PARAM_INSTANCE_IDS in parameters:
            instance_ids = parameters[self.PARAM_INSTANCE_IDS]
        else:
            instance_ids = [i.id for i in instances]
        for i in instances:
            if i.key_name is not None and i.key_name.startswith(prefix) and i.id in instance_ids:
                instance = dict()
                instance["id"] = i.id
                instance["public_ip"] = i.public_dns_name
                instance["private_ip"] = i.private_dns_name
                instance["state"]= i.state
                instance["key_name"] = i.key_name
                instanceList.append(instance)
        return instanceList
    
    def validate_credentials(self, credentials):
        '''
        '''
        if not credentials or not (credentials[self.PARAM_CREDS_PUBLIC] or credentials[self.PARAM_CREDS_PRIVATE]):
            return False
        try:
            conn = self.open_connection({
                self.PARAM_CREDENTIALS: credentials,
                self.PARAM_REGION: 'us-east-1'
            })
            # Send an actual request to test the creds
            conn.get_all_regions()
            return True
        except EC2ResponseError:
            return False
    
    def make_image(self, parameters, instance_id):
        '''
        '''
        conn = self.open_connection(parameters)
    	new_ami_id = conn.create_image(instance_id, parameters[self.PARAM_IMAGE_NAME])
    	new_ami = conn.get_image(new_ami_id)
    	while new_ami.state != 'available':
            time.sleep(5)
            new_ami.update()
    	# Make it public
        conn.modify_image_attribute(
    		new_ami_id, 
    		attribute='launchPermission', 
    		operation='add', 
    		groups='all'
    	)
        return new_ami_id

    def make_sleepy(self,parameters, instance_id):
        utils.log( "Making instance {0} sleepy...".format(instance_id))
        credentials = parameters[self.PARAM_CREDENTIALS]
        ec2 = boto.connect_cloudwatch(
            str(credentials[self.PARAM_CREDS_PUBLIC]),
            str(credentials[self.PARAM_CREDS_PRIVATE])
        )
        region = "us-east-1"
        terminate_arn = 'arn:aws:automate:{0}:ec2:terminate'.format(region)
        alarm_name = 'ec2_shutdown_sleepy_{0}'.format(instance_id)
        # define our alarm to terminate the instance if it gets sleepy
        # i.e. if CPU utilisation is less than 10% for 1 x 4 hr intervals    
        sleepy_alarm = MetricAlarm(
            name=alarm_name,
            namespace='AWS/EC2',
            metric='CPUUtilization',
            statistic='Average',
            comparison='<',
            threshold='10',
            period='3600',
            evaluation_periods=4,
            alarm_actions=[terminate_arn],
            dimensions={'InstanceId':instance_id}
        )
        # create the alarm.. Zzzz!
        ec2.create_alarm(sleepy_alarm)


    def run_instances(self, count, parameters, security_configured):
        """
        Spawns the specified number of EC2 instances using the parameters
        provided. This method is blocking in that it waits until the
        requested VMs are properly booted up. However if the requested
        VMs cannot be procured within 1800 seconds, this method will treat
        it as an error and return. (Also see documentation for the BaseAgent
        class)

        Args:
        count               No. of VMs to spawned
        parameters          A dictionary of parameters. This must contain 'keyname',
        'group', 'image_id' and 'instance_type' parameters.
        security_configured Uses this boolean value as an heuristic to
        detect brand new AppScale deployments.

        Returns:
        A tuple of the form (instances, public_ips, private_ips)
        """
        image_id = parameters[self.PARAM_IMAGE_ID]
        instance_type = parameters[self.PARAM_INSTANCE_TYPE]
        keyname = parameters[self.PARAM_KEYNAME]
        group = parameters[self.PARAM_GROUP]
        spot = parameters[self.PARAM_SPOT]
        utils.log('[{0}] [{1}] [{2}] [{3}] [ec2] [{4}] [{5}]'.format(
            count,
            image_id,
            instance_type,
            keyname,
            group,
            spot
        ))
        credentials = parameters[self.PARAM_CREDENTIALS]
        creds = parameters['credentials']
        f = open('userfile','w')
        userstr = """#!/bin/bash \nset -x \nexec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1 \n"""
        userstr += "echo BEGIN \n"
        #TODO: This doesnt work...
        # userstr += "su ubuntu \n"
        #TODO: So this is the workaround...(potentially unsafe to run worker as root with pickle serializer)
        userstr += "export C_FORCE_ROOT=1"
        userstr += 'source ~/.bashrc \n'
        # All wokers need an alarm, but the queue head doesn't
        skip_alarm = False
        if self.PARAM_QUEUE_HEAD in parameters and parameters[self.PARAM_QUEUE_HEAD]:
            skip_alarm = True
            # Queue head, needs to have at least two cores
            insufficient_cores = ['t1.micro', 'm1.small', 'm1.medium', 'm3.medium']
            if instance_type in insufficient_cores:
                instance_type = 'c3.large'
            # Create the user that we want to use to connect to the broker
            # and configure its permissions on the default vhost.
            userstr += "rabbitmqctl add_user stochss ucsb\n"
            userstr += 'rabbitmqctl set_permissions -p / stochss ".*" ".*" ".*"\n'
        else:
            # Update celery config file...it should have the correct IP
            # of the Queue head node, which should already be running.
            celery_config_filename = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "../../jobmanager/celeryconfig.py"
            )
            # Pass it line by line so theres no weird formatting errors from 
            # trying to echo a multi-line file directly on the command line
            with open(celery_config_filename, 'r') as celery_config_file:
                lines = celery_config_file.readlines()
                # Make sure we overwrite the file with our first write
                config_file_path = '/home/ubuntu/cloudrunner/services/jobmanager/celeryconfig.py'
                userstr += "echo '{0}' > {1}\n".format(lines[0], config_file_path)
                for line in lines[1:]:
                    userstr += "echo '{0}' >> {1}\n".format(line, config_file_path)
        # Even the queue head gets a celery worker
        if self.PARAM_WORKER_QUEUE in parameters:
            userstr += "nohup celery -A services.jobmanager.tasks worker --autoreload --loglevel=info -Q {0} --workdir /home/ubuntu/cloudrunner > /home/ubuntu/cloudrunner-worker.log 2>&1 & \n".format(
                parameters[self.PARAM_WORKER_QUEUE]
            )
        else:
            userstr += "nohup celery -A services.jobmanager.tasks worker --autoreload --loglevel=info --workdir /home/ubuntu/cloudrunner > /home/ubuntu/cloudrunner-worker.log 2>&1 & \n"
        f.write(userstr)
        f.close()
        start_time = datetime.datetime.now()
        active_public_ips = []
        active_private_ips = []
        active_instances = []

        try:
            attempts = 1
            while True:
                instance_info = self.describe_instances_old(parameters)
                active_public_ips = instance_info[0]
                active_private_ips = instance_info[1]
                active_instances = instance_info[2]

                # If security has been configured on this agent just now,
                # that's an indication that this is a fresh cloud deployment.
                # As such it's not expected to have any running VMs.
                if len(active_instances) > 0 or security_configured:
                    break
                elif attempts == self.DESCRIBE_INSTANCES_RETRY_COUNT:
                    self.handle_failure('Failed to invoke describe_instances')
                attempts += 1

            conn = self.open_connection(parameters)
            if spot == 'True':
                price = parameters[self.PARAM_SPOT_PRICE]
                spot_request = conn.request_spot_instances(
                    str(price),
                    image_id,
                    key_name=keyname,
                    security_groups=[group],
                    instance_type=instance_type,
                    count=count,
                    user_data = userstr
                )
            else:
                reservation = conn.run_instances(
                    image_id,
                    min_count=count,
                    max_count=count,
                    key_name=keyname,
                    security_groups=[group],
                    instance_type=instance_type,
                    user_data=userstr
                )

            instance_ids = []
            public_ips = []
            private_ips = []
            utils.sleep(10)
            end_time = datetime.datetime.now() + datetime.timedelta(0, self.MAX_VM_CREATION_TIME)
            now = datetime.datetime.now()

            while now < end_time:
                time_left = (end_time - now).seconds
                utils.log('[{0}] {1} seconds left...'.format(now, time_left))
                instance_info = self.describe_instances_old(parameters)
                public_ips = instance_info[0]
                private_ips = instance_info[1]
                instance_ids = instance_info[2]
                public_ips = utils.diff(public_ips, active_public_ips)
                private_ips = utils.diff(private_ips, active_private_ips)
                instance_ids = utils.diff(instance_ids, active_instances)
                if count == len(public_ips):
                    break
                utils.sleep(self.SLEEP_TIME)
                now = datetime.datetime.now()

            if not public_ips:
                self.handle_failure(
                    'No public IPs were able to be procured within the time limit'
                )

            if len(public_ips) != count:
                for index in range(0, len(public_ips)):
                    if public_ips[index] == '0.0.0.0':
                        instance_to_term = instance_ids[index]
                        utils.log('Instance {0} failed to get a public IP address and' \
                        ' is being terminated'.format(instance_to_term))
                        conn.terminate_instances([instance_to_term])

            end_time = datetime.datetime.now()
            total_time = end_time - start_time
            if spot:
                utils.log(
                    'TIMING: It took {0} seconds to spawn {1} spot instances'.format(total_time.seconds, count)
                )
            else:
                utils.log(
                    'TIMING: It took {0} seconds to spawn {1} regular instances'.format(total_time.seconds, count)
                )
                utils.log('Creating Alarms for the instances')
                for machineid in instance_ids:
                    if not skip_alarm:
                        self.make_sleepy(parameters, machineid)   
            return instance_ids, public_ips, private_ips
        except EC2ResponseError as exception:
            self.handle_failure(
                'EC2 response error while starting VMs: '+exception.error_message
            )
        except Exception as exception:
            if isinstance(exception, AgentRuntimeException):
                raise exception
            else:
                self.handle_failure('Error while starting VMs: ' + exception.message)

    def terminate_instances(self, parameters):
        """
        Stop one or more EC2 instances. The input instance IDs are
        fetched from the 'instance_ids' parameter in the input parameters
        map. (Also see documentation for the BaseAgent class)
        If parameters contains the 'prefix' key, instances will be terminated
        based on whether or not the keypair used to start them begins with
        the given prefix.

        Args:
        parameters  A dictionary of parameters
        """
        conn = self.open_connection(parameters)
        instance_ids = []
        if self.PARAM_KEY_PREFIX in parameters:
            prefix = parameters[self.PARAM_KEY_PREFIX]
            reservations = conn.get_all_instances()
            instances = [i for r in reservations for i in r.instances]
            for i in instances:
                if i.key_name is not None and i.key_name.startswith(prefix):
                    instance_ids.append(i.id)
        else:
            instance_ids = parameters[self.PARAM_INSTANCE_IDS]
        terminated_instances = conn.terminate_instances(instance_ids)
        for instance in terminated_instances:
            instance.update()
            while instance.state != 'terminated':
                time.sleep(5)
                instance.update()
            utils.log('Instance {0} was terminated'.format(instance.id))
        return True


    def open_connection(self, parameters):
        """
        Initialize a connection to the back-end EC2 APIs.

        Args:
        parameters  A dictionary containing the 'credentials' parameter.

        Returns:
        An instance of Boto EC2Connection
        """
        credentials = parameters[self.PARAM_CREDENTIALS]
        region = parameters[self.PARAM_REGION]
        return boto.ec2.connect_to_region(
            region,
            aws_access_key_id=str(credentials[self.PARAM_CREDS_PUBLIC]),
            aws_secret_access_key=str(credentials[self.PARAM_CREDS_PRIVATE])
        )

    def handle_failure(self, msg):
        """
        Log the specified error message and raise an AgentRuntimeException

        Args:
        msg An error message to be logged and included in the raised exception

        Raises:
        AgentRuntimeException Contains the input error message
        """
        utils.log(msg)
        raise WorkerRuntimeException(msg)

if __name__ == "__main__":
    argc = len(sys.argv)
    if argc > 2:
        action = sys.argv[1]
        if action == "launch" and argc > 2:
            params_file = sys.argv[2]
            params = yaml.load(open(params_file, 'r'))
            os.system('rm -rf {0}'.format(params_file))
            worker = EC2Worker()
            worker.run_instances(params["count"], params, params["security_configured"])
        else:
            pass
    else:
        pass