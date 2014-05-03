from time import sleep, strftime
import os, sys, uuid, string
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../lib/boto'))
from boto.exception import S3CreateError
from boto.s3.connection import S3Connection
from boto.s3.key import Key
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../'))
from utils import utils
from constants import CRConstants
from basefs import BaseFSAgent

class S3Agent(BaseFSAgent):
    '''
    '''
    BUCKET_PREFIX = "cloudrunner-"
    
    PARAM_CREDENTIALS = CRConstants.PARAM_CREDENTIALS
    PARAM_CREDS_PUBLIC = CRConstants.PARAM_CREDS_PUBLIC
    PARAM_CREDS_PRIVATE = CRConstants.PARAM_CREDS_PRIVATE
    PARAM_BUCKET_NAME = CRConstants.PARAM_BUCKET_NAME
    PARAM_FILE_PATH = CRConstants.PARAM_FILE_PATH
    PARAM_FILE_URL = CRConstants.PARAM_FILE_URL
    PARAM_OUTPUT_PATH = CRConstants.PARAM_OUTPUT_PATH
    
    READ_REQUIRED_PARAMS = [
        PARAM_CREDENTIALS,
        PARAM_FILE_URL,
        PARAM_OUTPUT_PATH
    ]
    
    WRITE_REQUIRED_PARAMS = [
        PARAM_CREDENTIALS,
        PARAM_FILE_PATH
    ]
    
    def read(self, params):
        # URLs will be of the form:
        #  https://bucket-name.s3.amazonaws.com/ssa-job.tar
        #  0     1 2                           3
        file_url = params[self.PARAM_FILE_URL]
        # We want to extract the bucket and key names
        url_segments = file_url.split('/')
        bucket_segments = url_segments[2].split('.')
        bucket_name = bucket_segments[0]
        for segment in bucket_segments[1:]:
            if segment == "s3":
                break
            bucket_name += '.{0}'.format(segment)
        key_name = '/'.join(url_segments[3:])
        conn = self.__open_connection(params[self.PARAM_CREDENTIALS])
        # Dont want to create the bucket if it doesn't exist
        bucket = self.__get_bucket(conn, bucket_name, create=False)
        if not bucket:
            return { 
                "success": False,
                "reason": "No bucket with the name {0} exists.".format(bucket_name)
            }
        
        key = bucket.get_key(key_name)
        if key:
            output_file_path = params[self.PARAM_OUTPUT_PATH]
            # If the user specified a directory, then we will just use the
            # key name as the file name inside of that directory.
            if os.path.isdir(output_file_path):
                output_file_path = os.path.join(output_file_path, key_name)
            key.get_contents_to_filename(output_file_path)
            return {
                "success": True,
                "output_file_path": output_file_path
            }
        else:
            return {
                "success": False,
                "reason": "No file exists with the key {0}.".format(key_name)
            }
    
    def write(self, params):
        file_path = params[self.PARAM_FILE_PATH]
        conn = self.__open_connection(params[self.PARAM_CREDENTIALS])
        # Now we need a bucket to place this file in
        if self.PARAM_BUCKET_NAME in params:
            bucket_name = params[self.PARAM_BUCKET_NAME]
            if not bucket_name.startswith(self.BUCKET_PREFIX):
                bucket_name = self.BUCKET_PREFIX+bucket_name
        else:
            bucket_name = self.BUCKET_PREFIX+strftime("%B-%Y")
        bucket_name = self.__sanitize_bucket_name(bucket_name)
        bucket = self.__get_bucket(conn, bucket_name)
        if not bucket:
            bucket = self.__get_bucket(
                conn,
                "{0}-{1}".format(bucket_name, uuid.uuid4())
            )
        result = {
            "bucket_name": bucket.name
        }
        k = Key(bucket)
        # We dont need the full directory structure, just the single file
        k.key = file_path.split('/')[-1]
        k.set_contents_from_filename(file_path)
        k.set_acl('public-read')
        result["output_url"] = k.generate_url(expires_in=0, query_auth=False)
        return result
    
    def delete(self, params):
        #TODO
        raise NotImplementedError
    
    def __sanitize_bucket_name(self, bucket_name):
        # Can't have capital letters in bucket names
        bucket_name = bucket_name.lower()
        temp = ""
        # Make sure its only letters, digits, hyphens, and periods
        acceptable_chars = string.letters + string.digits + '-.'
        for char in bucket_name:
            if char in acceptable_chars:
                temp += char
        return temp
    
    def __get_bucket(self, conn, bucket_name, create=True):
        # Does it exist?
        if conn.lookup(bucket_name):
            return conn.get_bucket(bucket_name)
        # If not, lets create it unless otherwise specified.
        elif create:
            # Bucket name might already be taken...
            try:
                return conn.create_bucket(bucket_name)
            except S3CreateError as e:
                #...if so then just return None
                return None
        else:
            return None
    
    def __open_connection(self, credentials):
        return S3Connection(
            credentials[self.PARAM_CREDS_PUBLIC],
            credentials[self.PARAM_CREDS_PRIVATE]
        )

