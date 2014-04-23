import os
import yaml
from constants import CRConstants

class CRConfigFile(object):
    '''
    '''
    CONFIG_FILE_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "cr-config.yaml"
    )
    
    @classmethod
    def available_infrastructures(cls):
        all_infra = []
        with open(cls.CONFIG_FILE_PATH, 'r') as config_file:
            yaml_config = yaml.load(config_file)
            all_programs = yaml_config[CRConstants.KEY_AVAIL_PROG]
            for program in all_programs:
                for infra in yaml_config[program][CRConstants.KEY_AVAIL_INFRA]:
                    if infra not in all_infra:
                        all_infra.append(infra)
        return all_infra
    
    @classmethod
    def available_programs(cls):
        '''
        '''
        with open(cls.CONFIG_FILE_PATH, 'r') as config_file:
            config = yaml.load(config_file)
            try:
                return config[CRConstants.KEY_AVAIL_PROG]
            except KeyError:
                return []
    
    @classmethod
    def available_infrastructures_for_program(cls, program):
        '''
        '''
        with open(cls.CONFIG_FILE_PATH, 'r') as config_file:
            config = yaml.load(config_file)
            try:
                return config[program][CRConstants.KEY_AVAIL_INFRA]
            except KeyError:
                return []
    
    @classmethod
    def absolute_path_to_program_dir(cls, program, infra):
        '''
        '''
        with open(cls.CONFIG_FILE_PATH, 'r') as config_file:
            config = yaml.load(config_file)
            return "{0}/{1}".format(
                config[CRConstants.KEY_SUPP_INFRA][infra][CRConstants.KEY_PROG_PATH],
                config[program][infra]
            )
    
    @classmethod
    def get_image_id(cls, infrastructure):
        with open(cls.CONFIG_FILE_PATH, 'r') as config_file:
            yaml_config = yaml.load(config_file)
            return yaml_config[CRConstants.KEY_SUPP_INFRA][infrastructure][CRConstants.KEY_IMAGE_ID]
    
    @classmethod
    def get_default_region_for_infrastructure(cls, infrastructure):
        with open(cls.CONFIG_FILE_PATH, 'r') as config_file:
            yaml_config = yaml.load(config_file)
            return yaml_config[CRConstants.KEY_SUPP_INFRA][infrastructure][CRConstants.KEY_REGION]