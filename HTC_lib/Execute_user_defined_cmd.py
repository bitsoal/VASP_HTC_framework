
# coding: utf-8

# In[4]:


from Utilities import decorated_os_system, get_time_str
import os


# In[5]:


def Execute_user_defined_cmd(cal_loc, user_defined_cmd_list, where_to_execute, log_txt):
    """
    Execute commands listed in user_defined_cmd_list under where_to_execute and write log into log_txt.
    input arguments:
        - cal_loc (str): The absolute path of the calculation folder
        - user_defined_cmd_list (list of str): a list of cmds to be executed.
        - where_to_execute (str): an absolute path under which cmds will be executed.
        - log_txt (str): the file to which log is written. Note that the absolute path should be used.
    If cmds are successfully executed, return True; Otherwise, return False
    """
    if user_defined_cmd_list:
        for cmd_ in user_defined_cmd_list:
            if not decorated_os_system(cmd=cmd_, where_to_execute=where_to_execute):
                with open(log_txt, "a") as f:
                    f.write("{} Error: at {}\n".format(get_time_str(), where_to_execute))
                    f.write("\t\t\tfail to execute user-defined-cmd {}\n".format(cmd_))
                    f.write("\t\t\tcreate __manual__ into {}\n".format(cal_loc))
                open(os.path.join(cal_loc, "__manual__"))
                return False
        with open(log_txt, "a") as f:
            f.write("{} INFO: at {}\n".format(get_time_str(), where_to_execute))
            f.write("\t\t\tsuccessfully execute user-defined-cmd as listed below:\n")
            for cmd_ in user_defined_cmd_list:
                f.write("\t\t\t\t{}\n".format(cmd_))
    return True

