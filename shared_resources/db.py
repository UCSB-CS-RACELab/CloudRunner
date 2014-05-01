import os, sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../'))
from constants import CRConstants

from databases.factory import DatabaseAgentFactory

class CloudDB(object):
    '''
    '''
    PARAM_INFRA = CRConstants.PARAM_INFRA
    PARAM_CREDENTIALS = CRConstants.PARAM_CREDENTIALS
    PARAM_DB_ENTRY = CRConstants.PARAM_DB_ENTRY
    PARAM_DB_ENTRIES = CRConstants.PARAM_DB_ENTRIES
    PARAM_DB_IDS = CRConstants.PARAM_DB_IDS
    
    GET_REQ_PARAMS = [
        PARAM_INFRA,
        PARAM_CREDENTIALS,
        PARAM_DB_IDS
    ]
    
    CREATE_REQ_PARAMS = [
        PARAM_INFRA,
        PARAM_CREDENTIALS,
        PARAM_DB_ENTRY
    ]
    
    PUT_REQ_PARAMS = [
        PARAM_INFRA,
        PARAM_CREDENTIALS,
        PARAM_DB_ENTRIES
    ]
    
    DELETE_REQ_PARAMS = [
        PARAM_INFRA,
        PARAM_CREDENTIALS,
        PARAM_DB_IDS
    ]
    
    @classmethod
    def get(cls, params):
        '''
        '''
        infrastructure = params[cls.PARAM_INFRA]
        db_agent = cls.__get_agent(infrastructure)
        result = db_agent.get(params)
        return result
    
    @classmethod
    def create(cls, params):
        '''
        '''
        infrastructure = params[cls.PARAM_INFRA]
        db_agent = cls.__get_agent(infrastructure)
        db_id = db_agent.create(params)
        return db_id
    
    @classmethod
    def put(cls, params):
        '''
        '''
        infrastructure = params[cls.PARAM_INFRA]
        db_agent = cls.__get_agent(infrastructure)
        success = db_agent.put(params)
        return success
    
    @classmethod
    def delete(cls, params):
        '''
        '''
        infrastructure = params[cls.PARAM_INFRA]
        db_agent = cls.__get_agent(infrastructure)
        # result = db_agent.delete(params[cls.PARAM_DB_ENTRY])
    
    @classmethod
    def __get_agent(cls, infrastructure):
        return DatabaseAgentFactory().create_agent(infrastructure)

