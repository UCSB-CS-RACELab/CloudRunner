import os, sys
import webapp2, logging
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../'))
from services.login.models import User
from handlers.base import BaseHandler

class MainPage(BaseHandler):
    '''
    Displays a welcome message.
    '''
    def authentication_required(self):
        return True
    
    def get(self):
        self.render_response("mainpage.html")

from handlers.auth import LoginPage, UserRegistrationPage, LogoutHandler, AccountSettingsPage
from handlers.admin import SecretTokenHandler, AdminPage
from handlers.credentials import CredentialsPage
from handlers.execution import ExecutionHandler
from handlers.status import StatusPage, JobStatusPage

config = {
    'webapp2_extras.sessions': { 'secret_key': 'my-super-secret-key' },
    'webapp2_extras.auth': { 'user_model': User }
}

app = webapp2.WSGIApplication(
    [
        ('/', MainPage),
        ('/login', LoginPage),
        ('/logout', LogoutHandler),
        ('/register', UserRegistrationPage),
        ('/admin', AdminPage),
        ('/secret_key', SecretTokenHandler),
        ('/account_settings', AccountSettingsPage),
        ('/credentials', CredentialsPage),
        ('/simulate', ExecutionHandler),
        ('/status', StatusPage),
        ('/status/[a-zA-Z0-9-_]+', JobStatusPage),
    ],
    config=config,
    # debug=True
)