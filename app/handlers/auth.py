import logging

from google.appengine.ext import ndb
from google.appengine.ext import db

from webapp2_extras import security

from base import BaseHandler
from services.login.models import User
from services.login.auth import GateKeeper, Registrar
from services.login.admin import PendingUsersList, SecretToken
from constants import CRConstants

class UserRegistrationPage(BaseHandler):
    '''
    '''
    def authentication_required(self):
        return False
    
    def get(self):
        ''' Corresponds to GET /register '''
        context = {}
        try:
            secret_key = self.request.GET['secret_key']
        except KeyError:
            secret_key = None
        
        if secret_key is None:
            # Normal user registration
            context['create_admin'] = False
        else:
            # Attempt to create an admin user
            # We will just assume the secret key is fine because it was checked by the login page
            # But it will be checked again before the admin is actually created in the POST
            context['create_admin'] = True
            context['secret_key'] = secret_key
        
        self.render_response('user_registration.html', **context)
    
    def post(self):
        '''
        This is where user registration takes place, both for regular users as well as admins.
        An admin registers by presenting a secret token in the query string, which will be sent with the
        POST data.
        A user can register only if they have been approved by the admin, i.e. they are in the approved_users
        list (see admin.py).
        '''
        logging.info(self.request.POST)

        try:
            secret_key = self.request.POST['secret_key']
        except KeyError:
            secret_key = None
        
        if secret_key is None:
            # Normal user registration
            logging.info('Registering a normal user...')
            params = {
                CRConstants.PARAM_USER_EMAIL: self.request.POST['email'],
                CRConstants.PARAM_USER_PASS: self.request.POST['password'],
                CRConstants.PARAM_USER_NAME: self.request.POST['name']
            }
            result = Registrar.register_new_user(params)
            if result["success"]:
                context = {
                    'success_alert': True,
                    'alert_message': 'Account creation successful! You may now log in with your new account.'
                }
                return self.render_response('login.html', **context)
            else:
                if 'message' in result:
                    context = {
                        'error_alert': True,
                        'alert_message': result['message']
                    }
                    return self.render_response('login.html', **context)
                else:
                    context = {
                        'email_address': self.request.POST['email'],
                        'name': self.request.POST['name'],
                        'user_registration_failed': True
                    }
                    return self.render_response('user_registration.html', **context)
        else:
            # Attempt to create an admin user
            logging.info('Registering an admin user...')
            params = {
                CRConstants.PARAM_ADMIN_TOKEN: secret_key,
                CRConstants.PARAM_USER_EMAIL: self.request.POST['email'],
                CRConstants.PARAM_USER_PASS: self.request.POST['password'],
                CRConstants.PARAM_USER_NAME: self.request.POST['name']
            }
            result = Registrar.register_new_admin(params)
            if result["success"]:
                context = {
                    'success_alert': True,
                    'alert_message': 'Account creation successful! You may now log in with your new account.'
                }
                return self.render_response('login.html', **context)
            else:
                reason = result["reason"]
                if reason == CRConstants.REGISTRATION_FAIL_ADMIN_EXISTS:
                    return self.redirect('/login')
                elif reason == CRConstants.REGISTRATION_FAIL_INVALID_TOKEN:
                    context = {
                        'error_alert': True,
                        'alert_message': 'Invalid secret token.'
                    }
                    return self.render_response('login.html', **context)
                elif reason == CRConstants.REGISTRATION_FAIL_UNEXPECTED:
                    context = {
                        'email_address': self.request.POST['email'],
                        'name': self.request.POST['name'],
                        'user_registration_failed': True
                    }
                    return self.render_response('user_registration.html', **context)
                else:
                    utils.log("Found unrecognized reason for admin registration failure: {0}".format(reason))

class LoginPage(BaseHandler):
    """
    """
    def authentication_required(self):
        return False
    
    def get(self):
        """ Corresponds to /login """
        # Need to log in
        try:
            secret_key = self.request.GET['secret_key']
        except KeyError:
            secret_key = None
        if Registrar.validate_token(secret_key):
            return self.redirect('/register?secret_key={0}'.format(secret_key))
        # Just ignore unauthorized secret key query string param completely...
        return self.render_response('login.html')
    
    def post(self):
        '''
        Login attempt or request for account
        '''
        email_address = self.request.POST['email']
        try:
            request_account = self.request.POST['request_account']
        except KeyError:
            request_account = False
            
        if request_account:
            # Just an email address here
            result = Registrar.request_user_account(email_address)
            if result["success"]:
                # Might have already been approved
                if "approved" in result and result["approved"]:
                    context = {
                        'approved_user_message': True
                    }
                    return self.render_response('user_registration.html', **context)
                # Else it was a successful request
                context = {
                    'success_alert': True,
                    'alert_message': 'Successfully requested an account!'
                }
                return self.render_response('login.html', **context)
            else:
                context = {
                    'error_alert': True,
                    'alert_message': 'You have already requested an account.'
                }
                return self.render_response('login.html', **context)
        else:
            # Login attempt, need to grab password too
            password = self.request.POST['password']
            params = {
                CRConstants.PARAM_USER_EMAIL: email_address,
                CRConstants.PARAM_USER_PASS: password
            }
            result = GateKeeper.login(params)
            if result["success"]:
                self.auth.set_session(result["user"])
                return self.redirect('/')
            else:
                context = {
                    'error_alert': True,
                    'alert_message': 'The email or password you entered is incorrect.'
                }
                return self.render_response('login.html', **context)

class LogoutHandler(BaseHandler):
    '''
    '''
    def authentication_required(self):
        return True
    
    def get(self):
        '''
        Logout.
        '''
        self.session.clear()
        self.auth.unset_session()
        self.redirect('/login')

class AccountSettingsPage(BaseHandler):
    """
    """
    def authentication_required(self):
        return True
        
    def get(self):
        """ Corresponds to /account_settings """
        context = {
            'name': self.user.name,
            'email_address': self.user.email_address
        }
        self.render_response('account_settings.html', **context)
    
    def post(self):
        '''
        Corresponds to a possible attempt to change some account settings.
        Possible fields to change:
        - name
        - email_address
        - password
        '''
        should_update_user = False
        new_name = self.request.POST['name']
        try:
            new_email = self.request.POST['email']
        except KeyError:
            new_email = self.user.email_address
        if self.user.name != new_name:
            self.user.name = new_name
            should_update_user = True
        if self.user.email_address != new_email:
            if self.user.change_auth_id(new_email):
                self.user.email_address = new_email
                should_update_user = True
            else:
                context = {
                    'name': self.user.name,
                    'email_address': self.user.email_address,
                    'error_alert': 'A user with that email address already exists.'
                }
                return self.render_response('account_settings.html', **context)
        
        try:
            new_password = self.request.POST["password"]
            current_password = self.request.POST["current_password"]
        except KeyError:
            new_password = None
        
        if new_password not in [None, '']:
            # Check that correct current password was entered
            if security.check_password_hash(current_password, self.user.password):
                # Correct
                self.user.set_password(new_password)
                should_update_user = True
            else:
                # Incorrect
                context = {
                    'name': self.user.name,
                    'email_address': self.user.email_address,
                    'error_alert': 'Incorrect password.'
                }
                return self.render_response('account_settings.html', **context)
        
        if should_update_user:
            self.user.put()
            context = {
                'name': self.user.name,
                'email_address': self.user.email_address,
                'success_alert': 'Successfully updated account settings!'
            }
            return self.render_response('account_settings.html', **context)

