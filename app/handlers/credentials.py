try:
  import json
except ImportError:
  from django.utils import simplejson as json
import sys
from collections import OrderedDict
import traceback
import __future__
import random, string
import time
from google.appengine.ext import db

from base import BaseHandler
from constants import CRConstants
from utils import utils
from services.cloudmanager import CloudManager, InvalidInfrastructureError

class CredentialsPage(BaseHandler):
    """
    /credentials
    """
    def authentication_required(self):
        return True
    
    def get(self):
        context = {}
        try:
            user_id = self.user.user_id()
        except Exception, e:
            raise InvalidUserException('Cannot determine the current user. '+str(e))
        try:
            infrastructure = self.request.get('infrastructure').lower()
            context = self.__get_context(user_id, infrastructure)
            # context['all_infrastructures'] += ['AWS', 'AWS']
        except InvalidInfrastructureError, e:
            context = self.__get_context(user_id, None)
            context['status'] = False
            context['banner_msg'] = "Unknown infrastructure specified: '{0}'".format(infrastructure)
        else:
            if not context["infrastructure"]:
                context["error_alert"] = "You haven't deployed any programs to one of the supported infrastructures yet!"
        return self.render_response('credentials.html', **context)
    
    def post(self):
        params = self.request.get
        try:
            # User id is a string
            user_id = self.user.user_id()
            if user_id is None:
                raise InvalidUserException
        except Exception, e:
            raise InvalidUserException('Cannot determine the current user. '+str(e))
        
        # Get the context of the page and make sure infrastructure is valid
        infrastructure = params('infrastructure').lower()
        context = {}
        try:
            context = self.__get_context(user_id, infrastructure)
        except InvalidInfrastructureError, e:
            context['status'] = False
            context['banner_msg'] = "Unknown infrastructure specified: '{0}'".format(infrastructure)
            return self.render_response('credentials.html', **context)
        
        if not context["infrastructure"]:
            context["error_alert"] = "You haven't deployed any programs to one of the supported infrastructures yet!"
            return self.render_response('credentials.html', **context)
        
        action = params('action')
        credentials = self.user.get_credentials(infrastructure)

        if action == 'save':
            # Save the access and private keys to the datastore
            credentials = {
                CRConstants.PARAM_CREDS_PUBLIC: params('access_key'),
                CRConstants.PARAM_CREDS_PRIVATE: params('secret_key')
            }
            context = self.__get_context(user_id, infrastructure, credentials=credentials)
            if context['valid_credentials']:
                self.user.set_credentials(infrastructure, credentials)
                self.user.put()
                context['credentials_msg'] = 'The {0} keys have been validated.'.format(infrastructure.upper())
                context['status'] = True
            else:
                context['credentials_msg'] = 'Invalid {0} credentials!'.format(infrastructure.upper())
            
            return self.render_response('credentials.html', **context)
        elif action == 'start':
            result = self.__start_vms(
                user_id,
                infrastructure,
                credentials,
                params('num_vms')
            )
            return self.redirect('/credentials?infrastructure={0}'.format(infrastructure))
        elif action == 'stop':
            result = self.__stop_vms(
                user_id,
                infrastructure,
                credentials
            )
            # Get the context again after stopping VMs
            context = self.__get_context(user_id, infrastructure, credentials=credentials)
            context['status'] = True
            context['msg'] = 'Sucessfully terminated all running compute nodes.'
            return self.render_response('credentials.html',**context)
        elif action == 'refresh':
            return self.redirect('/credentials?infrastructure={0}'.format(infrastructure.upper()))
        else:
            result = {
                'status': False,
                'msg': 'There was an error processing the request'
            }
            return self.render_response('credentials.html', **(dict(context, **result)))

    def __get_context(self, user_id, infrastructure, credentials=None):
        # Get all valid infrastructures
        all_infrastructures = [infra for infra in CloudManager.available_infrastructures() if infra != "local"]
        if not all_infrastructures:
            context = {
                "infrastructure": None,
                'status': False,
                'valid_credentials': False
            }
            return context
        # Check that we have an infrastructure
        if not infrastructure:
            infrastructure = all_infrastructures[0]
        # Get the credentials now
        if credentials is None:
            credentials = self.user.get_credentials(infrastructure)
        
        # Setup the basic context items
        context = {
            'infrastructure': infrastructure.upper(),
            'all_infrastructures': [infra.upper() for infra in all_infrastructures if infra != infrastructure]
        }
        cloud_manager = CloudManager()
        params = {
            CRConstants.PARAM_INFRA: infrastructure,
            CRConstants.PARAM_CREDENTIALS: credentials
        }
        # Check if the credentials are valid.
        if not cloud_manager.validate_credentials(params):
            context['status'] = False
            context['valid_credentials'] = False
            context['active_vms'] = False
            context['vm_status'] = False
            context['vm_status_msg'] = 'Could not determine the status of the VMs: Invalid Credentials.'            
        else:
            context['valid_credentials'] = True
            context['access_key'] = '*' * len(credentials['access_key'])
            context['secret_key'] = '*' * len(credentials['secret_key'])
            
            all_vms = cloud_manager.describe_instances(params)
            if all_vms:
                number_pending = 0
                number_running = 0
                for vm in all_vms:
                    if vm != None and vm['state'] == 'pending':
                        number_pending = number_pending + 1
                    elif vm != None and vm['state'] == 'running':
                        number_running = number_running + 1
                number_of_vms = len(all_vms)
                utils.log("number pending = " + str(number_pending))
                utils.log("number running = " + str(number_running))
                
                context['status'] = True
                context['number_of_vms'] = number_of_vms
                context['number_pending'] = number_pending
                context['number_running'] = number_running
                context['active_vms'] = number_running+number_pending != 0
            else:
                context['status'] = False
                context['active_vms'] = False
                if all_vms is None:
                    context['vm_status'] = False
                    context['vm_status_msg'] = 'Could not determine the status of the VMs.'
        return context
                    
    def __start_vms(self, user_id, infrastructure, credentials, num_vms):
        key_random_name = user_id + "-" + ''.join(
            random.choice(string.ascii_uppercase + string.digits) for x in range(6)
        )
        
        cloud_manager = CloudManager()
        launch_params = {
            CRConstants.PARAM_INFRA      : infrastructure,
            CRConstants.PARAM_CREDENTIALS: credentials,
            CRConstants.PARAM_NUM_VMS    : num_vms,
            CRConstants.PARAM_KEY_NAME   : key_random_name,
            CRConstants.PARAM_BLOCKING   : True
        }
        result = cloud_manager.launch_instances(launch_params)
        # if result != None and result['success']:
        #     result = {
        #         'status': True,
        #         'msg': 'Sucessfully requested '+ str(number_of_vms) + ' Virtual Machines.'
        #     }
        # else:
        #     result = {
        #         'status': False,
        #         'msg': 'Request to start the machines failed. Please contact the administrator.'
        #     }
        return result
    
    def __stop_vms(self, user_id, infrastructure, credentials):
        cloud_manager = CloudManager()
        terminate_params = {
            CRConstants.PARAM_INFRA      : infrastructure,
            CRConstants.PARAM_CREDENTIALS: credentials,
            CRConstants.PARAM_KEY_PREFIX : user_id,
            CRConstants.PARAM_BLOCKING   : True
        }
        result = cloud_manager.terminate_instances(terminate_params)
        return result

class InvalidUserException(Exception):
    pass

