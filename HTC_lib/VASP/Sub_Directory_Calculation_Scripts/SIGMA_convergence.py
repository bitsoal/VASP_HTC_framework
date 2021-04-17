#!/usr/bin/env python
# coding: utf-8

# In[69]:


import os, sys, re, math, shutil, json

##############################################################################################################
##DO NOT change this part.
##../setup.py will update this variable
HTC_package_path = "C:/Users/tyang/Documents/Jupyter_workspace/HTC/python_3"
assert os.path.isdir(HTC_package_path), "Cannot find this VASP_HTC package under {}".format(HTC_package_path)
if HTC_package_path not in sys.path:
    sys.path.append(HTC_package_path)
##############################################################################################################

from HTC_lib.VASP.INCAR.modify_vasp_incar import modify_vasp_incar


# In[1]:


__doc__ = """
    What this script does:
        It runs a series of calculations with different SIGMA and determines the nth largest SIGMA w.r.t which the term T*S in OUTCAR is converged.
        
    The command line to call this script looks like below:
    >>>python SIGMA_convergence.py [--start:float] [--end:float] [--step:float] [--max_no_of_points:integer] [--TS_convergence:float] [--which:integer] [--incar_template:filename] [--extra_copy] [--help]
    
    Arguments in a pair of brackets are optional
    * --start (float): the starting SIGMA. Default: 0.01
    * --end (float): the ending SIGMA. It is also the upper bound of SIGMA in this testing. See more in --max_no_of_points
                Default: 1
    * --step (float): the increment of SIGMA in the SIGMA testing. Default: 0.02
    * --max_no_of_points (integer>=2): the maximum number of testing points. If the number of testing points determined by --start, --end and --step is
                                larger than the value defined here, the first --max_no_of_points will be tested only.
                                If all --max_no_of_points testing points meet the TS_convergence criterion and the max SIGMA associated with --max_no_of_points
                                    is smaller than end, automatcially increase --max_no_of_points by 2. The process repeats until the max SIGMA associated with 
                                    --max_no_of_points hits --end or the TS_convergence criterion is unsatisfied for the first time.
                                    In the former case, the optimal SIGMA will be set to --end.
                                Default: 2
    * --TS_convergence (float in meV/atom): For ISMEAR>=0 (the Gaussian or Methfessel-Paxton smearing), SIGMA should be chosen in such a way that
            the term "entropy T*S" in OUTCAR is small (i.e. < 1-2meV/atom). --TS_convergence specifies this criterion of T*S in meV/atom.
            Default: 1
    * --which (1-based integer index): choose the "which"th largest SIGMA w.r.t. which the term T*S OUTCAR is converged.
                                        Default: 1
    * --incar_template (str): When writing INCAR, sorting INCAR tags in the same order as in the file referred by --incar_template.
    * --extra_copy: The additional file needed to be copied into each of the sub-directories where VASP calculations with different SIGMAs are performed. 
                    Separate them by + if there are more than one.
                    INCAR, POTCAR, KPOINTS and POSCAR are implicitly copied. So no need to set them here.
                    Default: Nothing
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
            1. set the optimal SIGMA to --end
            2. create a file named "INCAR.optimal" with the optimal SIGMA = --end
            3. __sub_dir_cal__ --> __done__ && create __SIGMA_convergence_hits_upper_bound__
        """


# In[2]:


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
            
        try:
            argv_dict["max_no_of_points"] = int(raw_argv_dict.get("--max_no_of_points", 2))
            assert argv_dict["max_no_of_points"] >= 2
        except:
            print(__doc__)
            raise Exception("The value passed to --max_no_of_points should be a positive integer >= 2. default: 2")
            
            
        argv_dict["incar_template"] = raw_argv_dict.get("--incar_template", "")
        if argv_dict["incar_template"]:
            assert os.path.isfile(argv_dict["incar_template"]), "The file specified via --incar_template doesn't exist"
        
        argv_dict["TS_convergence_unit"] = "eV"
        try:
            argv_dict["TS_convergence"] = float(raw_argv_dict.get("--ts_convergence", 1)) / 1000. * no_of_atoms # convert meV/atom to eV
        except:
            print(__doc__)
            raise Exception("The TS convergence criterion via '--TS_convergence' in the command line")
            
        try:
            argv_dict["which"] = int(raw_argv_dict.get("--which", 1))
        except:
            print(__doc__)
            raise Exception("--which is the 1-based index of the list of SIGMA in a descending order w.r.t which the term T*S in OUTCAR is converged.")
            
        argv_dict["extra_copy"] = [file for file in raw_argv_dict.get("--extra_copy", "").split("+") if file]
        for file in argv_dict["extra_copy"]:
            assert os.path.isfile(file), "{} doesn't exist under {}".format(file, os.getcwd())
            for std_vasp_input in ["INCAR", "POTCAR", "POSCAR", "KPOINTS"]:
                assert not file.endswith(std_vasp_input), "INCAR, POTCAR, POSCAR and KPOINTS will be copied implicitly. Don't set them via --extra_copy"
        
    
    with open("sigma_convergence_setup.json", "w") as setup:
        json.dump(argv_dict, setup, indent=4)
        
    sigma_list, sigma, step, end = [], argv_dict["start"], argv_dict["step"], argv_dict["end"]
    while sigma <= end:
        sigma_list.append(sigma)
        sigma += step
    argv_dict["sigma_list"] = sigma_list[:min([len(sigma_list), argv_dict["max_no_of_points"]])]
    argv_dict["is_upper_bound_reached"] = (argv_dict["sigma_list"] == sigma_list[-1])
    
    sub_dir_creation_summary_dict = {"extra_copy_to_sub_dir": [os.path.split(file)[1] for file in argv_dict["extra_copy"]]}
    sub_dir_creation_summary_dict["sub_dir_name_list"] = ["sigma_" + str(sigma) for sigma in argv_dict["sigma_list"]]
    with open("sub_dir_creation_summary.json", "w") as summary_df:
        json.dump(sub_dir_creation_summary_dict, summary_df, indent=4)
    
    return argv_dict             
            


# In[4]:


def prepare_cal_files(argv_dict):
    
    
    if argv_dict["end"] not in argv_dict["sigma_list"]:
        sigma_list = argv_dict["sigma_list"] + [argv_dict["end"]]
        is_end_sigma_appended = True
    else:
        sigma_list = argv_dict["sigma_list"]
        is_end_sigma_appended = False
    
    for sigma in sigma_list:
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
            if os.path.isfile(os.path.join(sub_dir_name, "opt_end_if_conv_satisfied_for_all_points")):
                pass
                #open(os.path.join(sub_dir_name, "__ready__"), "w").close()
                #print("%s: The VASP input files are already ready. Just create __ready__".format(sub_dir_name))
            else:
                shutil.copy("POSCAR", os.path.join(sub_dir_name, "POSCAR"))
                shutil.copy("KPOINTS", os.path.join(sub_dir_name, "KPOINTS"))
                shutil.copy("POTCAR", os.path.join(sub_dir_name, "POTCAR"))
                shutil.copy("INCAR", os.path.join(sub_dir_name, "INCAR"))
                
                if argv_dict["extra_copy"]:
                    for file in argv_dict["extra_copy"]:
                        shutil.copy2(file, sub_dir_name)
                print("Create sub-dir {} and copy the following files to it: INCAR, POSCAR, POTCAR, KPOINTS, ".format(sub_dir_name), end=" ")
                [print(extra_file, end=" ") for extra_file in argv_dict["extra_copy"]]
                
                if argv_dict["incar_template"] == "":
                    modify_vasp_incar(sub_dir_name, new_tags={"SIGMA": sigma}, rename_old_incar=False)
                else:
                    modify_vasp_incar(sub_dir_name, new_tags={"SIGMA": sigma}, rename_old_incar=False, incar_template=argv_dict["incar_template"])
                print(" && Set SIGMA = {} in {}/INCAR".format(sigma, sub_dir_name))
                
                if is_end_sigma_appended and sigma == sigma_list[-1]:
                    open(os.path.join(sub_dir_name, "opt_end_if_conv_satisfied_for_all_points"), "w").close()
                else:
                    open(os.path.join(sub_dir_name, "__ready__"), "w").close()
                    
                if not is_end_sigma_appended and sigma == argv_dict["end"]:
                    open(os.path.join(sub_dir_name, "opt_end_if_conv_satisfied_for_all_points"), "w").close()
            
            
        


# In[2]:


def are_all_sub_dir_cal_finished(argv_dict):
    
    for sigma in argv_dict["sigma_list"]:
        sub_dir_name = "sigma_" + str(sigma)
        
        if True not in [os.path.isfile(os.path.join(sub_dir_name, target_file)) for target_file in 
                        ["__done__", "__skipped__", "__done_cleaned_analyzed__", "__done_failed_to_clean_analyze__"]]:
            return False
        
    return True


# In[1]:


def find_converged_sigma(argv_dict):
    """ Find the "--which"th largest SIGMA w.r.t. which T*S in OUTCAR is converged.
    
    Note that every electronic iteration gives a T*S. We take the T*S of the last electronic iteration.
        
    return:
        if such SIGMA is found, return such SIGMA;
        otherwise:
            - return -1 if there is something wrong with parsing TS from OUTCAR.
            - return -2 if the optimal SIGMA cannot be found.
    """
    
    TS_list = []
    
    for sigma in argv_dict["sigma_list"]:
        sub_dir_name = "sigma_" + str(sigma)

        is_TS_found = False
        with open(os.path.join(sub_dir_name, "OUTCAR"), "r") as outcar:
            for line in outcar:
                if "entropy T*S    EENTRO =" in line:
                    last_TS = float(line.split("=")[1].strip())
                    is_TS_found = True
        if is_TS_found == False:#"Fail to parse T*S from {}".format(os.path.join(sub_dir_name, "OUTCAR"))
            open("__fail_to_parse_TS_from_OUTCAR_under_{}__".format(sub_dir_name), "w").close()
            return -1
        else:
            TS_list.append(last_TS)
    
    
    with open("SIGMA_VS_TS_Summary.dat", "w") as summary:
        summary.write("SIGMA\tTS\n")
        for sigma, TS in zip(argv_dict["sigma_list"], TS_list):
            summary.write("{}\t{}\n".format(sigma, TS))
    
    TS_ind, length = 0, len(TS_list)
    while TS_ind < length and abs(TS_list[TS_ind]) <= argv_dict["TS_convergence"]:
        TS_ind += 1
        
    if TS_ind == length: 
        #This indicates all testing SIGMAs satify the prescribed TS convergence. --> Fail to find the largest SIGMA w.r.t which TS convergence holds.
        return -2
    
    if TS_ind >=1:
        if TS_ind - argv_dict["which"] >= 0:
            return argv_dict["sigma_list"][TS_ind - argv_dict["which"]]
        else:
            return -2
    else:
        return -2


# In[2]:


def increase_max_no_of_points():
    with open("sigma_convergence_setup.json", "r") as setup:
        argv_dict = json.load(setup)
        
    argv_dict["max_no_of_points"] = argv_dict["max_no_of_points"] + 2
    
    with open("sigma_convergence_setup.json", "w") as setup:
        json.dump(argv_dict, setup, indent=4)


# In[74]:


if __name__ == "__main__":
    
    if "--help" in [argv.lower() for argv in sys.argv]:
        print(__doc__)
    else:
        argv_dict = read_and_set_default_arguments(sys.argv)
        prepare_cal_files(argv_dict)
        if are_all_sub_dir_cal_finished(argv_dict):
            converged_sigma = find_converged_sigma(argv_dict)
            if converged_sigma == -1:
                os.rename("__sub_dir_cal__", "__manual__")
                print("There is something wrong with parsing T*S from OUTCAR. __sub_dir_cal__ --> __manual__")
            elif converged_sigma == -2:
                if argv_dict["is_upper_bound_reached"]:
                    converged_sigma = argv_dict["end"]
                    shutil.copy(os.path.join("sigma_"+str(converged_sigma), "INCAR"), "INCAR.optimal")
                    os.rename("__sub_dir_cal__", "__done__")
                    open("__SIGMA_convergence_hits_upper_bound__", "w").close()
                    print("All sub-dir calculations finished and the largest testing SIGMA hits the one specified by --end.")
                    print("But the largest testing point still satisfies the T*S convergence criterion.")
                    print("Set the optimal SIGMA to the one specified by --end.")
                    print("INCAR.optimal is created with optimal SIGMA = --end = {}".format(converged_sigma))
                    print("create __SIGMA_convergence_hits_upper_bound__")
                else:
                    increase_max_no_of_points()
                    print("All sub-dir calculations finished and all testing points satisfy the T*S convergence criterion")
                    print("Note that the largest SIGMA associated with --max_no_of_points has not hitted the one specified by --end.")
                    print("Increase --max_no_of_points by 2 in sigma_convergence_setup.json")
                    print("Start preparing new sub-dir calculations...")
                    argv_dict = read_and_set_default_arguments(sys.argv)
                    prepare_cal_files(argv_dict)
            else:
                shutil.copy(os.path.join("sigma_"+str(converged_sigma), "INCAR"), "INCAR.optimal")
                os.rename("__sub_dir_cal__", "__done__")
                print("All sub-dir calculations finished and the minimum (maximum) sigma breaking (satisfying) the TS convergence criterion is identified.")
                print("INCAR.optimal is created with optimal SIGMA = {}".format(converged_sigma))
                print("__sub_dir_cal__ --> __done__")
        else:
            print("Some sub-dir calculations are still running...")

