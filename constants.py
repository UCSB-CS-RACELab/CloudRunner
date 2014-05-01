class CRConstants(object):
    '''
    Central container for all global CloudRunner constants.
    '''
    # Infrastructures
    INFRA_LOCAL = "local"
    INFRA_AWS = "aws"
    INFRA_EUCA = "euca"
    
    # Service parameter key names
    PARAM_INFRA = "infrastructure"
    PARAM_REGION = "region"
    PARAM_CREDENTIALS = "credentials"
    PARAM_CREDS_PUBLIC = "access_key"
    PARAM_CREDS_PRIVATE = "secret_key"
    PARAM_KEY_NAME = "keyname"
    PARAM_KEY_PREFIX = "prefix"
    PARAM_GROUP = "group"
    PARAM_INSTANCE_IDS = "instance_ids"
    PARAM_INSTANCE_ID = "instance_id"
    PARAM_NUM_VMS = "count"
    PARAM_BLOCKING = "blocking"
    PARAM_IMAGE_ID = "image_id"
    PARAM_IMAGE_NAME = "image_name"
    PARAM_INSTANCE_TYPE = "instance_type"
    PARAM_SPOT = "use_spot_instances"
    PARAM_SPOT_PRICE = "max_spot_price"
    PARAM_JOB_NAME = "name"
    PARAM_JOB_TYPE = "job_type"
    # PARAM_EXECUTABLE = "executable"
    PARAM_JOB_PARAMS = "parameters"
    # PARAM_YAML_DIR = "yaml_dir_path"
    PARAM_PROG_DIR_PATH = "program_dir_path"
    PARAM_JOB_PIDS = "pids"
    PARAM_DB_ID = "db_id"
    PARAM_DB_IDS = "db_ids"
    PARAM_DB_ENTRY = "db_entry_data"
    PARAM_DB_ENTRIES = "db_entries"
    PARAM_BUCKET_NAME = "bucket_name"
    PARAM_FILE_PATH = "local_file_path"
    PARAM_FILE_URL = "remote_file_url"
    PARAM_OUTPUT_PATH = "desired_output_path"
    
    # Possible job states for all jobs
    JOB_STATE_RUNNING = "running"
    JOB_STATE_PENDING = "pending"
    JOB_STATE_FAILED = "failed"
    JOB_STATE_FINISHED = "finished"
    
    # YAML file key names for config file
    KEY_AVAIL_PROG = "available_programs"
    KEY_AVAIL_INFRA = "available_infrastructures"
    KEY_SUPP_INFRA = "supported_infrastructures"
    KEY_PROG_PATH = "programs_path"
    KEY_SSH_USER = "ssh_username"
    KEY_IMAGE_ID = "image_id"
    KEY_REGION = "default_region"
    KEY_PROG_YAML_PATH = "programs_yaml_path"
    # YAML file key names for program dependency file
    KEY_PARAM_PREFIX = "parameter_prefix"
    KEY_PARAM_SUFFIX = "parameter_suffix"
    KEY_REQ_VALUE = "required_value_parameters"
    KEY_OPT_VALUE = "optional_value_parameters"
    KEY_REQ_FILE = "required_file_parameters"
    KEY_OPT_FILE = "optional_file_parameters"
    KEY_OPT_BOOL = "optional_boolean_parameters"
    KEY_FILE_NAME = "name"
    KEY_FILE_EXTENSION = "extension"
    KEY_EXECUTABLE = "executable"
    KEY_EXEC_NAME = "name"
    KEY_EXEC_LOCATION = "location"
    # REQUIRED_PROGRAM_YAML_KEYS is a dictionary specifying the required keys for
    # program dependency YAML files. The key in the dictionary represents a top-level
    # YAML key that is required. The value for each entry in the dictionary is a list
    # of all required YAML keys within the entry for that top-level YAML key.
    REQUIRED_PROGRAM_YAML_KEYS = {
        KEY_EXECUTABLE: [KEY_EXEC_NAME, KEY_EXEC_LOCATION],
        KEY_PARAM_PREFIX: [],
        KEY_PARAM_SUFFIX: [],
        KEY_REQ_VALUE: [],
        KEY_REQ_FILE: [KEY_FILE_NAME, KEY_FILE_EXTENSION]
    }
