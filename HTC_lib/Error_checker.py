
# coding: utf-8

# # created on Feb 18 2018

# In[1]:


import os, time, shutil
import re
import subprocess

from pymatgen.io.vasp.outputs import Oszicar, Vasprun

import numpy as np

from Query_from_OUTCAR import find_incar_tag_from_OUTCAR
from Utilities import get_time_str, search_file
from Preprocess_and_Postprocess import modify_vasp_incar


# In[2]:


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
                          "__rhosyg__":Vasp_out_rhosyg}
    
    on_the_fly = ["__too_few_bands__", "__electronic_divergence__", "__positive_energy__"]
    after_cal = on_the_fly + ["__pricel__", "__posmap__", "__bad_termination__", "__zbrent__", "__invgrp__"]
    after_cal += ["__too_few_kpoints__", "__rhosyg__", "__ionic_divergence__", "__unfinished_OUTCAR__"]
    
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


# In[3]:


class Write_and_read_error_tag(object):
    """
    Write or read error tag from file __error__ under folder cal_loc.
    input argument:
        -cal_loc (str): the location of the to-be-checked calculation
    """
    
    def __init__(self, cal_loc):
        self.cal_loc = cal_loc
        
    def write_error_tag(self, error_tag, file="__error__"):
        """
        input arguments:
            -error_tag (str): currently available: 
                        __unfinished_OUTCAR__, __electronic_divergence__, __ionic_divergence__, __positive_energy__
            -file (str): the file to write error_tag. Default: __error__
        """
        with open(os.path.join(self.cal_loc, file), "w") as f:
            f.write(error_tag)
            
    def read_error_tag(self, file="__killed__"):
        """
        input argument:
            -file (str): the file from which the error_tag is read.
        """
        with open(os.path.join(self.cal_loc, file), "r") as f:
            return f.read().strip()


# In[4]:


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
                If more than one files are found, it will raise an Exception.
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


# In[5]:


def file_existence_decorator(filename, true=True):
    def Func_wrapper(func):
        def func_wrapper(*args):
            file_loc = args[0].cal_loc
            if os.path.isfile(os.path.join(file_loc, filename)):
                return func(*args)
            else:
                if true:
                    return true_func(*args) #<---decorate method check of Check_xxx classes below.
                else:
                    return false_func(*args) #<--- decorate method correct of Check_xxx classes below.
            
        return func_wrapper
        
    def true_func(*args):
        return True
    
    def false_func(*args):
        return False
    
    return Func_wrapper


# In[6]:


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
    if os.path.isfile(os.path.join(cal_loc, target_file)):
        with open(os.path.join(cal_loc, target_file), "r") as f:
            for line in f:
                if target_str in line:
                    return True
        return False
    else:
        return False
    


# In[7]:


class Vasp_Error_Saver(object):
    """
    Backup INCAR, POSCAR, KPOINTS, OUTCAR, XDATCAR, vasp.out and queue stdout & stderr so as to facilitate the manual error repair.
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
        self.log_txt_loc, self.firework_name = os.path.split(cal_loc)
        self.log_txt = os.path.join(self.log_txt_loc, "log.txt")
        self.error_folder = os.path.join(self.cal_loc, "error_folder")
                
    def backup(self):
        if not os.path.isdir(self.error_folder):
            os.mkdir(self.error_folder)
            with open(self.log_txt, "a") as f:
                f.write("{} Backup: Create error_folder under {}\n".format(get_time_str(), self.firework_name))
        
        file_list = ["INCAR", "POSCAR", "KPOINTS", "XDATCAR", "OUTCAR", "OSZICAR", self.workflow[0]["vasp.out"]]
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

            #if stdout:
            #    os.remove(os.path.join(self.cal_loc, stdout))
            #    f.write("\t\t\tremove {}\n".format(stdout))
            #if stderr:
            #    os.remove(os.path.join(self.cal_loc, stderr))
            #    f.write("\t\t\tremove {}\n".format(stderr))
                
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
            if latest_std == curr_std:
                return "error_"+str(error_times)
            else:
                return "error_"+str(error_times+1)


# In[8]:


class Vasp_Error_Logger(Write_and_read_error_tag):
    """
    This class provides a method write_error_log which writes down the error information into log.txt for a material and
    changes file __running__ to file __error__, and writes down the error type into file __error__
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
        self.lot_txt_loc, self.firework_name = os.path.split(cal_loc)
        self.log_txt = os.path.join(self.log_txt, "log.txt")
    
    def write_error_log(self, target_error_str, error_type):
        error_type = error_type.strip()
        if isinstance(target_error_str, str):
            target_error_str_list = [target_error_str]
        elif isinstance(target_error_str, list):
            target_error_str_list = target_error_str
        else:
            raise Exception("target_error_str for Vasp_error_logger.write_error_log must be a string or a list of strings.")
            
        with open(self.log_txt, "a") as f:
            f.write("{} Error: {}\n".format(get_time_str(), self.firework_name))
            for error_str in target_error_str_list:
                f.write("\t\t{}\n".format(error_str))
            os.rename(os.path.join(self.cal_loc, "__running__"), os.path.join(self.cal_loc, "__error__"))
            f.write("\t\t\t__running__ --> __error__\n")
            f.write("\t\t\t write {} into __error__\n".format(error_type))
            super(Vasp_Error_Logger, self).write_error_tag(error_type)


# # For all error checkers, the check method will return False if an error is found. Otherwise return True

# In[9]:


class OUTCAR_status(Vasp_Error_Logger):
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
        self.log_txt_loc, self.firework_name = os.path.split(cal_loc)
        self.log_txt = os.path.join(self.log_txt_loc, "log.txt")
        self.target_str = "General timing and accounting informations for this job:"
        self.target_file = "OUTCAR"
        
        
    def check(self):
        
        #This if statement deactivates the check method until the calculation is done.
        if Queue_std_files(cal_loc=self.cal_loc, workflow=self.workflow) == [None, None]:
            return True
        
        if find_target_str(cal_loc=self.cal_loc, target_file=self.target_file, target_str=self.target_str):
            return True
        else:
            self.write_error_log()
            return False
    
    def write_error_log_(self):
        with open(self.log_txt, "a") as f:
            f.write("{} Error: The calculation fails to complete at {}\n".format(get_time_str(), self.firework_name))
            os.rename(os.path.join(self.cal_loc, "__running__"), os.path.join(self.cal_loc, "__error__"))
            f.write("\t\t\t__running__ --> __error__\n")
            f.write("\t\t\t write __unfinished_OUTCAR__ into __error__\n")
            super(OUTCAR_status, self).write_error_tag("__unfinished_OUTCAR__")
            
    def write_error_log(self):
        super(OUTCAR_status, self).write_error_log(target_error_str=self.target_str, error_type="__unfinished_OUTCAR__")
    
    def correct(self):
        return False
    


# In[10]:


class Vasp_out_pricel(Vasp_Error_Logger, Vasp_Error_Saver):
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
        self.log_txt_loc, self.firework_name = os.path.split(cal_loc)
        self.log_txt = os.path.join(self.log_txt_loc, "log.txt")
        self.target_file = self.workflow[0]["vasp.out"]
        self.target_str = "internal error in subroutine PRICEL"
        
        
    def check(self):
        
        #This method will be active only when the job is done.
        if Queue_std_files(cal_loc=self.cal_loc, workflow=self.workflow).find_std_files() == [None, None]:
            return True
        
        if find_target_str(cal_loc=self.cal_loc, target_file=self.target_file, target_str=self.target_str):
            self.write_error_log()
            return False
        else:
            return True
    
    def write_error_log_(self):
        with open(self.log_txt, "a") as f:
            f.write("{} Error: {}\n".format(get_time_str(), self.firework_name))
            f.write("\t\t{}\n".format(self.target_str))
            os.rename(os.path.join(self.cal_loc, "__running__"), os.path.join(self.cal_loc, "__error__"))
            f.write("\t\t\t__running__ --> __error__\n")
            f.write("\t\t\t write __pricel__ into __error__\n")
            super(Vasp_out_pricel, self).write_error_tag("__pricel__")
            
    def write_error_log(self):
        super(Vasp_out_pricel, self).write_error_log(target_error_str=self.target_str, error_type="__pricel__")
    
    def correct(self):
        incar_dict = modify_vasp_incar(cal_loc=self.cal_loc)
        SYMPREC = float(incar_dict.get("SYMPREC", 1.0e-5))
        ISYM = int(incar_dict.get("ISYM", 2))
        
        if ISYM != 0 or SYMPREC > 1.1e-9:
            super(Vasp_out_pricel, self).backup()
            modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"SYMPREC": 1e-8, "ISYM": 0}, rename_old_incar=False)
            with open(self.log_txt, "a") as f:
                f.write("{} Correction: reset INCAR tags as below at {}\n".format(get_time_str(), self.firework_name))
                f.write("\t\t\tSYMPREC: {} --> 1.0e-8\n".format(SYMPREC))
                f.write("\t\t\tISYM: {} --> 0\n".format(ISYM))
            return True
        else:
            return False



# In[11]:


class Vasp_out_too_few_bands(Vasp_Error_Logger, Vasp_Error_Saver):
    """
    Error checking type: after the calculation.
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
        self.log_txt_loc, self.firework_name = os.path.split(cal_loc)
        self.log_txt = os.path.join(self.log_txt_loc, "log.txt")
        self.target_file = self.workflow[0]["vasp.out"]
        self.target_str = "TOO FEW BANDS"
        
        
    def check(self):
        
        #This method will be active only when the job is done.
        if Queue_std_files(cal_loc=self.cal_loc, workflow=self.workflow).find_std_files() == [None, None]:
            return True
                
        if find_target_str(cal_loc=self.cal_loc, target_file=self.target_file, target_str=self.target_str):
            self.write_error_log()
            return False
        else:
            return True
    
    def write_error_log_(self):
        with open(self.log_txt, "a") as f:
            f.write("{} Error: {}\n".format(get_time_str(), self.firework_name))
            f.write("\t\t{}\n".format(self.target_str))
            os.rename(os.path.join(self.cal_loc, "__running__"), os.path.join(self.cal_loc, "__error__"))
            f.write("\t\t\t__running__ --> __error__\n")
            f.write("\t\t\t write __too_few_bands__ into __error__\n")
            super(Vasp_out_too_few_bands, self).write_error_tag("__too_few_bands__")
    
    def write_error_log(self):
        super(Vasp_out_too_few_bands, self).write_error_log(target_error_str=self.target_str, error_type="__too_few_bands__")
    
    @file_existence_decorator("OUTCAR", true=False)
    def correct(self):
        NBANDS = find_incar_tag_from_OUTCAR(cal_loc=self.cal_loc, tag="NBANDS")
        NBANDS_ = int(NBANDS*1.1)
        
        super(Vasp_out_too_few_bands, self).backup()
        modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"NBANDS": NBANDS_}, rename_old_incar=False)
        
        with open(self.log_txt, "a") as f:
            f.write("{} Correction: reset INCAR tags as below at {}\n".format(get_time_str(), self.firework_name))
            f.write("\t\t\tNBANDS: {} --> {}\n".format(NBANDS, NBANDS_))
        return True



# In[12]:


class Vasp_out_too_few_kpoints(Vasp_Error_Logger, Vasp_Error_Saver):
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
        self.log_txt_loc, self.firework_name = os.path.split(cal_loc)
        self.log_txt = os.path.join(self.log_txt_loc, "log.txt")
        self.target_file = self.workflow[0]["vasp.out"]
        self.target_str = "Tetrahedron method fails for NKPT<4."
        
        
    def check(self):
        
        #This method will be active only when the job is done.
        if Queue_std_files(cal_loc=self.cal_loc, workflow=self.workflow).find_std_files() == [None, None]:
            return True
                
        if find_target_str(cal_loc=self.cal_loc, target_file=self.target_file, target_str=self.target_str):
            self.write_error_log()
            return False
        else:
            return True
    
    def write_error_log_(self):
        with open(self.log_txt, "a") as f:
            f.write("{} Error: {}\n".format(get_time_str(), self.firework_name))
            f.write("\t\t{}\n".format(self.target_str))
            os.rename(os.path.join(self.cal_loc, "__running__"), os.path.join(self.cal_loc, "__error__"))
            f.write("\t\t\t__running__ --> __error__\n")
            f.write("\t\t\t write __too_few_kpoints__ into __error__\n")
            super(Vasp_out_too_few_kpoints, self).write_error_tag("__too_few_kpoints__")
            
    def write_error_log(self):
        super(Vasp_out_too_few_kpoints, self).write_error_log(target_error_str=self.target_str, error_type="__too_few_kpoints__")
    
    def correct(self):
        incar_dict = modify_vasp_incar(cal_loc=self.cal_loc)
        ISMEAR = int(incar_dict.get("ISMEAR", 1))
        SIGMA = float(incar_dict.get("SIGMA", 0.2))
        
        if ISMEAR == -5:     
            super(Vasp_out_too_few_kpoints, self).backup()
            modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"ISMEAR": 0, "SIGMA":0.05}, rename_old_incar=False)
            with open(self.log_txt, "a") as f:
                f.write("{} Correction: reset INCAR tags as below at {}\n".format(get_time_str(), self.firework_name))
                f.write("\t\t\tISMEAR: {} --> 0\n".format(ISMEAR))
                f.write("\t\t\tSIGMA: {} --> 0.05\n".format(SIGMA))
            return True
        else:
            return False



# In[13]:


class Vasp_out_posmap(Vasp_Error_Logger, Vasp_Error_Saver):
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
        self.log_txt_loc, self.firework_name = os.path.split(cal_loc)
        self.log_txt = os.path.join(self.log_txt_loc, "log.txt")
        self.target_file = self.workflow[0]["vasp.out"]
        #super(Vasp_out_posmap, self).__init__(cal_loc, workflow)
        self.target_str = "POSMAP internal error: symmetry equivalent atom not found"
        
        
        
    def check(self):
        #This method is deactive until the job is done
        if Queue_std_files(cal_loc=self.cal_loc, workflow=self.workflow).find_std_files() == [None, None]:
            return True
        
        if find_target_str(cal_loc=self.cal_loc, target_file=self.target_file, target_str=self.target_str):
            self.write_error_log()
            return False
        else:
            return True
    
    def write_error_log_(self):
        with open(self.log_txt, "a") as f:
            f.write("{} Error: {}\n".format(get_time_str(), self.firework_name))
            f.write("\t\t{}\n".format(self.target_str))
            os.rename(os.path.join(self.cal_loc, "__running__"), os.path.join(self.cal_loc, "__error__"))
            f.write("\t\t\t__running__ --> __error__\n")
            f.write("\t\t\t write __posmap__ into __error__\n")
            super(Vasp_out_posmap, self).write_error_tag("__posmap__")
            
    def write_error_log(self):
        super(Vasp_out_posmap, self).write_error_log(target_error_str=self.target_str, error_type="__posmap__")
    
    def correct(self):
        incar_dict = modify_vasp_incar(cal_loc=self.cal_loc)
        SYMPREC = float(incar_dict.get("SYMPREC", 1.0e-5))
        
        if SYMPREC > 1e-7:
            super(Vasp_out_posmap, self).backup()
            modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"SYMPREC": SYMPREC/10.}, rename_old_incar=False)
            with open(self.log_txt, "a") as f:
                f.write("{} Correction: reset INCAR tags as below at {}\n".format(get_time_str(), self.firework_name))
                f.write("\t\t\tSYMPREC: {} --> {}\n".format(SYMPREC, SYMPREC/10.))
            return True
        else:
            return False
        


# In[14]:


class Vasp_out_bad_termination(Vasp_Error_Logger):
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
        self.log_txt_loc, self.firework_name = os.path.split(cal_loc)
        self.log_txt = os.path.join(self.log_txt_loc, "log.txt")
        self.target_file = self.workflow[0]["vasp.out"]
        self.target_str = "=   BAD TERMINATION OF ONE OF YOUR APPLICATION PROCESSES"
        
        
        
    def check(self):
        #this method is not active until the job is done
        if Queue_std_files(cal_loc=self.cal_loc, workflow=self.workflow).find_std_files() == [None, None]:
            return True
        
        if find_target_str(cal_loc=self.cal_loc, target_file=self.target_file, target_str=self.target_str):
            self.write_error_log()
            return False
        else:
            return True
            
    
    def write_error_log_(self):
        with open(self.log_txt, "a") as f:
            f.write("{} Error: {}\n".format(get_time_str(), self.firework_name))
            f.write("\t\t{}\n".format(self.target_str))
            os.rename(os.path.join(self.cal_loc, "__running__"), os.path.join(self.cal_loc, "__error__"))
            f.write("\t\t\t__running__ --> __error__\n")
            f.write("\t\t\t write __bad_termination__ into __error__\n")
            super(Vasp_out_bad_termination, self).write_error_tag("__bad_termination__")
            
    def write_error_log(self):
        super(Vasp_out_bad_termination, self).write_error_log(target_error_str=self.target_str, error_type="__bad_termination__")
    
    def correct(self):
        if os.path.isfile(os.path.join(self.cal_loc, "__bad_termination__")):
            with open(self.log_txt, "a") as f:
                f.write("{} Correction: {}\n".format(get_time_str(), self.firework_name))
                f.write("\t\t\t{}\n".format(self.target_str))
                f.write("\t\t\tfile __bad_termination__ is detected in this folder\n")
                f.write("\t\t\tSo this is the second time to encounter such error\n")
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



# In[15]:


class Vasp_out_invgrp(Vasp_Error_Logger, Vasp_Error_Saver):
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
        self.log_txt_loc, self.firework_name = os.path.split(cal_loc)
        self.log_txt = os.path.join(self.log_txt_loc, "log.txt")
        self.target_file = self.workflow[0]["vasp.out"]
        self.target_str_list = [" VERY BAD NEWS! internal error in subroutine INVGRP:", 
                                "inverse of rotation matrix was not found (increase SYMPREC)"]
        
        
        
    def check(self):
        #this method is not active until the job is done
        if Queue_std_files(cal_loc=self.cal_loc, workflow=self.workflow).find_std_files() == [None, None]:
            return True
        
        no_error_list = []
        for target_str in self.target_str_list:
            no_error_list.append(find_target_str(cal_loc=self.cal_loc, target_file=self.target_file, target_str=target_str))
            
        if False in no_error_list:
            return True
        else:
            self.write_error_log()
            return False
    
    def write_error_log_(self):
        with open(self.log_txt, "a") as f:
            f.write("{} Error: {}\n".format(get_time_str(), self.firework_name))
            for target_str in self.target_str_list:
                f.write("\t\t{}\n".format(target_str))
            os.rename(os.path.join(self.cal_loc, "__running__"), os.path.join(self.cal_loc, "__error__"))
            f.write("\t\t\t__running__ --> __error__\n")
            f.write("\t\t\t write __invgrp__ into __error__\n")
            super(Vasp_out_invgrp, self).write_error_tag("__invgrp__")
            
    def write_error_log(self):
        super(Vasp_out_invgrp, self).write_error_log(target_error_str=self.target_str_list, error_type="__invgrp__")
    
    def correct(self):
        incar_dict = modify_vasp_incar(cal_loc=self.cal_loc)
        SYMPREC = incar_dict.get("SYMPREC", 1.0e-5)
        SYMPREC_ = SYMPREC * 5
        
        if SYMPREC_ < 0.9e-4:
            super(Vasp_out_invgrp, self).backup()
            modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"SYMPREC": SYMPREC_}, rename_old_incar=False)
            with open(self.log_txt, "a") as f:
                f.write("{} Correction: {}\n".format(get_time_str(), self.firework_name))
                f.write("\t\t\tSYMPREC: {}-->{}\n".format(SYMPREC, SYMPREC_))
            return True
        else:
            with open(self.log_txt, "a") as f:
                f.write("{} Correction: {}\n".format(get_time_str(), self.firework_name))
                f.write("\t\t\tSYMPREC={} is already too big.\n".format(SYMPREC))
            return False
                        


# In[16]:


class Vasp_out_zbrent(Vasp_Error_Logger, Vasp_Error_Saver):
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
        self.log_txt_loc, self.firework_name = os.path.split(cal_loc)
        self.log_txt = os.path.join(self.log_txt_loc, "log.txt")
        self.target_file = self.workflow[0]["vasp.out"]
        self.target_str_list = ["ZBRENT: fatal error in bracketing", 
                                "please rerun with smaller EDIFF, or copy CONTCAR", 
                                "to POSCAR and continue"]
        
        
        
    def check(self):
        #this method is not active until the job is done
        if Queue_std_files(cal_loc=self.cal_loc, workflow=self.workflow).find_std_files() == [None, None]:
            return True
        
        no_error_list = []
        for target_str in self.target_str_list:
            no_error_list.append(find_target_str(cal_loc=self.cal_loc, target_file=self.target_file, target_str=target_str))
            
        if False in no_error_list:
            return True
        else:
            self.write_error_log()
            return False
    
    def write_error_log_(self):
        with open(self.log_txt, "a") as f:
            f.write("{} Error: {}\n".format(get_time_str(), self.firework_name))
            for target_str in self.target_str_list:
                f.write("\t\t{}\n".format(target_str))
            os.rename(os.path.join(self.cal_loc, "__running__"), os.path.join(self.cal_loc, "__error__"))
            f.write("\t\t\t__running__ --> __error__\n")
            f.write("\t\t\t write __zbrent__ into __error__\n")
            super(Vasp_out_zbrent, self).write_error_tag("__zbrent__")
            
    def write_error_log(self):
        super(Vasp_out_zbrent, self).write_error_log(target_error_str=self.target_str_list, error_type="__zbrent__")
    
    
    def correct(self):
        EDIFF = find_incar_tag_from_OUTCAR(tag="EDIFF", cal_loc=self.cal_loc)
        IBRION = find_incar_tag_from_OUTCAR(tag="IBRION", cal_loc=self.cal_loc)
        
        if EDIFF <= 1.0e-6:
            with open(self.log_txt, "a") as f:
                f.write("{} Correction: {}\n".format(get_time_str(), self.firework_name))
                f.write("\t\t\tEDIFF {} is too small\n".format(EDIFF))
            return False
        else:
            super(Vasp_out_zbrent, self).backup()
            modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"EDIFF": EDIFF*0.5}, rename_old_incar=False)
            shutil.copyfile(os.path.join(self.cal_loc, "CONTCAR"), os.path.join(self.cal_loc, "POSCAR"))
            with open(self.log_txt, "a") as f:
                f.write("{} Correction: {}\n".format(get_time_str(), self.firework_name))
                f.write("\t\t\tEDIFF: {} --> {}\n".format(EDIFF, EDIFF*0.5))
                f.write("\t\t\tIBRION: {} --> 1\n".format(IBRION))
                f.write("\t\t\tCONTCAR --> POSCAR\n")
            return True
                        


# In[17]:


class Vasp_out_rhosyg(Vasp_Error_Logger, Vasp_Error_Saver):
    """
    Error checking type: after the calculation.
    Target file: vasp.out or the one specified by tag vasp.out
    Target error string: "RHOSYG internal error: stars are not distinct, try to increase SYMPREC to e.g."
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
        self.log_txt_loc, self.firework_name = os.path.split(cal_loc)
        self.log_txt = os.path.join(self.log_txt_loc, "log.txt")
        self.target_file = self.workflow[0]["vasp.out"]
        self.target_str = "RHOSYG internal error: stars are not distinct, try to increase SYMPREC to e.g."
        
        
        
    def check(self):
        #this method is not active until the job is done
        if Queue_std_files(cal_loc=self.cal_loc, workflow=self.workflow).find_std_files() == [None, None]:
            return True
        
        if find_target_str(cal_loc=self.cal_loc, target_file=self.target_file, target_str=self.target_str):
            self.write_error_log()
            return False
        else:
            return True
            
    
    def write_error_log_(self):
        with open(self.log_txt, "a") as f:
            f.write("{} Error: {}\n".format(get_time_str(), self.firework_name))
            for target_str in self.target_str_list:
                f.write("\t\t{}\n".format(target_str))
            os.rename(os.path.join(self.cal_loc, "__running__"), os.path.join(self.cal_loc, "__error__"))
            f.write("\t\t\t__running__ --> __error__\n")
            f.write("\t\t\t write __rhosyg__ into __error__\n")
            super(Vasp_out_rhosyg, self).write_error_tag("__rhosyg__")
            
    def write_error_log(self):
        super(Vasp_out_rhosyg, self).write_error_log(target_error_str=self.target_str, error_type="__rhosyg__")
    
    def correct(self):
        incar_dict = modify_vasp_incar(cal_loc=self.cal_loc)
        SYMPREC = float(incar_dict.get("SYMPREC", 1.0e-5))
        ISYM = int(incar_dict.get("ISYM", 2))
        
        if 1.0e-4 > SYMPREC:
            super(Vasp_out_rhosyg, self).backup()
            modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"SYMPREC": 1.0e-4}, rename_old_incar=False)
            with open(self.log_txt, "a") as f:
                f.write("{} Correction: {}\n".format(get_time_str(), self.firework_name))
                f.write("\t\t\tSYMPREC: {} --> 1.0e-4\n".format(SYMPREC))
            return True
        elif ISYM != 0:
            super(Vasp_out_rhosyg, self).backup()
            with open(self.log_txt, "a") as f:
                f.write("{} Correction: {}\n".format(get_time_str(), self.firework_name))
                f.write("\t\t\tISYM: {} --> 0\n".format(ISYM))
            return True
        else:
            return False                        


# In[18]:


class Electronic_divergence(Vasp_Error_Logger, Vasp_Error_Saver):
    """
    Error checking type: on the fly & after the calculation.
    Check if electonic cal divergences and the max ionoic step is reached.
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
        self.log_txt_loc, self.firework_name = os.path.split(cal_loc)
        self.log_txt = os.path.join(self.log_txt_loc, "log.txt")
        #super(Electronic_divergence, self).__init__(cal_loc)
        #Write_and_read_error_tag.__init__(self, cal_loc=self.cal_loc)
     
    #Because method check is called on the fly, this decorator avoids the case where OUTCAR 
    #has not been generated while calling this method
    @file_existence_decorator("OUTCAR")
    def check(self):
        NELM = find_incar_tag_from_OUTCAR(tag="NELM", cal_loc=self.cal_loc)
        EDIFF = find_incar_tag_from_OUTCAR(tag="EDIFF", cal_loc=self.cal_loc)
        #print(NELM, EDIFF)
        oszicar = Oszicar(os.path.join(self.cal_loc, "OSZICAR"))
        for electronic_steps in oszicar.electronic_steps:
            #print(len(electronic_steps))
            if len(electronic_steps) == NELM:
                last_step = electronic_steps[-1]
                #print(last_step["dE"], last_step["deps"])
                if abs(last_step["dE"]) > EDIFF or abs(last_step["deps"]) > EDIFF:
                    self.write_error_log()
                    return False
        return True
    
    def write_error_log_(self):
        with open(self.log_txt, "a") as f:
            f.write("{} Error: Electronic divergence happens at {}\n".format(get_time_str(), self.firework_name))
            os.rename(os.path.join(self.cal_loc, "__running__"), os.path.join(self.cal_loc, "__error__"))
            f.write("\t\t\t__running__ --> __error__\n")
            f.write("\t\t\twrite __electronic_divergence__ into __error__\n")
            super(Electronic_divergence, self).write_error_tag("__electronic_divergence__")
            
    def write_error_log(self):
        error_str = "Electronic divergence happens"
        super(Electronic_divergence, self).write_error_log(target_error_str=error_str, error_type="__electronic_divergence__")
    
    @file_existence_decorator("OUTCAR", False)
    def correct(self):
        """
        Orders of corrections:
            1st choice: if ALGO != Normal, set ALGO = Normal and NELM = 100 if original NELM < 100.
            2nd choice: AMIX=0.1, BMIX = 0.01, ICHARG = 2
            3rd choice: AMIN=0.01, BMIX=3.0, ICHARG =2
            4th choice: return False <-- fail to automatically recover.
            
        """
        NELM = find_incar_tag_from_OUTCAR(tag="NELM", cal_loc=self.cal_loc)
        EDIFF = find_incar_tag_from_OUTCAR(tag="EDIFF", cal_loc=self.cal_loc)
        IALGO = find_incar_tag_from_OUTCAR(tag="IALGO", cal_loc=self.cal_loc) # IALGO=38 <--> ALGO=Normal
        incar = modify_vasp_incar(cal_loc=self.cal_loc)
        AMIX = float(incar.get("AMIX", 0.4))
        BMIX = float(incar.get("BMIX", 1.0))
        AMIN = float(incar.get("AMIN", 0.1))
        
        if IALGO != 38:
            if float(EDIFF)*0.1 <= 1.0E-4:
                EDIFF_ = 0.1 * EDIFF
            elif float(EDIFF)*0.5 <= 1.0E-4:
                EDIFF_ *= 0.5 * EDIFF
            
            
            super(Electronic_divergence, self).backup()
            NELM_ = NELM if NELM > 100 else 100
            modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"ALGO": "Normal", "NELM": NELM_, "EDIFF": EDIFF_}, 
                              rename_old_incar=False)
            
            with open(self.log_txt, "a") as f:
                f.write("{} Correction: reset INCAR tags\n".format(get_time_str()))
                f.write("\t\t\tALGO = Normal\n\t\t\tNELM = {}\n".format(NELM))
                f.write("\t\t\tEDIFF = from {} to {}\n".format(EDIFF, EDIFF_))
                f.write("\t\t\tNELM = from {} to {}\n".format(NELM, NELM_))
            return True
        
        #print("AMIX={}, BMIX={}, AMIN={}".format(AMIX, BMIX, AMIN))
        #print("AMIX > 0.1 ={}, BMIX > 0.01={}".format(AMIX > 0.1, BMIX > 0.01))
        if AMIX > 0.1 and BMIX > 0.01:
            super(Electronic_divergence, self).backup()
            NELM_ = 150 if NELM < 150 else NELM
            modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"AMIX": 0.1, "BMIX": 0.01, "ICHARG": 2, "NELM": NELM_}, 
                              rename_old_incar=False)
            with open(self.log_txt, "a") as f:
                f.write("{} Correction: reset INCAR tags\n".format(get_time_str()))
                f.write("\t\t\tAMIX = 0.1\n")
                f.write("\t\t\tBMIX = 0.01\n")
                f.write("\t\t\tICHARG = 2\n")
                f.write("\t\t\tNELM = {}\n".format(NELM_))
            return True
        
        #print("Second method")
        if BMIX < 3.0 and AMIN > 0.01:
            super(Electronic_divergence, self).backup()
            NELM_ = 200 if 200 > NELM else NELM
            modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"AMIN": 0.01, "BMIX": 3.0, "ICHARG": 2, "NELM": NELM_}, 
                              remove_tags=["AMIX"], rename_old_incar=False)
            with open(self.log_txt, "a") as f:
                f.write("{} Correction: reset INCAR tags\n".format(get_time_str()))
                f.write("\t\t\tAMIN = 0.01\n")
                f.write("\t\t\tBMIX = 3.0\n")
                f.write("\t\t\tICHARG = 2\n")
                f.write("\t\t\tNELM = {}\n".format(NELM_))
                f.write("\t\t\tremove AMIX\n")
            return True
        
        return False
    


# In[19]:


class Ionic_divergence(Vasp_Error_Logger, Vasp_Error_Saver):
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
        self.log_txt_loc, self.firework_name = os.path.split(cal_loc)
        self.log_txt = os.path.join(self.log_txt_loc, "log.txt")
        
        #Write_and_read_error_tag.__init__(self, cal_loc=self.cal_loc)
        
    def check(self):
        
        #This if statement deactivates the check method until the calculation is done.
        if Queue_std_files(cal_loc=self.cal_loc, workflow=self.workflow).stdout_file == [None, None]:
            return True
        
        NSW = find_incar_tag_from_OUTCAR(tag="NSW", cal_loc=self.cal_loc)
        IBRION = find_incar_tag_from_OUTCAR(tag="IBRION", cal_loc=self.cal_loc)
        #EDIFFG = find_incar_tag_from_OUTCAR(tag="EDIFFG", cal_loc=self.cal_loc)
        #This if statement deactivates the check method unless the calculation is the structural optimization
        if NSW == 0 or IBRION == -1:
            return True
        
        target_str = "reached required accuracy - stopping structural energy minimisation"
        if find_target_str(cal_loc=self.cal_loc, target_file="OUTCAR", target_str=target_str):
            return True
         
        #v = Vasprun(os.path.join(self.cal_loc, "vasprun.xml"))
        #max_force = max([np.linalg.norm(a) for a in v.ionic_steps[-1]["forces"]])
        #if max_force
        
        self.write_error_log()
        return False
    
    def write_error_log_(self):
        with open(self.log_txt, "a") as f:
            f.write("{} Error: Ionic divergence happens at {}\n".format(get_time_str(), self.firework_name))
            os.rename(os.path.join(self.cal_loc, "__running__"), os.path.join(self.cal_loc, "__error__"))
            f.write("\t\t\t__running__ --> __error__\n")
            f.write("\t\t\twrite __ionic_divergence__ into __error__\n")
            super(Ionic_divergence, self).write_error_tag("__ionic_divergence__")
            
    def write_error_log(self):
        error_str = "Ionic divergence happens"
        super(Ionic_divergence, self).write_error_log(target_error_str=error_str, error_type="__ionic_divergence__")
    
    @file_existence_decorator("OSZICAR", False)
    @file_existence_decorator("OUTCAR", False)
    def correct(self):
        
        EDIFF = find_incar_tag_from_OUTCAR(cal_loc=self.cal_loc, tag="EDIFF")
        EDIFFG = find_incar_tag_from_OUTCAR(cal_loc=self.cal_loc, tag="EDIFFG")
        NSW = find_incar_tag_from_OUTCAR(cal_loc=self.cal_loc, tag="NSW")
        
        oszicar = Oszicar(filename=os.path.join(self.cal_loc, "OSZICAR"))
        if len(oszicar.electronic_steps) < NSW:
            super(Ionic_divergence, self).backup()
            shutil.move(os.path.join(self.cal_loc, "CONTCAR"), os.path.join(self.cal_loc, "POSCAR"))
            with open(self.log_txt, "a") as f:
                f.write("{} Correction: This error may be due to that the walltime is reached.\n".format(get_time_str()))
                #f.write("\t\t\tstdout_file --> stdout_file{}\n".format(new_suffix, new_suffix))
                #f.write("\t\t\tINCAR --> INCAR{}\n".format(new_suffix))
                #f.write("\t\t\tPOSCAR --> POSCAR{}\n".format(new_suffix))
                #f.write("\t\t\tXDATCAR --> XDATCAR{}\n".format(new_suffix))
                #f.write("\t\t\tOUTCAR --> OUTCAR{}\n".format(new_suffix))
                f.write("\t\t\tCONTCAR --> POSCAR\n")
                #f.write("\t\t\t{} --> {}{}\n".format(self.workflow[0]["vasp.out"], self.workflow[0]["vasp.out"], new_suffix))
            return True
        else:
            return False
        


# In[20]:


class Positive_energy(Vasp_Error_Logger, Vasp_Error_Saver):
    """
    Error checking type: on the fly & after the calculation.
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
        self.log_txt_loc, self.firework_name = os.path.split(cal_loc)
        self.log_txt = os.path.join(self.log_txt_loc, "log.txt")
        #super(Positive_energy, self).__init__(cal_loc)
        #Write_and_read_error_tag.__init__(self, cal_loc=self.cal_loc)
    
    #Because method check is called on the fly, this decorator avoids the case where OUTCAR 
    #has not been generated while calling this method
    @file_existence_decorator("OSZICAR")
    def check(self):
        oszicar = Oszicar(os.path.join(self.cal_loc, "OSZICAR"))
        for ionic_step in oszicar.ionic_steps:
            if ionic_step["E0"] > 0:
                self.write_error_log()
                return False
        return True
    
    def write_error_log_(self):
        with open(self.log_txt, "a") as f:
            f.write("{} Error: Positive energy has been found at {}\n".format(get_time_str(), self.firework_name))
            f.write("\t\t\t__running__ --> __error__\n")
            os.rename(os.path.join(self.cal_loc, "__running__"), os.path.join(self.cal_loc, "__error__"))
            f.write("\t\t\twrite __positive_energy__ into __error__\n")
            super(Positive_energy, self).write_error_tag("__positive_energy__")
            
    def write_error_log(self):
        error_str = "Positive energy has been found"
        super(Positive_energy, self).write_error_log(target_error_str=error_str, error_type="__positive_energy__")
    
    @file_existence_decorator("OUTCAR", False)
    def correct(self):
        IALGO = find_incar_tag_from_OUTCAR(cal_loc=self.cal_loc, tag="IALGO")
        
        if IALGO != 38:
            super(Positive_energy, self).backup()
            modify_vasp_incar(cal_loc=self.cal_loc, new_tags={"ALGO": "Normal"}, rename_old_incar=False)
            with open(self.log_txt, "a") as f:
                f.write("{} Correction: ALGO --> Normal\n".format(get_time_str()))
                #f.write("\t\t\tINCAR --> INCAR{}\n".format(new_suffix))
                #f.write("\t\t\tstdout_file --> stdout_file{}\n".format(new_suffix))
                #f.write("\t\t\tstderr_file --> stderr_file{}\n".format(new_suffix))
                #f.write("\t\t\tOSZICAR --> OSZICAR{}\n".format(new_suffix))
                #f.write("\t\t\tOUTCAR --> OUTCAR{}\n".format(new_suffix))
                #f.write("\t\t\t{} --> {}{}\n".format(self.workflow[0]["vasp.out"], self.workflow[0]["vasp.out"], new_suffix))
            return True
        
        return False


# In[21]:


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
        return True
    
    def correct(self):
        return False
    
    def write_error_log(self):
        pass

