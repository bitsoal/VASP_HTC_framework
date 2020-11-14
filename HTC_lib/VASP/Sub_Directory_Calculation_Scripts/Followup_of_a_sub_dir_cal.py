#!/usr/bin/env python
# coding: utf-8

# In[10]:


import os, sys, re, math, shutil, json

##############################################################################################################
##DO NOT change this part.
##../setup.py will update this variable
HTC_package_path = "C:/Users/tyang/Documents/Jupyter_workspace/HTC/python_3"
assert os.path.isdir(HTC_package_path), "Cannot find this VASP_HTC package under {}".format(HTC_package_path)
if HTC_package_path not in sys.path:
    sys.path.append(HTC_package_path)
##############################################################################################################


# In[5]:


__doc__ = """
    What this script does:
        This script prepares VASP input files of a sub-dir calculations following a sub-dir calculations.
        
    The command line to call this script looks like below:
    >>>python Followup_of_a_sub_dir_cal --files_from_parent_dir --prev_sub_dir_cal --sub_dir_names:filename [--files_from_prev_sub_dir_cal] [--contcar_to_poscar:Yes] [--extra_copy] [--help]
    Arguments in a pair of brackets are optional
    * --files_from_parent_dir: files to be copied to sub-directories. parent_dir is the directory where the current script is executed.
                            If more than one files to be copied, separate them with plus signs "+"
                            Note that INCAR, POSCAR, KPOINTS & POTCAR WILL NOT be IMPLICITLY copied to sub-dirs by this tag.
                            Default: nothing
    * --prev_sub_dir_cal: the directory name of the previous sub-dir calculations, from which the sub-dirs defined by --sub_dir_names will be copied.
                            Under each copied sub_dir, the files defined by --files_from_prev_sub_dir_cal will be copied, too.
                            Note that --prev_sub_dir_cal should be specified relative to where the current script is executed.
                            If you are using VASP_HTC_framework (https://github.com/bitsoal/VASP_HTC_framework), it should look like ../step_x_xxxx
    * --sub_dir_names: a json filename storing a python dict. The dict has a key "sub_dir_name_list" and the corresponding value is a list of sub-dir names.
                        We assume this json file is under the folder specified by --prev_sub_dir_cal. So JUST pass the the name of the json file to this tag.
                        Also see --prev_sub_dir_cal
                        Note that the sub-dir names of the current sub-dir calculations should be exactly same at the previous sub-dir calculations, i.e. 1-1 mapping
    * --files_from_prev_sub_dir_cal: see --prev_sub_dir_cal.
                            If more than one files to be copied, separate them with plus signs "+"
                            Note that INCAR, POTCAR, KPOINTS, POSCAR and CONTCAR are implicitly copied by this tag. No need set them here.
    * --contcar_to_poscar (Yes or No): Is CONTCAR changed to POSCAR under each of the current sub-dirs, once the copy from the previous sub-dir calculations finishes?
                            Default: Yes
    * --extra_copy: The additional file needed to be copied into each of the sub-directories where VASP calculations are performed. 
                    Separate them by + if there are more than one.
                    INCAR, POTCAR, KPOINTS and POSCAR are implicitly copied. So no need to set them here.
                    Default: Nothing
    * --help: Explain how to use this script and the input arguments.
    Note that there must be no whitespace in the argument-value pair.
    Note that after the first execution of this script, the parsed arguments will be saved into a file named as "followup_sub_dir_setup.json".
        Whenever followup_sub_dir_setup.json exists, the passed arguments in the command line will all be omitted and those in followup_sub_dir_setup.json
        will be used. "followup_sub_dir_setup.json" makes the strain effect estimation for each materials in the HTC calculations customizable.
        ****An exception: Every time this scripts is executed, it always examines the status of the previous sub-dir calculations (defined by --prev_sub_dir_cal).
            If its status is not __done__, update followup_sub_dir_setup.json by reading the command line parameters.
        
    Return:
        if all sub-dir calculations finished as signalled by __done__:
            __sub_dir_cal__ --> __done__
        """


# In[7]:


def read_and_set_default_arguments(argv_list):
    """ Parse cmd arguments and set default argument 
    OR
    Read arguments from a file named "followup_sub_dir_setup.jsonn" under the folder where this script is called.
    See __doc__ of this script for the detailed explanation between reading cmd arguments and followup_sub_dir_setup.json.
    """
    
    update_setup = True
    if os.path.isfile("followup_sub_dir_setup.json"):
        with open("followup_sub_dir_setup.json", "r") as setup:
            argv_dict = json.load(setup)
        update_setup = False
    
    if update_setup == False:
        if not os.path.isfile(os.path.join(argv_dict["prev_sub_dir_cal"], "__done__")):
            #the below signal tag is going to be added as a built-in tag in VASP_HTC_framework
            if not os.path.isfile(os.path.join(argv_dict["prev_sub_dir_cal"], "__done_clean__")):
                update_setup = True
    
    if update_setup:
        raw_argv_dict = {key: value for key, value in [argv.split(":") for argv in argv_list[1:]]}
        argv_dict = {}
        
        argv_dict["files_from_parent_dir"] = raw_argv_dict.get("--files_from_parent_dir", "")
        argv_dict["files_from_parent_dir"] = [file for file in argv_dict["files_from_parent_dir"].split("+") if file]
        for file in argv_dict["files_from_parent_dir"]:
            assert os.path.isfile(file), "The following file passed to --files_from_parent_dir does not exit in the parent directory where the current script is called: {}".format(file)
            
        try:
            argv_dict["prev_sub_dir_cal"] = raw_argv_dict["--prev_sub_dir_cal"]
            assert os.path.isdir(argv_dict["prev_sub_dir_cal"]), "the folder/directory passed to --prev_sub_dir_cal does not exist: {}".format(argv_dict["prev_sub_dir_cal"])
        except:
            print(__doc__)
            raise
        
        try:
            sub_dir_names_file = os.path.join(argv_dict["prev_sub_dir_cal"], raw_argv_dict["--sub_dir_names"])
            assert os.path.isfile(sub_dir_names_file), "{} passed to --sub_dir_names does not exist under {}".format(raw_argv_dict["--sub_dir_names"], argv_dict["prev_sub_dir_cal"])
            with open(sub_dir_names_file, "r") as f:
                argv_dict["sub_dir_names_list"] = json.load(f)["sub_dir_name_list"]
            for sub_dir_name in argv_dict["sub_dir_names_list"]:
                path_to_sub_dir = os.path.join(argv_dict["prev_sub_dir_cal"], sub_dir_name)
                assert os.path.isdir(path_to_sub_dir), "{} specified in the json file referred by --sub_dir_names does not exist under {}".format(sub_dir_name, argv_dict["prev_sub_dir_cal"])
        except:
            print(__doc__)
            raise
            
        
        argv_dict["files_from_prev_sub_dir_cal"] = raw_argv_dict.get("--files_from_prev_sub_dir_cal", "")
        argv_dict["files_from_prev_sub_dir_cal"] = [file for file in argv_dict["files_from_prev_sub_dir_cal"].split("+") if file] + ["INCAR", "POTCAR", "KPOINTS", "POSCAR", "CONTCAR"]
        argv_dict["files_from_prev_sub_dir_cal"] = list(set(argv_dict["files_from_prev_sub_dir_cal"]))
        for sub_dir_name in argv_dict["sub_dir_names_list"]:
            for filename in argv_dict["files_from_prev_sub_dir_cal"]:
                path_to_file = os.path.join(argv_dict["prev_sub_dir_cal"], sub_dir_name, filename)
                assert os.path.isfile(path_to_file), "file {} specified by --files_from_prev_sub_dir_cal, --prev_sub_dir_cal and --sub_dir_names does not exist".format(path_to_file)
        
        argv_dict["contcar_to_poscar"] = raw_argv_dict.get("--contcar_to_poscar", "yes").lower()
        argv_dict["contcar_to_poscar"] = True if "y" in argv_dict["contcar_to_poscar"] else False

        
        argv_dict["extra_copy"] = [file for file in raw_argv_dict.get("--extra_copy", "").split("+") if file]
        for file in argv_dict["extra_copy"]:
            assert os.path.isfile(file), "{} doesn't exist under {}".format(file, os.getcwd())
            for std_vasp_input in ["INCAR", "POTCAR", "POSCAR", "KPOINTS"]:
                assert not file.endswith(std_vasp_input), "INCAR, POTCAR, POSCAR and KPOINTS will be copied implicitly. Don't set them via --extra_copy"
        
    
    with open("followup_sub_dir_setup.json", "w") as setup:
        json.dump(argv_dict, setup, indent=4)
        
    sub_dir_creation_summary_dict = {"extra_copy_to_sub_dir": [os.path.split(file)[1] for file in argv_dict["extra_copy"]]}
    sub_dir_creation_summary_dict["sub_dir_name_list"] = argv_dict["sub_dir_names_list"]
    with open("sub_dir_creation_summary.json", "w") as summary_df:
        json.dump(sub_dir_creation_summary_dict, summary_df, indent=4)
        
    return argv_dict             
            


# In[9]:


def prepare_cal_files(argv_dict):
    
    prev_sub_dir_cal = argv_dict["prev_sub_dir_cal"]
    contcar_to_poscar = argv_dict["contcar_to_poscar"]
    
    for sub_dir_name in argv_dict["sub_dir_names_list"]:
        is_preparation_needed = True
        if not os.path.isdir(sub_dir_name):
            os.mkdir(sub_dir_name)
            print("Create {}".format(sub_dir_name), end=" && ")
        else:
            file_list = os.listdir(sub_dir_name)
            for filename in file_list:
                if filename.startswith("__") and filename.endswith("__"):
                    #The presence of any HTC signal file indicates that the sub-dir VASP calculation input files were prepared.
                    is_preparation_needed = False
                    break   
            
        if is_preparation_needed:
            print("copy the following files from {} to {}: ".format(os.path.join(prev_sub_dir_cal, sub_dir_name), sub_dir_name), end="")
            for filename in argv_dict["files_from_prev_sub_dir_cal"]:
                src_path_to_file = os.path.join(prev_sub_dir_cal, sub_dir_name, filename)
                dst_path_to_file = os.path.join(sub_dir_name, filename)
                shutil.copy(src_path_to_file, dst_path_to_file)
                print(filename, end=", ")
            print("", end=" && ")
            
            if contcar_to_poscar:
                shutil.copy(os.path.join(sub_dir_name, "CONTCAR"), os.path.join(sub_dir_name, "POSCAR"))
                print("contcar_to_poscar is Yes/True: CONTCAR --> POSCAR under {}".format(sub_dir_name), end=" && ")
            
            if argv_dict["files_from_parent_dir"]:
                print("copy the following files from the parent directory (./) to {}: ".format(sub_dir_name), end="")
            else:
                print("nothing to copy from the parent directory.", end="")
            for filename in argv_dict["files_from_parent_dir"]:
                shutil.copy(filename, os.path.join(sub_dir_name, filename))
                print(filename, end=", ")
            print("", end=" && ")
            
            if argv_dict["extra_copy"]:
                print(" extra_copy to {}: ".format(sub_dir_name), end="")
                for filename in argv_dict["extra_copy"]:
                    shutil.copy2(filename, sub_dir_name)
                    print(filename, end=", ")
                
            open(os.path.join(sub_dir_name, "__ready__"), "w").close()
            print("&& create __ready__")
            
            
        


# In[2]:


def are_all_sub_dir_cal_finished(argv_dict):
    
    for sub_dir_name in argv_dict["sub_dir_names_list"]:
        
        if True not in [os.path.join(os.path.join(sub_dir_name, target_file)) for target_file in 
                        ["__done__", "__skipped__", "__done_cleaned_analyzed__", "__done_failed_to_clean_analyze__"]]:
            return False
        
    return True


# In[74]:


if __name__ == "__main__":
    if "--help" in [argv.lower() for argv in sys.argv]:
        print(__doc__)
    else:
        argv_dict = read_and_set_default_arguments(sys.argv)
        prepare_cal_files(argv_dict)
        if are_all_sub_dir_cal_finished(argv_dict):
            os.rename("__sub_dir_cal__", "__done__")
            print("All sub-dir calculations finished.")
            print("__sub_dir_cal__ --> __done__")
        else:
            print("Some sub-dir calculations are still running...")

