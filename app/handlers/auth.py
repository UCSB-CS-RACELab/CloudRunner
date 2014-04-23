import logging

from google.appengine.ext import ndb
from google.appengine.ext import db

from webapp2_extras.auth import InvalidAuthIdError, InvalidPasswordError
from webapp2_extras import security

from base import BaseHandler
from services.login.models import User
from services.login.admin import PendingUsersList, SecretToken

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
            user_email = self.request.POST['email']
            # Has this user been approved?
            pending_users_list = PendingUsersList.shared_list()
            if pending_users_list.is_user_approved(user_email):
                # Then create the user
                _attrs = {
                    'email_address': user_email,
                    'name': self.request.POST['name'],
                    'password_raw': self.request.POST['password']
                }
                success, user = self.auth.store.user_model.create_user(user_email, **_attrs)
                
                if success:
                    # Remove the user from the approved list now
                    pending_users_list.remove_user_from_approved_list(user_email)
                    context = {
                        'success_alert': True,
                        'alert_message': 'Account creation successful! You may now log in with your new account.'
                    }
                    return self.render_response('login.html', **context)
                else:
                    logging.info("Acount registration failed for: {0}".format(user))
                    context = {
                        'email_address': self.request.POST['email'],
                        'name': self.request.POST['name'],
                        'user_registration_failed': True
                    }
                    return self.render_response('user_registration.html', **context)
            else:
                # Not approved
                context = {
                    'error_alert': True,
                    'alert_message': 'You need to be approved by the admin before you can create an account.'
                }
                return self.render_response('login.html', **context)
        else:
            # Attempt to create an admin user
            logging.info('Registering an admin user...')
            # Check the secret token
            if SecretToken.is_admin_token(secret_key):
                # Then we can attempt to create an admin
                if User.admin_exists():
                    logging.info("An admin already exists, canceling registration...")
                    # Delete the token from the DB and redirect to login, only one admin allowed
                    SecretToken.destroy_all()
                    return self.redirect('/login')
                else:
                    # CREATE THE ADMIN ALREADY
                    _attrs = {
                        'email_address': self.request.POST['email'],
                        'name': self.request.POST['name'],
                        'password_raw': self.request.POST['password'],
                        'is_admin': 'YES'
                    }
                    success, user = self.auth.store.user_model.create_user(_attrs['email_address'], **_attrs)
                    
                    if success:
                        # Invalidate the token
                        SecretToken.destroy_all()
                        context = {
                            'success_alert': True,
                            'alert_message': 'Account creation successful! You may now log in with your new account.'
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
                # Unauthorized secret key
                context = {
                    'error_alert': True,
                    'alert_message': 'Invalid secret token.'
                }
                return self.render_response('login.html', **context)

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
        logging.info("WORKS")
        if SecretToken.is_admin_token(secret_key) and not User.admin_exists():
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
            # Just an email address here, we should first make sure they havent been approved
            pending_users_list = PendingUsersList.shared_list()
            if pending_users_list.is_user_approved(email_address):
                context = {
                    'approved_user_message': True
                }
                return self.render_response('user_registration.html', **context)
            # Now add to approval waitlist
            success = pending_users_list.add_user_to_approval_waitlist(email_address)
            if success:
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
            try:
                user = self.auth.get_user_by_password(email_address, password, remember=True)
                # Success, put user in the session and redirect to home page
                self.auth.set_session(user)
                return self.redirect('/')
            except (InvalidAuthIdError, InvalidPasswordError) as e:
                logging.info('Login failed for user: {0} with exception: {1}'.format(email_address, e))
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

