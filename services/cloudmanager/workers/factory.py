import os, sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../'))
from constants import CRConstants

from ec2_worker import EC2Worker
# from euca_agent import EucalyptusAgent

__author__ = 'hiranya, chris'
__email__ = 'hiranya@appscale.com, chris@horukmail.com'

class CloudWorkerFactory(object):
    """
    Factory implementation which can be used to instantiate concrete infrastructure
    agents.
    """

    workers = {
        CRConstants.INFRA_AWS: EC2Worker,
        # CRConstants.INFRA_EUCA: EucalyptusWorker
    }

    def create_agent(self, infrastructure):
        """
        Instantiate a new infrastructure worker.

        Args:
        infrastructure  A string indicating the type of infrastructure
        worker to be initialized.

        Returns:
        An infrastructure worker instance that implements the BaseWorker API

        Raises:
        NameError       If the given input string does not map to any known
        worker type.
        """
        if infrastructure in self.workers:
            return self.workers[infrastructure]()
        else:
            raise NameError('Unrecognized infrastructure: ' + infrastructure)
