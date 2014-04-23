from __future__ import absolute_import

import os

from kombu import Queue

BROKER_URL = 'memory://'

#: warn if config module not found
os.environ['C_WNOCONF'] = 'yes'

#: Don't want log output when running suite.
CELERYD_HIJACK_ROOT_LOGGER = False

CELERY_RESULT_BACKEND = 'cache'
CELERY_CACHE_BACKEND = 'memory'
CELERY_RESULT_DBURI = 'sqlite:///test.db'
CELERY_SEND_TASK_ERROR_EMAILS = False

CELERY_DEFAULT_QUEUE = 'testcelery'
CELERY_DEFAULT_EXCHANGE = 'testcelery'
CELERY_DEFAULT_ROUTING_KEY = 'testcelery'
CELERY_QUEUES = (
    Queue('testcelery', routing_key='testcelery'),
)

CELERY_ENABLE_UTC = True
CELERY_TIMEZONE = 'UTC'

CELERYD_LOG_COLOR = False

# Mongo results tests (only executed if installed and running)
CELERY_MONGODB_BACKEND_SETTINGS = {
    'host': os.environ.get('MONGO_HOST') or 'localhost',
    'port': os.environ.get('MONGO_PORT') or 27017,
    'database': os.environ.get('MONGO_DB') or 'celery_unittests',
    'taskmeta_collection': (os.environ.get('MONGO_TASKMETA_COLLECTION')
                            or 'taskmeta_collection'),
}
if os.environ.get('MONGO_USER'):
    CELERY_MONGODB_BACKEND_SETTINGS['user'] = os.environ.get('MONGO_USER')
if os.environ.get('MONGO_PASSWORD'):
    CELERY_MONGODB_BACKEND_SETTINGS['password'] = \
        os.environ.get('MONGO_PASSWORD')
