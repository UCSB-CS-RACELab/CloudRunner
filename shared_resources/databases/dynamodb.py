import os, sys, traceback
import uuid
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../lib/boto'))
import boto.dynamodb
from boto.dynamodb.batch import BatchList, BatchWriteList
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
        for item_dict in batch_results['Responses'][table.name]['Items']:
            result[item_dict["taskid"]] = item_dict
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
        conn = self.__open_connection(params)
        result = {}
        if not self.__table_exists(conn):
            # Can't delete an item in a non-existent table
            result["success"] = False
            result["reason"] = "No DynamoDB table exists with the name: '{0}'.".format(self.TABLE_NAME)
        else:
            result["success"] = True
            db_ids = params[self.PARAM_DB_IDS]
            # We can only try to delete 25 entries at a time
            id_chunks = utils.chunks(db_ids, 25)
            # Each individual delete is atomic, but batch delete as a whole isn't
            # so we might need to retry deleting certain items in the batch.
            max_batch_retries = 5
            for id_chunk in id_chunks:
                utils.log("Batch deleting items with ids: {0}".format(id_chunk))
                # Batch delete the entries
                the_batch = conn.new_batch_write_list()
                the_batch.add_batch(
                    self.__get_table(conn),
                    deletes=id_chunk
                )
                response = conn.batch_write_item(the_batch)
                utils.log(response)
                unprocessed = response.get('UnprocessedItems', None)
                batch_retries = 0
                # Retry as many items as we can
                while unprocessed and batch_retries < max_batch_retries:
                    utils.log("Retrying UnprocessedItems: {0}".format(unprocessed))
                    response = conn.layer1.batch_write_item(unprocessed)
                    unprocessed = response.get('UnprocessedItems', None)
                    batch_retries += 1
                # If theres still some unprocessed, we just need to mark them
                # unsuccessful.
                if unprocessed:
                    utils.log("Couldn't delete UnprocessedItems: {0}".format(unprocessed))
                    for delete_request in unprocessed[self.TABLE_NAME]:
                        result[delete_request["Key"]["taskid"]] = False
                # Make sure the successful ones are marked as such
                for db_id in id_chunk:
                    if db_id in result:
                        continue
                    result[db_id] = True
        return result
    
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

