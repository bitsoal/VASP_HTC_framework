
# coding: utf-8

# # created on March 31 2018

# In[4]:


import os, shutil

from pymatgen import Structure

from Utilities import get_time_str#, get_current_firework_from_cal_loc


# In[5]:


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
    
    #firework = get_current_firework_from_cal_loc(cal_loc, workflow)
    firework_name = os.path.split(cal_loc)[-1]
    log_txt = os.path.join(cal_loc, "log.txt")
    
    if not os.path.isfile(os.path.join(cal_loc, "POSCAR")):
        
        if workflow[0]["sort_structure"]:
            structure = Structure.from_file(os.path.join(structure_file_folder, structure_filename))
            structure = structure.get_sorted_structure()
            structure.to(fmt="poscar", filename=os.path.join(cal_loc, "POSCAR"))
            with open(log_txt, "a") as f:
                f.write("{} INFO: no POSCAR in {}\n".format(get_time_str(), firework_name))
                f.write("\t\t\tsrc: {}\n".format(os.path.join(structure_file_folder, structure_filename)))
                f.write("\t\t\ttag sort_structure is on\n")
                f.write("\t\t\tSo write a sorted structure into POSCAR using pymatgen.Structure\n".format(os.path.join(structure_file_folder, 
                                                                                                                     structure_filename)))        
        else:
            if Is_Vasp_POSCAR(structure_filename=structure_filename, structure_file_folder=structure_file_folder):
                src = os.path.join(structure_file_folder, structure_filename)
                dst = os.path.join(cal_loc, "POSCAR")
                shutil.copyfile(src=src, dst=dst)
                with open(log_txt, "a") as f:
                    f.write("{} INFO: no POSCAR in {}\n".format(get_time_str(), firework_name))
                    f.write("\t\t\tWe find that src is POSCAR-formated and tag sort_structure is off\n".format(src))
                    f.write("\t\t\tSo write POSCAR by copying\n")
                    f.write("\t\t\t\t\tsrc: {}\n".format(src))
                    f.write("\t\t\t\t\tdst: {}\n".format(dst))
            else:
                structure = Structure.from_file(os.path.join(structure_file_folder, structure_filename))
                structure.to(fmt="poscar", filename=os.path.join(cal_loc, "POSCAR"))
                with open(log_txt, "a") as f:
                    f.write("{} INFO: no POSCAR in {}\n".format(get_time_str(), firework_name))
                    f.write("\t\t\tsrc: {}".format(os.path.join(structure_file_folder, structure_filename)))
                    f.write("\t\t\tSeems src is not POSCAR-formated\n")
                    f.write("\t\t\ttag sort_structure is off\n")
                    f.write("\t\t\tSo write an unsorted structure into POSCAR using pymatgen.Structure\n")


# In[6]:


def Is_Vasp_POSCAR(structure_filename, structure_file_folder):
    """
    Check if structure_filename under folder structure_file_folder in the form of POSCAR.
    If it is POSCAR-formated, return True; Otherwise, return False.
    """
    with open(os.path.join(structure_file_folder, structure_filename), "r") as f:
        lines = []
        for line in f:
            lines.append([item.strip() for item in line.strip().split() if item.strip()])
            
    #The second line is the length scale --> a number only
    if len(lines[1]) != 1:
        return False
    else:
        try:
            float(lines[1][0])
        except:
            return False
    
    #The third-fith lines are lattice vectors --> three numbers each line
    if len(lines[2]) != 3 or len(lines[3]) != 3 or len(lines[4])!=3:
        return False
    else:
        try:
            for lattice_vec in lines[2:5]:
                for entry in lattice_vec:
                    float(entry)
        except:
            return False
        
    return True

