#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os, sys
HTC_package_path = "C:/Users/tyang/Documents/Jupyter_workspace/HTC/python_3"
if  os.path.isdir(HTC_package_path) and HTC_package_path not in sys.path:
    sys.path.append(HTC_package_path)

from pymatgen.io.vasp.sets import MPRelaxSet
from pymatgen import Structure

from HTC_lib.VASP.Miscellaneous.Utilities import get_time_str#, get_current_firework_from_cal_loc


# In[2]:


def Write_Vasp_POTCAR(cal_loc, structure_filename, workflow):
    """
    Write POTCAR in folder cal_loc as follows:
        If POTCAR is missing, write POTCAR using pymatgen.io.vasp.sets.MPRelaxSet
    Input arguments:
        cal_loc (str): the absolute path
        structure_filename (str): the file from which the structure is read using pymatgen.Structure.from_file
        workflow
    """
    
    #firework = get_current_firework_from_cal_loc(cal_loc, workflow)
    firework_name = os.path.split(cal_loc)[-1]
    log_txt = os.path.join(cal_loc, "log.txt")
    
    if not os.path.isfile(os.path.join(cal_loc, "POTCAR")):
        structure = Structure.from_file(os.path.join(cal_loc, structure_filename))
        vis = MPRelaxSet(structure=structure)
        vis.potcar.write_file(filename=os.path.join(cal_loc, "POTCAR"))
        write_INCAR = True
        with open(log_txt, "a") as f:
            f.write("{} INFO: no POTCAR in {}\n".format(get_time_str(), firework_name))
            f.write("\t\t\tuse pymatgen.io.vasp.sets.MPRelaxSet to write POTCAR\n")
      
    
    

