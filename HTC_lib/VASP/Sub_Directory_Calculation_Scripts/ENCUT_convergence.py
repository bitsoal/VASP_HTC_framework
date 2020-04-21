#!/usr/bin/env python
# coding: utf-8

# In[69]:


import os, sys, re, math, shutil, json
HTC_package_path = "C:/Users/tyang/Documents/Jupyter_workspace/HTC/python_3"
if  os.path.isdir(HTC_package_path) and HTC_package_path not in sys.path:
    sys.path.append(HTC_package_path)

from HTC_lib.VASP.INCAR.modify_vasp_incar import modify_vasp_incar


# In[73]:


__doc__ = """
    What this script does:
        It runs a series of calculations with different ENCUT and determines the converged ENCUT w.r.t the total energy.
        
    The command line to call this script looks like below:
    >>>python ENCUT_convergence.py [--start:integer] --end:integer --step:integer --convergence:AB [--incar_template:filename] --help
    Arguments in a pair of brackets are optional
    * --start (integer): the starting ENCUT. Default: max(ENMAX) in POTCAR
    * --end (integer): the ending ENCUT. No default value
    * --step (integer): the increment of ENCUT in the ENCUT testing. Default: 50
    * --convergence : The total energy convergence. It has a form --convergence=AB, where A is the convergence criterion and B is the
                    unit which could be eV/atom, meV/atom, eV or meV. No default value.
    * --incar_template (str): When writing INCAR, sorting INCAR tags in the same order as in the file referred by --incar_template.
    * --help: Explain how to use this script and the input arguments.
    Note that there must be no whitespace in the argument-value pair.
    Note that after the first execution of this script, the parsed arguments will be saved into a file named as "encut_convergence_setup.json".
        Whenever encut_convergence_setup.json exists, the passed arguments in the command line will all be omitted and those in encut_convergence_setup.json
        will be used. "encut_convergence_setup.json" makes the ENCUT testing for each materials in the HTC calculations customizable.
        
    Return:
        If the converged ENCUT is successfully found:
            1. create a file named "INCAR.optimal" with the converged ENCUT
            2. __sub_dir_cal__ --> __done__
        else:
            __sub_dir_cal__ --> __manual__
        """


# In[68]:


def read_and_set_default_arguments(argv_list):
    """ Parse cmd arguments and set default argument 
    OR
    Read arguments from a file named "encut_convergence_setup.json" under the folder where this script is called.
    """
    
    if os.path.isfile("encut_convergence_setup.json"):
        with open("encut_convergence_setup.json", "r") as setup:
            argv_dict = json.load(setup)
    else:
        with open("POSCAR", "r") as poscar:
            for line_ind, line in enumerate(poscar):
                if line_ind in [5, 6]:
                    no_of_atoms = sum([int(atom_no) for atom_no in re.findall("[0-9]+", line)])
                    if no_of_atoms > 0: break
                                
        with open("POTCAR", "r") as potcar:
            enmax_list = []
            for line in potcar:
                if "ENMAX" in line:
                    enmax_list.append(float(line.split(";")[0].split("=")[1]))
        enmax = round(max(enmax_list)/5.)*5
        
        raw_argv_dict = {key.lower(): value for key, value in [argv.split(":") for argv in argv_list[1:]]}
        argv_dict = {}
        
        start_value = raw_argv_dict.get("--start", enmax)
        if isinstance(start_value, str):
            try:
                start_value = int(start_value)
            except:
                raise Exception("The value passed to --start should be an integer.")
        argv_dict["start"] = start_value
        
        try:
            print(float(raw_argv_dict["--end"]))
            argv_dict["end"] = int(raw_argv_dict["--end"])
        except:
            raise Exception("You must set the starting ENCUT via '--start' in the command line. It should be an integer")
        
        try:
            argv_dict["step"] = int(raw_argv_dict.get("--step", 50))
        except:
            raise Exception("The value passed to --step should be an integer")
            
            
        argv_dict["incar_template"] = raw_argv_dict.get("--incar_template", "")
        assert os.path.isfile(argv_dict["incar_template"]), "The file specified via --incar_template doesn't exist"
        
        try:
            convergence= raw_argv_dict["--convergence"].lower()
        except:
            raise Exception("You must set the energy convergence criterion via '--convergence' in the command line")
        #the below if clause convert criterion to eV.
        argv_dict["criterion_unit"] = "ev"
        if "mev/atom" in convergence:
            argv_dict["convergence"] = float(convergence.split("mev/atom")[0])*no_of_atoms/1000.
        elif "ev/atom" in convergence:
            argv_dict["convergence"] = float(convergence.split("ev/atom")[0])*no_of_atoms
        elif "mev" in convergence:
            argv_dict["convergence"] = float(convergence.split("mev")[0])/1000.
        elif "ev" in convergence:
            argv_dict["convergence"] = float(convergence.split("ev"))
        else:
            raise Exception("The energy convergence criterion should be set by '--convergence=AB', where A is a number and B should be ev, mev, ev/atom or mev/atom")
        
    
    with open("encut_convergence_setup.json", "w") as setup:
        json.dump(argv_dict, setup, indent=4)
        
    encut_list, encut, step, end = [], argv_dict["start"], argv_dict["step"], argv_dict["end"]
    while encut <= end:
        encut_list.append(encut)
        encut += step
    argv_dict["encut_list"] = encut_list
    
    return argv_dict             
            


# In[34]:


def prepare_cal_files(argv_dict):
    
    is_preparation_needed = True
    for encut in argv_dict["encut_list"]:
        sub_dir_name = "encut_" + str(encut)
        if not os.path.isdir(sub_dir_name):
            os.mkdir(sub_dir_name)
        
        file_list = os.listdir(sub_dir_name)
        for filename in file_list:
            if filename.startswith("__") and filename.endswith("__"):
                #The presence of any HTC signal file indicates that the sub-dir VASP calculation input files were prepared.
                is_preparation_needed = False
                break
        
        if is_preparation_needed:
            shutil.copy("POSCAR", os.path.join(sub_dir_name, "POSCAR"))
            shutil.copy("KPOINTS", os.path.join(sub_dir_name, "KPOINTS"))
            shutil.copy("POTCAR", os.path.join(sub_dir_name, "POTCAR"))
            shutil.copy("INCAR", os.path.join(sub_dir_name, "INCAR"))
            
            if argv_dict["incar_template"] == "":
                modify_vasp_incar(sub_dir_name, new_tags={"ENCUT": encut}, rename_old_incar=False)
            else:
                modify_vasp_incar(sub_dir_name, new_tags={"ENCUT": encut}, rename_old_incar=False, incar_template=argv_dict["incar_template"])
            
            open(os.path.join(sub_dir_name, "__ready__"), "w").close()
            
            
        


# In[38]:


def are_all_sub_dir_cal_finished(argv_dict):
    
    for encut in argv_dict["encut_list"]:
        sub_dir_name = "encut_" + str(encut)
        
        if not os.path.isfile(os.path.join(sub_dir_name, '__done__')):
            if not os.path.isfile(os.path.join(sub_dir_name, "__done_clean__")):
                return False
        
    return True


# In[62]:


def find_converged_encut(argv_dict):
    """ Find the converged ENCUT w.r.t. the total Energy E0 in OSZICAR.
    
    We have calculated the total energy (E0 in OSZICAR) of a given system for a series of ENCUT(i).
    ENCUT(i) are in an ascending order
    Let's arrange these total energy, E0(i), in the same order of ENUCT(i).
    Calculate the energy difference: dE0(i) = abs(E0(i+1)-E0(i))
    The covergence of ENCUT w.r.t E0 is reached only if there are at least two consecutive dE0(i) that meet the pre-defined convergence criterion.
    Assuming dE0(i)=E0(i+1)-E0(i) and dE0(i+1)=E0(i+2)-E0(i+1) are the first two consecutive satisfied dE, we choose the ENCUT corresponding to 
        E0(i+1) as the converged ENCUT
        
    return:
        if there is such a E0(i+1), return the corresponding ENCUT, i.e. ENUCT(i+1);
        otherwise, return 0
    """
    
    energy_list = []
    
    for encut in argv_dict["encut_list"]:
        sub_dir_name = "encut_" + str(encut)
        
        with open(os.path.join(sub_dir_name, "OSZICAR"), "r") as oszicar:
            for line in oszicar:
                pass
        try:
            energy = float(re.search("E0=([\s0-9E\.\-\+]+)d E", line)[1].strip())
            energy_list.append(energy)
        except:
            raise Exception("Fail to parse energy E0 from {}".format(os.path.join(sub_dir_name, "OSZICAR")))
            
    energy_diff_list = [energy_2 - energy_1 for energy_1, energy_2 in zip(energy_list[:-1], energy_list[1:])]
    
    with open("ENCUT_VS_E0_Summary.dat", "w") as summary:
        summary.write("ENCUT\tE0\tdE0\n")
        for encut, energy, energy_diff in zip(argv_dict["encut_list"], energy_list, energy_diff_list):
            summary.write("{}\t{}\t{}\n".format(encut, energy, energy_diff))
        summary.write("{}\t{}\n".format(argv_dict["encut_list"][-1], energy_list[-1]))
    
    count = 0
    for energy_diff_ind, energy_diff in enumerate(energy_diff_list):
        if abs(energy_diff ) <= argv_dict["convergence"]:
            count += 1
        else:
            count = 0
            
        if count == 2:
            return argv_dict["encut_list"][energy_diff_ind]
        
    return 0  


# In[74]:


if __name__ == "__main__":
    print(__doc__)
    
    argv_dict = read_and_set_default_arguments(sys.argv)
    prepare_cal_files(argv_dict)
    if are_all_sub_dir_cal_finished(argv_dict):
        converged_ENCUT = find_converged_encut(argv_dict)
        if converged_ENCUT == 0:
            os.rename("__sub_dir_cal__", "__manual__")
        else:
            shutil.copy(os.path.join("encut_"+str(converged_ENCUT), "INCAR"), "INCAR.optimal")
            os.rename("__sub_dir_cal__", "__done__")

