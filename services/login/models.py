import yaml
from google.appengine.ext import ndb
from webapp2_extras import security
from webapp2_extras.appengine.auth.models import User as WebApp2User

class User(WebApp2User):
    """
    Subclass of the WebApp2 User class to add functionality.
    The WebApp2User class is an expando model, so the User
     class inherits that functionality.
    (see https://developers.google.com/appengine/docs/python/datastore/expandoclass)
    """
    @classmethod
    def admin_exists(cls):
        '''
        Returns True if an admin user already exists in the DB, else False.
        '''
        admin = User.query().filter(ndb.GenericProperty('is_admin')=='YES').get()
        return admin is not None
    
    def user_id(self):
        return self.email_address
    
    def change_auth_id(self, auth_id):
       '''
       A helper method to change a user's auth id.

       :param auth_id:
           String representing a unique id for the user (i.e. email address).
       :returns
           A boolean that indicates if the auth_id is unique.
       '''
       unique = '{0}.auth_id:{1}'.format(self.__class__.__name__, auth_id)
       ok = self.unique_model.create(unique)
       if ok:
           # Need to delete the old auth_id from the 'unique' model store
           # see https://code.google.com/p/webapp-improved/source/browse/webapp2_extras/appengine/auth/models.py
           unique_auth_id = "{0}.auth_id:{1}".format(self.__class__.__name__, self.auth_ids[0])
           User.unique_model.delete_multi([unique_auth_id])
           self.auth_ids = [auth_id]
           return True
       else:
           return False
    
    def set_password(self, raw_password):
        '''
        Sets password for current user, stored as a hashed value.
        '''
        self.password = security.generate_password_hash(raw_password, length=12)
    
    def is_admin_user(self):
        '''
        Determine if this user is an admin by checking for the is_admin property
        - this is an expando model and is_admin property is added dynamically only for admins
        '''
        if "is_admin" in self._properties and self.is_admin == 'YES':
            return True
        return False
    
    def get_credentials(self, infrastructure):
        '''
        '''
        credentials = {}
        if "credentials" not in self._properties:
            credentials = {
                'access_key': None,
                'secret_key': None
            }
        else:
            infrastructure = infrastructure.lower()
            creds_yaml = yaml.load(self.credentials)
            try:
                credentials = creds_yaml[infrastructure]
            except KeyError, e:
                credentials = {
                    'access_key': None,
                    'secret_key': None
                }
        return credentials
    
    def set_credentials(self, infrastructure, credentials):
        '''
        '''
        infrastructure = infrastructure.lower()
        if "credentials" not in self._properties:
            self.credentials = "{}"
        creds_yaml = yaml.load(self.credentials)
        creds_yaml[infrastructure] = {
            'access_key': credentials['access_key'],
            'secret_key': credentials['secret_key']
        }
        self.credentials = yaml.dump(creds_yaml)

