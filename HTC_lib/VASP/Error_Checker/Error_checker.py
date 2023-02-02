#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os, time, shutil, sys, re, subprocess


##############################################################################################################
##DO NOT change this part.
##../setup.py will update this variable
HTC_package_path = "C:/Users/tyang/Documents/Jupyter_workspace/HTC/python_3"
assert os.path.isdir(HTC_package_path), "Cannot find this VASP_HTC package under {}".format(HTC_package_path)
if HTC_package_path not in sys.path:
    sys.path.append(HTC_package_path)
##############################################################################################################

from pymatgen.io.vasp.outputs import Oszicar, Vasprun
from pymatgen.core import Structure

import numpy as np

from HTC_lib.VASP.Miscellaneous.Query_from_OUTCAR import find_incar_tag_from_OUTCAR
from HTC_lib.VASP.Miscellaneous.Utilities import get_time_str, search_file, decorated_os_rename, get_current_firework_from_cal_loc, are_2_files_the_same
from HTC_lib.VASP.INCAR.Write_VASP_INCAR import get_bader_charge_tags
from HTC_lib.VASP.INCAR.modify_vasp_incar import modify_vasp_incar
from HTC_lib.VASP.POTCAR.potcar_toolkit import Potcar
from HTC_lib.VASP.POSCAR.POSCAR_IO_functions import sort_poscar, write_poscar

from HTC_lib.VASP.Error_Checker.Error_checker_auxiliary_function import get_trimed_oszicar


# In[11]:


def Vasp_Error_checker(error_type, cal_loc, workflow):  
    """
    Input error_type and return the instance of the associated error checker class which havs two methods, i.e. check, correct
    input arguments:
        - error_type (str or list of length 1): 
            - str: error_type is an error type, and an instance of the associated error checker will be returned.
            - list of length 1: the only entry is a string, "on_the_fly" or "after_cal"
                    - on_the_fly: all on-the-fly error checkers will be called one by one to check errors.
                                    If found, return True; Otherwise return False.
                    - after_cal: all error checkers will be called one by one to check errors.
                                    If found, return True; Otherwise return False.
        - cal_loc: the location of the calculation.
        - workflow:  the output of func Parse_calculation_workflow.parse_calculation_workflow
    """
    error_checker_dict = {"__unfinished_OUTCAR__": OUTCAR_status, 
                          "__electronic_divergence__": Electronic_divergence, 
                          "__ionic_divergence__": Ionic_divergence, 
                          "__pricel__":Vasp_out_pricel, 
                          "__posmap__": Vasp_out_posmap,
                          "__positive_energy__": Positive_energy, 
                          "__bad_termination__": Vasp_out_bad_termination, 
                          "__zbrent__":Vasp_out_zbrent, 
                          "__invgrp__": Vasp_out_invgrp, 
                          "__too_few_bands__": Vasp_out_too_few_bands, 
                          "__too_few_kpoints__":Vasp_out_too_few_kpoints, 
                          "__rhosyg__":Vasp_out_rhosyg, 
                          "__edddav__":Vasp_out_edddav, 
                          "__zpotrf__": Vasp_out_zpotrf, 
                          "__real_optlay__": Vasp_out_real_optlay, 
                          "__bader_charge__": Bader_Charge, 
                          "__pzunmtr_or_pzstein__": Vasp_out_pzunmtr_or_pzstein, 
                          "__nkx_gt_ikptd__": Vasp_out_nkx_gt_ikptd, 
                          "__pead__": Vasp_out_pead}
    
    on_the_fly = ["__too_few_bands__", "__electronic_divergence__", "__bader_charge__"]
    after_cal = on_the_fly + ["__pricel__", "__posmap__", "__bad_termination__", "__zbrent__", "__invgrp__"]
    after_cal += ["__too_few_kpoints__", "__rhosyg__", "__edddav__", "__zpotrf__", "__real_optlay__"]
    after_cal += ["__pzunmtr_or_pzstein__", "__nkx_gt_ikptd__", "__pead__"]
    after_cal += ["__positive_energy__", "__ionic_divergence__", "__unfinished_OUTCAR__"]
    
    
    if isinstance(error_type, str):  
        if error_type in error_checker_dict:
            return error_checker_dict[error_type](cal_loc=cal_loc, workflow=workflow)
        else:
            return Null_error_checker(cal_loc=cal_loc, workflow=workflow)
    elif isinstance(error_type, list):
        if error_type[0] == "on_the_fly":
            error_type_list = on_the_fly
        elif error_type[0] == "after_cal":
            error_type_list = after_cal
        else:
            raise Exception("The argument error_type of func Vasp_Error_checker must be a str or a list consisting of a str")
        if error_type[0] == "on_the_fly":
            for error_checker in on_the_fly:
                if not error_checker_dict[error_checker](cal_loc=cal_loc, workflow=workflow).check():
                    return False
            return True
        
        for error in error_type_list:
            if not error_checker_dict[error](cal_loc=cal_loc, workflow=workflow).check():
                return False
        return True


# In[5]:


class Write_and_read_error_tag(object):
    """
    Write/Read error tag from a given file under folder cal_loc.
    Default: Write into __error__; Read from __killed__
    input argument:
        -cal_loc (str): the location of the to-be-checked calculation
    """
    
    def __init__(self, cal_loc):
        self.cal_loc = cal_loc
        
    def write_error_tag(self, error_tag, file="__error__"):
        with open(os.path.join(self.cal_loc, file), "w") as f:
            f.write(error_tag)
            
    def read_error_tag(self, file="__killed__"):
        """
        input argument:
            -file (str): the file from which the error_tag is read.
        """
        with open(os.path.join(self.cal_loc, file), "r") as f:
            error_tag = f.read().strip()
        return error_tag


# In[6]:


class Queue_std_files():
    """
    Check if the queue stdout and stderr file exist, which have certain suffixes or prefixes as defined in workflow.
    The presence of the two files indicate that the calculation under cal_loc has completed either successfully or unsuccessfully.
    input arguments:
        -cal_loc: the location of the to-be-checked calculation
        - workflow: the output of func Parse_calculation_workflow.parse_calculation_workflow in which either the suffixes 
                    or prefixes are pointed out for the queue stdout and stderr files.
    Two methods are provided, either of which requires any additional input parameters.
        -find_std_files:
            - If found, return [stdout_filename, stderr_filename]
            - If not found, return [None, None]
            Note that func Utilities.search_file will be called to search for the file with the given prefix or suffix.
                If more than one files are found, it will return None.
        -remove_std_files:
            If stdout and stderr files are present under cal_loc, remove them.
    Note that the find_std_files is called in __init__, thereby providing two data, i.e. stdout_file, stderr_file
    """
    
    def __init__(self, cal_loc, workflow):
        self.cal_loc = cal_loc
        self.workflow = workflow
        self.stdout_file, self.stderr_file = self.find_std_files()
        
    def find_std_files(self):
        stdout_prefix, stdout_suffix = self.workflow[0]["queue_stdout_file_prefix"], self.workflow[0]["queue_stdout_file_suffix"]
        stderr_prefix, stderr_suffix = self.workflow[0]["queue_stderr_file_prefix"], self.workflow[0]["queue_stderr_file_suffix"]
    
        stdout_file = search_file(cal_loc=self.cal_loc, prefix=stdout_prefix, suffix=stdout_suffix)
        stderr_file = search_file(cal_loc=self.cal_loc, prefix=stderr_prefix, suffix=stderr_suffix)
    
        return [stdout_file, stderr_file]
        
    def remove_std_files(self):
        if self.stdout_file != None:
            os.remove(os.path.join(self.cal_loc, self.stdout_file))
        if self.stderr_file != None:
            os.remove(os.path.join(self.cal_loc, self.stderr_file))


# In[7]:


def  find_target_str(cal_loc, target_file, target_str):
    """
    input arguments:
        -cal_loc (str): the location of the calculation.
        -target_file (str): the filename of the target file under cal_loc
        -target_str (str)
    output:
        - If target_str is found, return True.
        - If target_str is not found, return False
    Note that if the target_file is not existent, return False
    """
    found_target_str = False
    if os.path.isfile(os.path.join(cal_loc, target_file)):
        with open(os.path.join(cal_loc, target_file), "r") as f:
            for line in f:
                if target_str in line:
                    found_target_str = True
                    break
    return found_target_str


# In[8]:


class Vasp_Error_Saver(object):
    """
    Back up INCAR, POSCAR, KPOINTS, OUTCAR, XDATCAR, vasp.out and queue stdout & stderr so as to facilitate the manual error repair.
    Note that additional files provided by HTC tag error_backup_files will be backed up.
    input arguments:
        -cal_loc: the location of the to-be-checked calculation
        -workflow: the output of func Parse_calculation_workflow.parse_calculation_workflow.
    methods:
        - backup: create a sub-sub-folder under sub-folder error_folder under cal_loc and save aforementioned VASP files.
        - find_error_times: return the number of times that errors have been detected for the cal under cal_loc
    """
    def __init__(self, cal_loc, workflow):
        self.workflow = workflow
        self.cal_loc = cal_loc
        self.firework_name = os.path.split(cal_loc)[-1]
        self.log_txt = os.path.join(self.cal_loc, "log.txt")
        self.error_folder = os.path.join(self.cal_loc, "error_folder")
        self.firework = get_current_firework_from_cal_loc(cal_loc, workflow)
                
    def backup(self):
        if not os.path.isdir(self.error_folder):
            os.mkdir(self.error_folder)
            with open(self.log_txt, "a") as f:
                f.write("{} Backup: Create error_folder under {}\n".format(get_time_str(), self.firework_name))
                
        file_list = [self.workflow[0]["vasp.out"], "__killed__"]
        if self.firework["error_backup_files"]:
            file_list.extend(list(self.firework["error_backup_files"]))
        else:
            file_list.extend(list(self.workflow[0]["error_backup_files"]))
        
        stdout, stderr = Queue_std_files(cal_loc=self.cal_loc, workflow=self.workflow).find_std_files()
        for std_file in [stdout, stderr]:
            if std_file:
                file_list.append(std_file)
            
        sub_error_folder_name = self.find_next_sub_error_folder_name()
        new_sub_error_folder = os.path.join(self.error_folder, sub_error_folder_name)
        if not os.path.isdir(new_sub_error_folder):
            os.mkdir(new_sub_error_folder)
        non_existent_file_list = []
        for file in file_list:
            src_file = os.path.join(self.cal_loc, file)
            dst_file = os.path.join(new_sub_error_folder, file)
            if os.path.isfile(src_file):
                shutil.copyfile(src=src_file, dst=dst_file)
            else:
                non_existent_file_list.append(file)
            
        with open(self.log_txt, "a") as f:
            f.write("{} Backup: at {}\n".format(get_time_str(), self.firework_name))
            f.write("\t\t\tcopy files below to {}:\n".format(os.path.join("error_folder", sub_error_folder_name)))
            f.write("\t\t\t\t")
            [f.write("{}\t".format(file_)) for file_ in file_list]
            f.write("\n")
                
            for file in non_existent_file_list:
                f.write("\t\t\tno {} to backup\n".format(file))
            
        
    def find_error_times(self):
        if not os.path.isdir(self.error_folder):
            return 0
        else:
            return len(os.listdir(self.error_folder))
                
    def find_next_sub_error_folder_name(self):
        error_times = self.find_error_times()
        if error_times == 0:
            return "error_1"
        else:
            latest_sub_error_folder = os.path.join(self.error_folder, "error_"+str(error_times))
            latest_std = Queue_std_files(cal_loc=latest_sub_error_folder, workflow=self.workflow).find_std_files()
            curr_std = Queue_std_files(cal_loc=self.cal_loc, workflow=self.workflow).find_std_files()
            
            outcar_cmp = are_2_files_the_same(os.path.join(latest_sub_error_folder, "OUTCAR"), os.path.join(self.cal_loc, "OUTCAR"))
            incar_cmp  = are_2_files_the_same(os.path.join(latest_sub_error_folder, "INCAR"),  os.path.join(self.cal_loc, "INCAR"))
            
            if latest_std == curr_std and outcar_cmp[-1] and incar_cmp[-1]:
                return "error_"+str(error_times)
            else:
                return "error_"+str(error_times+1)


# In[10]:


class Vasp_Error_Checker_Logger(Write_and_read_error_tag):
    """
    This class provides two methods:
        -write_error_log: writes down the error information into log.txt for a material and
        -write_correction_log: write the correction info into log.txt
    input arguments:
        -cal_loc: the location of the to-be-checked calculation
        -workflow: the output of func Parse_calculation_workflow.parse_calculation_workflow.
    write_error_log method:
        input arguments:
            -target_error_str (list or str): an error string or a list of error strings.
            -error_type (str): the error type that will be written into file __error__
    """
    
    def __init__(self, cal_loc, workflow):
        self.cal_loc = cal_loc
        self.workflow = workflow
        self.firework_name = os.path.split(cal_loc)[-1]
        self.log_txt = os.path.join(self.cal_loc, "log.txt")
    
    def write_error_log(self, target_error_str, error_type):
        error_type = error_type.strip()
        if isinstance(target_error_str, str):
            target_error_str_list = [target_error_str]
        elif isinstance(target_error_str, list):
            target_error_str_list = target_error_str
        else:
            raise Exception("target_error_str for Vasp_Error_Checker_Logger.write_error_log must be a string or a list of strings.")
            
        with open(self.log_txt, "a") as f:
            f.write("{} Error: {}\n".format(get_time_str(), self.firework_name))
            for error_str in target_error_str_list:
                f.write("\t\t{}\n".format(error_str))
            #decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
            #os.rename(os.path.join(self.cal_loc, "__running__"), os.path.join(self.cal_loc, "__error__"))
            f.write("\t\t\t__running__ --> __error__\n")
            f.write("\t\t\t write {} into __error__\n".format(error_type))
        super(Vasp_Error_Checker_Logger, self).write_error_tag(error_type)
    
    def write_file_absence_log(self, filename_list = [], initial_signal_file="", final_signal_file=""):
        """
        Write the log for the absence of files listed in the input filename_list and the name change from initial_signal_file 
            to final_signal_file if provided.
        input arguments:
            filename_list (list of str): a list of filenames. Default: empty list
            initial_signal_file (str): Default: ""
            final_signal_file (str): Default: ""
        Note that the log for the name change of the signal file will be written only when filename_list is not empty. 
            initial_signal_file and final_signal_file must be provided at the same time.
        """
        if filename_list:
            with open(self.log_txt, "a") as f:
                f.write("{} File Missing: {}\n".format(get_time_str(), self.firework_name))
                f.write("\t\t\tThe file(s) listed below is(are) missing.\n\t\t\t\t")
                for filename in filename_list:
                    f.write("{}\t".format(filename))
                f.write("\n")
                if initial_signal_file != "" and final_signal_file != "":
                    f.write("\t\t\tchange the signal file name:\n")
                    f.write("\t\t\t\t{} --> {}\n".format(initial_signal_file, final_signal_file))
                              
            
    def write_correction_log(self, new_incar_tags={}, remove_incar_tags=[], new_filenames={}, remove_files=[]):
        """
        write the correction log
        input arguments:
            new_incar_tags (dict): key-INCAR tags, value-corresponding values. Default: empty dictionary
            remove_incar_tags (list): a list of INCAR tags. Default: empty list
            new_filenames (dict): key-old filename, value-new filename. Default: empty dictionary
            remove_files (list): file list that will be removed
        """
        with open(self.log_txt, "a") as f:
            f.write("{} Correction: {}\n".format(get_time_str(), self.firework_name))
            if new_incar_tags:
                f.write("\t\tnew incar tags:\n")
                for tag, value in new_incar_tags.items():
                    f.write("\t\t\t{} = {}\n".format(tag, value))
            if remove_incar_tags:
                f.write("\t\tremove incar tags:\n\t\t\t")
                for tag in remove_incar_tags:
                    f.write("{}\t".format(tag))
                f.write("\n")
            if new_filenames:
                f.write("\t\trename files:\n")
                for old_name, new_name in new_filenames.items():
                    f.write("\t\t\t{} --> {}\n".format(old_name, new_name))
            if remove_files:
                f.write("t\t\tremove files below:\n")
                for file in remove_files:
                    if os.path.isfile(os.path.join(self.cal_loc, file)):
                        os.remove(os.path.join(self.cal_loc, file))
                        f.write("\t\t\t{}\n".format(file))
                    else:
                        f.write("\t\t\t{} isn't present --> no need to remove\n".format(file))


# # For all error checkers, the check method will return False if an error is found. Otherwise return True

# In[2]:


class OUTCAR_status(Vasp_Error_Checker_Logger):
    """
    Error chekcing type: after the calculation.
    If the calculation successfully completes, "General timing and accounting informations for this job:" will 
    be found at the end of OUTCAR
    inherit methods write_error_tag and read_error_tag from class Write_and_read_error__.
    input arguments:
        -cal_loc: the location of the to-be-checked calculation
        -workflow: the output of func Parse_calculation_workflow.parse_calculation_workflow.
    check method: return True, if found; return False and write error logs otherwise.
    """
    def __init__(self, cal_loc, workflow):
        self.workflow = workflow
        self.cal_loc = cal_loc
        self.firework_name = os.path.split(cal_loc)[-1]
        self.log_txt = os.path.join(self.cal_loc, "log.txt")
        self.target_str = "General timing and accounting informations for this job:"
        self.target_file = "OUTCAR"
            
    def check(self):
        """
        Return:
            - False if an error is found;
            - True otherwise.
        """
        
        #This if statement deactivates the check method until the calculation is done.
        if Queue_std_files(cal_loc=self.cal_loc, workflow=self.workflow) == [None, None]:
            return True
        
        #Since the job is done, OUTCAR must exist.
        if not os.path.isfile(os.path.join(self.cal_loc, self.target_file)):
            decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
            #os.rename(os.path.join(self.cal_loc, "__running__"), os.path.join(self.cal_loc, "__error__"))
            super(OUTCAR_status, self).write_file_absence_log(filename_list = [self.target_file], 
                                                              initial_signal_file="__running__", 
                                                              final_signal_file="__error__")
            return False
        
        if find_target_str(cal_loc=self.cal_loc, target_file=self.target_file, target_str=self.target_str) or        find_target_str(cal_loc=self.cal_loc, target_file=self.target_file, target_str="Finished calculating partial charge density."):
            return True
        else:
            decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__") 
            #This above filename change will be logged by the write_error_log below.
            self.write_error_log()
            return False
    
    def write_error_log(self):
        target_str_list = ["\t\tcannot find the critical line in OUTCAR, which indicates the job successfully finished:"]
        target_str_list.append(self.target_str)
        super(OUTCAR_status, self).write_error_log(target_error_str=target_str_list, error_type="__unfinished_OUTCAR__")
    
    def correct(self):
        return False
    


# In[9]:


class Vasp_out_pricel(Vasp_Error_Checker_Logger, Vasp_Error_Saver):
    """
    Error checking type: after the calculation.
    Target file: vasp.out or the one specified by tag vasp.out
    Target error string: "internal error in subroutine PRICEL"
    inherit methods write_error_tag and read_error_tag from class Write_and_read_error__.
    input arguments:
        -cal_loc: the location of the to-be-checked calculation
        -workflow: the output of func Parse_calculation_workflow.parse_calculation_workflow.
    check method: return True, if not found; return False and write error logs otherwise.
    """
    def __init__(self, cal_loc, workflow):
        Vasp_Error_Saver.__init__(self, cal_loc=cal_loc, workflow=workflow)
        
        self.workflow = workflow
        self.cal_loc = cal_loc
        self.firework_name = os.path.split(cal_loc)[-1]
        self.log_txt = os.path.join(self.cal_loc, "log.txt")
        self.target_file = self.workflow[0]["vasp.out"]
        self.target_str = "internal error in subroutine PRICEL"
        
        
    def check(self):
        """
        Return:
            - False if an error is found;
            - True otherwise.
        """
        
        #This method will be active only when the job is done.
        if Queue_std_files(cal_loc=self.cal_loc, workflow=self.workflow).find_std_files() == [None, None]:
            return True
        
        #Since the job is done, vasp.out must exist
        if not os.path.isfile(os.path.join(self.cal_loc, self.target_file)):
            decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
            #os.rename(os.path.join(self.cal_loc, "__running__"), os.path.join(self.cal_loc, "__error__"))
            super(Vasp_out_pricel, self).write_file_absence_log(filename_list = [self.target_file], 
                                                              initial_signal_file="__running__", 
                                                              final_signal_file="__error__")
            return False
            
        
        if find_target_str(cal_loc=self.cal_loc, target_file=self.target_file, target_str=self.target_str):
            decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
            self.write_error_log()
            return False
        else:
            return True

            
    def write_error_log(self):
        super(Vasp_out_pricel, self).write_error_log(target_error_str=self.target_str, error_type="__pricel__")
    
    def correct(self):
        """
        This correction is borrowed from custodian and modified.
        https://materialsproject.github.io/custodian/_modules/custodian/vasp/handlers.html#VaspErrorHandler.correct
        """
        incar_dict = modify_vasp_incar(cal_loc=self.cal_loc)
        SYMPREC = float(incar_dict.get("SYMPREC", 1.0e-5))
        ISYM = int(incar_dict.get("ISYM", 2))
        
        if ISYM != 0 or SYMPREC > 1.1e-9:
            super(Vasp_out_pricel, self).backup()
            #modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"SYMPREC": 1e-8, "ISYM": 0}, rename_old_incar=False)
            modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"SYMPREC": 1e-8, "ISYM": 0}, rename_old_incar=False, 
                              incar_template=self.workflow[0]["incar_template_list"], 
                              valid_incar_tags=self.workflow[0]["valid_incar_tags_list"])
            super(Vasp_out_pricel, self).write_correction_log(new_incar_tags={"SYMPREC": 1e-8, "ISYM": 0})
            return True
        else:
            return False


# In[10]:


class Vasp_out_too_few_bands(Vasp_Error_Checker_Logger, Vasp_Error_Saver):
    """
    Error checking type: on the fly.
    Target file: vasp.out or the one specified by tag vasp.out
    Target error string: "TOO FEW BANDS"
    inherit methods write_error_tag and read_error_tag from class Write_and_read_error__.
    input arguments:
        -cal_loc: the location of the to-be-checked calculation
        -workflow: the output of func Parse_calculation_workflow.parse_calculation_workflow.
    check method: return True, if not found; return False and write error logs otherwise.
    """
    def __init__(self, cal_loc, workflow):
        Vasp_Error_Saver.__init__(self, cal_loc=cal_loc, workflow=workflow)
        
        self.workflow = workflow
        self.cal_loc = cal_loc
        self.firework_name = os.path.split(cal_loc)[-1]
        self.log_txt = os.path.join(self.cal_loc, "log.txt")
        self.target_file = self.workflow[0]["vasp.out"]
        self.target_str = "TOO FEW BANDS"
        
        
    def check(self):
        """
        Return:
            - False if an error is found;
            - True otherwise.
        """
        if not os.path.isfile(os.path.join(self.cal_loc, self.workflow[0]["vasp.out"])):
            return True
                
        if find_target_str(cal_loc=self.cal_loc, target_file=self.target_file, target_str=self.target_str):
            decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
            self.write_error_log()
            return False
        else:
            return True
    
    
    def write_error_log(self):
        super(Vasp_out_too_few_bands, self).write_error_log(target_error_str=self.target_str, error_type="__too_few_bands__")
    
    def correct(self):
        """
        This correction is borrowed from custodian and modified.
        https://materialsproject.github.io/custodian/_modules/custodian/vasp/handlers.html#VaspErrorHandler.correct
        """
        if not os.path.isfile(os.path.join(self.cal_loc, "OUTCAR")):
            open(os.path.join(self.cal_loc, "__cannot_find_OUTCAR_for_correction__"), "w").close()
            super(Vasp_out_too_few_bands, self).write_file_absence_log(filename_list = ["OUTCAR"])
            return False
        
        NBANDS = find_incar_tag_from_OUTCAR(cal_loc=self.cal_loc, tag="NBANDS")
        NBANDS_ = int(NBANDS*1.1)
        if NBANDS_ == NBANDS:
            NBANDS_ += 1
        
        super(Vasp_out_too_few_bands, self).backup()
        #modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"NBANDS": NBANDS_}, rename_old_incar=False)
        modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"NBANDS": NBANDS_}, rename_old_incar=False, 
                          incar_template=self.workflow[0]["incar_template_list"], 
                          valid_incar_tags=self.workflow[0]["valid_incar_tags_list"])
        super(Vasp_out_too_few_bands, self).write_correction_log(new_incar_tags={"NBANDS": NBANDS_})
        return True


# In[11]:


class Vasp_out_too_few_kpoints(Vasp_Error_Checker_Logger, Vasp_Error_Saver):
    """
    Error checking type: after the calculation.
    Target file: vasp.out or the one specified by tag vasp.out
    Target error string: "Tetrahedron method fails for NKPT<4."
    inherit methods write_error_tag and read_error_tag from class Write_and_read_error__.
    input arguments:
        -cal_loc: the location of the to-be-checked calculation
        -workflow: the output of func Parse_calculation_workflow.parse_calculation_workflow.
    check method: return True, if not found; return False and write error logs otherwise.
    """
    def __init__(self, cal_loc, workflow):
        Vasp_Error_Saver.__init__(self, cal_loc=cal_loc, workflow=workflow)
        
        self.workflow = workflow
        self.cal_loc = cal_loc
        self.firework_name = os.path.split(cal_loc)[-1]
        self.log_txt = os.path.join(self.cal_loc, "log.txt")
        self.target_file = self.workflow[0]["vasp.out"]
        self.target_str = "Tetrahedron method fails for NKPT<4."
        
        
    def check(self):
        """
        Return:
            - False if an error is found;
            - True otherwise.
        """        
        #This method will be active only when the job is done.
        if Queue_std_files(cal_loc=self.cal_loc, workflow=self.workflow).find_std_files() == [None, None]:
            return True
        
        #Since the job is done, vasp.out must exist
        if not os.path.isfile(os.path.join(self.cal_loc, self.target_file)):
            decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
            #os.rename(os.path.join(self.cal_loc, "__running__"), os.path.join(self.cal_loc, "__error__"))
            super(Vasp_out_too_few_kpoints, self).write_file_absence_log(filename_list = [self.target_file], 
                                                                         initial_signal_file="__running__", 
                                                                         final_signal_file="__error__")
            return False
                
        if find_target_str(cal_loc=self.cal_loc, target_file=self.target_file, target_str=self.target_str):
            decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
            self.write_error_log()
            return False
        else:
            return True
    
            
    def write_error_log(self):
        super(Vasp_out_too_few_kpoints, self).write_error_log(target_error_str=self.target_str, error_type="__too_few_kpoints__")
    
    def correct(self):
        incar_dict = modify_vasp_incar(cal_loc=self.cal_loc)
        ISMEAR = int(incar_dict.get("ISMEAR", 1))
        SIGMA = float(incar_dict.get("SIGMA", 0.2))
        
        if ISMEAR == -5:     
            super(Vasp_out_too_few_kpoints, self).backup()
            #modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"ISMEAR": 0, "SIGMA":0.05}, rename_old_incar=False)
            modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"ISMEAR": 0, "SIGMA":0.05}, rename_old_incar=False, 
                              incar_template=self.workflow[0]["incar_template_list"], 
                              valid_incar_tags=self.workflow[0]["valid_incar_tags_list"])
            super(Vasp_out_too_few_kpoints, self).write_correction_log(new_incar_tags={"ISMEAR": 0, "SIGMA":0.05})
            return True
        else:
            return False


# In[12]:


class Vasp_out_posmap(Vasp_Error_Checker_Logger, Vasp_Error_Saver):
    """
    Error checking type: after the calculation.
    Target file: vasp.out or the one specified by tag vasp.out
    Target error string: "POSMAP internal error: symmetry equivalent atom not found"
    inherit methods write_error_tag and read_error_tag from class Write_and_read_error__.
    input arguments:
        -cal_loc: the location of the to-be-checked calculation
        -workflow: the output of func Parse_calculation_workflow.parse_calculation_workflow.
    check method: return True, if not found; return False and write error logs otherwise.
    """
    def __init__(self, cal_loc, workflow):
        Vasp_Error_Saver.__init__(self, cal_loc=cal_loc, workflow=workflow)
        
        self.workflow = workflow
        self.cal_loc = cal_loc
        self.firework_name = os.path.split(cal_loc)[-1]
        self.log_txt = os.path.join(self.cal_loc, "log.txt")
        self.target_file = self.workflow[0]["vasp.out"]
        #super(Vasp_out_posmap, self).__init__(cal_loc, workflow)
        self.target_str = "POSMAP internal error: symmetry equivalent atom not found"
        
        
        
    def check(self):
        """
        Return:
            - False if an error is found;
            - True otherwise.
        """        
        #This method is deactive until the job is done
        if Queue_std_files(cal_loc=self.cal_loc, workflow=self.workflow).find_std_files() == [None, None]:
            return True
        
        #Since the job is done, vasp.out must exist
        if not os.path.isfile(os.path.join(self.cal_loc, self.target_file)):
            decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
            #os.rename(os.path.join(self.cal_loc, "__running__"), os.path.join(self.cal_loc, "__error__"))
            super(Vasp_out_posmaps, self).write_file_absence_log(filename_list = [self.target_file], 
                                                                 initial_signal_file="__running__", 
                                                                 final_signal_file="__error__")
            return False
        
        if find_target_str(cal_loc=self.cal_loc, target_file=self.target_file, target_str=self.target_str):
            decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
            self.write_error_log()
            return False
        else:
            return True
    
            
    def write_error_log(self):
        super(Vasp_out_posmap, self).write_error_log(target_error_str=self.target_str, error_type="__posmap__")
    
    def correct(self):
        """
        This correction is borrowed from custodian and modified.
        https://materialsproject.github.io/custodian/_modules/custodian/vasp/handlers.html#VaspErrorHandler.correct
        """
        incar_dict = modify_vasp_incar(cal_loc=self.cal_loc)
        SYMPREC = float(incar_dict.get("SYMPREC", 1.0e-5))
        
        if SYMPREC > 1e-7:
            super(Vasp_out_posmap, self).backup()
            #modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"SYMPREC": SYMPREC/10.}, rename_old_incar=False)
            modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"SYMPREC": SYMPREC/10.}, rename_old_incar=False, 
                              incar_template=self.workflow[0]["incar_template_list"], 
                              valid_incar_tags=self.workflow[0]["valid_incar_tags_list"])
            super(Vasp_out_posmap, self).write_correction_log(new_incar_tags={"SYMPREC": SYMPREC/10.})
            return True
        else:
            return False
        


# In[12]:


class Vasp_out_real_optlay(Vasp_Error_Checker_Logger, Vasp_Error_Saver):
    """
    Error checking type: after the calculation.
    Target file: vasp.out or the one specified by tag vasp.out
    Target error string: "REAL_OPTLAY: internal error (1)"
    inherit methods write_error_tag and read_error_tag from class Write_and_read_error__.
    input arguments:
        -cal_loc: the location of the to-be-checked calculation
        -workflow: the output of func Parse_calculation_workflow.parse_calculation_workflow.
    check method: return True, if not found; return False and write error logs otherwise.
    """
    def __init__(self, cal_loc, workflow):
        Vasp_Error_Saver.__init__(self, cal_loc=cal_loc, workflow=workflow)
        
        self.workflow = workflow
        self.cal_loc = cal_loc
        self.firework_name = os.path.split(cal_loc)[-1]
        self.log_txt = os.path.join(self.cal_loc, "log.txt")
        self.target_file = self.workflow[0]["vasp.out"]
        #super(Vasp_out_posmap, self).__init__(cal_loc, workflow)
        self.target_str = "REAL_OPTLAY: internal error (1)"
        
    def check(self):
        """
        Return:
            - False if an error is found;
            - True otherwise.
        """        
        #This method is deactive until the job is done
        if Queue_std_files(cal_loc=self.cal_loc, workflow=self.workflow).find_std_files() == [None, None]:
            return True
        
        #Since the job is done, vasp.out must exist
        if not os.path.isfile(os.path.join(self.cal_loc, self.target_file)):
            decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
            #os.rename(os.path.join(self.cal_loc, "__running__"), os.path.join(self.cal_loc, "__error__"))
            super(Vasp_out_real_optlay, self).write_file_absence_log(filename_list = [self.target_file], 
                                                                     initial_signal_file="__running__", 
                                                                     final_signal_file="__error__")
            return False
        
        if find_target_str(cal_loc=self.cal_loc, target_file=self.target_file, target_str=self.target_str):
            decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
            self.write_error_log()
            return False
        else:
            return True
    
            
    def write_error_log(self):
        super(Vasp_out_real_optlay, self).write_error_log(target_error_str=self.target_str, error_type="__real_optlay__")
        
    def correct(self):
        incar_dict = modify_vasp_incar(cal_loc=self.cal_loc)
        
        lreal = incar_dict.get("LREAL", ".FALSE.").lower()
        if "f" in lreal:
            return False
        else:
            super(Vasp_out_real_optlay, self).backup()
            modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"LREAL": " .FALSE."}, rename_old_incar=False, 
                              incar_template=self.workflow[0]["incar_template_list"], 
                              valid_incar_tags=self.workflow[0]["valid_incar_tags_list"])
            super(Vasp_out_real_optlay, self).write_correction_log(new_incar_tags={"LREAL": ".FALSE."})
            return True
    
    def correct_(self): #This correction seems to be unable to resolve the problem.
        """
        This correction is borrowed from the vasp forum:
        https://www.vasp.at/forum/viewtopic.php?f=4&t=5354
        combine them such that the element with the hightest ENMAX is the first one (please don't forget that you will also have to re-arrange POSCAR!)
        """
        potcar = Potcar(filename="POTCAR", cal_loc=self.cal_loc)
        old_atomic_species = potcar.get_atomic_species()
        enmax_enmin_dict = potcar.get_enmax_enmin()
        newly_ordered_atomic_species = sorted(enmax_enmin_dict.keys(), key=lambda species: float(enmax_enmin_dict[species]["ENMAX"]), reverse=True)
        
        if old_atomic_species == newly_ordered_atomic_species:
            return False
        else:
            super(Vasp_out_real_optlay, self).backup()
            old_struct = Structure.from_file(os.path.join(self.cal_loc, "POSCAR")).get_sorted_structure()
            poscar_dict = sort_poscar(by="atomic_species", key=lambda species: float(enmax_enmin_dict[species[1]]["ENMAX"]), reverse=True, 
                                      poscar_filename="POSCAR", cal_loc=self.cal_loc)
            write_poscar(poscar_dict=poscar_dict, filename="POSCAR", cal_loc=self.cal_loc)
            new_struct = Structure.from_file(os.path.join(self.cal_loc, "POSCAR")).get_sorted_structure()
            
            if old_struct.species != new_struct.species:
                with open(self.log_txt, "a") as log_f:
                    log_f.write("{} Debug: The old and new sorted POSCAR have different atomic species list.".format(get_time_str()))
                return False
            if np.max(np.abs(old_struct.frac_coords - new_struct.frac_coords)) > 1.0E-5:
                with open(self.log_txt, "a") as log_f:
                    log_f.write("{} Debug: The old and new sorted POSCAR have fractional coordinate difference > 1.0e-5.".format(get_time_str()))
                return False
            
            potcar.sort_and_write_potcar(new_atomic_species_sequence=newly_ordered_atomic_species, filename="POTCAR", cal_loc=self.cal_loc)
            
            with open(self.log_txt, "a") as log_f:
                log_f.write("{} Correction: {}\n".format(get_time_str(), self.firework_name))
                log_f.write("\t\t\tSort POSCAR and POTCAR in such a way that the atomic species are arranged in a descending order of ENMAX\n")
                
            return True


# In[13]:


class Vasp_out_bad_termination(Vasp_Error_Checker_Logger):
    """
    Error checking type: after the calculation.
    Target file: vasp.out or the one specified by tag vasp.out
    Target error string: "=   BAD TERMINATION OF ONE OF YOUR APPLICATION PROCESSES"
    inherit methods write_error_tag and read_error_tag from class Write_and_read_error__.
    input arguments:
        -cal_loc: the location of the to-be-checked calculation
        -workflow: the output of func Parse_calculation_workflow.parse_calculation_workflow.
    check method: return True, if not found; return False and write error logs otherwise.
    """
    def __init__(self, cal_loc, workflow):
        self.workflow = workflow
        self.cal_loc = cal_loc
        self.firework_name = os.path.split(cal_loc)[-1]
        self.log_txt = os.path.join(self.cal_loc, "log.txt")
        self.target_file = self.workflow[0]["vasp.out"]
        self.target_str = "=   BAD TERMINATION OF ONE OF YOUR APPLICATION PROCESSES"
        
        
        
    def check(self):
        """
        Return:
            - False if an error is found;
            - True otherwise.
        """        
        #this method is not active until the job is done
        if Queue_std_files(cal_loc=self.cal_loc, workflow=self.workflow).find_std_files() == [None, None]:
            return True
        
        #Since the job is done, vasp.out must exist
        if not os.path.isfile(os.path.join(self.cal_loc, self.target_file)):
            decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
            #os.rename(os.path.join(self.cal_loc, "__running__"), os.path.join(self.cal_loc, "__error__"))
            super(Vasp_out_bad_termination, self).write_file_absence_log(filename_list = [self.target_file], 
                                                                         initial_signal_file="__running__", 
                                                                         final_signal_file="__error__")
            return False
        
        if find_target_str(cal_loc=self.cal_loc, target_file=self.target_file, target_str=self.target_str):
            decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
            self.write_error_log()
            return False
        else:
            return True
            
            
    def write_error_log(self):
        super(Vasp_out_bad_termination, self).write_error_log(target_error_str=self.target_str, error_type="__bad_termination__")
    
    def correct(self):
        if os.path.isfile(os.path.join(self.cal_loc, "__bad_termination__")):
            with open(self.log_txt, "a") as f:
                f.write("{} Correction: {}\n".format(get_time_str(), self.firework_name))
                f.write("\t\t\t{}\n".format(self.target_str))
                f.write("\t\t\tfile __bad_termination__ is detected in this folder\n")
                f.write("\t\t\tThis is the second time to encounter such error\n")
            return False
        else:
            open(os.path.join(self.cal_loc, "__bad_termination__"), "w").close()
            Queue_std_files(cal_loc=self.cal_loc, workflow=self.workflow).remove_std_files()
            with open(self.log_txt, "a") as f:
                f.write("{} Correction: {}\n".format(get_time_str(), self.firework_name))
                f.write("\t\t\t{}\n".format(self.target_str))
                f.write("\t\t\tThis is the first time to encounter such error --> Input set remains unchanged.\n")
                f.write("\t\t\tremove queue stdout and stderr.\n")
                f.write("\t\t\tcreate file __bad_termination__\n")
            return True


# In[14]:


class Vasp_out_invgrp(Vasp_Error_Checker_Logger, Vasp_Error_Saver):
    """
    Error checking type: after the calculation.
    Target file: vasp.out or the one specified by tag vasp.out
    Target error string: "VERY BAD NEWS! internal error in subroutine INVGRP:" 
                        && "inverse of rotation matrix was not found (increase SYMPREC)"
    inherit methods write_error_tag and read_error_tag from class Write_and_read_error__.
    input arguments:
        -cal_loc: the location of the to-be-checked calculation
        -workflow: the output of func Parse_calculation_workflow.parse_calculation_workflow.
    check method: return True, if not found; return False and write error logs otherwise.
    correct method: if SYMPREC*5 < 0.9e-4, SYMPREC = SYMPREC*5 and return True; Otherwise return False
    """
    def __init__(self, cal_loc, workflow):
        Vasp_Error_Saver.__init__(self, cal_loc=cal_loc, workflow=workflow)
        
        self.workflow = workflow
        self.cal_loc = cal_loc
        self.firework_name = os.path.split(cal_loc)[-1]
        self.log_txt = os.path.join(self.cal_loc, "log.txt")
        self.target_file = self.workflow[0]["vasp.out"]
        self.target_str_list = [" VERY BAD NEWS! internal error in subroutine INVGRP:", 
                                "inverse of rotation matrix was not found (increase SYMPREC)"]
        
        
    def check(self):
        """
        Return:
            - False if an error is found;
            - True otherwise.
        """        
        #this method is not active until the job is done
        if Queue_std_files(cal_loc=self.cal_loc, workflow=self.workflow).find_std_files() == [None, None]:
            return True
        
        #Since the job is done, vasp.out must exist
        if not os.path.isfile(os.path.join(self.cal_loc, self.target_file)):
            decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
            #os.rename(os.path.join(self.cal_loc, "__running__"), os.path.join(self.cal_loc, "__error__"))
            super(Vasp_out_invgrp, self).write_file_absence_log(filename_list = [self.target_file], 
                                                                initial_signal_file="__running__", 
                                                                final_signal_file="__error__")
            return False
        
        no_error_list = []
        for target_str in self.target_str_list:
            no_error_list.append(find_target_str(cal_loc=self.cal_loc, target_file=self.target_file, target_str=target_str))
            
        if False in no_error_list:
            return True
        else:
            decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
            self.write_error_log()
            return False

    
            
    def write_error_log(self):
        super(Vasp_out_invgrp, self).write_error_log(target_error_str=self.target_str_list, error_type="__invgrp__")
    
    def correct(self):
        """
        This correction is borrowed from custodian and modified.
        https://materialsproject.github.io/custodian/_modules/custodian/vasp/handlers.html#VaspErrorHandler.correct
        """
        incar_dict = modify_vasp_incar(cal_loc=self.cal_loc)
        SYMPREC = float(incar_dict.get("SYMPREC", 1.0e-5))
        SYMPREC_ = SYMPREC * 5
        
        if SYMPREC_ < 0.9e-4:
            super(Vasp_out_invgrp, self).backup()
            #modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"SYMPREC": SYMPREC_}, rename_old_incar=False)
            modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"SYMPREC": SYMPREC_}, rename_old_incar=False, 
                              incar_template=self.workflow[0]["incar_template_list"], 
                              valid_incar_tags=self.workflow[0]["valid_incar_tags_list"])
            super(Vasp_out_invgrp, self).write_correction_log(new_incar_tags={"SYMPREC": SYMPREC_})
            return True
        else:
            with open(self.log_txt, "a") as f:
                f.write("{} Correction: {}\n".format(get_time_str(), self.firework_name))
                f.write("\t\t\tSYMPREC={} is already too big.\n".format(SYMPREC))
            return False
                        


# In[15]:


class Vasp_out_zbrent(Vasp_Error_Checker_Logger, Vasp_Error_Saver):
    """
    Error checking type: after the calculation.
    Target file: vasp.out or the one specified by tag vasp.out
    Target error string: "ZBRENT: fatal error in bracketing" && "please rerun with smaller EDIFF, or copy CONTCAR"
                        && "to POSCAR and continue"
    inherit methods write_error_tag and read_error_tag from class Write_and_read_error__.
    input arguments:
        -cal_loc: the location of the to-be-checked calculation
        -workflow: the output of func Parse_calculation_workflow.parse_calculation_workflow.
    check method: return True, if not found; return False and write error logs otherwise.
    correct method: IBRION --> 1 & EDIFF --> 0.5*EDIFF & CONTCAR --> POSCAR
    """
    def __init__(self, cal_loc, workflow):
        Vasp_Error_Saver.__init__(self, cal_loc=cal_loc, workflow=workflow)
        
        self.workflow = workflow
        self.cal_loc = cal_loc
        self.firework_name = os.path.split(cal_loc)[-1]
        self.log_txt = os.path.join(self.cal_loc, "log.txt")
        self.target_file = self.workflow[0]["vasp.out"]
        self.target_str_list = ["ZBRENT: fatal error in bracketing", 
                                "please rerun with smaller EDIFF, or copy CONTCAR", 
                                "to POSCAR and continue"]
        
        
    def check(self):
        """
        Return:
            - False if an error is found;
            - True otherwise.
        """        
        #this method is not active until the job is done
        if Queue_std_files(cal_loc=self.cal_loc, workflow=self.workflow).find_std_files() == [None, None]:
            return True
        
        #Since the job is done, vasp.out must exist
        if not os.path.isfile(os.path.join(self.cal_loc, self.target_file)):
            decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
            #os.rename(os.path.join(self.cal_loc, "__running__"), os.path.join(self.cal_loc, "__error__"))
            super(Vasp_out_zbrent, self).write_file_absence_log(filename_list = [self.target_file], 
                                                                initial_signal_file="__running__", 
                                                                final_signal_file="__error__")
            return False
        
        no_error_list = []
        for target_str in self.target_str_list:
            no_error_list.append(find_target_str(cal_loc=self.cal_loc, target_file=self.target_file, target_str=target_str))
            
        if False in no_error_list:
            return True
        else:
            decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
            self.write_error_log()
            return False
    
            
    def write_error_log(self):
        super(Vasp_out_zbrent, self).write_error_log(target_error_str=self.target_str_list, error_type="__zbrent__")
    
    def correct(self):
        """
        This correction is borrowed from custodian and modified.
        https://materialsproject.github.io/custodian/_modules/custodian/vasp/handlers.html#VaspErrorHandler.correct
        """
        if not os.path.isfile(os.path.join(self.cal_loc, "OUTCAR")):
            open(os.path.join(self.cal_loc, "__cannot_find_OUTCAR_for_corrections__"), "w").close()
            super(Vasp_out_zbrent, self).write_file_absence_log(filename_list = ["OUTCAR"])
            return False
                
        EDIFF = find_incar_tag_from_OUTCAR(tag="EDIFF", cal_loc=self.cal_loc)
        IBRION = find_incar_tag_from_OUTCAR(tag="IBRION", cal_loc=self.cal_loc)
        
        super(Vasp_out_zbrent, self).backup()
        new_tags = {}
        if EDIFF * 0.5 >= 1.0e-6:
            new_tags["EDIFF"] = EDIFF * 0.5
        if IBRION != 1:
            new_tags["IBRION"] = 1
        
        #modify_vasp_incar(cal_loc=self.cal_loc, new_tags=new_tags, rename_old_incar=False)
        modify_vasp_incar(cal_loc=self.cal_loc, new_tags=new_tags, rename_old_incar=False, 
                          incar_template=self.workflow[0]["incar_template_list"], 
                          valid_incar_tags=self.workflow[0]["valid_incar_tags_list"])
        
        shutil.copyfile(os.path.join(self.cal_loc, "CONTCAR"), os.path.join(self.cal_loc, "POSCAR"))
        
        super(Vasp_out_zbrent, self).write_correction_log(new_incar_tags=new_tags, new_filenames={"CONTCAR": "POSCAR"})

        return True
                        


# In[15]:


class Vasp_out_pead(Vasp_Error_Checker_Logger, Vasp_Error_Saver):
    """
    Error checking type: after the calculation.
    Target file: vasp.out or the one specified by tag vasp.out
    Target error string: "Your generating k-point grid is not commensurate to the symmetry" 
                        && "of the lattice.  This does not sit well in combination with the"
                        && "PEAD routines, sorry ..."
    inherit methods write_error_tag and read_error_tag from class Write_and_read_error__.
    input arguments:
        -cal_loc: the location of the to-be-checked calculation
        -workflow: the output of func Parse_calculation_workflow.parse_calculation_workflow.
    check method: return True, if not found; return False and write error logs otherwise.
    correct method: remove INCAR tag LPEAD
    """
    def __init__(self, cal_loc, workflow):
        Vasp_Error_Saver.__init__(self, cal_loc=cal_loc, workflow=workflow)
        
        self.workflow = workflow
        self.cal_loc = cal_loc
        self.firework_name = os.path.split(cal_loc)[-1]
        self.log_txt = os.path.join(self.cal_loc, "log.txt")
        self.target_file = self.workflow[0]["vasp.out"]
        self.target_str_list = ["Your generating k-point grid is not commensurate to the symmetry", 
                                "of the lattice.  This does not sit well in combination with the", 
                                "PEAD routines, sorry ..."]
        
        
    def check(self):
        """
        Return:
            - False if an error is found;
            - True otherwise.
        """        
        #this method is not active until the job is done
        if Queue_std_files(cal_loc=self.cal_loc, workflow=self.workflow).find_std_files() == [None, None]:
            return True
        
        #Since the job is done, vasp.out must exist
        if not os.path.isfile(os.path.join(self.cal_loc, self.target_file)):
            decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
            super(Vasp_out_pead, self).write_file_absence_log(filename_list = [self.target_file], 
                                                                initial_signal_file="__running__", 
                                                                final_signal_file="__error__")
            return False
        
        no_error_list = []
        for target_str in self.target_str_list:
            no_error_list.append(find_target_str(cal_loc=self.cal_loc, target_file=self.target_file, target_str=target_str))
            
        if False in no_error_list:
            return True
        else:
            decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
            self.write_error_log()
            return False
    
            
    def write_error_log(self):
        super(Vasp_out_pead, self).write_error_log(target_error_str=self.target_str_list, error_type="__pead__")
    
    def correct(self):
        if not os.path.isfile(os.path.join(self.cal_loc, "OUTCAR")):
            open(os.path.join(self.cal_loc, "__cannot_find_OUTCAR_for_corrections__"), "w").close()
            super(Vasp_out_pead, self).write_file_absence_log(filename_list = ["OUTCAR"])
            return False
                
        LPEAD = find_incar_tag_from_OUTCAR(tag="LPEAD", cal_loc=self.cal_loc)
        if LPEAD == False: #This error seems to be incured only when LPEAD is set to True.
            return False
        
        super(Vasp_out_pead, self).backup()
        
        #modify_vasp_incar(cal_loc=self.cal_loc, new_tags=new_tags, rename_old_incar=False)
        modify_vasp_incar(cal_loc=self.cal_loc, remove_tags=["LPEAD"], rename_old_incar=False, 
                          incar_template=self.workflow[0]["incar_template_list"], 
                          valid_incar_tags=self.workflow[0]["valid_incar_tags_list"])
        
        
        super(Vasp_out_pead, self).write_correction_log(remove_incar_tags=["LPEAD"])

        return True
                        


# In[16]:


class Vasp_out_rhosyg(Vasp_Error_Checker_Logger, Vasp_Error_Saver):
    """
    Error checking type: after the calculation.
    Target file: vasp.out or the one specified by tag vasp.out
    Target error string: "RHOSYG internal error: stars are not distinct, try to increase SYMPREC to e.g."
    inherit methods write_error_tag and read_error_tag from class Write_and_read_error__.
    input arguments:
        -cal_loc: the location of the to-be-checked calculation
        -workflow: the output of func Parse_calculation_workflow.parse_calculation_workflow.
    check method: return True, if not found; return False and write error logs otherwise.
    correct method: if SYMPREC < 1.0E-4, SYMPREC --> 1.0E-4 & return True;
                    elif SYMPREC >= 1.0e-4 and ISYM != 0, ISYM --> 0 & return True;
                    else: return False
    """
    def __init__(self, cal_loc, workflow):
        Vasp_Error_Saver.__init__(self, cal_loc=cal_loc, workflow=workflow)
        
        self.workflow = workflow
        self.cal_loc = cal_loc
        self.firework_name = os.path.split(cal_loc)[-1]
        self.log_txt = os.path.join(self.cal_loc, "log.txt")
        self.target_file = self.workflow[0]["vasp.out"]
        self.target_str = "RHOSYG internal error: stars are not distinct, try to increase SYMPREC to e.g."
        
        
        
    def check(self):
        """
        Return:
            - False if an error is found;
            - True otherwise.
        """        
        #this method is not active until the job is done
        if Queue_std_files(cal_loc=self.cal_loc, workflow=self.workflow).find_std_files() == [None, None]:
            return True
        
        #Since the job is done, vasp.out must exist
        if not os.path.isfile(os.path.join(self.cal_loc, self.target_file)):
            decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
            #os.rename(os.path.join(self.cal_loc, "__running__"), os.path.join(self.cal_loc, "__error__"))
            super(Vasp_out_rhosyg, self).write_file_absence_log(filename_list = [self.target_file], 
                                                                initial_signal_file="__running__", 
                                                                final_signal_file="__error__")
            return False
        
        if find_target_str(cal_loc=self.cal_loc, target_file=self.target_file, target_str=self.target_str):
            decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
            self.write_error_log()
            return False
        else:
            return True
            
            
    def write_error_log(self):
        super(Vasp_out_rhosyg, self).write_error_log(target_error_str=self.target_str, error_type="__rhosyg__")
    
    def correct(self):
        """
        This correction is borrowed from custodian and modified.
        https://materialsproject.github.io/custodian/_modules/custodian/vasp/handlers.html#VaspErrorHandler.correct
        """
        incar_dict = modify_vasp_incar(cal_loc=self.cal_loc)
        SYMPREC = float(incar_dict.get("SYMPREC", 1.0e-5))
        ISYM = int(incar_dict.get("ISYM", 2))
        
        if 1.0e-4 > SYMPREC:
            super(Vasp_out_rhosyg, self).backup()
            #modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"SYMPREC": 1.0e-4}, rename_old_incar=False)
            modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"SYMPREC": 1.0e-4}, rename_old_incar=False, 
                              incar_template=self.workflow[0]["incar_template_list"], 
                              valid_incar_tags=self.workflow[0]["valid_incar_tags_list"])
            super(Vasp_out_rhosyg, self).write_correction_log(new_incar_tags={"SYMPREC": 1.0e-4})
            return True
        elif ISYM != 0:
            super(Vasp_out_rhosyg, self).backup()
            #modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"ISYM": 0}, rename_old_incar=False)
            modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"ISYM": 0}, rename_old_incar=False, 
                              incar_template=self.workflow[0]["incar_template_list"], 
                              valid_incar_tags=self.workflow[0]["valid_incar_tags_list"])
            super(Vasp_out_rhosyg, self).write_correction_log(new_incar_tags={"ISYM": 0})
            return True
        else:
            return False                        


# In[17]:


class Vasp_out_zpotrf(Vasp_Error_Checker_Logger, Vasp_Error_Saver):
    """
    Error checking type: after the calculation.
    Target file: vasp.out or the one specified by tag vasp.out
    Target error string: "LAPACK: Routine ZPOTRF failed"
    inherit methods write_error_tag and read_error_tag from class Write_and_read_error__.
    input arguments:
        -cal_loc: the location of the to-be-checked calculation
        -workflow: the output of func Parse_calculation_workflow.parse_calculation_workflow.
    check method: return True, if not found; return False and write error logs otherwise.
    correct method: decrease POTIM and switch off symmetry. The lower bound for POTIM is 0.05
    """
    def __init__(self, cal_loc, workflow):
        Vasp_Error_Saver.__init__(self, cal_loc=cal_loc, workflow=workflow)
        
        self.workflow = workflow
        self.cal_loc = cal_loc
        self.firework_name = os.path.split(cal_loc)[-1]
        self.log_txt = os.path.join(self.cal_loc, "log.txt")
        self.target_file = self.workflow[0]["vasp.out"]
        self.target_str = "LAPACK: Routine ZPOTRF failed"
        
        
    def check(self):
        """
        Return:
            - False if an error is found;
            - True otherwise.
        """        
        #this method is not active until the job is done
        if Queue_std_files(cal_loc=self.cal_loc, workflow=self.workflow).find_std_files() == [None, None]:
            return True
        
        #Since the job is done, vasp.out must exist
        if not os.path.isfile(os.path.join(self.cal_loc, self.target_file)):
            decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
            #os.rename(os.path.join(self.cal_loc, "__running__"), os.path.join(self.cal_loc, "__error__"))
            super(Vasp_out_zpotrf, self).write_file_absence_log(filename_list = [self.target_file], 
                                                                initial_signal_file="__running__", 
                                                                final_signal_file="__error__")
            return False
        
        if find_target_str(cal_loc=self.cal_loc, target_file=self.target_file, target_str=self.target_str):
            decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
            self.write_error_log()
            return False
        else:
            return True
            
            
    def write_error_log(self):
        super(Vasp_out_zpotrf, self).write_error_log(target_error_str=self.target_str, error_type="__zpotrf__")
    
    def correct(self):
        """
        This correction is borrowed from custodian and modified.
        https://materialsproject.github.io/custodian/_modules/custodian/vasp/handlers.html#VaspErrorHandler.correct
        """
        if not os.path.isfile(os.path.join(self.cal_loc, "OUTCAR")):
            open(os.path.join(self.cal_loc, "__cannot_find_OUTCAR_for_corrections__"), "w").close()
            super(Vasp_out_zpotrf, self).write_file_absence_log(filename_list = ["OUTCAR"])
            return False
        
        if not os.path.isfile(os.path.join(self.cal_loc, "OSZICAR")):
            open(os.path.join(self.cal_loc, "__cannot_find_OSZICAR_for_corrections__"), "w").close()
            super(Vasp_out_zpotrf, self).write_file_absence_log(filename_list = ["OSZICAR"])
            return False
        
        incar_dict = modify_vasp_incar(cal_loc=self.cal_loc)
        ISYM = int(incar_dict.get("ISYM", 2))
        POTIM = float(incar_dict.get("POTIM", 0.5))
        ICHARG = find_incar_tag_from_OUTCAR(tag="ICHARG", cal_loc=self.cal_loc)
        NSW = find_incar_tag_from_OUTCAR(tag="NSW", cal_loc=self.cal_loc)
        IBRION = find_incar_tag_from_OUTCAR(tag="IBRION", cal_loc=self.cal_loc)
        
        new_tags = {}
        if ISYM != 0:
            new_tags["ISYM"] = 0
        
        if NSW != 0 and IBRION != -1:
            if POTIM*0.5 >= 0.05:
                new_tags["POTIM"] = POTIM * 0.5
                
        if new_tags == {}:
            return False
        else:
            delete_files = []
            if ICHARG < 10:
                for file_ in ["WAVECAR", "CHGCAR", "CHG"]:
                    if os.path.isfile(os.path.join(self.cal_loc, file_)):
                        os.remove(os.path.join(self.cal_loc, file_))
                        delete_files.append(file_)
            super(Vasp_out_zpotrf, self).backup()
            #modify_vasp_incar(cal_loc=self.cal_loc, new_tags=new_tags, rename_old_incar=False)
            modify_vasp_incar(cal_loc=self.cal_loc, new_tags=new_tags, rename_old_incar=False, 
                              incar_template=self.workflow[0]["incar_template_list"], 
                              valid_incar_tags=self.workflow[0]["valid_incar_tags_list"])
            super(Vasp_out_zpotrf, self).write_correction_log(new_incar_tags=new_tags, remove_files=delete_files)
            return True
                            


# In[18]:


class Vasp_out_edddav(Vasp_Error_Checker_Logger, Vasp_Error_Saver):
    """
    Error checking type: after the calculation.
    Target file: vasp.out or the one specified by tag vasp.out
    Target error string: "Error EDDDAV: Call to ZHEGV failed"
    inherit methods write_error_tag and read_error_tag from class Write_and_read_error__.
    input arguments:
        -cal_loc: the location of the to-be-checked calculation
        -workflow: the output of func Parse_calculation_workflow.parse_calculation_workflow.
    check method: return True, if not found; return False and write error logs otherwise.
    correct method: if ICHARG < 10, remove CHGCAR; 
                    if ALGO != All, set it to All and return True;
                    if ALGO == All, return False
    """
    def __init__(self, cal_loc, workflow):
        Vasp_Error_Saver.__init__(self, cal_loc=cal_loc, workflow=workflow)
        
        self.workflow = workflow
        self.cal_loc = cal_loc
        self.firework_name = os.path.split(cal_loc)[-1]
        self.log_txt = os.path.join(self.cal_loc, "log.txt")
        self.target_file = self.workflow[0]["vasp.out"]
        self.target_str = "Error EDDDAV: Call to ZHEGV failed"
        
        
    def check(self):
        """
        Return:
            - False if an error is found;
            - True otherwise.
        """        
        #this method is not active until the job is done
        if Queue_std_files(cal_loc=self.cal_loc, workflow=self.workflow).find_std_files() == [None, None]:
            return True
        
        #Since the job is done, vasp.out must exist
        if not os.path.isfile(os.path.join(self.cal_loc, self.target_file)):
            decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
            #os.rename(os.path.join(self.cal_loc, "__running__"), os.path.join(self.cal_loc, "__error__"))
            super(Vasp_out_edddav, self).write_file_absence_log(filename_list = [self.target_file], 
                                                                initial_signal_file="__running__", 
                                                                final_signal_file="__error__")
            return False
        
        if find_target_str(cal_loc=self.cal_loc, target_file=self.target_file, target_str=self.target_str):
            decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
            self.write_error_log()
            return False
        else:
            return True
            
            
    def write_error_log(self):
        super(Vasp_out_edddav, self).write_error_log(target_error_str=self.target_str, error_type="__edddav__")
    
    
    def correct(self):
        """
        This correction is borrowed from custodian and modified.
        https://materialsproject.github.io/custodian/_modules/custodian/vasp/handlers.html#VaspErrorHandler.correct
        """
        if not os.path.isfile(os.path.join(self.cal_loc, "OUTCAR")):
            open(os.path.join(self.cal_loc, "__cannot_find_OUTCAR_for_corrections__"), "w").close()
            super(Vasp_out_edddav, self).write_file_absence_log(filename_list = ["OUTCAR"])
            return False
        
        ICHARG = find_incar_tag_from_OUTCAR(cal_loc=self.cal_loc, tag="ICHARG")
        incar_dict = modify_vasp_incar(cal_loc=self.cal_loc)
        ALGO = incar_dict.get("ALGO", "Normal").lower()
        
        if ICHARG < 10:
            if os.path.isfile(os.path.join(self.cal_loc, "CHGCAR")):
                os.remove(os.path.join(self.cal_loc, "CHGCAR"))
        if ALGO != "all":
            super(Vasp_out_edddav, self).backup()
            #modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"ALGO": "All"}, remove_tags=["AMIX", "BMIX", "AMIN"], rename_old_incar=False)
            modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"ALGO": "All"}, remove_tags=["AMIX", "BMIX", "AMIN"], rename_old_incar=False, 
                              incar_template=self.workflow[0]["incar_template_list"], 
                              valid_incar_tags=self.workflow[0]["valid_incar_tags_list"])
            super(Vasp_out_edddav, self).write_correction_log(new_incar_tags={"ALGO": "All"}, remove_incar_tags=["AMIX", "BMIX", "AMIN"], 
                                                              remove_files=["CHGCAR"])
            return True
        
        return False                       


# class Vasp_out_real_optlay(Vasp_Error_Checker_Logger, Vasp_Error_Saver):
#     """
#     Error checking type: after the calculation.
#     Target file: vasp.out or the one specified by tag vasp.out
#     Target error string: "REAL_OPTLAY: internal error"
#     inherit methods write_error_tag and read_error_tag from class Write_and_read_error__.
#     input arguments:
#         -cal_loc: the location of the to-be-checked calculation
#         -workflow: the output of func Parse_calculation_workflow.parse_calculation_workflow.
#     check method: return True, if not found; return False and write error logs otherwise.
#     correct method: if LREAL = .TRUE., reset it to .FALSE. and return True; Otherwise, return False
#     """
#     def __init__(self, cal_loc, workflow):
#         Vasp_Error_Saver.__init__(self, cal_loc=cal_loc, workflow=workflow)
#         
#         self.workflow = workflow
#         self.cal_loc = cal_loc
#         self.firework_name = os.path.split(cal_loc)[-1]
#         self.log_txt = os.path.join(self.cal_loc, "log.txt")
#         self.target_file = self.workflow[0]["vasp.out"]
#         self.target_str = "REAL_OPTLAY: internal error"
#         
#     def check(self):
#         """
#         Return:
#             - False if an error is found;
#             - True otherwise.
#         """        
#         #this method is not active until the job is done
#         if Queue_std_files(cal_loc=self.cal_loc, workflow=self.workflow).find_std_files() == [None, None]:
#             return True
#         
#         #Since the job is done, vasp.out must exist
#         if not os.path.isfile(os.path.join(self.cal_loc, self.target_file)):
#             decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
#             #os.rename(os.path.join(self.cal_loc, "__running__"), os.path.join(self.cal_loc, "__error__"))
#             super(Vasp_out_real_optlay, self).write_file_absence_log(filename_list = [self.target_file], 
#                                                                      initial_signal_file="__running__", 
#                                                                      final_signal_file="__error__")
#             return False
#         
#         if find_target_str(cal_loc=self.cal_loc, target_file=self.target_file, target_str=self.target_str):
#             decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
#             self.write_error_log()
#             return False
#         else:
#             return True
#             
#             
#     def write_error_log(self):
#         super(Vasp_out_real_optlay, self).write_error_log(target_error_str=self.target_str, error_type="__real_optlay__")
#     
#     
#     def correct(self):
#         target_str = "Therefore set LREAL=.FALSE. in the  INCAR file"
#         if find_target_str(cal_loc=self.cal_loc, target_file=self.target_file, target_str=target_str):
#             super(Vasp_out_real_optlay, self).backup()
#             #modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"LREAL": ".FALSE."}, rename_old_incar=False)
#             modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"LREAL": ".FALSE."}, rename_old_incar=False, 
#                               incar_template=self.workflow[0]["incar_template_list"], 
#                               valid_incar_tags=self.workflow[0]["valid_incar_tags_list"])
#             super(Vasp_out_real_optlay, self).write_correction_log(new_incar_tags={"LREAL": ".FALSE."})
#             return True
#         
#         
#         return False                       

# In[20]:


class Vasp_out_pzunmtr_or_pzstein(Vasp_Error_Checker_Logger, Vasp_Error_Saver):
    """
    Error checking type: after the calculation.
    Target file: vasp.out or the one specified by tag vasp.out
    Target error string: "PZUNMTR parameter number" or "PZSTEIN parameter number
    inherit methods write_error_tag and read_error_tag from class Write_and_read_error__.
    input arguments:
        -cal_loc: the location of the to-be-checked calculation
        -workflow: the output of func Parse_calculation_workflow.parse_calculation_workflow.
    check method: return True, if not found; return False and write error logs otherwise.
    correct method: if ALGO != Normal, reset it to Normal and return True; Otherwise, return False
    """
    def __init__(self, cal_loc, workflow):
        Vasp_Error_Saver.__init__(self, cal_loc=cal_loc, workflow=workflow)
        
        self.workflow = workflow
        self.cal_loc = cal_loc
        self.firework_name = os.path.split(cal_loc)[-1]
        self.log_txt = os.path.join(self.cal_loc, "log.txt")
        self.target_file = self.workflow[0]["vasp.out"]
        self.target_str_list = ["PZUNMTR parameter number", "PZSTEIN parameter number"]
        
    def check(self):
        """
        Return:
            - False if an error is found;
            - True otherwise.
        """        
        #this method is not active until the job is done
        if Queue_std_files(cal_loc=self.cal_loc, workflow=self.workflow).find_std_files() == [None, None]:
            return True
        
        #Since the job is done, vasp.out must exist
        if not os.path.isfile(os.path.join(self.cal_loc, self.target_file)):
            decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
            #os.rename(os.path.join(self.cal_loc, "__running__"), os.path.join(self.cal_loc, "__error__"))
            super(Vasp_out_pzunmtr_or_pzstein, self).write_file_absence_log(filename_list = [self.target_file], 
                                                                            initial_signal_file="__running__", 
                                                                            final_signal_file="__error__")
            return False
        
        for target_str in self.target_str_list:
            if find_target_str(cal_loc=self.cal_loc, target_file=self.target_file, target_str=target_str):
                self.target_str = target_str
                decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
                self.write_error_log()
                return False
        else:
            return True
            
            
    def write_error_log(self):
        super(Vasp_out_pzunmtr_or_pzstein, self).write_error_log(target_error_str=self.target_str, error_type="__pzunmtr_or_pzstein__")
    
    
    def correct(self):
        IALGO = find_incar_tag_from_OUTCAR(tag="IALGO", cal_loc=self.cal_loc) # IALGO=38 <--> ALGO=Normal
        if IALGO != 38:
            super(Vasp_out_pzunmtr_or_pzstein, self).backup()
            #modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"ALGO": "Normal"}, rename_old_incar=False)
            modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"ALGO": "Normal"}, rename_old_incar=False, 
                              incar_template=self.workflow[0]["incar_template_list"], 
                              valid_incar_tags=self.workflow[0]["valid_incar_tags_list"])
            super(Vasp_out_pzunmtr_or_pzstein, self).write_correction_log(new_incar_tags={"ALGO": "Normal"})
            return True
        
        return False                       


# In[11]:


class Vasp_out_nkx_gt_ikptd(Vasp_Error_Checker_Logger, Vasp_Error_Saver):
    """
    Error checking type: after the calculation.
    Target file: vasp.out or the one specified by tag vasp.out
    Target error string: "VERY BAD NEWS! internal error in subroutine IBZKPT" or "NKX>IKPTD"
    inherit methods write_error_tag and read_error_tag from class Write_and_read_error__.
    input arguments:
        -cal_loc: the location of the to-be-checked calculation
        -workflow: the output of func Parse_calculation_workflow.parse_calculation_workflow.
    check method: return True, if not found; return False and write error logs otherwise.
    correct method: This error indicates the k-point hits the inherent upper bound of VASP. It cannot be fixed
                What we do is to __killed__ --> __nkx_gt_ikptd__
    """
    def __init__(self, cal_loc, workflow):
        Vasp_Error_Saver.__init__(self, cal_loc=cal_loc, workflow=workflow)
        
        self.workflow = workflow
        self.cal_loc = cal_loc
        self.firework_name = os.path.split(cal_loc)[-1]
        self.log_txt = os.path.join(self.cal_loc, "log.txt")
        self.target_file = self.workflow[0]["vasp.out"]
        self.target_str_list = ["VERY BAD NEWS! internal error in subroutine IBZKPT:", "NKX>IKPTD"]
        
    def check(self):
        """
        Return:
            - False if an error is found;
            - True otherwise.
        """        
        #this method is not active until the job is done
        if Queue_std_files(cal_loc=self.cal_loc, workflow=self.workflow).find_std_files() == [None, None]:
            return True
        
        #Since the job is done, vasp.out must exist
        if not os.path.isfile(os.path.join(self.cal_loc, self.target_file)):
            decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
            #os.rename(os.path.join(self.cal_loc, "__running__"), os.path.join(self.cal_loc, "__error__"))
            super(Vasp_out_nkx_gt_ikptd, self).write_file_absence_log(filename_list = [self.target_file], 
                                                                      initial_signal_file="__running__", 
                                                                      final_signal_file="__error__")
            return False
        
        if all([find_target_str(cal_loc=self.cal_loc, target_file=self.target_file, target_str=target_str) for target_str in self.target_str_list]):
            self.target_str = "\n".join(self.target_str_list)
            decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
            self.write_error_log()
            return False
        else:
            return True
            
            
    def write_error_log(self):
        super(Vasp_out_nkx_gt_ikptd, self).write_error_log(target_error_str=self.target_str, error_type="__nkx_gt_ikptd__")
    
    
    def correct(self):
        """
        - return True if the error is corrected;
        - return False if the error fails to be corrected;
        - return "already_handled": For a specific error that fails to be corrected within this method, if you want to change its signal file from __killed__ to
            to one rather than __manual__, you need to do so within this correct method. In this case, the general logging associated with False is unlikely appropriate.
            You also need to write the log file within this correct method.
        """
        decorated_os_rename(loc=self.cal_loc, old_filename="__killed__", new_filename="__nkx_gt_ikptd__")
        with open(self.log_txt, "a") as log_f:
            log_f.write("{} Killed: This error (__nkx_gt_ikptd__) means that the k-points are so dense for {} as to exceed the inherent upper bound of VASP.\n".format(get_time_str(), self.firework_name))
            log_f.write("\t\t\tTo get rid of this error, you need to adjust NKDIMD and NTETD in main.F.\n")
            log_f.write("\t\t\tHere we do nothing but change __killed__ to __nkx_gt_ikptd__\n")
        return "already_handled"


# In[21]:


class Electronic_divergence(Vasp_Error_Checker_Logger, Vasp_Error_Saver):
    """
    Error checking type: on the fly & after the calculation.
    Check if electonic cal divergences and the max electronic step is reached.
    inherit methods write_error_tag and read_error_tag from class Write_and_read_error__.
    input arguments:
        -cal_loc: the location of the to-be-checked calculation
        -workflow: the output of func Parse_calculation_workflow.parse_calculation_workflow
    check method: return True if reahced; return False and write error logs otherwise.
    """
    def __init__(self, cal_loc, workflow):
        Vasp_Error_Saver.__init__(self, cal_loc=cal_loc, workflow=workflow)
        
        self.workflow = workflow
        self.cal_loc = cal_loc
        self.firework_name = os.path.split(cal_loc)[-1]
        self.log_txt = os.path.join(self.cal_loc, "log.txt")
        #super(Electronic_divergence, self).__init__(cal_loc)
        #Write_and_read_error_tag.__init__(self, cal_loc=self.cal_loc)
     
    
    def check(self):
        """
        Return:
            - False if an error is found;
            - True otherwise.
        """        
        if not os.path.isfile(os.path.join(self.cal_loc, "OUTCAR")) or not os.path.isfile(os.path.join(self.cal_loc, "OSZICAR")):
            return True
        
        incar_dict = modify_vasp_incar(cal_loc=self.cal_loc)
        NELM = int(incar_dict.get("NELM", 60))
        EDIFF = float(incar_dict.get("EDIFF", 1.0e-4))
        
        #print(NELM, EDIFF)
        try:
            if get_trimed_oszicar(cal_loc=self.cal_loc, original_oszicar="OSZICAR", output_oszicar="oszicar"):
                oszicar = Oszicar(os.path.join(self.cal_loc, "oszicar"))
            else: # The ongoing calculation may not have a complete OSZICAR
                return True
        except Exception as inst:
            decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__manual__")
            shutil.copyfile(src=os.path.join(self.cal_loc, "OSZICAR"), dst=os.path.join(self.cal_loc, "OSZICAR_for_debugging"))
            with open(self.log_txt, "a") as log_f:
                log_f.write("{}: ".format(get_time_str()))
                log_f.write(" An error occurs when parsing OSZICAR using pymatgen.io.vasp.outputs.Oszicar. See below:\n")
                log_f.write("\t{}".format(inst))
                log_f.write("\t__running__ --> __manual__\n")
                log_f.write("\tcopy OSZICAR to OSZICAR_for_debugging.\n")
            return False
        finally:
            if os.path.isfile(os.path.join(self.cal_loc, "oszicar")):
                os.remove(os.path.join(self.cal_loc, "oszicar"))
            
        for electronic_steps in oszicar.electronic_steps:
            #print(len(electronic_steps))
            if len(electronic_steps) == NELM:
                last_step = electronic_steps[-1]
                #print(last_step["dE"], last_step["deps"])
                if abs(last_step["dE"]) > EDIFF or abs(last_step["deps"]) > EDIFF:
                    decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
                    self.write_error_log()
                    return False
        return True
    
            
    def write_error_log(self):
        error_str = "Electronic divergence happens"
        super(Electronic_divergence, self).write_error_log(target_error_str=error_str, error_type="__electronic_divergence__")
    
    def correct(self):
        """
        Orders of corrections:
            1st option: if ALGO != Normal, set ALGO = Normal and NELM = 200 if original NELM < 200; 
                        If the dipole correction is on, try to set DIPOL if not present
            2nd option: if the dipole correction is on, try to set DIPOL if not present.
            3rd option: AMIX=0.1, BMIX = 0.01, ICHARG = 2 and NELM = 300 if original NELM < 300
            4th option: AMIN=0.01, BMIX=3.0, ICHARG =2 and NELM = 400 if original NELM < 400
            5th option: return False <-- fail to automatically recover.
            Note that for the 1st, 2nd, 3rd, 4th options, if EDIFF*5 <= 1.0E-4, we also set EDIFF = EDIFF*5
        This correction is borrowed from custodian and modified.
        https://materialsproject.github.io/custodian/_modules/custodian/vasp/handlers.html#VaspErrorHandler.correct
        """
        if not os.path.isfile(os.path.join(self.cal_loc, "OUTCAR")):
            open(os.path.join(self.cal_loc, "__cannot_find_OUTCAR_for_corrections__"), "w").close()
            super(Electronic_divergence, self).write_file_absence_log(filename_list = ["OUTCAR"])
            return False
        
        NELM = find_incar_tag_from_OUTCAR(tag="NELM", cal_loc=self.cal_loc)
        EDIFF = find_incar_tag_from_OUTCAR(tag="EDIFF", cal_loc=self.cal_loc)
        IALGO = find_incar_tag_from_OUTCAR(tag="IALGO", cal_loc=self.cal_loc) # IALGO=38 <--> ALGO=Normal
        incar = modify_vasp_incar(cal_loc=self.cal_loc)
        AMIX = float(incar.get("AMIX", 0.4))
        BMIX = float(incar.get("BMIX", 1.0))
        AMIN = float(incar.get("AMIN", 0.1))
        #according to vaspwiki, IDIPOL will be switched on if it is 1, 2, 3, or 4. 
        #Here we use 0 to denote the absence of the dipole correction
        IDIPOL = int(incar.get("IDIPOL", 0)) 
        DIPOL = incar.get("DIPOL", "")
        
        new_incar_tags = {"LREAL": ".FALSE."}
        
        if EDIFF*5 <= 1.0E-4:
            new_incar_tags["EDIFF"] = EDIFF * 5

        
        if IALGO != 38:                        
            super(Electronic_divergence, self).backup()
            new_incar_tags["ALGO"] = "Normal"
            new_incar_tags["NELM"] = NELM if NELM > 200 else 200
            #For the calculations involved in the dipole correction, set the dipol center.
            #Note that 0.5 is set along x and y directions, while the geometrical center is adopted along the z direction.
            if IDIPOL != 0:
                if DIPOL == "":
                    struct = Structure.from_file(os.path.join(self.cal_loc, "POSCAR"))
                    mean_a = np.mean(struct.frac_coords[:, 0])
                    mean_b = np.mean(struct.frac_coords[:, 1])
                    mean_c = np.mean(struct.frac_coords[:, 2])
                    new_incar_tags["DIPOL"] = "{:.3} {:.3} {:.3}".format(mean_a, mean_b, mean_c)
                    new_incar_tags["ICHARG"] = 2
                    
            #modify_vasp_incar(cal_loc=self.cal_loc, new_tags=new_incar_tags, rename_old_incar=False)
            modify_vasp_incar(cal_loc=self.cal_loc, new_tags=new_incar_tags, rename_old_incar=False, 
                              incar_template=self.workflow[0]["incar_template_list"], 
                              valid_incar_tags=self.workflow[0]["valid_incar_tags_list"])
            super(Electronic_divergence, self).write_correction_log(new_incar_tags=new_incar_tags)
            return True
        
        #For the calculations involved in the dipole correction, set the dipol center.
        #Note that 0.5 is set along x and y directions, while the geometrical center is adopted along the z direction.    
        if IDIPOL != 0: 
            if DIPOL == "":
                super(Electronic_divergence, self).backup()
                struct = Structure.from_file(os.path.join(self.cal_loc, "POSCAR"))
                mean_a = np.mean(struct.frac_coords[:, 0])
                mean_b = np.mean(struct.frac_coords[:, 1])
                mean_c = np.mean(struct.frac_coords[:, 2])
                new_incar_tags["DIPOL"] = "{:.3} {:.3} {:.3}".format(mean_a, mean_b, mean_c)
                new_incar_tags["ICHARG"] = 2
                #modify_vasp_incar(cal_loc=self.cal_loc, new_tags=new_incar_tags, rename_old_incar=False)
                modify_vasp_incar(cal_loc=self.cal_loc, new_tags=new_incar_tags, rename_old_incar=False, 
                                  incar_template=self.workflow[0]["incar_template_list"], 
                                  valid_incar_tags=self.workflow[0]["valid_incar_tags_list"])
                super(Electronic_divergence, self).write_correction_log(new_incar_tags=new_incar_tags)
                return True
        
        if BMIX == 3.0:
            return False
        
        if AMIX > 0.1 and BMIX > 0.01:
            super(Electronic_divergence, self).backup()
            new_incar_tags["NELM"] = NELM if NELM > 300 else 300
            new_incar_tags["AMIX"] = 0.1
            new_incar_tags["BMIX"] = 0.01
            new_incar_tags["ICHARG"] = 2
            #modify_vasp_incar(cal_loc=self.cal_loc, new_tags=new_incar_tags, rename_old_incar=False)
            modify_vasp_incar(cal_loc=self.cal_loc, new_tags=new_incar_tags, rename_old_incar=False, 
                              incar_template=self.workflow[0]["incar_template_list"], 
                              valid_incar_tags=self.workflow[0]["valid_incar_tags_list"])
            super(Electronic_divergence, self).write_correction_log(new_incar_tags=new_incar_tags)
            return True
        
        if BMIX < 3.0 and AMIN > 0.01:
            super(Electronic_divergence, self).backup()
            new_incar_tags["NELM"] = NELM if NELM > 400 else 400
            new_incar_tags["AMIN"] = 0.01
            new_incar_tags["BMIX"] = 3.0
            new_incar_tags["ICHARG"] = 2
            #modify_vasp_incar(cal_loc=self.cal_loc, new_tags=new_incar_tags, remove_tags=["AMIX"], rename_old_incar=False)
            modify_vasp_incar(cal_loc=self.cal_loc, new_tags=new_incar_tags, remove_tags=["AMIX"], rename_old_incar=False, 
                              incar_template=self.workflow[0]["incar_template_list"], 
                              valid_incar_tags=self.workflow[0]["valid_incar_tags_list"])
            super(Electronic_divergence, self).write_correction_log(new_incar_tags=new_incar_tags, remove_incar_tags=["AMIX"])
            return True
        
        return False
    


# In[22]:


class Ionic_divergence(Vasp_Error_Checker_Logger, Vasp_Error_Saver):
    """
    Error checking type: after the calculation.
    Check if the ionic convergence is reached.
    inherit methods write_error_tag and read_error_tag from class Write_and_read_error__.
    input arguments:
        -cal_loc: the location of the to-be-checked calculation.
        -workflow:  the output of func Parse_calculation_workflow.parse_calculation_workflow
    check method: return True if reached; return False and write error logs otherwise.
    """
    def __init__(self, cal_loc, workflow):
        Vasp_Error_Saver.__init__(self, cal_loc=cal_loc, workflow=workflow)
        
        self.workflow = workflow
        self.cal_loc = cal_loc
        self.firework_name = os.path.split(cal_loc)
        self.firework = get_current_firework_from_cal_loc(cal_loc=cal_loc, workflow=workflow)
        self.log_txt = os.path.join(self.cal_loc, "log.txt")
        
        #Write_and_read_error_tag.__init__(self, cal_loc=self.cal_loc)
    
    def check(self):
        """
        Return:
            - False if an error is found;
            - True otherwise.
        """        
        #This if statement deactivates the check method until the calculation is done.
        if Queue_std_files(cal_loc=self.cal_loc, workflow=self.workflow).stdout_file == [None, None]:
            return True
        
        #Since the job is done, vasp.out must exist
        if not os.path.isfile(os.path.join(self.cal_loc, "OUTCAR")):
            decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
            #os.rename(os.path.join(self.cal_loc, "__running__"), os.path.join(self.cal_loc, "__error__"))
            super(Ionic_divergence, self).write_file_absence_log(filename_list = ["OUTCAR"], 
                                                                 initial_signal_file="__running__", 
                                                                 final_signal_file="__error__")
            return False
        
        incar_dict = modify_vasp_incar(cal_loc=self.cal_loc)
        NSW = int(incar_dict.get("NSW", 0))
        default_IBRION = -1 if NSW in [0, -1] else 0
        IBRION = int(incar_dict.get("IBRION", default_IBRION))
        #NSW = find_incar_tag_from_OUTCAR(tag="NSW", cal_loc=self.cal_loc)
        #IBRION = find_incar_tag_from_OUTCAR(tag="IBRION", cal_loc=self.cal_loc)
        #EDIFFG = find_incar_tag_from_OUTCAR(tag="EDIFFG", cal_loc=self.cal_loc)
        #This if statement deactivates the check method unless the calculation is the structural optimization
        if NSW == 0 or IBRION in [-1, 5, 6, 7, 8]:
            return True
        
        target_str = "reached required accuracy - stopping structural energy minimisation"
        if find_target_str(cal_loc=self.cal_loc, target_file="OUTCAR", target_str=target_str):
            if self.firework["max_ionic_step"] == -1:
                return True
            else:
                with open(os.path.join(self.cal_loc, "OUTCAR"), "r") as f:
                    max_ionic_iteration_no = 0
                    for line in f:
                        if "-- Iteration" in line:
                            iteration_no = int(line.split("Iteration")[1].strip().split("(")[0])
                            max_ionic_iteration_no = max([iteration_no, max_ionic_iteration_no])
                if max_ionic_iteration_no == 0:
                    with open(self.log_txt, "a") as log_f:
                        log_f.write("{}: Oops! You are doing a structural optimization, but the number of ionic iterations is found to be ZERO from OUTCAR.\n".format(get_time_str()))
                        log_f.write("\t\tYou have to manually handle it. __running__ --> __manual__\n")
                    decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__manual__")
                    return False
                elif max_ionic_iteration_no <= self.firework["max_ionic_step"]:
                    return True
                else:
                    with open(os.path.join(self.cal_loc, "__converged_but_exceeded_specified_max_ionic_step__"), "w") as f:
                        f.write("%d" % max_ionic_iteration_no)
                        
        decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
        self.write_error_log()
        return False
    
            
    def write_error_log(self):
        error_str = "Ionic divergence happens"
        super(Ionic_divergence, self).write_error_log(target_error_str=error_str, error_type="__ionic_divergence__")
    
    def correct(self):
        if not os.path.isfile(os.path.join(self.cal_loc, "OUTCAR")):
            open(os.path.join(self.cal_loc, "__cannot_find_OUTCAR_for_corrections__"), "w").close()
            super(Ionic_divergence, self).write_file_absence_log(filename_list = ["OUTCAR"])
            return False
        
        if os.path.isfile(os.path.join(self.cal_loc, "__converged_but_exceeded_specified_max_ionic_step__")):
            super(Ionic_divergence, self).backup()
            shutil.move(os.path.join(self.cal_loc, "CONTCAR"), os.path.join(self.cal_loc, "POSCAR"))
            #modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"IBRION": 1}, rename_old_incar=False)
            modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"IBRION": 1}, rename_old_incar=False, 
                              incar_template=self.workflow[0]["incar_template_list"], 
                              valid_incar_tags=self.workflow[0]["valid_incar_tags_list"])
            with open(os.path.join(self.cal_loc, "__converged_but_exceeded_specified_max_ionic_step__"), "r") as f:
                max_ionic_iteration_no = int(next(f))
            os.remove(os.path.join(self.cal_loc, "__converged_but_exceeded_specified_max_ionic_step__"))
            with open(self.log_txt, "a") as f:
                f.write("{} Correction: {}\n".format(get_time_str(), self.firework_name))
                f.write("\t\t\tThe ionic relaxation converges after {} steps\n".format(max_ionic_iteration_no))
                f.write("\t\t\tBut max_ionic_step is set to {}. So try one more round.\n".format(self.firework["max_ionic_step"]))
                f.write("\t\t\tIBRION = 1,  CONTCAR --> POSCAR.\n")
                f.write("\t\t\tDelete the file named __converged_but_exceeded_specified_max_ionic_step__.\n")
            return True
        
        if not os.path.isfile(os.path.join(self.cal_loc, "OSZICAR")):
            open(os.path.join(self.cal_loc, "__cannot_find_OSZICAR_for_corrections__"), "w").close()
            super(Ionic_divergence, self).write_file_absence_log(filename_list = ["OSZICAR"])
            return False
        
        
        incar_dict = modify_vasp_incar(cal_loc=self.cal_loc)
        NSW = int(incar_dict.get("NSW", 0))
        default_IBRION = -1 if NSW in [0, -1] else 0
        IBRION = int(incar_dict.get("IBRION", default_IBRION))
        EDIFF = float(incar_dict.get("EDIFF", 1E-4))
        EDIFFG = float(incar_dict.get("EDIFFG", EDIFF * 10))
        #EDIFF = find_incar_tag_from_OUTCAR(cal_loc=self.cal_loc, tag="EDIFF")
        #EDIFFG = find_incar_tag_from_OUTCAR(cal_loc=self.cal_loc, tag="EDIFFG")
        #NSW = find_incar_tag_from_OUTCAR(cal_loc=self.cal_loc, tag="NSW")
        #IBRION = find_incar_tag_from_OUTCAR(cal_loc=self.cal_loc, tag="IBRION")
        
        try:
            if get_trimed_oszicar(cal_loc=self.cal_loc, original_oszicar="OSZICAR", output_oszicar="oszicar"):
                oszicar = Oszicar(os.path.join(self.cal_loc, "oszicar"))
            else: # The ongoing calculation may not have a complete OSZICAR
                return True
        except Exception as inst:
            decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__manual__")
            shutil.copyfile(src=os.path.join(self.cal_loc, "OSZICAR"), dst=os.path.join(self.cal_loc, "OSZICAR_for_debugging"))
            with open(self.log_txt, "a") as log_f:
                log_f.write("{}: ".format(get_time_str()))
                log_f.write(" An error occurs when parsing OSZICAR using pymatgen.io.vasp.outputs.Oszicar. See below:\n")
                log_f.write("\t{}".format(inst))
                log_f.write("\t__running__ --> __manual__\n")
                log_f.write("\tcopy OSZICAR to OSZICAR_for_debugging.\n")
            return False
        finally:
            if os.path.isfile(os.path.join(self.cal_loc, "oszicar")):
                os.remove(os.path.join(self.cal_loc, "oszicar"))
        
        if len(oszicar.electronic_steps) < NSW:
            #check if CONTCAR is empty.
            with open(os.path.join(self.cal_loc, "CONTCAR"), "r") as f:
                lines = [line for line in f if line.strip()]
            if lines == []:
                with open(self.log_txt, "a") as f:
                    f.write("{} Correction: {}\n".format(get_time_str(), self.firework_name))
                    f.write("\t\t\tCONTCAR is empty, so the error may not be triggered by the limited walltime.\n")
                return False
                    
            super(Ionic_divergence, self).backup()
            shutil.move(os.path.join(self.cal_loc, "CONTCAR"), os.path.join(self.cal_loc, "POSCAR"))
            with open(self.log_txt, "a") as f:
                f.write("{} Correction: {}\n".format(get_time_str(), self.firework_name))
                f.write("\t\t\tThis error may be due to that the walltime is reached.\n")
                f.write("\t\t\tCONTCAR --> POSCAR\n")
            return True
        elif IBRION in [2, 3]:
            super(Ionic_divergence, self).backup()
            shutil.move(os.path.join(self.cal_loc, "CONTCAR"), os.path.join(self.cal_loc, "POSCAR"))
            #modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"IBRION": 1}, rename_old_incar=False)
            modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"IBRION": 1, "NSW": 400}, rename_old_incar=False, 
                              incar_template=self.workflow[0]["incar_template_list"], 
                              valid_incar_tags=self.workflow[0]["valid_incar_tags_list"])
            with open(self.log_txt, "a") as f:
                f.write("{} Correction: {}\n".format(get_time_str(), self.firework_name))
                f.write("\t\t\tThe ionic step reaches the preset maximum step ({})\n".format(NSW))
                f.write("\t\t\tBut IBRION is {}, not 1. So try one more round.\n".format(IBRION))
                f.write("\t\t\tIBRION = 1 & NSW = 400,  CONTCAR --> POSCAR.\n")
            return True
        else:
            return False
        


# In[23]:


class Positive_energy(Vasp_Error_Checker_Logger, Vasp_Error_Saver):
    """
    Error checking type: after the calculation.
    Check if a electronic run has positive energy.
    inherit methods write_error_tag and read_error_tag from class Write_and_read_error__.
    input arguments:
        -cal_loc: the location of the to-be-checked calculation.
        -workflow:  the output of func Parse_calculation_workflow.parse_calculation_workflow
    check method: return True if negative; return False and write error logs otherwise.
    """
    
    def __init__(self, cal_loc, workflow):
        Vasp_Error_Saver.__init__(self, cal_loc=cal_loc, workflow=workflow)
        
        self.workflow = workflow
        self.cal_loc = cal_loc
        self.firework_name = os.path.split(cal_loc)[-1]
        self.log_txt = os.path.join(self.cal_loc, "log.txt")
        #super(Positive_energy, self).__init__(cal_loc)
        #Write_and_read_error_tag.__init__(self, cal_loc=self.cal_loc)
    
    def check(self):
        """
        Return:
            - False if an error is found;
            - True otherwise.
        """        
        #This if statement deactivates the check method until the calculation is done.
        if Queue_std_files(cal_loc=self.cal_loc, workflow=self.workflow).stdout_file == [None, None]:
            return True
        
        #Since the job is done, vasp.out must exist
        if not os.path.isfile(os.path.join(self.cal_loc, "OSZICAR")):
            decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
            #os.rename(os.path.join(self.cal_loc, "__running__"), os.path.join(self.cal_loc, "__error__"))
            super(Positive_energy, self).write_file_absence_log(filename_list = ["OSZICAR"], 
                                                                initial_signal_file="__running__", 
                                                                final_signal_file="__error__")
            return False
        
        try:
            if get_trimed_oszicar(cal_loc=self.cal_loc, original_oszicar="OSZICAR", output_oszicar="oszicar"):
                oszicar = Oszicar(os.path.join(self.cal_loc, "oszicar"))
            else: # The ongoing calculation may not have a complete OSZICAR
                return True
            #oszicar = Oszicar(os.path.join(self.cal_loc, "OSZICAR"))
            if oszicar.final_energy > 0:
                decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
                self.write_error_log()
                return False
        except Exception as inst:
            decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__manual__")
            shutil.copyfile(src=os.path.join(self.cal_loc, "OSZICAR"), dst=os.path.join(self.cal_loc, "OSZICAR_for_debugging"))
            with open(self.log_txt, "a") as log_f:
                log_f.write("{}: ".format(get_time_str()))
                log_f.write(" An error occurs when parsing OSZICAR using pymatgen.io.vasp.outputs.Oszicar. See below:\n")
                log_f.write("\t{}".format(inst))
                log_f.write("\t__running__ --> __manual__\n")
                log_f.write("\tcopy OSZICAR to OSZICAR_for_debugging.\n")
            return False
        finally:
            if os.path.isfile(os.path.join(self.cal_loc, "oszicar")):
                os.remove(os.path.join(self.cal_loc, "oszicar"))
        
        return True
    
            
    def write_error_log(self):
        error_str = "Positive energy has been found"
        super(Positive_energy, self).write_error_log(target_error_str=error_str, error_type="__positive_energy__")
    
    def correct(self):
        """
        This correction is borrowed from custodian and modified.
        https://materialsproject.github.io/custodian/_modules/custodian/vasp/handlers.html#VaspErrorHandler.correct
        """
        if not os.path.isfile(os.path.join(self.cal_loc, "OUTCAR")):
            open(os.path.join(self.cal_loc, "__cannot_find_OUTCAR_for_corrections__"), "w").close()
            super(Positive_energy, self).write_file_absence_log(filename_list = ["OUTCAR"])
            return False
        
        IALGO = find_incar_tag_from_OUTCAR(cal_loc=self.cal_loc, tag="IALGO")
        
        if IALGO != 38:
            super(Positive_energy, self).backup()
            #modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"ALGO": "Normal"}, rename_old_incar=False)
            modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"ALGO": "Normal"}, rename_old_incar=False, 
                              incar_template=self.workflow[0]["incar_template_list"], 
                              valid_incar_tags=self.workflow[0]["valid_incar_tags_list"])
            super(Positive_energy, self).write_correction_log(new_incar_tags={"ALGO": "Normal"})
            #with open(self.log_txt, "a") as f:
            #    f.write("{} Correction: ALGO --> Normal\n".format(get_time_str()))
            return True
        
        return False


# In[24]:


class Bader_Charge(Vasp_Error_Checker_Logger, Vasp_Error_Saver):
    """
    Error checking type: on the fly.
    If Bader Charge is going to be calculated (bader_charge tag is on), check LAECHG, NGXF, NGYF, NGZF, LCHARG.
    inherit methods write_error_tag and read_error_tag from class Write_and_read_error__.
    input arguments:
        -cal_loc: the location of the to-be-checked calculation.
        -workflow:  the output of func Parse_calculation_workflow.parse_calculation_workflow
    check method: if bader_charge is on and any of LAECHG, NGXF, NGYF, NGZF, LCHARG is not set properly, trigger an error named __bader_charge__
    correction: set LAECHG, NGXF, NGYF, NGZF, LCHARG properly
    """
    
    def __init__(self, cal_loc, workflow):
        Vasp_Error_Saver.__init__(self, cal_loc=cal_loc, workflow=workflow)
        
        self.workflow = workflow
        self.cal_loc = cal_loc
        self.firework_name = os.path.split(cal_loc)[-1]
        self.log_txt = os.path.join(self.cal_loc, "log.txt")
        self.firework = get_current_firework_from_cal_loc(cal_loc=cal_loc, workflow=workflow)

    
    def check(self):
        """
        Return:
            - False if an error is found;
            - True otherwise.
        """        
        if self.firework["bader_charge"] == False:
            return True
        
        incar_dict = modify_vasp_incar(cal_loc=self.cal_loc)
        all_in = True
        for tag in ["LAECHG", "NGXF", "NGYF", "NGZF"]:
            if tag not in incar_dict.keys():
                all_in = False
                break
        
        if "LCHARG" in incar_dict.keys():
            if "t" not in incar_dict["LCHARG"].lower():
                all_in = False
                
        if all_in == False:
            if self.firework["step_no"] == 1:
                if os.path.isfile(os.path.join(self.cal_loc, "OUTCAR")):
                    if find_target_str(cal_loc=self.cal_loc, target_file="OUTCAR", target_str="dimension x,y,z NGXF="):
                        decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
                        self.write_error_log()
                        return False
            else:
                decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
                self.write_error_log()
                return False
        return True    
            
    def write_error_log(self):
        error_str = "INCAR tags related to the Bader Charge Calculation are not set properly"
        super(Bader_Charge, self).write_error_log(target_error_str=error_str, error_type="__bader_charge__")
    
    def correct(self):
        """
        Please refer to http://theory.cm.utexas.edu/henkelman/code/bader/ for the INCAR tag settings for Bader Charge Analysis
            LCHARG = .TRUE.
            LAECHG = .TRUE.
            NGXF   = 2 * default value
            NGYF   = 2 * default value
            NGZF   = 2 * default value
        """
        if self.firework["step_no"] == 1:
            new_incar_tags = get_bader_charge_tags(cal_loc=self.cal_loc)
        else:
            prev_cal = os.path.join(os.path.split(self.cal_loc)[0], self.workflow[self.firework["copy_which_step"]-1]["firework_folder_name"])
            new_incar_tags = get_bader_charge_tags(cal_loc=prev_cal)
        
        super(Bader_Charge, self).backup()
        #modify_vasp_incar(cal_loc=self.cal_loc, new_tags=new_incar_tags, rename_old_incar="INCAR.no_bader_charge")
        modify_vasp_incar(cal_loc=self.cal_loc, new_tags=new_incar_tags, rename_old_incar="INCAR.no_bader_charge", 
                          incar_template=self.workflow[0]["incar_template_list"], 
                          valid_incar_tags=self.workflow[0]["valid_incar_tags_list"])
        super(Bader_Charge, self).write_correction_log(new_incar_tags=new_incar_tags)
        return True
        


# In[25]:


class Null_error_checker(object):
    """
    This class deals with any exceptional cases where the error_type in __error__ under cal_loc is not written
    by our defined Error Checker classes in this sript.
    This class makes the wrapper Vasp_Error_checker robust to deal with any cases.
    input arguments:
        -cal_loc: the location of the to-be-checked calculation.
        -workflow:  the output of func Parse_calculation_workflow.parse_calculation_workflow
    
    When method check is called, return True.
    When method correct is called, return False.
    """
    
    def __init__(self, cal_loc, workflow):
        pass
    
    def check(self):
        """
        Always return True
        """
        return True
    
    def correct(self):
        """
        Always return False
        """
        return False
    
    def write_error_log(self):
        pass

