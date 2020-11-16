#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os, sys, subprocess

##############################################################################################################
##DO NOT change this part.
##../setup.py will update this variable
HTC_package_path = "C:/Users/tyang/Documents/Jupyter_workspace/HTC/python_3"
assert os.path.isdir(HTC_package_path), "Cannot find this VASP_HTC package under {}".format(HTC_package_path)
if HTC_package_path not in sys.path:
    sys.path.append(HTC_package_path)
##############################################################################################################


from HTC_lib.VASP.Miscellaneous.Utilities import decorated_os_system, get_time_str, get_mat_folder_name_from_cal_loc


# In[6]:


def Execute_shell_cmd(cal_loc, user_defined_cmd_list, where_to_execute, defined_by_which_htc_tag=None):
#def Execute_user_defined_cmd(cal_loc, user_defined_cmd_list, where_to_execute):
    """
    Execute commands listed in user_defined_cmd_list under where_to_execute and write log into log_txt.
    input arguments:
        - cal_loc (str): The absolute path of the calculation folder
        - user_defined_cmd_list (list of str): a list of cmds to be executed.
        - where_to_execute (str): an absolute path under which cmds will be executed.
        - defined_by_which_htc_tag (str or None): the name of the htc tag by which the user_defined_cmd_list is defined. Default: None
    If cmds are successfully executed, return True; Otherwise, return False
    """
    if user_defined_cmd_list:
        
        #Find the material folder name from cal_loc. The LAST folder whose name starts with "step_x_" ("x" is a number) is the indicator.
        #e.g. >>>get_mat_folder_name_from_cal_loc(cal_loc="/home/user1/htc_test/cal_folder/material_A/step_1_str_opt")
        #     "material_A"
        #     >>>get_mat_folder_name_from_cal_loc(cal_loc="/home/user1/htc_test/cal_folder/material_A/step_3_chg_diff/step_1_H_consituent")
        #     "step_3_chg_diff"
        material_folder_name = get_mat_folder_name_from_cal_loc(cal_loc=cal_loc)
        user_defined_cmd_list = [cmd.replace("${MAT_FOLDER_NAME}", material_folder_name) for cmd in user_defined_cmd_list]
        
        current_dir = os.getcwd()
        
        open(os.path.join(where_to_execute, "running_cmd"), "w").close()
        
        with open(os.path.join(cal_loc, "log.txt"), "a") as f:
            f.write("{} CMD: at {}\n".format(get_time_str(), where_to_execute))
            if defined_by_which_htc_tag == None:
                f.write("\tTry to execute the below commands one by one:\n")
            else:
                f.write("\tTry to execute the below commands defined by {} one by one:\n".format(defined_by_which_htc_tag))
            f.write("\t\t{}\n".format(", ".join(user_defined_cmd_list)))
            f.write("\t\tOutput or Error of each command:\n")
            
        for cmd_ind, cmd_ in enumerate(user_defined_cmd_list):
            with open(os.path.join(cal_loc, "log.txt"), "a") as f:
                f.write("\t\t\t>>>Command {}: {}\n".format(cmd_ind, cmd_))
                
            os.chdir(where_to_execute)
            for i in range(10): #To avoid the case where the server is too busy to respond to the command. Hope the server is able to respond to either of the 10 trails.
                result = subprocess.run(cmd_, text=True, capture_output=True, shell=True)
                if result.returncode == 0:
                    break
            os.chdir(current_dir)
            
            if result.returncode != 0:
                stderr = result.stderr if result.stderr else ""
                with open(os.path.join(cal_loc, "log.txt"), "a") as f:
                    f.write("\t\t\t\tExecution status: Failed\n")
                    f.write("\t\t\t\tError:\n")
                    [f.write("\t\t\t\t{}\n".format(stderr_)) for stderr_ in stderr.split("\n")]
                    f.write("\t\tStop executing any following command(s) and create __manual__\n")
                open(os.path.join(cal_loc, "__manual__"), "w").close()
                os.remove(os.path.join(where_to_execute, "running_cmd"))
                return False
            else:
                stdout = result.stdout if result.stdout else ""
                with open(os.path.join(cal_loc, "log.txt"), "a") as f:
                    f.write("\t\t\t\tExecution status: Succeeded\n")
                    f.write("\t\t\t\tOutput (if any):\n")
                    [f.write("\t\t\t\t\t{}\n".format(stdout_)) for stdout_ in stdout.split("\n")]
                    
        os.remove(os.path.join(where_to_execute, "running_cmd"))
    return True


# In[4]:


def Old_Execute_user_defined_cmd(cal_loc, user_defined_cmd_list, where_to_execute):
    """
    Execute commands listed in user_defined_cmd_list under where_to_execute and write log into log_txt.
    input arguments:
        - cal_loc (str): The absolute path of the calculation folder
        - user_defined_cmd_list (list of str): a list of cmds to be executed.
        - where_to_execute (str): an absolute path under which cmds will be executed.
    If cmds are successfully executed, return True; Otherwise, return False
    """
    if user_defined_cmd_list:
        for cmd_ in user_defined_cmd_list:
            if not decorated_os_system(cmd=cmd_, where_to_execute=where_to_execute):
                with open(os.path.join(cal_loc, "log.txt"), "a") as f:
                    f.write("{} Error: at {}\n".format(get_time_str(), where_to_execute))
                    f.write("\t\t\tfail to execute user-defined-cmd {}\n".format(cmd_))
                    f.write("\t\t\tcreate __manual__ into {}\n".format(cal_loc))
                open(os.path.join(cal_loc, "__manual__"), "w").close()
                return False
        with open(os.path.join(cal_loc, "log.txt"), "a") as f:
            f.write("{} INFO: at {}\n".format(get_time_str(), where_to_execute))
            f.write("\t\t\tsuccessfully execute user-defined-cmd as listed below:\n")
            for cmd_ in user_defined_cmd_list:
                f.write("\t\t\t\t{}\n".format(cmd_))
    return True

