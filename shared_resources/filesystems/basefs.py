

class BaseFSAgent(object):
    '''
    Defines the API that a file system agent must support before it can
    be added into CloudRunner.
    '''
    def get(self, params):
        raise NotImplementedError
    
    def put(self, params):
        raise NotImplementedError
    
    def delete(self, params):
        raise NotImplementedError

