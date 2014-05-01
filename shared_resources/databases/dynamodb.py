import os, sys, traceback
import uuid
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../lib/boto'))
import boto.dynamodb
from boto.dynamodb.batch import BatchList
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../'))
from utils import utils
from constants import CRConstants
from basedb import BaseDBAgent

class DynamoDBAgent(BaseDBAgent):
    '''
    '''
    TABLE_NAME = "CloudRunner"
    
    PARAM_REGION = CRConstants.PARAM_REGION
    PARAM_CREDENTIALS = CRConstants.PARAM_CREDENTIALS
    PARAM_CREDS_PUBLIC = CRConstants.PARAM_CREDS_PUBLIC
    PARAM_CREDS_PRIVATE = CRConstants.PARAM_CREDS_PRIVATE
    PARAM_DB_ENTRY = CRConstants.PARAM_DB_ENTRY
    PARAM_DB_ENTRIES = CRConstants.PARAM_DB_ENTRIES
    PARAM_DB_IDS = CRConstants.PARAM_DB_IDS
    
    def get(self, params):
        conn = self.__open_connection(params)
        if not self.__table_exists(conn):
            # Can't get an item in a non-existent table
            result = {
                'success': False
            }
            return result
        
        result = {
            'success': True
        }
        table = self.__get_table(conn)
        db_IDs = params[self.PARAM_DB_IDS]
        print "*********************"
        print db_IDs
        print "*********************"
        # Batch get the entries
        the_batch = BatchList(conn)
        the_batch.add_batch(table, keys=db_IDs)
        batch_results = conn.batch_get_item(the_batch)
        print batch_results
        for item_dict in batch_results['Responses'][table.name]['Items']:
            result[item_dict["taskid"]] = item_dict
        # for db_id in db_IDs:
        #     item = table.get_item(
        #         hash_key=db_id
        #     )
        #     result[db_id] = item
        return result
    
    def create(self, params):
        conn = self.__open_connection(params)
        table = \
            self.__create_table(conn) if not self.__table_exists(conn) \
            else self.__get_table(conn)
        taskid = str(uuid.uuid4())
        item = table.new_item(
            hash_key=taskid,
            attrs=params[self.PARAM_DB_ENTRY]
        )
        item.put()
        return taskid
    
    def put(self, params):
        conn = self.__open_connection(params)
        if not self.__table_exists(conn):
            # Can't update an item in a non-existent table
            return False
        else:
            table = self.__get_table(conn)
            db_entries = params[self.PARAM_DB_ENTRIES]
            for db_id, updated_attrs in db_entries.items():
                item = table.get_item(
                    hash_key=db_id
                )
                item.update(updated_attrs)
                item.put()
        return True
    
    def delete(self, params):
        pass
    
    def __table_exists(self, conn, table_name=TABLE_NAME):
        try:
            table = conn.get_table(table_name)
            return table != None
        except Exception as e:
            utils.log("Checking for DynamoDB table raised exception: {0}, with traceback: {1}".format(
                e,
                traceback.format_exc()
            ))
            return False
    
    def __create_table(self, conn, table_name=TABLE_NAME):
        table_schema = conn.create_schema(
            hash_key_name='taskid',
            hash_key_proto_value=str
        )
        table = conn.create_table(
            name=table_name,
            schema=table_schema,
            read_units=6,
            write_units=4
        )
        return table
    
    def __get_table(self, conn, table_name=TABLE_NAME):
        return conn.get_table(table_name)
    
    def __open_connection(self, params):
        credentials = params[self.PARAM_CREDENTIALS]
        region = params[self.PARAM_REGION]
        return boto.dynamodb.connect_to_region(
            region,
            aws_access_key_id=str(credentials[self.PARAM_CREDS_PUBLIC]),
            aws_secret_access_key=str(credentials[self.PARAM_CREDS_PRIVATE])
        )

