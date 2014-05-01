#!/usr/bin/env python
import os, subprocess, sys
import argparse, shlex, yaml
import fileinput, glob
import time
from datetime import datetime
from constants import CRConstants
from config_file import CRConfigFile
from services.cloudmanager import CloudManager

class CRBuilder(object):
    '''
    '''
    CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cr-config.yaml")
    
    INFRA_LOCAL = CRConstants.INFRA_LOCAL
    INFRA_AWS = CRConstants.INFRA_AWS
    
    KEY_PROG_PATH = CRConstants.KEY_PROG_PATH
    KEY_SUPP_INFRA = CRConstants.KEY_SUPP_INFRA
    KEY_AVAIL_PROG = CRConstants.KEY_AVAIL_PROG
    KEY_AVAIL_INFRA = CRConstants.KEY_AVAIL_INFRA
    KEY_SSH_USER = CRConstants.KEY_SSH_USER
    KEY_IMAGE_ID = CRConstants.KEY_IMAGE_ID
    KEY_PROG_YAML_PATH = CRConstants.KEY_PROG_YAML_PATH
    KEY_EXECUTABLE = CRConstants.KEY_EXECUTABLE
    KEY_EXEC_NAME = CRConstants.KEY_EXEC_NAME
    
    def __init__(self, skip_init=False, infrastructure=None, programs_path=None, programs_yaml_path=None):
        '''
        Initializes the CloudRunner builder by reading variables from the config file.
        '''
        if skip_init and infrastructure and programs_path and programs_yaml_path:
            self.supported_infra = {
                infrastructure: {
                    self.KEY_PROG_PATH: programs_path,
                    self.KEY_PROG_YAML_PATH: programs_yaml_path
                }
            }
            return
        
        if not os.path.exists(self.CONFIG_FILE_PATH):
            print "Missing configuration file. Expected to be found at '{0}'.".format(self.CONFIG_FILE_PATH)
            exit(-1)
        update_config = False
        with open(self.CONFIG_FILE_PATH, "r") as config_file:
            # Save the config file as a dictionary attribute
            self.config = yaml.load(config_file)
            # Save certain key-value pairs directly as attributes
            self.supported_infra = self.config[self.KEY_SUPP_INFRA]
            # Make sure local info is always available
            if self.INFRA_LOCAL not in self.supported_infra:
                self.supported_infra[self.INFRA_LOCAL] = {
                    self.KEY_PROG_PATH: os.path.join(os.path.abspath(
                        os.path.dirname(os.path.abspath(__file__)),
                        "../programs"
                    )),
                    self.KEY_PROG_YAML_PATH: os.path.join(os.path.abspath(
                        os.path.dirname(os.path.abspath(__file__)),
                        "../programs_yaml"
                    ))
                }
                self.config[self.KEY_SUPP_INFRA] = self.supported_infra
                update_config = True
            elif self.KEY_PROG_PATH not in self.supported_infra[self.INFRA_LOCAL]:
                self.supported_infra[self.INFRA_LOCAL][self.KEY_PROG_PATH] = os.path.join(os.path.abspath(
                    os.path.dirname(os.path.abspath(__file__)),
                    "../programs"
                ))
                self.config[self.KEY_SUPP_INFRA] = self.supported_infra
                update_config = True
            elif self.KEY_PROG_YAML_PATH not in self.supported_infra[self.INFRA_LOCAL]:
                self.supported_infra[self.INFRA_LOCAL][self.KEY_PROG_YAML_PATH] = os.path.join(os.path.abspath(
                    os.path.dirname(os.path.abspath(__file__)),
                    "../programs_yaml"
                ))
                self.config[self.KEY_SUPP_INFRA] = self.supported_infra
                update_config = True
            # Make sure all the dirs exist
            local_dirs = [
                self.supported_infra[self.INFRA_LOCAL][self.KEY_PROG_PATH],
                self.supported_infra[self.INFRA_LOCAL][self.KEY_PROG_YAML_PATH]
            ]
            for local_path in local_dirs:
                if not os.path.exists(local_path):
                    os.system("mkdir {0}".format(local_path))
                elif os.path.exists(local_path) and not os.path.isdir(local_path):
                    failure_msg = "Error! File already exists at {0} and it is not a directory.\n".format(local_path)
                    failure_msg += "CloudRunner uses this location to store information about built programs."
                    self.__exit_with_failure(failure_msg)
                # else it exists and is a directory
            # Now check the entries for the other infrastructures
            for infra in self.supported_infra:
                if infra != self.INFRA_LOCAL:
                    if self.KEY_PROG_PATH not in self.supported_infra[infra]:
                        failure_msg = "Error! CloudRunner config file ({0}) is missing the entry for the"
                        " programs location of the '{1}' infrastructure".format(
                            self.CONFIG_FILE_PATH,
                            infra
                        )
                        self.__exit_with_failure(failure_msg)
                    elif self.KEY_PROG_YAML_PATH not in self.supported_infra[infra]:
                        failure_msg = "Error! CloudRunner config file ({0}) is missing the entry for the"
                        " programs YAML location of the '{1}' infrastructure".format(
                            self.CONFIG_FILE_PATH,
                            infra
                        )
                        self.__exit_with_failure(failure_msg)
        # Update config file if necessary
        if update_config:
            self.__update_YAML_config()
    
    def build(self):
        '''
        '''
        # Before grabbing YAML config, initialize any services
        deploying_cloud = True#len(self.infra) > 1
        if deploying_cloud:
            self.cloud_manager = CloudManager()
        #
        for index, infrastructure in enumerate(self.infra):
            if infrastructure == self.INFRA_LOCAL:
                print "Building input program(s) locally..."
                for git_URL in self.git_clone_URLs:
                    build_result = self.__run_build_process(
                        git_URL,
                        infrastructure,
                        verbose=True
                    )
                    # Need to update config file with the location of each executable
                    program_dir_path = build_result['program_dir_path']
                    program_dir_name = program_dir_path.split('/')[-1]
                    print "Updating CR configuration files..."
                    for program_yaml in build_result["programs"]:
                        program_system_name, program_relative_location = self.__update_config_for_successful_executable(
                            program_yaml,
                            program_dir_name,
                            infrastructure,
                            # Only update UI if requested
                            update_UI=self.generate_UI
                        )
                        # Update name of YAML file now
                        os.system("cp {0}/{1} {2}/{3}.yaml".format(
                            program_dir_path,
                            program_yaml["file_name"],
                            self.supported_infra[infrastructure][self.KEY_PROG_YAML_PATH],
                            program_system_name
                        ))
                    # Update the config file
                    self.__update_YAML_config()
                    print "Finished."
            else:# infrastructure == 'aws'
                print "Launching instance for the '{0}' infrastructure...".format(infrastructure)
                
                params = {
                    'infrastructure': infrastructure,
                    'count': 1,
                    'blocking': True,
                    'credentials': self.__get_credentials(infrastructure)
                }
                launch_result = self.cloud_manager.launch_instances(params)
                # time.sleep(5)
                print "Finished."
                
                instance_ip = launch_result["instances"][0]["public_ip"]
                instance_id = launch_result["instances"][0]["id"]
                keypair_path = launch_result["key_pair_path"]
                print "Deploying and building your program(s) on the new instance..."
                # ssh in and build
                ssh_and_build_string = "ssh -o 'StrictHostKeyChecking no' -i {0} {1}@{2}".format(
                    keypair_path,
                    self.supported_infra[infrastructure][self.KEY_SSH_USER],
                    instance_ip
                )
                ssh_and_build_string += " 'cd ~/cloudrunner ; python cr_build.py internal {0} {1} {2}".format(
                    infrastructure,
                    self.supported_infra[infrastructure][self.KEY_PROG_PATH],
                    self.supported_infra[infrastructure][self.KEY_PROG_YAML_PATH]
                )
                for git_URL in self.git_clone_URLs:
                    ssh_and_build_string += " {0}".format(git_URL)
                ssh_and_build_string += "'"
                print ssh_and_build_string
                t1 = datetime.now()
                p = subprocess.Popen(
                    shlex.split(ssh_and_build_string),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                stdout, stderr = p.communicate()
                t2 = datetime.now()
                # Make sure the SSH command didn't just time out, assume this only
                # happens within first SSH_RETRY_TIME seconds
                SSH_RETRY_TIME = 5
                if p.returncode != 0:
                    total_time = (t2-t1).total_seconds()
                    while total_time < SSH_RETRY_TIME:
                        p = subprocess.Popen(
                            shlex.split(ssh_and_build_string),
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                        )
                        stdout, stderr = p.communicate()
                        if p.returncode == 0:
                            break
                        total_time = (datetime.now() - t1).total_seconds()
                print "Finished."
                if p.returncode != 0:
                    # Then at least one program failed, but some might have succeeded
                    should_make_image = self.__handle_cloud_failure(
                        stdout,
                        infrastructure,
                        keypair_path,
                        instance_ip
                    )
                    if should_make_image:
                        print "Creating new worker image for the '{0}' infrastructure...".format(infrastructure)
                        # __make_cloud_image() also terminates the instance
                        self.__make_cloud_image(infrastructure, instance_id)
                    else:
                        print "All programs failed to build for the '{0}' infrastructure. Cleaning up...".format(infrastructure)
                        terminate_params = {
                            self.cloud_manager.PARAM_INFRA: infrastructure,
                            self.cloud_manager.PARAM_CREDENTIALS: self.__get_credentials(infrastructure),
                            self.cloud_manager.PARAM_INSTANCE_IDS: [instance_id],
                            self.cloud_manager.PARAM_BLOCKING: True
                        }
                        #self.cloud_manager.terminate_instances(terminate_params)
                    print "Finished."
                    continue
                # Else it succeeded, now we need to parse stdout to get info we need
                self.__handle_cloud_success(
                    stdout,
                    infrastructure,
                    keypair_path,
                    instance_ip
                )
                print "All of the programs that you submitted for deployment were built successfully."
                print "Creating new worker image for the '{0}' infrastructure...".format(infrastructure)
                # And make a new image / terminate instance
                self.__make_cloud_image(infrastructure, instance_id)
                print "Finished."
    
    def wrapper_for_build_process(self, git_URL, infrastructure):
        return self.__run_build_process(git_URL, infrastructure)
    
    def __update_YAML_config(self):
        with open(self.CONFIG_FILE_PATH, "w") as config_file:
            config_file.write(yaml.dump(self.config))
    
    def __exit_with_failure(self, message):
        print message
        exit(-1)
    
    def __get_credentials(self, infrastructure):
        access_key = self.__getattribute__("{0}_access_key".format(infrastructure))[0]
        secret_key = self.__getattribute__("{0}_secret_key".format(infrastructure))[0]
        return {
            self.cloud_manager.PARAM_CREDS_PUBLIC: access_key,
            self.cloud_manager.PARAM_CREDS_PRIVATE: secret_key
        }
    
    def __get_program_system_name(self, program_dir, program_yaml):
        return "{0}-{1}".format(
            program_dir,
            program_yaml[self.KEY_EXECUTABLE][self.KEY_EXEC_NAME]
        )
    
    def __get_remote_program_yaml(self, keypair_path, infra_username, instance_ip, remote_yaml_path):
        scp_prog_yaml_str = "scp -i {0} {1}@{2}:{3} {4}/".format(
            keypair_path,
            infra_username,
            instance_ip,
            remote_yaml_path,
            self.supported_infra[self.INFRA_LOCAL][self.KEY_PROG_YAML_PATH]
        )
        p = subprocess.Popen(
            shlex.split(scp_prog_yaml_str),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = p.communicate()
    
    def __handle_cloud_success(self, build_stdout, infrastructure, keypair_path, instance_ip):
        # All programs that CloudRunner attempted to build were built successfully
        current_git_URL = None
        program_yaml_string = ''
        for line in build_stdout.split('\n'):
            if line in self.git_clone_URLs:
                current_git_URL = line
            elif current_git_URL:
                if line == 'Succeeded':
                    # There should be one of these for each git_URL
                    print "Successfully built the program at '{0}' for the '{1}' infrastructure.".format(
                        current_git_URL,
                        infrastructure
                    )
                elif line:
                    if line == "Program YAML Start":
                        program_yaml_string = ''
                    elif line == "Program YAML Finish":
                        # This YAML has a few extra keys that we create (see Case 1 in
                        # if __name__ == "__main__")
                        program_yaml = yaml.load(program_yaml_string.rstrip('\n'))
                        relative_program_dir = program_yaml.pop('relative_program_dir')
                        # This will update the config file on the Cloud worker...not entirely
                        # necessary to keep this file up to date, but we do want the program
                        # yaml to be placed in the correct directory (which also happens in
                        # this method).
                        program_system_name, program_relative_location = self.__update_config_for_successful_executable(
                            program_yaml,
                            relative_program_dir,
                            infrastructure,
                            update_UI=self.generate_UI
                        )
                        if self.INFRA_LOCAL not in self.config[program_system_name] or True:
                            # Then we haven't successfully built this locally, but we still need the program
                            # description YAML file since it was built successfully on the cloud
                            remote_yaml_path = "{0}/{1}.yaml".format(
                                self.supported_infra[infrastructure][self.KEY_PROG_YAML_PATH],
                                program_system_name
                            )
                            self.__get_remote_program_yaml(
                                keypair_path,
                                self.supported_infra[infrastructure][self.KEY_SSH_USER],
                                instance_ip,
                                remote_yaml_path
                            )
                    else:
                        program_yaml_string += line+"\n"
    
    def __handle_cloud_failure(self, build_stdout, infrastructure, key_pair_path, instance_ip):
        # At least one program failed to build, some might have succeeded
        should_make_image = False
        current_git_URL = None
        program_success = False
        program_yaml_string = ''
        failure_yaml_string = ''
        for line in build_stdout.split('\n'):
            if line in self.git_clone_URLs:
                current_git_URL = line
                program_success = False
            elif current_git_URL:
                if line == 'Succeeded':
                    should_make_image = True
                    print "Successfully built the program at '{0}' for the '{1}' infrastructure.".format(
                        current_git_URL,
                        infrastructure
                    )
                    program_success = True
                elif line == "Failed":
                    print "Failed to build the program at '{0}' for the '{1}' infrastructure.".format(
                        current_git_URL,
                        infrastructure
                    )
                    program_success = False
                elif program_success: # and line not in self.git_clone_URLs+['Succeeded', 'Failed']
                    if line == "Program YAML Start":
                        program_yaml_string = ''
                    elif line == "Program YAML Finish":
                        # This YAML has a few extra keys that we create (see Case 1 in
                        # if __name__ == "__main__")
                        program_yaml = yaml.load(program_yaml_string.rstrip('\n'))
                        relative_program_dir = program_yaml.pop('relative_program_dir')
                        program_system_name, program_relative_location = self.__update_config_for_successful_executable(
                            program_yaml,
                            relative_program_dir,
                            infrastructure,
                            update_UI=self.generate_UI
                        )
                        if self.INFRA_LOCAL not in self.config[program_system_name] or True:
                            # Then we haven't successfully built this locally, but we still need the program
                            # description YAML file since it was built successfully on the cloud
                            remote_yaml_path = "{0}/{1}.yaml".format(
                                self.supported_infra[infrastructure][self.KEY_PROG_YAML_PATH],
                                program_system_name
                            )
                            self.__get_remote_program_yaml(
                                keypair_path,
                                self.supported_infra[infrastructure][self.KEY_SSH_USER],
                                instance_ip,
                                remote_yaml_path
                            )
                    else:
                        program_yaml_string += line+"\n"
                else: # line not in self.git_clone_URLs+['Succeeded', 'Failed'] and not program_success
                    if line == "Failure YAML Finish":
                        failure_yaml = yaml.load(failure_yaml_string.rstrip("\n"))
                        if 'logs_location' in failure_yaml:
                            # This must be the remote file location of the logs for the failed program
                            remote_logs_location = failure_yaml['logs_location']
                            local_logs_location = os.path.abspath('{0}-{1}-logs'.format(
                                remote_logs_location.split('/')[-1],
                                infrastructure
                            ))
                            os.system("mkdir -p {0}".format(local_logs_location))
                            scp_logs_string = "scp -i {0} {1}@{2}:{3}/*.log {4}/".format(
                                key_pair_path,
                                self.supported_infra[infrastructure][self.KEY_SSH_USER],
                                instance_ip,
                                remote_logs_location,
                                local_logs_location
                            )
                            p = subprocess.Popen(
                                shlex.split(scp_logs_string),
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE
                            )
                            p.communicate()
                            print "Logs for the build process can be found at {0}/.".format(local_logs_location)
                        else:
                            print "Logs for the build process couldn't be obtained.",
                            if 'reason' in failure_yaml:
                                print " Reported reason for failure: '{0}'.".format(failure_yaml['reason'])
                            else:
                                print ""
                    else:
                        failure_yaml_string += line+"\n"
        return should_make_image
    
    def __update_config_for_successful_executable(self, program_yaml, program_dir_name, infrastructure, update_UI=False):
        program_system_name = self.__get_program_system_name(program_dir_name, program_yaml)
        program_relative_location = os.path.join(
            program_dir_name,
            program_yaml['executable']['location']
        )
        if program_system_name not in self.config[self.KEY_AVAIL_PROG]:
            self.config[self.KEY_AVAIL_PROG].append(program_system_name)
            self.config[program_system_name] = {
                self.KEY_AVAIL_INFRA: [infrastructure],
                infrastructure: program_relative_location
            }
        else:
            self.config[program_system_name][self.KEY_AVAIL_INFRA].append(infrastructure)
            self.config[program_system_name][infrastructure] = program_relative_location
        # Update the actual YAML config file
        self.__update_YAML_config()
        # Optionally update UI
        if update_UI:
            # Update of select_job_type view is done when writing to config file
            parameters_template_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "input_job_parameters_template.html"
            )
            self.__update_UI_with_YAML(
                program_yaml,
                parameters_template_path,
                program_system_name
            )
        
        return (program_system_name, program_relative_location)
    
    def __make_cloud_image(self, infrastructure, instance_id):
        credentials = self.__get_credentials(infrastructure)
        params = {
            self.cloud_manager.PARAM_INFRA: infrastructure,
            self.cloud_manager.PARAM_CREDENTIALS: credentials,
            self.cloud_manager.PARAM_INSTANCE_ID: instance_id
        }
        image_creation_result = self.cloud_manager.create_image(params)
        # TODO: Delete the old image?
        self.supported_infra[infrastructure][self.KEY_IMAGE_ID] = image_creation_result["image_id"]
        self.config[self.KEY_SUPP_INFRA] = self.supported_infra
        self.__update_YAML_config()
        
        terminate_params = {
            self.cloud_manager.PARAM_INFRA: infrastructure,
            self.cloud_manager.PARAM_CREDENTIALS: credentials,
            self.cloud_manager.PARAM_INSTANCE_IDS: [instance_id],
            self.cloud_manager.PARAM_BLOCKING: True
        }
        self.cloud_manager.terminate_instances(terminate_params)
    
    def __run_build_process(self, git_URL, infrastructure, verbose=False):
        result = {}
        programs_dir_path = self.supported_infra[infrastructure][self.KEY_PROG_PATH]
        # Extract the name for the program's folder from Git URL
        program_dir_name = git_URL.split('/')[-1].split('.')[0].capitalize()
        if verbose:
            print "Creating a directory in '{0}' for '{1}'...".format(
                programs_dir_path,
                program_dir_name
            )
        program_dir_path = os.path.join(
            programs_dir_path,
            program_dir_name
        )
        # Make sure it doesn't exist until we create it
        #TODO: Might not want to create directory if there was a naming conflict...
        #      Just ask the user to rename the repo...?
        #      A program's system name relies on the name of the dir where it was created,
        #      because the dir is named after the Git repo. Don't want different system
        #      names for a single program across infrastructures.
        new_program_dir_path = program_dir_path
        ctr = 1
        while True:
            try:
                os.mkdir(new_program_dir_path)
            except OSError, e:
                new_program_dir_path = program_dir_path+"-"+str(ctr)
                ctr += 1
                if ctr > 20:
                    failure_reason = "Couldn't create a directory for {0}-x, for x from 1 to {1}.".format(
                        program_dir_path,
                        ctr-1
                    )
                    if verbose:
                        print failure_reason
                    result = {
                        'success': False,
                        'reason': failure_reason
                    }
                    return result
                continue
            program_dir_path = new_program_dir_path
            break
        result["program_dir_path"] = program_dir_path
        program_dir_name = program_dir_path.split('/')[-1]
        
        if verbose:
            print "Finished."
            print "Cloning the program at '{0}' into '{1}'...".format(
                git_URL,
                program_dir_path
            )
        # Clone the repo into the new dir
        git_clone_string = 'git clone {0} {1}'.format(git_URL, program_dir_path)
        p = subprocess.Popen(
            shlex.split(git_clone_string),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        p.communicate()
        if p.returncode != 0:
            failure_reason = "Couldn't clone {0}".format(git_URL)
            if verbose:
                # Failed to clone this repo, report to user
                print failure_reason
            # Clean up temp dir and continue to next URL
            subprocess.Popen(
                shlex.split('rm -rf {0}'.format(program_dir_path)),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            ).communicate()
            result = {
                'success': False,
                'reason': failure_reason
            }
            return result
        
        if verbose:
            print "Finished."
            # Now attempt to build the program
            print "Building '{0}' now...".format(program_dir_name)
        # Change working dir to the programs dir
        cwd = os.getcwd()
        os.chdir(program_dir_path)
        if not self.__build_program():
            os.chdir(cwd)
            result = {
                'success': False,
                'logs_location': program_dir_path
            }
            return result
        result['success'] = True
        if verbose:
            print "Finished."
        # Now get all of the program description YAML files
        all_yaml_files = glob.glob("CR*.yaml")
        prog_yaml_dir_path = self.supported_infra[infrastructure][self.KEY_PROG_YAML_PATH]
        result["programs"] = []
        for yaml_file in all_yaml_files:
            with open(yaml_file, 'r') as yaml_content:
                # First, add the YAML to the result, with some additional info
                program_yaml = yaml.load(yaml_content)
                result["programs"].append(program_yaml)
                result["programs"][-1]["file_name"] = yaml_file
                # Now copy the YAML program description file to the programs_yaml directory
                program_system_name = self.__get_program_system_name(
                    program_dir_name,
                    program_yaml
                )
                copy_prog_yaml_string = "cp {0} {1}/{2}.yaml".format(
                    yaml_file,
                    prog_yaml_dir_path,
                    program_system_name
                )
                subprocess.Popen(
                    shlex.split(copy_prog_yaml_string),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                ).communicate()
        # Change working dir back before we return...
        os.chdir(cwd)
        return result
    
    def __build_program(self):
        # First run the build script
        self.build_stderr = os.path.abspath("build_stderr.log")
        self.build_stdout = os.path.abspath("build_stdout.log")
        build_stderr = open(self.build_stderr, "w")
        build_stdout = open(self.build_stdout, "w")
        build_process = subprocess.Popen(
            shlex.split("sh CRBuild.sh"),
            stdout=build_stderr,
            stderr=build_stdout
        )
        build_process.communicate()
        build_stderr.close()
        build_stdout.close()
        # Then test success
        self.test_stderr = os.path.abspath("test_stderr.log")
        self.test_stdout = os.path.abspath("test_stdout.log")
        test_stderr = open(self.test_stderr, "w")
        test_stdout = open(self.test_stdout, "w")
        test_process = subprocess.Popen(
            shlex.split("sh CRTest.sh"),
            stdout=test_stdout,
            stderr=test_stderr
        )
        test_process.communicate()
        test_stderr.close()
        test_stdout.close()
        test_success = test_process.returncode
        if test_success != 0:
            # Test script failed, so the build process failed
            return False
        # Success
        return True
    
    # def genUI(self, yc, ptp, psn):
    #     self.__update_UI_with_YAML(yc, ptp, psn)
    
    def __update_UI_with_YAML(self, yaml_config, parameters_template_path, program_system_name):
        if 'executable' in yaml_config:
            new_parameters_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "app/views/{0}.html".format(program_system_name)
            )
            if os.path.exists(new_parameters_path):
                print "Found a view already at '{0}'. Not generating UI for the '{1}' executable.".format(
                    new_parameters_path,
                    yaml_config['executable']['name']
                )
                return
            print "Creating a view for the '{0}' executable at '{1}'.".format(
                yaml_config['executable']['name'],
                new_parameters_path
            )
            # We need to create a copy of the template file
            copy_str = "cp {0} {1}".format(parameters_template_path, new_parameters_path)
            os.system(copy_str)
            # And now add in the inputs...
            for line in fileinput.input(new_parameters_path, inplace=1):
                if line.find("START ADDING REQUIRED HERE") > -1:
                    # We don't want this line, we want to remove it and start adding inputs here
                    for file_param in yaml_config["required_file_parameters"]:
                        param_name = file_param['name']
                        display_name = param_name.capitalize() + " File"
                        form_name = param_name + "-fileName"
                        print '<div class="form-group">'
                        print '<label for="{0}">{1}</label>'.format(param_name, display_name)
                        print '<input name="{0}" type="file" id="{1}">'.format(form_name, param_name)
                        print '</div>'
                    for value_param in yaml_config["required_value_parameters"]:
                        print '<div class="form-group">'
                        print '<label for="{0}">{1}</label>'.format(value_param, value_param.capitalize())
                        print '<input name="{0}" class="form-control" type="text" id="{0}">'.format(value_param)
                        print '</div>'
                elif line.find("START ADDING OPTIONAL HERE") > -1:
                    # Again, we don't want this line, just want to start adding inputs here
                    if "optional_file_parameters" in yaml_config:
                        for file_param in yaml_config["optional_file_parameters"]:
                            param_name = file_param['name']
                            display_name = param_name.capitalize() + " File Name"
                            form_name = param_name + "-fileName"
                            print '<div class="form-group">'
                            print '<label for="{0}">{1}</label>'.format(param_name, display_name)
                            print '<input name="{0}" type="file" id="{1}">'.format(form_name, param_name)
                            print '</div>'
                    if "optional_value_parameters" in yaml_config:
                        for value_param in yaml_config["optional_value_parameters"]:
                            print '<div class="form-group">'
                            print '<label for="{0}">{1}</label>'.format(value_param, value_param.capitalize())
                            print '<input name="{0}" class="form-control" type="text" id="{0}">'.format(value_param)
                            print '</div>'
                    if "optional_boolean_parameters" in yaml_config:
                        for boolean_param in yaml_config["optional_boolean_parameters"]:
                            print '<div class="checkbox">'
                            print '<label>'
                            print '<input name="{0}" type="checkbox" value="True">'.format(boolean_param)
                            print boolean_param.capitalize()
                            print '</label>'
                            print '</div>'
                else:
                    print line,


if __name__ == "__main__":
    # There are two valid cases for how this script can get called
    
    # Case 1. We are calling cr_build from an SSH connection internally to build programs on each
    # cloud infrastructure. (see the build() method)
    # example call:
    #  'python cr_build.py internal aws /home/ubuntu/cloudrunner/programs /home/ubuntu/cloudrunner/programs_yaml https://github.com/XX/YY.git'
    argc = len(sys.argv)
    # if sys.argv[1] == 'ui':
    #     builder = CRBuilder(
    #         skip_init=True,
    #         infrastructure="local",
    #         programs_path="/Users/choruk/src/stochss/programs"
    #     )
    #     builder.genUI(
    #         yaml.load(open("/Users/choruk/src/stochss/programs/testing/CR1.yaml", "r")),
    #         "/Users/choruk/src/stochss/cloudrunner/input_job_parameters_template.html",
    #         "Testing-ssa"
    #     )
    # el
    if argc > 5 and sys.argv[1] == "internal":
        infrastructure = sys.argv[2]
        programs_dir_path = sys.argv[3]
        programs_yaml_dir_path = sys.argv[4]
        cloudrunner_builder = CRBuilder(
            skip_init=True,
            infrastructure=infrastructure,
            programs_path=programs_dir_path,
            programs_yaml_path=programs_yaml_dir_path
        )
        git_URLs = []
        for i in range (5, argc):
            git_URLs.append(sys.argv[i])
        
        failed = False
        for git_URL in git_URLs:
            print git_URL
            build_result = cloudrunner_builder.wrapper_for_build_process(
                git_URL,
                infrastructure
            )
            if build_result['success']:
                print "Succeeded"
                for program_yaml in build_result["programs"]:
                    # Offset into the string where the name of the program directory starts
                    # relative to the directory containing all programs
                    program_offset = len(programs_dir_path) + 1
                    program_yaml["relative_program_dir"] = build_result["program_dir_path"][program_offset:]
                    print "Program YAML Start"
                    print yaml.dump(program_yaml).strip('\n')
                    print "Program YAML Finish"
            else:
                failed = True
                print "Failed"
                failure_yaml = {}
                if 'logs_location' in build_result:
                    failure_yaml['logs_location'] = build_result['logs_location']
                if 'reason' in build_result:
                    failure_yaml['reason'] = build_result['reason']
                print yaml.dump(failure_yaml).strip('\n')
                print "Failure YAML Finish"
        if failed:
            exit(-1)
        
    # Case 2. cr_build is called from the command line by an actual user.
    else:
        cloudrunner_builder = CRBuilder()
        parser = argparse.ArgumentParser(
            description='Use CloudRunner to add new programs into the system.',
            prog='./cr_build.py'
        )
        parser.add_argument(
            'git_clone_URLs',
            metavar='https://github.com/XX/YY.git',
            type=str, nargs='+',
            help='One or more Git clone URLs of programs to deploy and build.'
        )
        infra = [infra for infra in cloudrunner_builder.supported_infra if infra != cloudrunner_builder.INFRA_LOCAL]
        parser.add_argument(
            '--infra',
            required=True,
            type=str, nargs='+',
            choices=infra+[cloudrunner_builder.INFRA_LOCAL],
            help='One or more infrastructures where the program(s) should be deployed and built.'
        )
        for cloud in infra:
            # Every cloud provider needs to have credentials in form of public/secret keys
            parser.add_argument(
                '--{0}-access-key'.format(cloud),
                type=str, nargs=1,
                help="Your public access key used to access the '{0}' infrastructure."
                " Only needs to be included if you specified this infrastructure in the --infra argument.".format(cloud)
            )
            parser.add_argument(
                '--{0}-secret-key'.format(cloud),
                type=str, nargs=1,
                help="Your secret access key used to access the '{0}' infrastructure."
                " Only needs to be included if you specified this infrastructure in the --infra argument.".format(cloud)
            )
        parser.add_argument(
            '--generate-UI',
            action='store_true',
            help='If present, CloudRunner will generate/update the relevant UI.'
        )
        parser.parse_args(namespace=cloudrunner_builder)
        # print vars(cloudrunner_builder)
    
        if cloudrunner_builder.infra:
            # Make sure all the credentials were specified
            for infra in cloudrunner_builder.infra:
                if infra == cloudrunner_builder.INFRA_LOCAL: continue
                # We know that the cloudrunner_builder object has these attributes because argparse adds them
                missing_access_key = cloudrunner_builder.__getattribute__("{0}_access_key".format(infra)) is None
                missing_secret_key = cloudrunner_builder.__getattribute__("{0}_secret_key".format(infra)) is None
                if missing_access_key or missing_secret_key:
                    parser.error("You failed to include all of the necessary credentials for the '{0}' infrastructure.".format(infra))
        else:
            print "Shouldn't get here"
            sys.exit(1)
    
        cloudrunner_builder.build()