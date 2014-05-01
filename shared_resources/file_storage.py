import os, sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../'))
from constants import CRConstants

from filesystems.factory import FileSystemFactory

class CloudFileStorage(object):
    '''
    '''
    PARAM_INFRA = CRConstants.PARAM_INFRA
    PARAM_CREDENTIALS = CRConstants.PARAM_CREDENTIALS
    
    @classmethod
    def read(cls, params):
        '''
        '''
        infrastructure = params[cls.PARAM_INFRA]
        agent = cls.__get_agent(infrastructure)
        return agent.read(params)
    
    @classmethod
    def write(cls, params):
        '''
        '''
        infrastructure = params[cls.PARAM_INFRA]
        agent = cls.__get_agent(infrastructure)
        return agent.write(params)
    
    @classmethod
    def delete(cls, params):
        '''
        '''
        pass
    
    @classmethod
    def __get_agent(cls, infrastructure):
        return FileSystemFactory().create_agent(infrastructure)

