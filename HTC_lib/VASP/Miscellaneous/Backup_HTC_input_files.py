#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os, sys, shutil
HTC_lib_path = "C:/Users/tyang/Documents/Jupyter_workspace/HTC/python_3"
if HTC_lib_path not in sys.path:
    sys.path.append(HTC_lib_path)
    
from HTC_lib.VASP.Miscellaneous.Utilities import get_time_str, find_next_name, construct_name


# In[2]:


def are_two_files_the_same(file_1, file_2):
    if not os.path.isfile(file_2):
        return False
    
    with open(file_1, "r") as f_1, open(file_2, "r") as f_2:
        len_1, len_2 = 0, 0
        for lline in f_1:
            len_1 += 1
        for line in f_2:
            len_2 += 1
    if len_1 != len_2:
        return False
    
    with open(file_1, "r") as f_1, open(file_2, "r") as f_2:
        for line_1, line_2 in zip(f_1, f_2):
            if line_1 != line_2:
                return False
    return True


# In[3]:


def backup_a_file(src_folder, src_file, dst_folder, overwrite=True):
    if not os.path.isdir(dst_folder):
        os.mkdir(dst_folder)
    
    if overwrite:
        if not are_two_files_the_same(os.path.join(src_folder, src_file), os.path.join(dst_folder, src_file)):
            shutil.copy(os.path.join(src_folder, src_file), os.path.join(dst_folder, src_file))
    else:
        next_name_dict = find_next_name(dst_folder, orig_name=src_file)
        next_name, next_name_suffix = next_name_dict["next_name"], next_name_dict["pref_suf_no"]
        backup = False
        if next_name_suffix == 0:
            backup = True
        else:
            current_name = construct_name(orig_name=src_file, pref_suf_no=next_name_suffix-1)
            if not are_two_files_the_same(os.path.join(src_folder, src_file), os.path.join(dst_folder, current_name)):
                backup = True
                
        if backup:
            shutil.copy(os.path.join(src_folder, src_file), os.path.join(dst_folder, next_name))
            with open(os.path.join(dst_folder, src_file+".log"), "a") as log_f:
                log_f.write("{}: Seems that you have made changes on {} under {}\n".format(get_time_str(), src_file, src_folder))
                log_f.write("\tbackup: src_folder: {}\n\tsrc_file: {}\n\tdst_folder: {}\n\tdst_file: {}\n".format(src_folder, src_file, dst_folder, next_name))


# In[4]:


def backup_htc_input_files(src_folder, file_or_folder_list, dst_folder):
    if not os.path.isdir(dst_folder):
        os.mkdir(dst_folder)
    
    for target in file_or_folder_list:
        if os.path.isfile(os.path.join(src_folder, target)):
            backup_a_file(src_folder, target, dst_folder)
        elif os.path.isdir(os.path.join(src_folder, target)):
            new_src_folder = os.path.join(src_folder, target)
            new_dst_folder = os.path.join(dst_folder, target)
            backup_htc_input_files(new_src_folder, os.listdir(new_src_folder), new_dst_folder)


# backup_htc_input_files(".", ["Execute_user_defined_cmd.ipynb", "__pycache__"], "test/")
# backup_a_file(".", "Utilities.ipynb", "test/", overwrite=False)
