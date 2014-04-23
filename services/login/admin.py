from google.appengine.ext import ndb
from google.appengine.ext import db

from models import User

class SecretToken(db.Model):
    '''
    '''
    key_string = db.StringProperty()
    
    @classmethod
    def destroy_all(cls):
        ''' Deletes the secret token(s) currently stored in the DB. '''
        all_keys = cls.all()
        if all_keys is not None:
            for key in all_keys:
                db.delete(key)
    
    @classmethod
    def is_admin_token(cls, token_string):
        '''
        Checks whether the token represented by token_string is the valid admin token.
        @param token_string: A string representing the admin token.
        @returns: True if token_string is the valid admin token, False otherwise.
        '''
        if token_string is None:
            return False
        else:
            if cls(key_string=token_string).__is_equal_to_admin_token():
                return True
            else:
                return False
    
    @classmethod
    def create(cls, token_string):
        '''
        Deletes all secret tokens currently in the database before creating and
         returning a new SecretToken.
        '''
        cls.destroy_all()
        cls(key_string=token_string).put()
    
    def __is_equal_to(self, other_key):
        '''
        '''
        return self.key_string == other_key.key_string
    
    def __is_equal_to_admin_token(self):
        '''
        '''
        admin_token = db.GqlQuery("SELECT * FROM SecretToken").get()
        if admin_token is None:
            return False
        else:
            return self.__is_equal_to(admin_token)

class PendingUsersList(db.Model):
    """
    A model to store the list of pending users.
    This includes users who haven't been given access yet,
     as well as users who have been given access and haven't yet logged in.
    Once a user logs in, a User model is created for them in the datastore
     and they are removed from this list.
    """
    users_waiting_approval = db.StringListProperty()
    approved_users = db.StringListProperty()
    
    @classmethod
    def shared_list(cls):
        """
        The idea is that only one of these lists exist in the datastore.
        This method encapsulates that logic and retrieves that list.
        """
        shared_list = db.GqlQuery("SELECT * FROM " + cls.__name__).get()
        if shared_list is None:
            shared_list = cls()
            shared_list.put()
        return shared_list
    
    def is_user_approved(self, user_email):
        """ Check if the given email address belongs to an approved user """
        if self.approved_users and (user_email in self.approved_users):
            return True
        return False
    
    def add_user_to_approval_waitlist(self, user_email):
        """
        Add the given email address to the list of users waiting approval
         as long as the given user_email is not a current user's email.
        Returns False if email address already in list, else True.
        """
        if (self.users_waiting_approval and (user_email in self.users_waiting_approval)) or User.get_by_auth_id(user_email):
            return False
        self.users_waiting_approval.append(user_email)
        self.put()
        return True
    
    def remove_user_from_approval_waitlist(self, user_email):
        '''
        Removes the given email address from the approval waitlist.
        This function is currently only called when the email exists in the waitlist so 
         theres no checking to do.
        '''
        self.users_waiting_approval.remove(user_email)
        self.put()
        
    def approve_user(self, user_email, awaiting_approval):
        """
        Add given email address to list of approved users and 
         remove it from waiting approval list if needed.
        Returns False if email address already in list, else True
        """
        if self.approved_users and (user_email in self.approved_users):
            return False
        if awaiting_approval:
            self.users_waiting_approval.remove(user_email)
        self.approved_users.append(user_email)
        self.put()
        return True
    
    def remove_user_from_approved_list(self, user_email):
        self.approved_users.remove(user_email)
        self.put()
