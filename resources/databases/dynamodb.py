import os, sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../lib/boto'))
import boto
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../'))
from constants import CRConstants
from basedb import BaseDBAgent

class DynamoDBAgent(BaseDBAgent):
    '''
    '''
    PARAM_REGION = CRConstants.PARAM_REGION
    PARAM_CREDENTIALS = CRConstants.PARAM_CREDENTIALS
    PARAM_CREDS_PUBLIC = CRConstants.PARAM_CREDS_PUBLIC
    PARAM_CREDS_PRIVATE = CRConstants.PARAM_CREDS_PRIVATE
    
    def get(self, params):
        pass
    
    def create(self, params):
        pass
    
    def put(self, params):
        pass
    
    def delete(self, params):
        pass
    
    def __table_exists(self):
        pass
    
    def __create_table(self):
        pass
    
    def __open_connection(self, params):
        credentials = params[self.PARAM_CREDENTIALS]
        region = params[self.PARAM_REGION]
        return boto.connect_dynamodb(
            str(credentials[self.PARAM_CREDS_PUBLIC]),
            str(credentials[self.PARAM_CREDS_PRIVATE]),
            region=region
        )

