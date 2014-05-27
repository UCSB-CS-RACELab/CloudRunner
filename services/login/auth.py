import sys, os
from google.appengine.ext import ndb
from google.appengine.ext import db

from webapp2_extras import auth, security

from cloudrunnerapp import BaseHandler
from models import User

from admin import PendingUsersList, SecretToken
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../'))
from constants import CRConstants
from utils import utils

class Registrar(object):
    '''
    Implements interface for registering new accounts.
    '''
    PARAM_ADMIN_TOKEN = CRConstants.PARAM_ADMIN_TOKEN
    PARAM_USER_EMAIL = CRConstants.PARAM_USER_EMAIL
    PARAM_USER_PASS = CRConstants.PARAM_USER_PASS
    PARAM_USER_NAME = CRConstants.PARAM_USER_NAME
    
    REGISTRATION_FAIL_ADMIN_EXISTS = CRConstants.REGISTRATION_FAIL_ADMIN_EXISTS
    REGISTRATION_FAIL_INVALID_TOKEN = CRConstants.REGISTRATION_FAIL_INVALID_TOKEN
    REGISTRATION_FAIL_UNEXPECTED = CRConstants.REGISTRATION_FAIL_UNEXPECTED
    
    @classmethod
    def validate_token(cls, token):
        '''
        '''
        return SecretToken.is_admin_token(token) and not User.admin_exists()
    
    @classmethod
    def register_new_admin(cls, params):
        '''
        '''
        secret_key = params[cls.PARAM_ADMIN_TOKEN]
        email_address = params[cls.PARAM_USER_EMAIL]
        password = params[cls.PARAM_USER_PASS]
        name = params[cls.PARAM_USER_NAME]
        # Check the secret token
        if SecretToken.is_admin_token(secret_key):
            # Then we can attempt to create an admin
            if User.admin_exists():
                logging.info("An admin already exists, canceling registration...")
                # Delete the token from the DB and redirect to login, only one admin allowed
                SecretToken.destroy_all()
                result = {
                    "success": False,
                    "reason": cls.REGISTRATION_FAIL_ADMIN_EXISTS
                }
                return result
            else:
                # CREATE THE ADMIN ALREADY
                _attrs = {
                    'email_address': email_address,
                    'name': name,
                    'password_raw': password,
                    'is_admin': 'YES'
                }
                success, user = cls.auth.store.user_model.create_user(_attrs['email_address'], **_attrs)
                
                if success:
                    # Invalidate the token
                    SecretToken.destroy_all()
                    result = { 'success': True }
                    return result
                else:
                    result = {
                        'success': False,
                        'reason': cls.REGISTRATION_FAIL_UNEXPECTED
                    }
                    return cls.render_response('user_registration.html', **context)
        else:
            # Unauthorized secret key
            result = {
                'success': False,
                'reason': cls.REGISTRATION_FAIL_INVALID_TOKEN
            }
            return result
    
    @classmethod
    def register_new_user(cls, params):
        '''
        '''
        email_address = params[cls.PARAM_USER_EMAIL]
        password = params[cls.PARAM_USER_PASS]
        name = params[cls.PARAM_USER_NAME]
        # Has this user been approved?
        pending_users_list = PendingUsersList.shared_list()
        if pending_users_list.is_user_approved(email_address):
            # Then create the user
            _attrs = {
                'email_address': email_address,
                'name': name,
                'password_raw': password
            }
            success, user = cls.auth.store.user_model.create_user(
                email_address,
                **_attrs
            )
            if success:
                # Remove the user from the approved list now
                pending_users_list.remove_user_from_approved_list(email_address)
                result = { 'success': True }
                return result
            else:
                # Some unexpected error
                logging.info("Acount registration failed for: {0}".format(user))
                result = { 'success': False }
                return result
        else:
            # Not approved
            result = {
                'success': False,
                'message': 'You need to be approved by the admin before you can create an account.'
            }
            return result
    
    @classmethod
    def request_user_account(cls, email_address):
        '''
        '''
        # Check if already approved
        pending_users_list = PendingUsersList.shared_list()
        if pending_users_list.is_user_approved(email_address):
            result = {
                'success': True,
                'approved': True
            }
            return result
        # Now add to approval waitlist
        success = pending_users_list.add_user_to_approval_waitlist(email_address)
        if success:
            result = { 'success': True }
            return result
        else:
            # User already requested an account...
            result = { 'success': False }
            return result

class GateKeeper(object):
    '''
    Implements the interface for login attempts.
    '''
    PARAM_USER_EMAIL = CRConstants.PARAM_USER_EMAIL
    PARAM_USER_PASS = CRConstants.PARAM_USER_PASS
    
    @classmethod
    def login(cls, params):
        '''
        '''
        email_address = params[cls.PARAM_USER_EMAIL]
        password = params[cls.PARAM_USER_PASS]
        try:
            user = auth.get_auth().get_user_by_password(email_address, password, remember=True)
        # Signify invalid login attempt
        except (auth.InvalidAuthIdError, auth.InvalidPasswordError) as e:
            utils.log('Login failed for user: {0} with exception: {1}'.format(email_address, e))
            result = { 'success': False }
            return result
        # Otherwise it succeeded
        result = { 
            'success': True,
            'user': user
        }
        return result

