import os, sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../'))
from constants import CRConstants

from s3 import S3Agent

class FileSystemFactory(object):
    '''
    Factory implementation which can be used to instantiate concrete file
    storage system agents.
    '''

    file_systems = {
        CRConstants.INFRA_AWS: S3Agent,
    }

    def create_agent(self, infrastructure):
        """
        Instantiate a new file storage system agent.

        @param infrastructure:
        A string indicating the type of infrastructure where the file
         storage system agent is needed.

        @returns:
        A file storage system agent instance that implements the
        BaseFSAgent API.

        @raises NameError:
        If the given input string does not map to any known
         agent type.
        """
        if infrastructure in self.file_systems:
            return self.file_systems[infrastructure]()
        else:
            raise NameError('Unrecognized infrastructure: ' + infrastructure)
