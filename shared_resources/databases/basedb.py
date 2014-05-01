

class BaseDBAgent(object):
    '''
    Defines the API that a DB agent must support before it can
    be added into CloudRunner.
    '''
    def get(self, params):
        raise NotImplementedError
    
    def create(self, params):
        '''
        This method should return the ID that can be used to access the
        DB entry that gets created.
        '''
        raise NotImplementedError
    
    def put(self, params):
        raise NotImplementedError
    
    def delete(self, params):
        raise NotImplementedError

