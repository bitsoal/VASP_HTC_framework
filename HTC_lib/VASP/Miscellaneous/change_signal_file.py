#!/usr/bin/env python
# coding: utf-8

# In[42]:


import os, sys

##############################################################################################################
##DO NOT change this part.
##../setup.py will update this variable
HTC_package_path = "C:/Users/tyang/Documents/Jupyter_workspace/HTC/python_3"
assert os.path.isdir(HTC_package_path), "Cannot find this VASP_HTC package under {}".format(HTC_package_path)
if HTC_package_path not in sys.path:
    sys.path.append(HTC_package_path)
##############################################################################################################

from HTC_lib.VASP.Miscellaneous.Utilities import get_time_str


# In[43]:


def read_setup_of_changing_signal_file(filename, log_filename):
    assert os.path.isfile(filename), "{} does not exist".format(filename)
    
    setup_dict = {}
    with open(filename, "r") as f:
        for line in f:
            line = line.split("#")[0].strip()
            if line.count("=") == 1:
                key, item = [item.strip() for item in line.split("=")]
                setup_dict[key.lower()] = item
                
    if "original_signal_file" not in setup_dict.keys() or "target_signal_file" not in setup_dict.keys() or "no_of_changes" not in setup_dict.keys():
        with open(log_filename, "a") as log_f:
            log_f.write(get_time_str() + " ")
            log_f.write("Error: You forgot to set original_signal_file, target_signal_file or no_of_changes. Please try again.\n")
        return {}
    
    is_signal_file_good = True
    if not setup_dict["original_signal_file"].startswith("__"):
        is_signal_file_good = False
    elif not setup_dict["original_signal_file"].endswith("__"):
        is_signal_file_good = False
    elif not setup_dict["target_signal_file"].startswith("__"):
        is_signal_file_good = False
    elif not setup_dict["target_signal_file"].endswith("__"):
        is_signal_file_good = False
    if not is_signal_file_good:
        with open(log_filename, "a") as log_f:
            log_f.write(get_time_str() + " ")
            log_f.write("Error: Any signal file should start and end with double underscores ('__'). Please follow this rule and try again\n")
        return {}
    
    try:
        setup_dict["no_of_changes"] = int(setup_dict["no_of_changes"])
        assert setup_dict["no_of_changes"] > 0
    except:
        output_str = "no_of_changes defines how many of calculations tagged by {} will be changed to {}.".format(setup_dict["original_signal_file"], setup_dict["target_signal_file"])
        output_str += " It should be a positive integer."
        with open(log_filename, "a") as log_f:
            log_f.write(get_time_str() + " ")
            log_f.write("Error: " + output_str + "\n")
        return {}
        
    return setup_dict


# In[44]:


def change_signal_file(cal_status_dict, filename="__change_signal_file__"):
    log_filename = filename + ".log"
    with open(filename, "r") as f:
        lines = list(f)
    with open(log_filename, "w") as log_f:
        log_f.write(get_time_str()+"\n")
        log_f.write("\t{} is copied here:\n".format(filename) + "-"*50 + "\n")
        for line in lines:
            log_f.write(line)
        log_f.write("-"*50 + "\n")
    
    setup_dict = read_setup_of_changing_signal_file(filename=filename, log_filename=log_filename)
    if setup_dict == {}:
        return cal_status_dict
    
    original_status_key = setup_dict["original_signal_file"].strip("_") + "_folder_list"
    if original_status_key not in cal_status_dict.keys() or len(cal_status_dict[original_status_key]) == 0:
        with open(log_filename, "a") as log_f:
            log_f.write(get_time_str() + " ")
            log_f.write("Error: None of the calculations is originally tagged by {} or categorized into {}".format(setup_dict["original_signal_file"], original_status_key))
        return cal_status_dict
    
    target_status_key = setup_dict["target_signal_file"].strip("_") + "_folder_list"
    target_cal_folder_list = []
    if target_status_key not in cal_status_dict.keys():
        cal_status_dict[target_status_key] = []
    for i in range(min([len(cal_status_dict[original_status_key]), setup_dict["no_of_changes"]])):
        target_cal_folder_list.append(cal_status_dict[original_status_key].pop())
    
    with open(log_filename, "a") as log_f:
        log_f.write(get_time_str() + " ")
        log_f.write("The status for the below calculations will be changed from {} to {}:\n".format(setup_dict["original_signal_file"], setup_dict["target_signal_file"]))
    for target_cal_folder in target_cal_folder_list:
        os.rename(os.path.join(target_cal_folder, setup_dict["original_signal_file"]), os.path.join(target_cal_folder, setup_dict["target_signal_file"]))
        with open(os.path.join(target_cal_folder, "log.txt"), "a") as log_f:
            log_f.write("{}: Signal File Change:\n".format(get_time_str()))
            log_f.write("\tThis calculation is randomly chosen and its status is changed from {} to {}\n".format(setup_dict["original_signal_file"], setup_dict["target_signal_file"]))
        
        cal_status_dict[target_status_key].append(target_cal_folder)
        
        with open(log_filename, "a") as log_f:
            log_f.write(get_time_str() + " Done ")
            log_f.write(target_cal_folder + "\n")
    
    return cal_status_dict

