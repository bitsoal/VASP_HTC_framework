#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os, sys

##############################################################################################################
##DO NOT change this part.
##../setup.py will update this variable
HTC_package_path = "C:/Users/tyang/Documents/Jupyter_workspace/HTC/python_3"
assert os.path.isdir(HTC_package_path), "Cannot find this VASP_HTC package under {}".format(HTC_package_path)
if HTC_package_path not in sys.path:
    sys.path.append(HTC_package_path)
##############################################################################################################
from HTC_lib.VASP.Miscellaneous.Execute_bash_shell_cmd import Execute_shell_cmd


# In[2]:


def get_trimed_oszicar(cal_loc, original_oszicar, output_oszicar):
    with open(os.path.join(cal_loc, original_oszicar), "r") as oszicar_f:
        oszicar_lines = list(oszicar_f)
        
    last_eff_line_ind = 0
    for line_ind, line in enumerate(oszicar_lines):
        if "E0=" in line and "F=" in line:
            last_eff_line_ind = line_ind
    
    if last_eff_line_ind == 0:
        return False
    else:
        with open(os.path.join(cal_loc, output_oszicar), "w") as oszicar_f:
            for line in oszicar_lines[:last_eff_line_ind+1]:
                oszicar_f.write(line)
        return True


# In[ ]:


def update_kpoints_as_per_kpoints_cmd(cal_loc, firework, remove_existing_KPOINTS = True):
    """
    This function is invoked to (a) remove existing KPOINTS (only if remove_existing_KPOINTS=True) and (b) create 
    a new KPOINTS according to the command(s) specified by tag 'kpoints_cmd'.
    """
    if remove_existing_KPOINTS:
        if os.path.isfile(os.path.join(cal_loc, "KPOINTS")):
            os.remove(os.path.join(cal_loc, "KPOINTS"))
    #Note: In the case that tag 'update_kpoints_every_round' is activated, tag 'kpoints_cmd' has been checked and would
    #      not be empty or not set in Parse_calculation_workflow.py. 
    #The relevant logs will be written by Execute_shell_cmd
    status = Execute_shell_cmd(cal_loc=cal_loc, user_defined_cmd_list=firework["kpoints_cmd"], 
                               where_to_execute=cal_loc, defined_by_which_htc_tag="kpoints_cmd")
    
    output_str = "Since update_kpoints_every_round is activated and this structure optimization changes "
    output_str += "either the cell shape or cell volume, KPOINTS is also updated as per tag 'kpoints_cmd'. "
    output_str += "The results of 'kpoints_cmd' is what's above the preceding Correction line."
            
    if status == False: 
        return False, output_str #If the commands failed to run, stop running the following codes.
    else:
        return True, output_str


# In[5]:


if __name__ == "__main__":
    print(get_trimed_oszicar(".", "OSZICAR", "OSZICAR_111"))

