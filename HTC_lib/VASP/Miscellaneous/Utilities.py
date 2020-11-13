#!/usr/bin/env python
# coding: utf-8

# In[3]:


import os, time, shutil, re
import subprocess


# In[2]:


def get_time_str():
    return time.strftime("%Y-%m-%d-%H:%M:%S")


# In[3]:


def get_time_suffix():
    return time.strftime("%Y_%m_%d_%H_%M_%S")


# In[4]:


def find_next_name(cal_loc, orig_name="INCAR"):
    """
    Next names look like _INCAR_0, _INCAR_1, _INCAR_2.
    """
    file_list = os.listdir(cal_loc)
    for i in range(100):
        #print(orig_name, str(i))
        next_name = "_" + orig_name + "_" + str(i)
        if not next_name in file_list:
            return {"next_name": next_name, "pref_suf_no": i}


# In[5]:


def construct_name(orig_name, pref_suf_no):
    """
    See func find_next_name for the name construction rule.
    """
    return "_" + orig_name + "_" + str(pref_suf_no)


# In[6]:


def decorated_os_rename(loc, old_filename, new_filename, clear_content=False):
    """
    A decorated version of os.rename.
    Before os.rename:
        - Check whether old_filname and new_filename exist
            - if old_filename does not exist, directly create a file named new_filename using open()
    After os.rename:
        - if clear_content is True, clear the file.
    input arguments:
        - loc (str): a directory
        - old_filename (str)
        - new_filename (str)
        optional
            - clear_conent (bool): If True, clear the file. Default: False
    """
    old_file = os.path.join(loc, old_filename)
    new_file = os.path.join(loc, new_filename)
    
    if os.path.isfile(old_file):
        os.rename(old_file, new_file)
    else:
        open(new_file, "w").close()
        
    if clear_content:
        open(new_file, "w").close()


# In[7]:



def rename_files(loc, file_list, additional_file_list=[]):
    """
    rename files such that it is convenient for human to deal with errors that can not be fixed automatically.
    input argument:
        - loc (str): a directory
        - file_list (list): a set of file names.
        - additional_file_list (list): a set of file names. Defalut: []
        Note that file_list and additonal_file_list together determine the smallest suffix and only files in 
            file_list will be renamed via the determined suffix.
    the new_suffix will be returned.
    """
    max_suffix = 0
    total_file_list = file_list + additional_file_list
    suffix_list = []
    for file in total_file_list:
        new_name = find_next_name(cal_loc=loc, orig_name=file)
        suffix_list.append(new_name["pref_suf_no"])
    pref_suf_no = max(suffix_list)
            
    dir0 = os.getcwd()
    os.chdir(loc)
    for file in file_list:
        shutil.move(file, construct_name(orig_name=file, pref_suf_no=pref_suf_no))
    os.chdir(loc)
    
    return pref_suf_no


# In[8]:


def search_file(cal_loc, prefix="", suffix=""):
    """
    Find the file under folder cal_loc which has either a given prefix or a given suffix, or both.
    input argument:
        - cal_loc (str): a folder.
        - prefix (str): default ""
        - suffix (str): default ""
    raise error if more than one files are found.
    return the file name if only one file is found.
    return None if not found.
    """
    if prefix == "" and suffix == "":
        return None
    
    file_list = []
    for file in os.listdir(cal_loc):
        if os.path.isfile(os.path.join(cal_loc, file)):
            file_list.append(file)
            
    target_file_list = []
    for file in file_list:
        if prefix != "" and not file.startswith(prefix):
            continue
        if suffix != "" and not file.endswith(suffix):
            continue
        target_file_list.append(file)
        
    if len(target_file_list) > 1:
        with open(os.path.join(cal_loc, "log.txt"), "a") as f:
            f.write("\nError: Given the prefix {} and suffix {}, more than one files are found: \n".format(prefix, suffix))
            f.write(("{}\t"*len(target_file_list)).format(*target_file_list))
            f.write("under {}\n".format(cal_loc))
            f.write("\t\tcreate __manual__\n")
        with open(os.path.join(cal_loc, "__manual__"), "w") as f:
            f.write("The given prefix {} and suffix {} are not unique enough to match only file".format(prefix, suffix))
        #raise Exception("See error above.")
    elif len(target_file_list) == 1:
        return target_file_list[0]
    else:
        return None


# In[9]:


def copy_and_move_files(src_dir, dst_dir, copy_files=[], move_files=[], contcar_to_poscar=False):
    """
    copy, move files from folder src to folder dst and remove files under folder src.
    input arguments:
        - src_dir (str): the source folder under which files are copied, moved or removed.
        - dst_dir (str): the destination folder to which files are copied or moved from folder src_dir. 
                    If not existent, create the folder.
        - copy_files (list or tuple): each entry of copy_files is a filename (str) which will be copied to folder dst_dir.
                    default: empty list
        - move_files (list or tuple): each entry of move_files is a filename (str) which will be moved to folder dst_dir.
                    default: empty list
        - contcar_to_poscar (True or False): copy CONTCAR under src_dir to dst_dir and rename it as POSCAR. 
                    default: False
    return a dictionary having keys below:
        - copy_files: a list of files that are supposed to be copied but cannot be found at src
        - move_files: a list of files that are supposed to be moved but cannot be found at src
    """
    non_existent_files = {"copy_files": [], "move_files": []}
    
    if contcar_to_poscar:
        copy_files =tuple(list(copy_files) + ["CONTCAR"])
    
    copy_files = set(copy_files)
    move_files = set(move_files)
    
    if not os.path.isdir(dst_dir):
        os.mkdir(dst_dir)
        
    for copy_file in copy_files:
        src = os.path.join(src_dir, copy_file)
        dst = os.path.join(dst_dir, copy_file)
        if os.path.isfile(src):
            shutil.copyfile(src=src, dst=dst) #, follow_symlinks=False)
        else:
            non_existent_files["copy_files"].append(src)
        #assert os.path.isfile(src), "Error: no {} under folder {}".format(copy_file, src_dir)
        
        
    for move_file in move_files:
        src = os.path.join(src_dir, move_file)
        dst = os.path.join(dst_dir, move_file)
        if os.path.isfile(src):
            shutil.move(src=src, dst=dst)
        else:
            non_existent_files["move_files"].append(src)
        
    if contcar_to_poscar:
        shutil.move(os.path.join(dst_dir, "CONTCAR"), os.path.join(dst_dir, "POSCAR"))
        
    return non_existent_files


# In[10]:


def get_current_firework_from_cal_loc(cal_loc, workflow):
    """
    return the current firework by analyzing cal_loc.
    input arguments:
        - cal_loc (str): absolute calculation directory.
        - workflow
    """
    cal_loc0 = cal_loc
    while True:
        heading_path, firework_name = os.path.split(cal_loc)
        if firework_name.startswith("step_"):
            break
        else:
            cal_loc = heading_path
    for firework in workflow:
        if firework_name == firework["firework_folder_name"]:
            return firework
    raise Exception("Cannot parse a firework name from the path below:\n%s" % cal_loc0)


# In[39]:


def get_mat_folder_name_from_cal_loc(cal_loc):
    """
    get_mat_folder_name_from_cal_loc(cal_loc) return the material folder name by parsing cal_loc.
    input argument:
        - cal_loc (str): absolute calculation directory.
        
    Example 1. >>>get_mat_folder_name_from_cal_loc(cal_loc="/home/user1/htc_test/cal_folder/material_A/step_1_str_opt")
             "material_A"
    Example 2. >>>get_mat_folder_name_from_cal_loc(cal_loc="/home/user1/htc_test/cal_folder/material_A/step_3_chg_diff/step_1_H_consituent")
             "step_3_chg_diff"
             
        1. Note that in this function, the folder name starting with "step_x_" (x is a number), which is "step_1_" in Example 1, is used as an indicator. The name of its parent folder is what would be returned by this function, i.e. "material_A" in Example 1
        2. Given a path, if there are more than one folders whose name starts with "step_x_", the parent folder of the last one will be returned. See Example 2 above.
    """
    assert re.search("step_\d+_", cal_loc), "The path below does not contain a folder name starting with 'step_x_', where x is a number. Cannot parse the material folder name from it.\n\n%s\n\nThe document of this function is shown below%s" % (cal_loc, get_mat_folder_name_from_cal_loc.__doc__)
    
    cal_loc0 = cal_loc
    while True:
        head, tail = os.path.split(cal_loc)
        cal_loc = head
        m = re.match("step_\d+_", tail)
        if m:
            break
    
    head, mat_folder_name = os.path.split(cal_loc)
    assert mat_folder_name, "Fail to parse the material folder name from the path below\n\n%s\n\nSee the document of this function below: %s" % (cal_loc0, get_mat_folder_name_from_cal_loc.__doc__)
    
    return mat_folder_name
    


# In[11]:


def decorated_os_system(cmd, where_to_execute):
    """
    decorated os.system to tackle the cases where the cmd is not successfully executed.
    input arguments:
        - cmd (str): required.
        - where_to_execute (str): The absolute path
    cmd will be executed once.
    If the exist status is 0 (successful), return True; Otherwise, return False.
    """
    dir0 = os.getcwd()
    os.chdir(where_to_execute)
    try:
        status = os.system(cmd)
    except Exception as err:
        pass
    else:
        if status == 0:
            return True
    
    os.chdir(dir0)
    return False  


# In[12]:


def decorated_subprocess_check_output(args, stdin=None, stderr=None, shell=True, no_of_trails=10):
    trail_no = 0
    error_list = []
    while trail_no < no_of_trails:
        try:
            output = subprocess.check_output(args, stdin=stdin, stderr=stderr, shell=shell).decode("utf-8")
        except Exception as err:
            error_list.append(err)
        else:
            break
        trail_no += 1
    if type(args) == list:
        args = " ".join(args)
    assert trail_no != no_of_trails,     "The command below has been called %d times but all failed. Make sure it is correct\nwhere to call: %s\ncmd:%s" % (no_of_trails, os.getcwd(), args)
    return output, error_list

