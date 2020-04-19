#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os, sys
HTC_package_path = "C:/Users/tyang/Documents/Jupyter_workspace/HTC/python_3"
if  os.path.isdir(HTC_package_path) and HTC_package_path not in sys.path:
    sys.path.append(HTC_package_path)

from HTC_lib.VASP.Miscellaneous.Utilities import decorated_os_system, get_time_str


# In[5]:


def Execute_user_defined_cmd(cal_loc, user_defined_cmd_list, where_to_execute):
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

