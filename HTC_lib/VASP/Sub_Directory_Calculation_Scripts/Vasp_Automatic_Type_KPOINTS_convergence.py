#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os, sys, re, math, shutil, json
HTC_package_path = "C:/Users/tyang/Documents/Jupyter_workspace/HTC/python_3"
if  os.path.isdir(HTC_package_path) and HTC_package_path not in sys.path:
    sys.path.append(HTC_package_path)
    
from HTC_lib.VASP.KPOINTS.VASP_Automatic_K_Mesh import VaspAutomaticKMesh

from pymatgen import Structure


# In[1]:


__doc__ = """
    What this script does:
        It runs a series of calculations with different KPOINTSs of the VASP automatic type and determines the KPOINTS w.r.t. which the total energy is converged.
        Note that the total enerngy convergence is essentially w.r.t. the number of k-points in IRBZ (denoted as Nk_IRBZ), Rather Than NL.
        Note that it makes no sense to test the total energy convergence w.r.t. KPOINTS for 0D systems.
        
    The command line to call this script looks like below:
    >>>python Vasp_Automatic_Type_KPOINTS_convergence.py [--NL_start:integer] [--NL_end:integer] [--dN:A|A_B_C|any_A] [--convergence:AB] [--convergence_type:chg|aver] [--no_of_consecutive_convergences:integer] [--which:integer] --max_vacuum_thickness:A_B_C [--kmesh_type:Gamma|Monkhorst-Pack|Auto] [--shift:A_B_C] [--symprec_latt_const:float] [--symprec_angle:float] [--max_no_of_points:integer] [--extra_copy] [--help]
    
    Arguments in a pair of brackets are optional
    * --NL_start (integer): the starting NL. N in "NL" stands for the subdivision of the k-mesh in an axis; L in "NL" stands for the lattice constant.
                        NL means N_i * L_i (i=x, y, z). In the ideal case, NL = NL_x = NL_y = NL_z to ensure that k-spacing is the same for all PBC axes
                        PBC: periodic boundary condition
                    Default: 10
    * --NL_end (integer): the ending NL. 
                    Default: 100
    * --dN : the smallest increment of N for the PBC axis in the KPOINTS testing. 
            Three formats are supported:
                1. --dN:A, where A is an integer >=1. The increment along all PBC axes should be larger than or equal to A.
                2. --dN:A_B_C, where A, B and C are integers >=1. The increment along the PBC x-, y- and z-axis should be >= A, B and C, respectively.
                3. --dN:any_A, where A is an integer >=1. The increment along AT LEAST one PBC axis is >= A.
            It doesn't make sence to test the total energy convergence w.r.t. KPIONTS for 0D systems.
            Default: --dN:2
    * --convergence: The total energy convergence. It has a form --convergence=AB, where A is the convergence criterion and B is the
                    unit which could be eV/atom, meV/atom, eV or meV.
                    Note that we sort these set of calculations in an ascending order of the number k-points in the IRBZ (denoted as Nk_IRBZ).
                    The total energy convergence is eseentially w.r.t. NK_IRBZ, NOT NL
                    Default: 1meV/atom
    * --convergence_type: Either chg or aver. The former means the change in the total energy w.r.t. Nk_IRBZ; The latter means the average total energy.
                    Seee --no_of_consecutive_convergences below for the application of this paramter.
                    Default: --convergence_type:aver
                    
    * --no_of_consecutive_convergences (integer>=2): Let's denote the number passed to --no_of_consecutive_convergences as NCC.
                    1. --convergence_type:incr,
                        If there are NCC consencutive absolute changes in the total energy which are smaller or equal to the convergence criterion (--convergence),
                            the KPOINTS testing is successful;
                        else: the testing fails.
                    2. --convergence_type:aver,
                        If there are NCC consecutive total energies and the maximum deviation from the average of the NCC total energies is smaller or equal to
                            the convergence criterion (--convergence), the KPOINTS testing is successful.
                        else: the testing fails.
                    Default: 3 
    * --which (1-based integer index): choose Nk_IRBZ from the first ascending converged Nk_IRBZ list.
                                        The KPOINTS associated with the chosen converged Nk_IRBZ is considered as the converged/optimal one.
                    Default: 2
    * --max_vacuum_thickness: A, B, C in "A_B_C" are the maximum vacuum thickness along the x-, y- and z-axis, respectively.
                            If the vacuum thickness along the i-th axis is larger than the value defined here, the i-th axis is considered non-PBC.
                            If the vacuum thickness along the i-th axis is smaller than or equal to the value defined here, the i-th axis is considered PBC.
                            The subdivision for the non-PBC axis will be set to 1.
                            This allows us to handle 0D, 1D, 2D and 3D materials simultaneously.
                            The unit is Angstrom
                            If you are sure PBC holds along all axes, set A, B, C to a giant number, e.g. 1000_1000_1000
                    Default: No default. 
    * --kmesh_type: The automatic k-mesh type. It could be one of "Gamma", "Monkhorst-Pack" or "Auto". Only the first letter matters. Case-insensitive
            If it is set to "Auto", "Gamma" will be chosen if any of the calculated subdivisions along the pbc axes is odd; Otherwise, "Monkhorst-Pack"
            In the following cases, --kmesh_type will be internally set to "Gamma" regardless of the input value:
                1. The lattice is hexagonal
                2. The calculated subdivisions are (1, 1, 1)
                3. ISMEAR = -5 in INCAR
            Such kind of philosophy of choosing k-mesh type is followed by VASP_Automatic_K_Mesh.VaspAutomaticKMesh.get_kpoints_setup
            Default: Auto
    * --shift: A, B, C in A_B_C are the optional shift in KPOINTS.
            Default: 0_0_0
    * --symprec_latt_const (float): the tolerance used to tell if any two of the lattice constants are euqal.
                                    The unit is Angstrom.
                                ***This argument together with --symprec_angle are used to tell if the lattice is hexagonal. If it is, set Gamma-centered k-mesh***
                                Default: 0.1
    * --symprec_angle (float): the tolerance used to tell if any of the lattice angles is equal to 60 or 120 degrees.
                                The unit is degree.
                            ***This argument together with symprec_angle are used to tell if the lattice is hexagonal. If it is, set Gamma-centered k-mesh***
                                Default: 1
    * --max_no_of_points (integer): the maximum number of testing points. If the number of testing points determined by --NL_start, --NL_end and --dN is largert than the 
                                    value defined here, the first --max_no_of_points testing points will be tested only.
                                    Default: 10
    * --extra_copy: The additional file needed to be copied into each of the sub-directories where VASP calculations with different KPOINTSs are performed. 
                    Separate them by + if there are more than one.
                    INCAR, POTCAR, KPOINTS and POSCAR are implicitly copied. So no need to set them here.
                    Default: Nothing

    * --help: Explain how to use this script and the input arguments.
    Note that there must be no whitespace in the argument-value pair.
    Note that after the first execution of this script, the parsed arguments will be saved into a file named as "kpoints_convergence_setup.json".
        Whenever kpoints_convergence_setup.json exists, the passed arguments in the command line will all be omitted and those in kpoints_convergence_setup.json
        will be used. "kpoints_convergence_setup.json" makes the KPOINTS testing for each materials in the HTC calculations customizable.
        
    Return:
        If the converged KPOINTS is successfully found:
            1. create a file named "KPOINTS.optimal"
            2. __sub_dir_cal__ --> __done__
        else:
            __sub_dir_cal__ --> __manual__
        """


# In[4]:


def read_and_set_default_arguments(argv_list):
    """ Parse cmd arguments and set default argument 
    OR
    Read arguments from a file named "kpoints_convergence_setup.json" under the folder where this script is called.
    """
    
    if os.path.isfile("kpoints_convergence_setup.json"):
        with open("kpoints_convergence_setup.json", "r") as setup:
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
            argv_dict["NL_start"] = int(raw_argv_dict.get("--nl_start", 10))
        except:
            print(__doc__)
            raise Exception("The value passed to --NL_start should be an integer. See more in the above document")
        
        try:
            argv_dict["NL_end"] = int(raw_argv_dict.get("--nl_end", 60))
        except:
            print(__doc__)
            raise Exception("The value passed to --NL_end should be an integer. See more in the above document")
        
        try:
            argv = raw_argv_dict.get("--dn", "2")
            items = re.findall("[0-9]+", argv)
            if len(items) == 1:
                assert int(items[0]) > 0
                if argv == items[0]:
                    argv = [int(argv)] * 3
                elif argv.lower() == ("any_" + items[0]):
                    argv = {"any": int(items[0])}
                else:
                    assert 1 == 2
            elif len(items) == 3:
                assert argv == "_".join(items)
                argv = [int(item) for item in items]
                assert False not in [item >= 0 for item in argv]
                assert True in [item > 0 for item in argv]
            else:
                assert 1 == 2
            
            argv_dict["dN"] = argv
        except:
            print(__doc__)
            raise Exception("Fail to parse --dN. See the above document to ensure it is set properly")
            
        try:
            argv_dict["max_no_of_points"] = int(raw_argv_dict.get("--max_no_of_points", 10))
            assert argv_dict["max_no_of_points"] > 0
        except:
            print(__doc__)
            raise Exception("Fail to parse --max_no_of_points or its value is not positive. See more in the above document.")
        
        convergence= raw_argv_dict.get("--convergence", "1meV/atom").lower()
        argv_dict["convergence_unit"] = "ev"
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
            raise Exception("The energy convergence criterion should be set by '--convergence=AB', where A is a number and B should be ev, mev, ev/atom or mev/atom.\nSee more in the above document")
            
        
        if "--convergence_type" in raw_argv_dict.keys():
            convergence_type = raw_argv_dict["[--convergence_type"].lower()
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
            raise Exception("Fail to parse --no_of_consecutive_convergences or its value is incorrect. See the above document to ensure that it is set properly.")
            
        try:
            argv_dict["which"] = int(raw_argv_dict.get("--which", 2))
            assert argv_dict["which"] <= argv_dict["no_of_consecutive_convergences"] + 1
        except:
            print(__doc__)
            raise Exception("Fail to parse --which or its value is invalid. See the above document to ensure it is set properly.")
        
        try:
            argv_dict["max_vacuum_thickness"] = raw_argv_dict["--max_vacuum_thickness"]
            argv_dict["max_vacuum_thickness"] = [int(thickness) for thickness in argv_dict["max_vacuum_thickness"].split("_")[:3]]
        except:
            print(__doc__)
            raise Exception("You must set --max_vacuum_thickness. See the above document to ensure that it is set properly.")
            
        
        kmesh_type = raw_argv_dict.get("--kmesh_type", "Auto").lower()
        if kmesh_type.startswith("g"):
            kmesh_type = "Gamma"
        elif kmesh_type.startswith("m"):
            kmesh_type = "Monkhorst-Pack"
        elif kmesh_type.startswith("a"):
            kmesh_type = "Auto"
        else:
            print(__doc__)
            raise Exception("Fail to parse --kmesh_type. See the above document to ensure that it is set properly..")
        argv_dict["kmesh_type"] = kmesh_type
        
        try:
            argv_dict["shift"] = [int(st) if st=="0" else float(st) for st in raw_argv_dict.get("--shift", "0_0_0").split("_")[:3]]
        except:
            print(__doc__)
            raise Exception("Fail to parse --shift. See the above document to ensure that it is set properly.")
            
        try:
            argv_dict["symprec_latt_const"] = float(raw_argv_dict.get("--symprec_latt_const", 0.1))
        except:
            print(__doc__)
            raise Exception("Fail to parse --symprec_latt_const. See the above document to ensure that it is set properly.")
            
        try:
            argv_dict["symprec_angle"] = float(raw_argv_dict.get("--symprec_angle", 1))
        except:
            print(__doc__)
            raise Exception("Fail to parse --symprec_angle. See the above document to ensure that it is set properly.")
            
        argv_dict["extra_copy"] = [file for file in raw_argv_dict.get("--extra_copy", "").split("+") if file]
        for file in argv_dict["extra_copy"]:
            assert os.path.isfile(file), "{} doesn't exist under {}".format(file, os.getcwd())
            for std_vasp_input in ["INCAR", "POTCAR", "POSCAR", "KPOINTS"]:
                assert not file.endswith(std_vasp_input), "INCAR, POTCAR, POSCAR and KPOINTS will be copied implicitly. Don't set them via --extra_copy"
            
                
    with open("kpoints_convergence_setup.json", "w") as setup:
        json.dump(argv_dict, setup, indent=4)
        
    
    input_kwargvs = {}
    for key in ["kmesh_type", "shift", "max_vacuum_thickness", "symprec_latt_const", "symprec_angle"]:
        input_kwargvs[key] = argv_dict[key]
    input_kwargvs["cal_loc"] = "."

    NL_list, kpoints_setup_list, NL, dN, NL_end = [], [], argv_dict["NL_start"], argv_dict["dN"], argv_dict["NL_end"]
    while NL <= NL_end:
        kpoints_setup = VaspAutomaticKMesh(NL=NL, **input_kwargvs).get_kpoints_setup()
        optimal_NL = list(kpoints_setup["optimal_NL"].keys())[0]
        pbc_subdivision = VaspAutomaticKMesh.get_pbc_sublist(kpoints_setup["subdivisions"], kpoints_setup["pbc_type_of_xyz"])
        is_NL_unique = False
        if NL_list == []:
            is_NL_unique = True
            if isinstance(argv_dict["dN"], list):
                pbc_dN_list = VaspAutomaticKMesh.get_pbc_sublist(argv_dict["dN"], kpoints_setup["pbc_type_of_xyz"])
        elif isinstance(argv_dict["dN"], list):
            if False not in [dN <= (pbc_div_1 - pbc_div_0) for dN, pbc_div_0, pbc_div_1 in zip(pbc_dN_list, pbc_subdivision_0, pbc_subdivision)]:
                is_NL_unique = True
        elif isinstance(argv_dict["dN"], dict):
            if True in [argv_dict["dN"]["any"] <= (pbc_div_1 - pbc_div_0) for pbc_div_0, pbc_div_1 in zip(pbc_subdivision_0, pbc_subdivision)]:
                is_NL_unique = True
          
        #For test only
        if False and NL_list == [] and is_NL_unique:
            print(kpoints_setup["subdivisions"], NL, optimal_NL, kpoints_setup["equivalent_NL"])
        elif False and is_NL_unique:
            print(kpoints_setup["subdivisions"], NL, optimal_NL, kpoints_setup["equivalent_NL"], end=" ")
            if isinstance(argv_dict["dN"], list):
                print([dN <= (pbc_div_1 - pbc_div_0) for dN, pbc_div_0, pbc_div_1 in zip(pbc_dN_list, pbc_subdivision_0, pbc_subdivision)])
            else:
                print([argv_dict["dN"]["any"] <= (pbc_div_1 - pbc_div_0) for pbc_div_0, pbc_div_1 in zip(pbc_subdivision_0, pbc_subdivision)])
                
            
        NL = max(kpoints_setup["equivalent_NL"]) + 1
        if is_NL_unique:
            pbc_subdivision_0 = pbc_subdivision
            kpoints_setup["NL"] = optimal_NL
            kpoints_setup_list.append(kpoints_setup)
            NL_list.append(optimal_NL)
        

    argv_dict["NL_list"] = NL_list[:min([len(NL_list), argv_dict["max_no_of_points"]])]
    argv_dict["kpoints_setup_list"] = kpoints_setup_list[:min([len(NL_list), argv_dict["max_no_of_points"]])]
    
    return argv_dict             
            


# In[2]:


def prepare_cal_files(argv_dict):
    
    for kpoints_setup, NL in zip(argv_dict["kpoints_setup_list"], argv_dict["NL_list"]):
        is_preparation_needed = True
        sub_dir_name = "NL_" + str(NL)
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
            
            VaspAutomaticKMesh.write_KPOINTS(kpoints_setup=kpoints_setup, cal_loc=sub_dir_name)
            
            open(os.path.join(sub_dir_name, "__ready__"), "w").close()


# In[10]:


def are_all_sub_dir_cal_finished(argv_dict):
    
    for NL in argv_dict["NL_list"]:
        sub_dir_name = "NL_" + str(NL)
        
        if not os.path.isfile(os.path.join(sub_dir_name, '__done__')):
            if not os.path.isfile(os.path.join(sub_dir_name, "__done_clean__")):
                return False
        
    return True


# In[15]:


def find_converged_NL(argv_dict):
    """ Find the converged Nk_IRBZ w.r.t. the total Energy E0 in OSZICAR.
    
        Two different cases:
        1. convergence_type:incr,
            If there are NCC consencutive absolute changes in the total energy which are smaller or equal to the convergence criterion (convergence),
                the KPOINTS testing is successful;
            else: the testing fails.
        2. convergence_type:aver,
            If there are NCC consecutive total energies and the maximum deviation from the average of the NCC total energies is smaller or equal to
                the convergence criterion (convergence), the KPOINTS testing is successful.
            else: the testing fails.
    
    The paramter --which or which (1-based index) determines which Nk_IRBZ/KPOINTS is chosen as the optimal one among the NCC consecutively convgered Nk_IRBZs/KPOINTSs.
    
        
    return:
        if the optimal Nk_IRBZ, return the associated NL.
        otherwise, return 0
    """
    
    Nk_IRBZ_dict = {}
    
    for NL in argv_dict["NL_list"]:
        sub_dir_name = "NL_" + str(NL)
            
        with open(os.path.join(sub_dir_name, "IBZKPT"), "r") as ibzkpt:
            next(ibzkpt)
            try:
                Nk_IRBZ = int(re.findall("[0-9]+", next(ibzkpt))[0])
                if Nk_IRBZ not in Nk_IRBZ_dict.keys():
                    Nk_IRBZ_dict[Nk_IRBZ] = {"NL": NL}
            except:
                open("__fail_to_parse_the_number_of_k_points_in_IRBZ_from_{}__".format(os.path.join(sub_dir_name, "IBZKPT")), "w").close()
                return 0
                
        with open(os.path.join(sub_dir_name, "OSZICAR"), "r") as oszicar:
            for line in oszicar:
                pass
        try:
            energy = float(re.search("E0=([\s0-9E\.\-\+]+)d E", line)[1].strip())
            Nk_IRBZ_dict[Nk_IRBZ]["energy"] = energy
        except:
            open("__fail_to_parse_energy_E0_from_{}__".format(os.path.join(sub_dir_name, "OSZICAR")), "w").close()
            return 0            
    
    sorted_Nk_IRBZ_list = sorted(Nk_IRBZ_dict.keys())
    energy_diff_list = [Nk_IRBZ_dict[nk_irbz_2]["energy"] - Nk_IRBZ_dict[nk_irbz_1]["energy"] 
                        for nk_irbz_1, nk_irbz_2 in zip(sorted_Nk_IRBZ_list[:-1], sorted_Nk_IRBZ_list[1:])]
    
    energy_diff_list.append("")
    with open("Nk_IRBZ_VS_E0_Summary.dat", "w") as summary:
        summary.write("Nk_IRBZ\tNL\tE0\tdE0\n")
        for nk_irbz_ind, nk_irbz in enumerate(sorted_Nk_IRBZ_list):
            summary.write("{}\t{}\t{}\t{}\n".format(nk_irbz, Nk_IRBZ_dict[nk_irbz]["NL"], 
                                                    Nk_IRBZ_dict[nk_irbz]["energy"], energy_diff_list[nk_irbz_ind]))
    energy_diff_list.pop()
    
    if argv_dict["convergence_type"] == "aver":
        compound_energy_list, average_energy_list, max_dev_list = [], [], []
        if len(argv_dict["NL_list"]) < argv_dict["no_of_consecutive_convergences"]:
            open("__no_enough_data_points_to_estimate_the_average_energy__", "w").close()
            return 0
        else:
            for start_ind in range(len(argv_dict["NL_list"]) - argv_dict["no_of_consecutive_convergences"] + 1):
                compound_energy_list.append([Nk_IRBZ_dict[sorted_Nk_IRBZ_list[start_ind + d_ind]]["energy"] for d_ind in range(argv_dict["no_of_consecutive_convergences"])])
                average_energy_list.append(sum(compound_energy_list[-1]) / argv_dict["no_of_consecutive_convergences"])
                max_dev_list.append(max([abs(energy - average_energy_list[-1]) for energy in compound_energy_list[-1]]))
                
        with open("Nk_IRBZ_VS_E0_Summary.dat", "a") as summary:
            for start_ind in range(len(argv_dict["NL_list"]) - argv_dict["no_of_consecutive_convergences"] + 1):
                summary.write("\nNk_IRBZ\tNL\tE0\tdeviation from average\n")
                for d_ind in range(argv_dict["no_of_consecutive_convergences"]):
                    summary.write("{}\t{}\t{}\t{}\n".format(sorted_Nk_IRBZ_list[start_ind+d_ind], 
                                                            Nk_IRBZ_dict[sorted_Nk_IRBZ_list[start_ind+d_ind]]["NL"], 
                                                            compound_energy_list[start_ind][d_ind], 
                                                            compound_energy_list[start_ind][d_ind] - average_energy_list[start_ind]))
                summary.write("average: {}\nmax abs deviation: {}\n".format(average_energy_list[start_ind], max_dev_list[start_ind]))

    if argv_dict["convergence_type"] == "chg":
        count = 0
        for energy_diff_ind, energy_diff in enumerate(energy_diff_list):
            if abs(energy_diff ) <= argv_dict["convergence"]:
                count += 1
            else:
                count = 0
            
            if count == argv_dict["no_of_consecutive_convergences"]:
                converged_nk_irbz = sorted_Nk_IRBZ_list[energy_diff_ind - argv_dict["no_of_consecutive_convergences"] + argv_dict["which"]]
                return Nk_IRBZ_dict[converged_nk_irbz]["NL"]
    else:
        for ind, max_dev in enumerate(max_dev_list):
            if max_dev <= argv_dict["convergence"]:
                return Nk_IRBZ_dict[sorted_Nk_IRBZ_list[ind + argv_dict["which"] - 1]]["NL"]
        
    return 0  


# In[74]:


if __name__ == "__main__":
    if "--help" in [argv.lower() for argv in sys.argv]:
        print(__doc__)
    else:
        argv_dict = read_and_set_default_arguments(sys.argv)
        prepare_cal_files(argv_dict)
        if are_all_sub_dir_cal_finished(argv_dict):
            converged_NL = find_converged_NL(argv_dict)
            if converged_NL == 0:
                os.rename("__sub_dir_cal__", "__manual__")
            else:
                shutil.copy(os.path.join("NL_"+str(converged_NL), "KPOINTS"), "KPOINTS.optimal")
                os.rename("__sub_dir_cal__", "__done__")

