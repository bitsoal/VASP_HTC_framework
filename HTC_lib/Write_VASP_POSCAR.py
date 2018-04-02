
# coding: utf-8

# # created on March 31 2018

# In[3]:


import os, shutil

from pymatgen import Structure

from Utilities import get_time_str, get_current_firework_from_cal_loc


# In[2]:


def Write_Vasp_POSCAR(cal_loc, structure_filename, structure_file_folder, workflow):
    """
    Write POSCAR in folder cal_loc as follows:
        If no POSCAR in cal_loc, write POSCAR:
            If tag sort_structure is on, struture_filename under structure_file_folder is assumed in the form of POSCAR.
                In this case, just copy the file and rename it as POSCAR
            If tag sort_structure is off, write POSCAR using pymatgen.Structure
        If POSCAR is present, nothing has been done.
    Input arguments:
        cal_loc (str): the absolute path of the calculation folders
        structure_filename (str): the file from which the structure is read using pymatgen.Structure.from_file
        structure_file_folder (str): the absolute path of the folder where structure_filename can accessed.
        workflow
    """
    
    firework = get_current_firework_from_cal_loc(cal_loc, workflow)
    log_txt_loc, firework_name = os.path.split(cal_loc)
    log_txt = os.path.join(log_txt_loc, "log.txt")
    
    if not os.path.isfile(os.path.join(cal_loc, "POSCAR")):
        if workflow[0]["sort_structure"]:
            structure = Structure.from_file(os.path.join(structure_file_folder, structure_filename))
            structure = structure.get_sorted_structure()
            structure.to(fmt="poscar", filename=os.path.join(cal_loc, "POSCAR"))
            with open(log_txt, "a") as f:
                f.write("{} INFO: no POSCAR in {}\n".format(get_time_str(), firework_name))
                f.write("\t\t\twrite POSCAR using pymatgen.Structure from {}\n".format(os.path.join(structure_file_folder, 
                                                                                                    structure_filename)))
                
        else:
            src = os.path.join(structure_file_folder, structure_filename)
            dst = os.path.join(cal_loc, "POSCAR")
            shutil.copyfile(src=src, dst=dst)
            with open(log_txt, "a") as f:
                f.write("{} INFO: no POSCAR in {}\n".format(get_time_str(), firework_name))
                f.write("\t\t\ttag sort_structure is off\n")
                f.write("\t\t\twrite POSCAR by copying\n")
                f.write("\t\t\t\t\tsrc: {}\n".format(src))
                f.write("\t\t\t\t\tdst: {}\n".format(dst))

