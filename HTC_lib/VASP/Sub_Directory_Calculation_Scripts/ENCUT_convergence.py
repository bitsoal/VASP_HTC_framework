#!/usr/bin/env python
# coding: utf-8

# In[4]:


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
        It runs a series of calculations with different ENCUT and determines the ENCUT w.r.t which the total energy is reached.
        
    The command line to call this script looks like below:
    >>>python ENCUT_convergence.py [--start:integer] --end:integer [--step:integer] [--max_no_of_points:integer] [--opt_encut_if_conv_failed:integer] --convergence:AB [--convergence_type:chg|aver] [--no_of_consecutive_convergences:integer] [--which:integer] [--incar_template:filename] [--extra_copy] [--help]
    Arguments in a pair of brackets are optional
    * --start (integer): the starting ENCUT. Default: max(ENMAX) in POTCAR
    * --end (integer): the ending ENCUT. No default value
    * --step (integer): the increment of ENCUT in the ENCUT testing. Default: 50
    * --max_no_of_points (integer >=2): the maximum number of testing points. If the number of testing points determined by --start, --end and --step is largert than the 
                                    value defined here, the first --max_no_of_points testing points will be tested only.
                                    If --max_no_of_points testing points do not give us a converged ENCUT, --max_no_of_points will
                                        be automatically increased by 2 repeated until the corresponding ENCUT is larger than --end or
                                        the converged ENCUT is found. In the former case, --opt_ENCUT_if_conv_failed provides the optimal ENCUT
                                    Default: 10
    * --opt_encut_if_conv_failed (integer>=520): If the largest testing ENCUT hits --end and convergence is not achieved yet, --opt_encut_if_conv_failed
                                    will be thought of as the converged/optimal ENCUT
                                    default: 520  <--- The ENCUT used in Materials Project (https://docs.materialsproject.org/methodology/total-energies/)
    * --convergence: The total energy convergence. It has a form --convergence=AB, where A is the convergence criterion and B is the
                    unit which could be eV/atom, meV/atom, eV or meV. 
                    Default: no default value.
    * --convergence_type: Either chg or aver. The former means the change in the total energy w.r.t. ENCUT; The latter means the average total energy.
                    Seee --no_of_consecutive_convergences below for the application of this paramter.
                    Default: --convergence_type:aver
    * --no_of_consecutive_convergences (integer>=2): Let's denote the number passed to --no_of_consecutive_convergences as NCC.
            1. convergence_type:incr,
                If there are NCC consencutive absolute changes in the total energy which are smaller or equal to the convergence criterion (convergence),
                    the ENCUT testing is successful;
                else: the testing fails.
            2. convergence_type:aver,
                1. Arrange E0s in an ascending order of the corresponding ENCUTs.
                2. Construct a list of E0 subsets: the i-th subset consists of all E0s whose index is equal to or larger than i.
                3. For each E0 subset, evaluate the average, the maximum deviation from the average (max_dev) and the maximum difference between any two E0s (max_diff)
                4. Find the first E0 subset for which both max_dev and max_diff is smaller than or equal to the convergence criterion, and its set size is at least NCC.            
                    If there is a such kind of E0 subset, the testing is successful/converged. The paramter --which or which (1-based index) determines which E0 in the E0 subset is considered optimal,
                        and the corresponding ENCUT is said to be the optimal ENCUT.
                    else:
                        the testing fails.
                    Default: 3    
    * --which (1-based integer index): choose ENCUT from those associated with the consecutively converged total energies.
                    Default: 2
    * --incar_template (str): When writing INCAR, sorting INCAR tags in the same order as in the file referred by --incar_template.
    * --extra_copy: The additional file needed to be copied into each of the sub-directories where VASP calculations with different ENCUTs are performed. 
                    Separate them by + if there are more than one.
                    INCAR, POTCAR, KPOINTS and POSCAR are implicitly copied. So no need to set them here.
                    Default: Nothing
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
            1. --opt_encut_if_conv_failed will defines the optimal/converged ENCUT
            2. __sub_dir_cal__ --> __done__ and create __ENCUT_convergence_failed__
        """


# In[1]:


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
        
        
        try:
            argv_dict["start"] = int(raw_argv_dict.get("--start", enmax))
        except:
            print(__doc__)
            raise Exception("The value passed to --start should be an integer.")
        
        
        try:
            argv_dict["end"] = int(raw_argv_dict["--end"])
        except:
            print(__doc__)
            raise Exception("You must set the ending ENCUT via '--end' in the command line. It should be an integer")
        
        try:
            argv_dict["step"] = int(raw_argv_dict.get("--step", 50))
        except:
            print(__doc__)
            raise Exception("The value passed to --step should be an integer")
            
        try:
            argv_dict["max_no_of_points"] = int(raw_argv_dict.get("--max_no_of_points", 10))
            assert argv_dict["max_no_of_points"] >= 2
        except:
            print(__doc__)
            raise Exception("The value passed to --max_no_of_points should be a positive integer >= 2. default: 10")
            
        try:
            argv_dict["opt_encut_if_conv_failed"] = int(raw_argv_dict.get("--opt_encut_if_conv_failed", 520))
            assert argv_dict["opt_encut_if_conv_failed"] >= 520
        except:
            print(__doc__)
            raise Exception("The value passed to --opt_encut_if_conv_failed should be an integer >= 520. default: 520")
        
        
        argv_dict["incar_template"] = raw_argv_dict.get("--incar_template", "")
        if argv_dict["incar_template"]:
            assert os.path.isfile(argv_dict["incar_template"]), "The file specified via --incar_template doesn't exist"
        
        try:
            convergence= raw_argv_dict["--convergence"].lower()
        except:
            print(__doc__)
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
            print(__doc__)
            raise Exception("The energy convergence criterion should be set by '--convergence=AB', where A is a number and B should be ev, mev, ev/atom or mev/atom")
            
        if "--convergence_type" in raw_argv_dict.keys():
            convergence_type = raw_argv_dict["--convergence_type"].lower()
            if convergence_type.startswith("chg"):
                argv_dict["convergence_type"] = "chg"
            elif convergence_type.startswith("aver"):
                argv_dict["convergence_type"] = "aver"
            else:
                print(__doc__)
                raise Exception("The value passed to --convergence_type should be either 'chg' or 'aver'. See the above document for more details.")
        else:
            argv_dict["convergence_type"] = "aver"
            
        try:
            argv_dict["no_of_consecutive_convergences"] = int(raw_argv_dict.get("--no_of_consecutive_convergences", 3))
            assert argv_dict["no_of_consecutive_convergences"] >= 2
        except:
            print(__doc__)
            raise Exception("--no_of_consecutive_convergences should be an integer>=2")
            
        try:
            argv_dict["which"] = int(raw_argv_dict.get("--which", 2))
            assert argv_dict["which"] <= argv_dict["no_of_consecutive_convergences"]+1
        except:
            print(__doc__)
            raise Exception("--which should be an integer=1, 2,..., --no_of_consecutive_convergences+1")
            
        
        argv_dict["extra_copy"] = [file for file in raw_argv_dict.get("--extra_copy", "").split("+") if file]
        for file in argv_dict["extra_copy"]:
            assert os.path.isfile(file), "{} doesn't exist under {}".format(file, os.getcwd())
            for std_vasp_input in ["INCAR", "POTCAR", "POSCAR", "KPOINTS"]:
                assert not file.endswith(std_vasp_input), "INCAR, POTCAR, POSCAR and KPOINTS will be copied implicitly. Don't set them via --extra_copy"
        
    
    with open("encut_convergence_setup.json", "w") as setup:
        json.dump(argv_dict, setup, indent=4)
        
    encut_list, encut, step, end = [], argv_dict["start"], argv_dict["step"], argv_dict["end"]
    while encut <= end:
        encut_list.append(encut)
        encut += step
    argv_dict["encut_list"] = encut_list[:min([len(encut_list), argv_dict["max_no_of_points"]])]
    argv_dict["is_end_encut_reached"] = (argv_dict["encut_list"][-1] == encut_list[-1])
    
    sub_dir_creation_summary_dict = {"extra_copy_to_sub_dir": [os.path.split(file)[1] for file in argv_dict["extra_copy"]]}
    sub_dir_creation_summary_dict["sub_dir_name_list"] = ["encut_" + str(encut) for encut in argv_dict["encut_list"]]
    with open("sub_dir_creation_summary.json", "w") as summary_df:
        json.dump(sub_dir_creation_summary_dict, summary_df, indent=4)
    
    return argv_dict             
            


# In[6]:


def prepare_cal_files(argv_dict):
    
    if argv_dict["opt_encut_if_conv_failed"] not in argv_dict["encut_list"]:
        encut_list = argv_dict["encut_list"] + [argv_dict["opt_encut_if_conv_failed"]]
        is_opt_encut_if_conv_failed_appended = True
    else:
        encut_list = argv_dict["encut_list"]
        is_opt_encut_if_conv_failed_appended = False
    
    for encut in encut_list:
        is_preparation_needed = True
        sub_dir_name = "encut_" + str(encut)
        
        if not os.path.isdir(sub_dir_name):
            os.mkdir(sub_dir_name)
        else:
            file_list = os.listdir(sub_dir_name)
            for filename in file_list:
                if filename.startswith("__") and filename.endswith("__"):
                    #The presence of any HTC signal file indicates that the sub-dir VASP calculation input files were prepared.
                    is_preparation_needed = False
                    break
        
        if is_preparation_needed:
            if os.path.isfile(os.path.join(sub_dir_name, "opt_encut_if_conv_failed")):
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
                    modify_vasp_incar(sub_dir_name, new_tags={"ENCUT": encut}, rename_old_incar=False)
                else:
                    modify_vasp_incar(sub_dir_name, new_tags={"ENCUT": encut}, rename_old_incar=False, incar_template=argv_dict["incar_template"])
                print(" && Set ENCUT = {} in {}/INCAR".format(encut, sub_dir_name))
                
                if is_opt_encut_if_conv_failed_appended and encut_list[-1] == encut:
                    open(os.path.join(sub_dir_name, "opt_encut_if_conv_failed"), "w").close()
                else:
                    open(os.path.join(sub_dir_name, "__ready__"), "w").close()
                    
                if not is_opt_encut_if_conv_failed_appended and argv_dict["opt_encut_if_conv_failed"] == encut:
                    open(os.path.join(sub_dir_name, "opt_encut_if_conv_failed"), "w").close()


# In[3]:


def are_all_sub_dir_cal_finished(argv_dict):
    
    for encut in argv_dict["encut_list"]:
        sub_dir_name = "encut_" + str(encut)
        
        if True not in [os.path.isfile(os.path.join(sub_dir_name, target_file)) for target_file in 
                        ["__done__", "__skipped__", "__done_cleaned_analyzed__", "__done_failed_to_clean_analyze__"]]:
            return False
        
    return True


# In[6]:


def find_converged_encut(argv_dict):
    """ Find the converged ENCUT w.r.t. the total Energy E0 in OSZICAR.
    
    Two different cases:
        1. convergence_type:chg,
            If there are NCC consencutive absolute changes in the total energy which are smaller or equal to the convergence criterion (convergence),
                the ENCUT testing is successful;
            else: the testing fails.
        2. convergence_type:aver,
            1. Arrange E0s in an ascending order of the corresponding ENCUTs.
            2. Construct a list of E0 subsets: the i-th subset consists of all E0s whose index is equal to or larger than i.
            3. For each E0 subset, evaluate the average, the maximum deviation from the average (max_dev) and the maximum difference between any two E0s (max_diff)
            4. Find the first E0 subset for which both max_dev and max_diff is smaller than or equal to the convergence criterion, and its set size is at least NCC.            
                If there is a such kind of E0 subset, the testing is successful/converged. The paramter --which or which (1-based index) determines which E0 in the E0 subset is considered optimal,
                    and the corresponding ENCUT is said to be the optimal ENCUT.
                else:
                    the testing fails.
        
    return:
        if optimal ENCUT is found, return it;
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
            open("__fail_to_parse_energy_E0_from_{}__".format(os.path.join(sub_dir_name, "OSZICAR")), "w").close()
            return 0
            
    energy_diff_list = [energy_2 - energy_1 for energy_1, energy_2 in zip(energy_list[:-1], energy_list[1:])]
    
    with open("ENCUT_VS_E0_Summary.dat", "w") as summary:
        summary.write("ENCUT\tE0\tdE0\n")
        for encut, energy, energy_diff in zip(argv_dict["encut_list"], energy_list, energy_diff_list):
            summary.write("{}\t{}\t{}\n".format(encut, energy, energy_diff))
        summary.write("{}\t{}\n".format(argv_dict["encut_list"][-1], energy_list[-1]))
        
    if argv_dict["convergence_type"] == "aver":
        average_energy_list, max_dev_list, max_diff_list = [], [], []
        if len(argv_dict["encut_list"]) < argv_dict["no_of_consecutive_convergences"]:
            open("__no_enough_data_points_to_estimate_the_average_energy__", "w").close()
            return 0
        else:
            for start_ind in range(len(argv_dict["encut_list"]) - argv_dict["no_of_consecutive_convergences"] + 1):
                average_energy_list.append(sum(energy_list[start_ind:]) / len(energy_list[start_ind:]))
                max_diff_list.append(max(energy_list[start_ind:]) - min(energy_list[start_ind:]))
                max_dev_list.append(max([abs(energy - average_energy_list[-1]) for energy in energy_list[start_ind:]]))
                
        with open("ENCUT_VS_E0_Summary.dat", "a") as summary:
            for start_ind in range(len(argv_dict["encut_list"]) - argv_dict["no_of_consecutive_convergences"] + 1):
                summary.write("\nENCUT\tE0\tdeviation from average\n")
                for d_ind, energy_ in enumerate(energy_list[start_ind:]):
                    encut_ = argv_dict["encut_list"][start_ind + d_ind]
                    deviation_ = energy_ - average_energy_list[start_ind]
                    summary.write("{}\t{}\t{}\n".format(encut_, energy_, deviation_))
                summary.write("average: {}\nmax abs deviation: {}\n".format(average_energy_list[start_ind], max_dev_list[start_ind]))
                summary.write("max difference: {}\n".format(max_diff_list[start_ind]))
                    
                
    if argv_dict["convergence_type"] == "chg":
        count = 0
        for energy_diff_ind, energy_diff in enumerate(energy_diff_list):
            if abs(energy_diff ) <= argv_dict["convergence"]:
                count += 1
            else:
                count = 0
            
            if count == argv_dict["no_of_consecutive_convergences"]:
                return argv_dict["encut_list"][energy_diff_ind - argv_dict["no_of_consecutive_convergences"] + argv_dict["which"]]
    else:
        for ind, max_dev in enumerate(max_dev_list):
            if max_dev <= argv_dict["convergence"] and max_diff_list[ind] <= argv_dict["convergence"]:
                return argv_dict["encut_list"][ind + argv_dict["which"] - 1]
        
    return 0  


# In[3]:


def increase_max_no_of_points():
    with open("encut_convergence_setup.json", "r") as setup:
        argv_dict = json.load(setup)
        
    argv_dict["max_no_of_points"] = argv_dict["max_no_of_points"] + 2
    
    with open("encut_convergence_setup.json", "w") as setup:
        json.dump(argv_dict, setup, indent=4)


# In[74]:


if __name__ == "__main__":
    if "--help" in [argv.lower() for argv in sys.argv]:
        print(__doc__)
    else:
        argv_dict = read_and_set_default_arguments(sys.argv)
        prepare_cal_files(argv_dict)
        if are_all_sub_dir_cal_finished(argv_dict):
            converged_ENCUT = find_converged_encut(argv_dict)
            if converged_ENCUT == 0:
                if argv_dict["is_end_encut_reached"]:
                    converged_ENCUT = argv_dict["opt_encut_if_conv_failed"]
                    shutil.copy(os.path.join("encut_"+str(converged_ENCUT), "INCAR"), "INCAR.optimal")
                    os.rename("__sub_dir_cal__", "__done__")
                    open("__ENCUT_convergence_failed__", "w").close()
                    print("All sub-dir calculations finished and the testing ENCUT hits the maxmum ENCUT specified by --end.", end=" ")
                    print("But covergence is still not reached.")
                    print("INCAR.optimal is created with optimal ENCUT = opt_encut_if_conv_failed = {}".format(converged_ENCUT))
                    print("__sub_dir_cal__ --> __done__ && create __ENCUT_convergence_failed__")
                else:
                    increase_max_no_of_points()
                    print("All sub-dir calculations finished but convergence is not reached.")
                    print("Note that the testing ENCUT has not hitted the maximum ENCUT specified by --end yet.")
                    print("Increase --max_no_of_points by 2 in encut_convergence_setup.json")
                    print("Start preparing new sub-dir calculations...")
                    argv_dict = read_and_set_default_arguments(sys.argv)
                    prepare_cal_files(argv_dict)
            else:
                shutil.copy(os.path.join("encut_"+str(converged_ENCUT), "INCAR"), "INCAR.optimal")
                os.rename("__sub_dir_cal__", "__done__")
                print("All sub-dir calculations finished and covergence is reached.")
                print("INCAR.optimal is created with optimal ENCUT = {}".format(converged_ENCUT))
                print("__sub_dir_cal__ --> __done__")
        else:
            print("Some sub-dir calculations are still running...")

