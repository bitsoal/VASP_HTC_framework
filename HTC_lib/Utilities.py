
# coding: utf-8

# # created on Feb 18 2018

# In[1]:


import os, time, shutil
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
        print("\nError: Given the prefix {} and suffix {}, more than one file are found: ".format(prefix, suffix))
        print(("{}\t"*len(target_file_list)).format(*target_file_list))
        print("under {}\n".format(cal_loc))
        raise Exception("See error above.")
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
    firework_name = os.path.split(cal_loc)[-1]
    for firework in workflow:
        if firework_name == firework["firework_folder_name"]:
            return firework

