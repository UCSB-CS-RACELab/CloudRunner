from google.appengine.ext import ndb
from google.appengine.ext import db

from webapp2_extras.auth import InvalidAuthIdError, InvalidPasswordError
from webapp2_extras import security

from cloudrunnerapp import BaseHandler
from models import User

from admin import PendingUsersList, SecretToken

class GateKeeper(object):
    '''
    Implements the interface for login attempts.
    '''
    # def 