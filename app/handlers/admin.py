try:
  import json
except ImportError:
  from django.utils import simplejson as json
import logging, string, random

from base import BaseHandler
from services.login.admin import SecretToken, PendingUsersList
from services.login.models import User

class SecretTokenHandler(BaseHandler):
    '''
    Handles the endpoint for secret key creation.
    '''
    def authentication_required(self):
        return False
    
    def post(self):
        '''
        A POST to /secret_key means a new secret key should be generated from the string in the request body.
        '''
        # Dont allow requests from outside connections
        if self.request.headers['Host'].find('localhost') == -1:
            return
        SecretToken.create(self.request.get('key_string'))
        self.response.out.write('Successful secret key creation!')

def admin_required(handler):
    """
    Decorator for requiring admin access to page.
    Assumes user already logged in, so redirects to profile page if not admin
    """
    def check_admin(self, *args, **kwargs):
        if self.user.is_admin_user:
            return handler(self, *args, **kwargs)
        else:
            self.redirect('/profile')
    return check_admin

class AdminPage(BaseHandler):
    """
    """
    def authentication_required(self):
        return True
    
    @admin_required
    def get(self):
        """ Corresponds to GET /admin """
        users = User.query().fetch()
        if len(users) == 0:
            users = None
        pending_users_list = PendingUsersList.shared_list()

        context = {
            'active_users': users,
            'approved_users': pending_users_list.approved_users,
            'users_waiting_approval': pending_users_list.users_waiting_approval
        }
        self.render_response('admin.html', **context)
        
    @admin_required
    def post(self):
        """
        Main entry point of ajax calls from Admin page.
        """
        action = self.request.get('action')
        email = self.request.get('email')
        logging.info("Processing admin request to perform action '{0}' with email '{1}'".format(action, email))
        json_result = {
            'email': email
        }
        failure_message = ''
        if action in ['approve', 'approve1']:
            result = self._approve_user(email, action == 'approve1')
        elif action == 'deny':
            result = self._deny_user(email)
        elif action == 'revoke':
            result = self._revoke_user(email)
        elif action == 'delete':
            result = self._delete_user(email)
            if not result:
                failure_message = "You can't delete the admin user!"
        elif action == 'reset':
            result, password = self._reset_user_password(email)
            json_result['password'] = password
        else:
            json_result['success'] = False
            return self.response.write(json.dumps(json_result))
        
        json_result['success'] = result
        if failure_message is not '':
            json_result['message'] = failure_message
        return self.response.write(json.dumps(json_result))
    
    def _approve_user(self, email, awaiting_approval):
        """ Add user to approved users list and remove it from the waiting approval list if necessary """
        pending_users_list = PendingUsersList.shared_list()
        success = pending_users_list.approve_user(email, awaiting_approval)
        return success
    
    def _deny_user(self, email):
        """ Remove user from waiting approval list """
        pending_users_list = PendingUsersList.shared_list()
        pending_users_list.remove_user_from_approval_waitlist(email)
        return True
        
    def _revoke_user(self, email):
        """ Remove user from approved users list """
        pending_users_list = PendingUsersList.shared_list()
        pending_users_list.remove_user_from_approved_list(email)
        return True

    def _delete_user(self, email):
        """ Delete existing user """
        user = User.get_by_auth_id(email)
        if user:
            if user.is_admin_user():
                return False
            # Delete from db
            user.key.delete()
            # Need to delete the auth_id from the 'unique' model store
            # see https://code.google.com/p/webapp-improved/source/browse/webapp2_extras/appengine/auth/models.py
            unique_auth_id = "User.auth_id:{0}".format(email)
            User.unique_model.delete_multi([unique_auth_id])
        return True
    
    def _reset_user_password(self, email):
        '''
        Reset the password of the user with the given email address to a
         random password that they will be sure to change immediately.
        Returns a tuple (success, password), where success is a boolean
         indicating whether or not the operation completed and password is 
         the new password of the user if success is True.
        '''
        user = User.get_by_auth_id(email)
        # First we have 5 letters (upper/lowercase) or digits
        random_password = ''.join(random.choice(string.ascii_letters + string.digits) for x in range(5))
        # Then 2 punctuation chars
        random_password += ''.join(random.choice(string.punctuation) for x in range(2))
        # Then 5 more letters or digits
        random_password += ''.join(random.choice(string.ascii_letters + string.digits) for x in range(5))
        user.set_password(random_password)
        user.put()
        return (True, random_password)
