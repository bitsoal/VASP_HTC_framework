#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os, sys
HTC_package_path = "C:/Users/tyang/Documents/Jupyter_workspace/HTC/python_3"
if  os.path.isdir(HTC_package_path) and HTC_package_path not in sys.path:
    sys.path.append(HTC_package_path)
    
from HTC_lib.VASP.INCAR.modify_vasp_incar import modify_vasp_incar
from HTC_lib.VASP.POSCAR.POSCAR_IO_functions import read_poscar
from HTC_lib.VASP.Miscellaneous.Utilities import get_current_firework_from_cal_loc, get_time_str

from pymatgen.core import Structure


# In[2]:


def choose_ispin_based_on_prev_cal(current_cal_loc, prev_cal_step, mag_threshold, workflow):
    """
    Read the total magnetic moment (tot_mag) from OSZICAR of the previous calculation step specified by prev_cal_step, and 
    compare it with mag_threshold.
    mag_threshold: a dictionary with 2 key-value pairs - {"mag": a float number, "mag_type": "tot" or "per_atom"}
            e.g. {"mag": 0.02, "mag_type": "per_atom"} <--> the threshold is 0.02 Bohr magneton per atom.
                 {"mag": 0.02, "mag_type": "tot"} <--> the threshold is the total of 0.02 Bohr magneton.
    This function returns:
        I.  (1, tot_mag) if abs(tot_mag) <= mag_threshold.
        II. (2, tot_mag) otherwise;
    Note that there are four special cases:
        a) prev_cal_step should not be a sub-directory calculation, where there are multiple sub-dir calculations and 
            it is ambiguous to refer to the OSZICAR of which sub-dir cal. --> raise an error
        b) ispin is only meaningful if the current calculation is collinear;--> raise an error
        c) the previous calculation should be spin-polarized --> create __manual__ and __non_spin_polarized_prev_cal__, and return False
        d) OSZICAR of prev_cal_step does not exist --> create __manual__ and __no_prev_cal_OSZICAR__, and return False
    """    
    
    current_cal_step = get_current_firework_from_cal_loc(current_cal_loc, workflow)["firework_folder_name"]
    prev_cal_loc = os.path.join(current_cal_loc.split(current_cal_step)[0], prev_cal_step)
    prev_OSZICAR_path = os.path.join(current_cal_loc.split(current_cal_step)[0], prev_cal_step, "OSZICAR")
    prev_cal_firework = get_current_firework_from_cal_loc(prev_OSZICAR_path, workflow)
    
    #special case 1
    if prev_cal_firework["sub_dir_cal"]:
        output_str = "You are looking at OSZICAR of %s to decide ispin of %s. " % (prev_cal_loc, current_cal_loc)
        output_str += "But this function is not supported if the former calculation is a sub-dir calculation (sub_dir_cal=Yes in HTC_calculation_setup_file or HTC_calculation_setup_folder)"
        raise Exception(output_str)
    
    #special case 2
    current_incar_dict = modify_vasp_incar(current_cal_loc)
    LSORBIT = current_incar_dict.get("LSORBIT", ".FALSE.").strip().lower()
    if LSORBIT in [".true.", "t"]:
        output_str = "You are looking at OSZICAR of %s to decide ispin of %s. " % (prev_cal_loc, current_cal_loc)
        output_str += "But the latter calculation is non-collinear --> setting ispin is meaningless"
        raise Exception(output_str)
        
    #special case 3
    prev_incar_dict = modify_vasp_incar(prev_cal_loc)
    prev_ispin = int(prev_incar_dict.get("ISPIN", 1))
    if prev_ispin == 1:
        with open(os.path.join(current_cal_loc, "log.txt"), "a") as log_f:
            log_f.write("{}: You are trying to set ispin of the current step based on the previous calculation of {}\n".format(get_time_str(), prev_cal_step))
            log_f.write("\t\t\tHowever, the previous calculation is non-spin-polarized\n")
            log_f.write("\t\tNotwitdhstanding, let's assume the total magnetic moment of the previous step is 0.\n")
            log_f.write("\t\t\tCreate files __manual__ and __non_spin_polarized_prev_cal__ as a warning signal for you to check if this is what you want\n")
        open(os.path.join(current_cal_loc, "__manual__"), "w").close()
        open(os.path.join(current_cal_loc, "__non_spin_polarized_prev_cal__"), "w").close()
        #return False
        return 1, 0  #The 1st entry: The ISPIN value of the current calculation step; The 2nd entry: Since the previous calculation is non-spin polarized, the total magnetic moement should be zero.
    
    #special case 4
    if not os.path.isfile(prev_OSZICAR_path):
        with open(os.path.join(current_cal_loc, "log.txt"), "a") as log_f:
            log_f.write("{}: You are trying to set ispin of the current step based on the previous calculation of {}\n".format(get_time_str(), prev_cal_step))
            log_f.write("\t\t\tBut there is no OSZICAR under the former calculation folder\n")
            log_f.write("\t\t\tCreate files __manual__ and __no_prev_cal_OSZICAR__\n")
        open(os.path.join(current_cal_loc, "__manual__"), "w").close()
        open(os.path.join(current_cal_loc, "__no_prev_cal_OSZICAR__"), "w").close()
        return False
    else: 
        with open(prev_OSZICAR_path, "r") as oszicar_f:
            for last_line in oszicar_f:
                continue
        try:
            output_str = ""
            if "mag=" not in last_line:
                output_str = "No keyword 'mag=' in the last line of OSZICAR of the previous calculation step {}\n".format(prev_cal_step)
                raise Exception
            else:
                tot_mag = float(last_line.split("mag=")[1].strip())
        except:
            with open(os.path.join(current_cal_loc, "log.txt"), "a") as log_f:
                log_f.write("{}: You are trying to set ispin of the current step based on the previous calculation of {}\n".format(get_time_str(), prev_cal_step))
                log_f.write("\t\t\tBut it fails to parse the total magnetic moment from OSIZCAR of the previous calculation\n")
                log_f.write("\t\t\tCreate files __manual__ and __fail_to_parse_tot_mag_of_prev_cal__\n")
            open(os.path.join(current_cal_loc, "__manual__"), "w").close()
            open(os.path.join(current_cal_loc, "__fail_to_parse_tot_mag_of_prev_cal__"), "w").close()
            return False
        
        if mag_threshold["mag_type"] == "per_atom":
            total_no_of_atoms = read_poscar(poscar_filename="POSCAR", cal_loc=prev_cal_loc)["total_no_of_atoms"]
            #To debug read_poscar
            struct = Structure.from_file(os.path.join(prev_cal_loc, "POSCAR"))
            assert total_no_of_atoms == len(struct.species)
            
            tot_mag_threshold = total_no_of_atoms * mag_threshold["mag"]
        else:
            tot_mag_threshold = mag_threshold["mag"]
            
        if abs(tot_mag) <= tot_mag_threshold:
            return 1, tot_mag
        else:
            return 2, tot_mag
        

