import os
import webapp2, jinja2
from webapp2_extras import auth, sessions, sessions_memcache
from services.login.models import User
from utils import utils

class BaseHandler(webapp2.RequestHandler):
    """
    The base handler that extends the dispatch() method to start the session store and save all sessions at the end of a request:
    It also has helper methods for storing and retrieving objects from session and for rendering the response to the clients.
    All the request handlers should extend this class.
    """
    OUTPUT_DIR_LOCATION = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "../../output"
    )
    
    def __init__(self, request, response):
        # Initialize the jinja environment
        self.jinja_environment = jinja2.Environment(
            autoescape=True,
            loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../views'))
        )
        # Initialize logger
        utils.initialize_logger()
        self.auth = auth.get_auth()
        # If not logged in, the dispatch() call will redirect to /login if needed
        if self.logged_in():
            # Make sure a handler has a reference to the current user
            user_dict = self.auth.get_user_by_session()
            self.user = self.auth.store.user_model.get_by_id(user_dict['user_id'])
        #
        webapp2.RequestHandler.__init__(self, request, response)
        
    def dispatch(self):
        # Authentication check
        if self.authentication_required() and not self.logged_in():
            return self.redirect('/login')
        # Get a session store for this request.
        self.session_store = sessions.get_store(request=self.request)
        # Using memcache for storing sessions.
        self.session = self.session_store.get_session(name='mc_session', factory=sessions_memcache.MemcacheSessionFactory)
        try:
            # Dispatch the request.
            webapp2.RequestHandler.dispatch(self)
        finally:
            # Save all sessions.
            self.session_store.save_sessions(self.response)
    
    def authentication_required(self):
        print type(self).__name__
        raise Exception("Subclass must implement me!")
        
    def logged_in(self):
        return self.auth.get_user_by_session() is not None
			
    def get_session_property(self, key):
        """ Get the value for the given session property. """
        try:
            return self.session[key]            
        except KeyError:
            return None
    
    def set_session_property(self, key, value):
        """ Set the value for the given session property. """
        self.session[key] = value
            
    def render_response(self, _template, **context):
        """ Process the template and render response. """
        if self.logged_in():
            ctx = {'user': self.user}
        else:
            ctx = {}
        ctx.update(context)
        #
        template = self.jinja_environment.get_template(_template)
        self.response.out.write(template.render({'active_upload': True}, **ctx))