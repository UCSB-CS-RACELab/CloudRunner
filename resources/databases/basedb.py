

class BaseDBAgent(object):
    '''
    Defines the API that a DB agent must support before it can
    be added into CloudRunner.
    '''
    def get(self, params):
        raise NotImplementedError
    
    def put(self, params):
        raise NotImplementedError

