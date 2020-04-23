#!/usr/bin/env python
# coding: utf-8

# In[69]:


import os, sys, re, math, shutil, json
HTC_package_path = "C:/Users/tyang/Documents/Jupyter_workspace/HTC/python_3"
if  os.path.isdir(HTC_package_path) and HTC_package_path not in sys.path:
    sys.path.append(HTC_package_path)

from HTC_lib.VASP.INCAR.modify_vasp_incar import modify_vasp_incar


# In[24]:


__doc__ = """
    What this script does:
        It runs a series of calculations with different SIGMA and determines the nth largest SIGMA w.r.t which the term T*S in OUTCAR is converged.
        
    The command line to call this script looks like below:
    >>>python SIGMA_convergence.py [--start:float] --end:float --step:float [--TS_convergence:float] [--which:integer] [--incar_template:filename] [--help]
    
    Arguments in a pair of brackets are optional
    * --start (float): the starting SIGMA. Default: 0.01
    * --end (float): the ending SIGMA. Default: 1
    * --step (float): the increment of SIGMA in the SIGMA testing. Default: 0.02
    * --TS_convergence (float in meV/atom): For ISMEAR>=0 (the Gaussian or Methfessel-Paxton smearing), SIGMA should be chosen in such a way that
            the term "entropy T*S" in OUTCAR is small (i.e. < 1-2meV/atom). --TS_convergence specifies this criterion of T*S in meV/atom.
            Default: 1
    * --which (1-based integer index): choose the "which"th largest SIGMA w.r.t. which the term T*S OUTCAR is converged.
                                        Default: 1
    * --incar_template (str): When writing INCAR, sorting INCAR tags in the same order as in the file referred by --incar_template.
    * --help: Explain how to use this script and the input arguments.
    Note that there must be no whitespace in the argument-value pair.
    Note that after the first execution of this script, the parsed arguments will be saved into a file named as "sigma_convergence_setup.json".
        Whenever sigma_convergence_setup.json exists, the passed arguments in the command line will all be omitted and those in sigma_convergence_setup.json
        will be used. "sigma_convergence_setup.json" makes the SIGMA testing for each materials in the HTC calculations customizable.
        
    Return:
        If the converged SIGMA is successfully found:
            1. create a file named "INCAR.optimal" with the converged SIGMA
            2. __sub_dir_cal__ --> __done__
        else:
            __sub_dir_cal__ --> __manual__
        """


# In[26]:


def read_and_set_default_arguments(argv_list):
    """ Parse cmd arguments and set default argument 
    OR
    Read arguments from a file named "sigma_convergence_setup.json" under the folder where this script is called.
    """
    
    if os.path.isfile("sigma_convergence_setup.json"):
        with open("sigma_convergence_setup.json", "r") as setup:
            argv_dict = json.load(setup)
    else:
        with open("POSCAR", "r") as poscar:
            for line_ind, line in enumerate(poscar):
                if line_ind in [5, 6]:
                    no_of_atoms = sum([int(atom_no) for atom_no in re.findall("[0-9]+", line)])
                    if no_of_atoms > 0: break
        
        raw_argv_dict = {key.lower(): value for key, value in [argv.split(":") for argv in argv_list[1:]]}
        argv_dict = {}
        
        
        try:
            argv_dict["start"] = float(raw_argv_dict.get("--start", 0.01))
        except:
            print(__doc__)
            raise Exception("The value passed to --start should be a floating point number. default: 0.01")
        
        try:
            argv_dict["end"] = float(raw_argv_dict.get("--end", 1))
        except:
            print(__doc__)
            raise Exception("The value passed to --end should be a floating point number. default: 1")
        
        try:
            argv_dict["step"] = float(raw_argv_dict.get("--step", 0.02))
        except:
            print(__doc__)
            raise Exception("The value passed to --step should be a floating point number. default: 0.02")
            
            
        argv_dict["incar_template"] = raw_argv_dict.get("--incar_template", "")
        if argv_dict["incar_template"]:
            assert os.path.isfile(argv_dict["incar_template"]), "The file specified via --incar_template doesn't exist"
        
        argv_dict["TS_convergence_unit"] = "eV"
        try:
            argv_dict["TS_convergence"] = float(raw_argv_dict.get("--TS_convergence", 1)) / 1000. * no_of_atoms # convert meV/atom to eV
        except:
            print(__doc__)
            raise Exception("The TS convergence criterion via '--TS_convergence' in the command line")
            
        try:
            argv_dict["which"] = int(raw_argv_dict.get("--which", 1))
        except:
            print(__doc__)
            raise Exception("--which is the 1-based index of the list of SIGMA in a descending order w.r.t which the term T*S in OUTCAR is converged.")
        
    
    with open("sigma_convergence_setup.json", "w") as setup:
        json.dump(argv_dict, setup, indent=4)
        
    sigma_list, sigma, step, end = [], argv_dict["start"], argv_dict["step"], argv_dict["end"]
    while sigma <= end:
        sigma_list.append(sigma)
        sigma += step
    argv_dict["sigma_list"] = sigma_list
    
    return argv_dict             
            


# In[27]:


def prepare_cal_files(argv_dict):
    
    
    for sigma in argv_dict["sigma_list"]:
        is_preparation_needed = True
        sub_dir_name = "sigma_" + str(sigma)
        
        if not os.path.isdir(sub_dir_name):
            os.mkdir(sub_dir_name)
        else:
            file_list = os.listdir(sub_dir_name)
            for filename in file_list:
                if filename.startswith("__") and filename.endswith("__"):
                    #The presence of any HTC signal file indicates that the sub-dir VASP calculation input files were prepared.
                    is_preparation_needed = False
                    break
                
        incar_dict = modify_vasp_incar(".")
        assert int(incar_dict["ISMEAR"]) >= 0, "SIGMA is valid only for the Gaussian (ISMEAR=0) or Methfessel-Paxton smearing (ISMEAR>0, normally 1 or 2)"
        
        if is_preparation_needed:
            shutil.copy("POSCAR", os.path.join(sub_dir_name, "POSCAR"))
            shutil.copy("KPOINTS", os.path.join(sub_dir_name, "KPOINTS"))
            shutil.copy("POTCAR", os.path.join(sub_dir_name, "POTCAR"))
            shutil.copy("INCAR", os.path.join(sub_dir_name, "INCAR"))
            
            if argv_dict["incar_template"] == "":
                modify_vasp_incar(sub_dir_name, new_tags={"SIGMA": sigma}, rename_old_incar=False)
            else:
                modify_vasp_incar(sub_dir_name, new_tags={"SIGMA": sigma}, rename_old_incar=False, incar_template=argv_dict["incar_template"])
            
            open(os.path.join(sub_dir_name, "__ready__"), "w").close()
            
            
        


# In[28]:


def are_all_sub_dir_cal_finished(argv_dict):
    
    for sigma in argv_dict["sigma_list"]:
        sub_dir_name = "sigma_" + str(sigma)
        
        if not os.path.isfile(os.path.join(sub_dir_name, '__done__')):
            if not os.path.isfile(os.path.join(sub_dir_name, "__done_clean__")):
                return False
        
    return True


# In[30]:


def find_converged_sigma(argv_dict):
    """ Find the "--which"th largest SIGMA w.r.t. which T*S in OUTCAR is converged.
        
    return:
        if such SIGMA is found, return such SIGMA;
        otherwise, return 0
    """
    
    TS_list = []
    
    for sigma in argv_dict["sigma_list"]:
        sub_dir_name = "sigma_" + str(sigma)

        is_TS_found = False
        with open(os.path.join(sub_dir_name, "OUTCAR"), "r") as outcar:
            for line in outcar:
                if "entropy T*S    EENTRO =" in line:
                    TS = float(line.split("=")[1].strip())
                    is_TS_found = True
                    break
        if is_TS_found == False:#"Fail to parse T*S from {}".format(os.path.join(sub_dir_name, "OUTCAR"))
            open("__fail_to_parse_TS_from_OUTCAR_under_{}__".format(sub_dir_name), "w").close()
            return 0
    
    
    with open("SIGMA_VS_TS_Summary.dat", "w") as summary:
        summary.write("SIGMA\tTS\n")
        for sigma, TS in zip(argv_dict["sigma_list"], TS_list):
            summary.write("{}\t{}\n".format(sigma, TS))
    
    TS_ind = 0
    while TS_list[TS_ind] <= argv_dict["TS_convergence"]:
        TS_ind += 1
    
    if TS_ind >=1:
        if TS_ind - argv_dict["which"] >= 0:
            return argv_dict["sigma_list"][TS_ind - argv_dict["which"]]
        else:
            return 0
    else:
        return 0


# In[74]:


if __name__ == "__main__":
    #print(__doc__)
    
    argv_dict = read_and_set_default_arguments(sys.argv)
    prepare_cal_files(argv_dict)
    if are_all_sub_dir_cal_finished(argv_dict):
        converged_sigma = find_converged_sigma(argv_dict)
        if converged_sigma == 0:
            os.rename("__sub_dir_cal__", "__manual__")
        else:
            shutil.copy(os.path.join("sigma_"+str(converged_sigma), "INCAR"), "INCAR.optimal")
            os.rename("__sub_dir_cal__", "__done__")

