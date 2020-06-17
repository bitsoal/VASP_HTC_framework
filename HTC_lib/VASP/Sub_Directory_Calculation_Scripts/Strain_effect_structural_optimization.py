#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os, sys, re, math, shutil, json

##############################################################################################################
##DO NOT change this part.
##../setup.py will update this variable
HTC_package_path = "C:/Users/tyang/Documents/Jupyter_workspace/HTC/python_3"
assert os.path.isdir(HTC_package_path), "Cannot find this VASP_HTC package under {}".format(HTC_package_path)
if HTC_package_path not in sys.path:
    sys.path.append(HTC_package_path)
##############################################################################################################

from HTC_lib.VASP.KPOINTS.VASP_Automatic_K_Mesh import VaspAutomaticKMesh


# In[2]:


__doc__ = """
    What this script does:
        This script generate a series of strained POSCAR as prscribed by users and distributes them into sub-folders for sub-dir calculations.
        
    The command line to call this script looks like below:
    >>>python Strain_effect_structural_optimization.py --strain_0:float --strain_N:float --step:float --which_axis:x|y|z|xy|yz|zx|xyz|pbc [--opt_kpoints_setup] [--extra_copy] [--help]
    Arguments in a pair of brackets are optional
    * --strain_0 (float): the maximally compressive strain. e.g. 0.94: a 6% compressive strain
    * --strain_N (float): the maximally tensile strain. e.g. 1.08: an 8% tensile strain.
    * --step (float): the increment of the strain starting from strain_0
    * --which_axis: to which axis (axes) the strain is applied. It could be any one of the following:
                    x OR y OR z OR xy OR yz OR zx OR xyz OR pbc
                    The order does not matter, e.g. xy is equivalent to yx
                    pbc means that the strain is applied to all of the axis (axes) along which the periodic boundary condition is physically satisfied. This reuiqres that --opt_kpoints_setup be set, from which the max allowed vacuum thickness for each axis is read.
    * --opt_kpoints_setup: a json file containing the optimal kpoints setup, which is created when Vasp_Automatic_Type_KPOINTS_convergence.py succeeded determining the optiaml KPOINTS.
                            If this arguement is set, rescale KPOINTS associated each strained POSCAR to ensure that the optimal NL is reached and the same kmesh_type is adopted
                            If this arguement is not set, just copy KPOINTS into sub-folders. The copied KPOINTS will be used for sub-dir cal
    * --extra_copy: The additional file needed to be copied into each of the sub-directories where VASP calculations with different ENCUTs are performed. 
                    Separate them by + if there are more than one.
                    INCAR, POTCAR, KPOINTS and POSCAR are implicitly copied. So no need to set them here.
                    Default: Nothing
    * --help: Explain how to use this script and the input arguments.
    Note that there must be no whitespace in the argument-value pair.
    Note that after the first execution of this script, the parsed arguments will be saved into a file named as "strain_effect_str_opt_setup.json".
        Whenever strain_effect_str_opt_setup.json exists, the passed arguments in the command line will all be omitted and those in strain_effect_str_opt_setup.json
        will be used. "strain_effect_str_opt_setup.json" makes the strain effect estimation for each materials in the HTC calculations customizable.
        
    Return:
        if all sub-dir calculations finished as signalled by __done__:
            __sub_dir_cal__ --> __done__
        """


# In[4]:


def read_and_set_default_arguments(argv_list):
    """ Parse cmd arguments and set default argument 
    OR
    Read arguments from a file named "strain_effect_str_opt_setup.json" under the folder where this script is called.
    """
    
    if os.path.isfile("strain_effect_str_opt_setup.json"):
        with open("strain_effect_str_opt_setup.json", "r") as setup:
            argv_dict = json.load(setup)
    else:
        
        raw_argv_dict = {key: value for key, value in [argv.split(":") for argv in argv_list[1:]]}
        argv_dict = {}
        
        try:
            argv_dict["strain_0"] = float(raw_argv_dict["--strain_0"])
        except:
            print(__doc__)
            raise Exception("You must set the maximally compressive strain via --strain_0. e.g. 0.94 means a maximal 6% compressive strain")
            
        try:
            argv_dict["strain_N"] = float(raw_argv_dict["--strain_N"])
        except:
            print(__doc__)
            raise Exception("You must set the maximally tensile strain via --strain_N. e.g. 1.08 means a maximal 8% tensile strain.")
        
        try:
            argv_dict["step"] = float(raw_argv_dict["--step"])
        except:
            print(__doc__)
            raise Exception("You must set the strain increment via --step. It should be a float number.")
            
        if "--opt_kpoints_setup" in raw_argv_dict.keys():
            assert os.path.isfile(raw_argv_dict["--opt_kpoints_setup"]), "The json file specified by --opt_kpoints_setup does not exist."
            argv_dict["opt_kpoints_setup"] = raw_argv_dict["--opt_kpoints_setup"]
            with open(argv_dict["opt_kpoints_setup"], "r") as opt_kpoints_setup_f:
                argv_dict["opt_kpoints_setup_dict"] = json.load(opt_kpoints_setup_f)
        else:
            argv_dict["opt_kpoints_setup"] = None
            argv_dict["opt_kpoints_setup_dict"] = None
            
        try:
            which_axis = raw_argv_dict["--which_axis"].lower()
        except:
            print(__doc__)
            raise Exception("You must specify to which axis (axes) the strain is applied via --which_axis.")
        if "pbc" in which_axis:
            assert argv_dict["opt_kpoints_setup_dict"] != None, "--which_axis has been set to pbc, which requires --opt_kpoints_setup to be set. Because we read from the file specified by the latter the max allowed vacuum thickness for each axis"
            pbc_type_of_xyz = VaspAutomaticKMesh.does_pbc_hold_along_xyz_axes(cal_loc=".", str_filename="POSCAR", 
                                                                             max_vacuum_thickness=argv_dict["opt_kpoints_setup_dict"]["max_vacuum_thickness"])
            argv_dict["which_axis"] = [axis_ind for axis_ind, pbc_type in enumerate(pbc_type_of_xyz) if pbc_type]
        else:
            argv_dict["which_axis"] = [axis_ind for axis_ind, axis in enumerate(["x", "y", "z"]) if axis in which_axis]
        assert argv_dict["which_axis"], "Based on the values passed to --which_axis and --opt_kpoints_setup, we find that the strain won't be applied to any axis. Pls double check."            
        
        argv_dict["extra_copy"] = [file for file in raw_argv_dict.get("--extra_copy", "").split("+") if file]
        for file in argv_dict["extra_copy"]:
            assert os.path.isfile(file), "{} doesn't exist under {}".format(file, os.getcwd())
            for std_vasp_input in ["INCAR", "POTCAR", "POSCAR", "KPOINTS"]:
                assert not file.endswith(std_vasp_input), "INCAR, POTCAR, POSCAR and KPOINTS will be copied implicitly. Don't set them via --extra_copy"
        
    
    with open("strain_effect_str_opt_setup.json", "w") as setup:
        json.dump(argv_dict, setup, indent=4)
        
    strain_list, strain, step, end = [], argv_dict["strain_0"], argv_dict["step"], argv_dict["strain_N"]
    while strain <= end:
        strain_list.append(strain)
        strain += step
    argv_dict["strain_list"] = strain_list
    
    sub_dir_creation_summary_dict = {"extra_copy_to_sub_dir": [os.path.split(file)[1] for file in argv_dict["extra_copy"]]}
    sub_dir_creation_summary_dict["sub_dir_name_list"] = ["strain_" + str(strain) for strain in strain_list]
    with open("sub_dir_creation_summary.json", "w") as summary_df:
        json.dump(sub_dir_creation_summary_dict, summary_df, indent=4)
        
    
    return argv_dict             
            


# In[5]:


def prepare_cal_files(argv_dict):
    
    for strain in argv_dict["strain_list"]:
        is_preparation_needed = True
        sub_dir_name = "strain_" + str(strain)
        
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
            shutil.copy("POSCAR", os.path.join(sub_dir_name, "POSCAR"))
            shutil.copy("KPOINTS", os.path.join(sub_dir_name, "KPOINTS"))
            shutil.copy("POTCAR", os.path.join(sub_dir_name, "POTCAR"))
            shutil.copy("INCAR", os.path.join(sub_dir_name, "INCAR"))
            
            if argv_dict["extra_copy"]:
                for file in argv_dict["extra_copy"]:
                    shutil.copy2(file, sub_dir_name)
            print("Create sub-dir {} and copy the following files to it: INCAR, POSCAR, POTCAR, KPOINTS, ".format(sub_dir_name), end=" ")
            [print(extra_file, end=" ") for extra_file in argv_dict["extra_copy"]]
            
            with open("POSCAR", "r") as poscar_f:
                poscar_list = list(poscar_f)
            
            for axis_ind in argv_dict["which_axis"]:
                line_ind = 2 + axis_ind
                new_latt_vec = [float(latt_vec_i) * strain for latt_vec_i in poscar_list[line_ind].split("#")[0].split("!")[0].split() if latt_vec_i]
                poscar_list[line_ind] = "    ".join([str(latt_vec_i) for latt_vec_i in new_latt_vec]) + "\n"
            
            with open(os.path.join(sub_dir_name, "POSCAR"), "w") as poscar_f:
                [poscar_f.write(poscar_line) for poscar_line in poscar_list]
            which_axis = ", ".join([["x", "y", "z"][axis_ind] for axis_ind in argv_dict["which_axis"]])
            print("&& apply a strain of {} to {}/POSCAR along the {} direction(s)".format(strain, sub_dir_name, which_axis), end=" ")
            
            if argv_dict["opt_kpoints_setup_dict"] != None:
                print("&& --opt_kpoints_setup is set --> rescale KPOINTS", end=" ")
                kmesher = VaspAutomaticKMesh(cal_loc=sub_dir_name, **argv_dict["opt_kpoints_setup_dict"])
                VaspAutomaticKMesh.write_KPOINTS(kpoints_setup=kmesher.get_kpoints_setup(), cal_loc=sub_dir_name)
                
            else:
                print("&& --opt_kpoints_setup is not set --> use the copied KPOINTS", end=" ")
            
            
            open(os.path.join(sub_dir_name, "__ready__"), "w").close()
            print("&& create __ready__")
            
            
        


# In[6]:


def are_all_sub_dir_cal_finished(argv_dict):
    
    for encut in argv_dict["strain_list"]:
        sub_dir_name = "strain_" + str(encut)
        
        if not os.path.isfile(os.path.join(sub_dir_name, '__done__')):
            if not os.path.isfile(os.path.join(sub_dir_name, "__done_clean__")):
                return False
        
    return True


# In[74]:


if __name__ == "__main__":
    if "--help" in [argv.lower() for argv in sys.argv]:
        print(__doc__)
    else:
        argv_dict = read_and_set_default_arguments(sys.argv)
        prepare_cal_files(argv_dict)
        if are_all_sub_dir_cal_finished(argv_dict):
            os.rename("__sub_dir_cal__", "__done__")
            print("All sub-dir calculations finished.")
            print("__sub_dir_cal__ --> __done__")
        else:
            print("Some sub-dir calculations are still running...")

