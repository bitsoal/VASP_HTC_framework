#!/usr/bin/env python
# coding: utf-8

# In[1]:


# coding: utf-8

# Application: coded for lattice constant optimization using the sub-dir calculations. Optimize and calculate the energy of a strcuture with serveral different lattice constants, and make a cubic spline interpolation to obtain the optimal lattice constants.
# 
# How to use it: 
# >>>python optimize_lattice_constant_VASP no_of_points scaling_1 scaling_2 scaling_3 ... scaling_no_of_points [x] [y] [z] [tol]
# Note that this script will read the POSCAR in the same folder where this script is run. So there must be a POSCAR as a parent POSCAR based on which a series of strucures by scaling the lattice vectors of the parent structure will be created for sub-dir calculations
# Note that this script will also read KPOINTS in the same folder where this script is run. When POSCAR is rescaled, KPOINTS will be rescaled accordingly.
# arguments:
#     no_of_points: an integer, the number of structures with different lattice constants that will be calculated for the subsequent cubic spline interpolation for the optimal lattice constant estimation
#     scaling_1, scaling_2, ..., scaling_no_of_points: a list of scaling factors that will be applied to the universal scaling or lattice vector a, b or c
#     x y z: any combination of x, y and z. determine which lattice vector(s) is(are) scaled. If all the three are chosen, the universal scaling in POSCAR will be scaled rather than the three lattice vectors.
#          Note that you have to tell which lattice vector(s) to be optimized. Otherwise, this script will stop working.
#     tol: the interpolated optimal lattice constant (l_inter) is considered accurate if the difference between the corresponding interpolated energy and the DFT-calculated one at l_inter is smaller than tol
#          format of tol: Number+meV or Number+meV/atom   (Note that the unit is case-insensitive)
#          default: 0.1meV
#     
# e.g.
# rescale the lattice vector a by multiplying it with 0.96, 0.98, 1.0, 1.02 and 1.04 at tol = 0.1meV
# >>>python optimize_lattice_constant_VASP 5 0.96 0.98 1.0 1.02 1.04 x
# 
# rescale the lattice vector a and b by multiplying them with 0.94, 0.96, 0.98, 1.0, 1.02 and 1.04 at tol = 0.1meV/atom
# >>>python optimize_lattice_constant_VASP 6 0.94 0.96 0.98 1.0 1.02 1.04 x y 0.1meV/atom
# 
# rescale the univeral scaling in the parent POSCAR by multiplying it with 0.98, 1.0, 1.02 and 1.04 at tol = 0.01meV/atom
# >>>python optimize_lattice_constant_VASP 4 0.98 1.0 1.02 1.04 x y z 1e-2meV/atom

import sys, os, json, copy, shutil, re
from scipy import interpolate
import numpy as np
import matplotlib.pyplot as plt

from pymatgen.core import Structure #For testing purpose


# In[2]:


def read_cal_status():
    if os.path.isfile("latt_param_opt_setup.json"):
        with open("latt_param_opt_setup.json", "r") as f:
            status_dict = json.load(f)
    else:
        status_dict = {"scaling list": [], 
                       "opt which latt vec": "",
                       "cal folder list": [], 
                       "interpolated result": [], 
                       "verification folder": None, 
                       "tol": 0.1, "tol unit": "mev", 
                       "max_no_of_points": 10,
                       "Notes": """1. optimize_lattice_constant_VASP.py always first tries to read the setup from latt_param_opt_setup.json. 
                           If the latter is not present, it will then read the setup from the command line.
                           2.  If you want to customize the setup for a specific system, change "scaling list", "tol", "tol unit" and "max_no_of_points" only"""}
    return status_dict

def write_cal_status(status_dict):
    with open("latt_param_opt_setup.json", "w") as f:
        json.dump(status_dict, f, indent=4)
        
def read_parent_POSCAR():
    with open("POSCAR", "r") as f:
        lines = list(f)
    universal_scaling = float(lines[1].strip(" \n"))
    latt_a = [float(i) for i in lines[2].strip(" \n").split()]
    latt_b = [float(i) for i in lines[3].strip(" \n").split()]
    latt_c = [float(i) for i in lines[4].strip(" \n").split()]
    
    no_of_atoms_list = re.findall("[\d]+", lines[5].split("#")[0].split("!")[0])
    no_of_atoms_list += re.findall("[\d]+", lines[6].split("#")[0].split("!")[0])
    tot_no_of_atoms = sum([int(no_of_atoms) for no_of_atoms in no_of_atoms_list])
    struct = Structure.from_file("POSCAR")
    assert tot_no_of_atoms == len(struct.species), "Fail to count the number of atoms from %s/POSCAR = %d" % (os.getcwd(), tot_no_of_atoms)
    
    return {"comment": lines[0], "universal scaling": universal_scaling, 
            "latt_a": latt_a, "latt_b": latt_b, "latt_c": latt_c, 
            "others": lines[5:], "tot_no_of_atoms": tot_no_of_atoms}

def write_POSCAR(POSCAR, where_to_write):
    with open(os.path.join(where_to_write, "POSCAR"), "w") as f:
        f.write(POSCAR["comment"])
        f.write("%f\n" % POSCAR["universal scaling"])
        f.write("    %f  %f  %f\n" % tuple(POSCAR["latt_a"]))
        f.write("    %f  %f  %f\n" % tuple(POSCAR["latt_b"]))
        f.write("    %f  %f  %f\n" % tuple(POSCAR["latt_c"]))
        for line in POSCAR["others"]:
            f.write(line)

def read_a_file(filename, where_to_read):
    return list(open(os.path.join(where_to_read, filename), "r"))

def write_a_file(file, filename, where_to_write):
    with open(os.path.join(where_to_write, filename), "w") as f:
        for line in file:
            f.write(line)
            
def read_parent_INCAR():
    return read_a_file("INCAR", ".")

def write_INCAR(INCAR, where_to_write):
    write_a_file(INCAR, "INCAR", where_to_write)
    
def read_parent_KPOINTS():
    return read_a_file("KPOINTS", ".")
    
def write_KPOINTS(KPOINTS, where_to_write):
    write_a_file(KPOINTS, "KPOINTS", where_to_write)
    
def read_energy_from_OSZICAR(where_to_read):
    with open(os.path.join(where_to_read, "OSZICAR"), "r") as f:
        energy_line = list(f)[-1]
    return float(energy_line.split("E0=")[1].strip().split("d")[0])


# In[33]:


def prepare_rescaled_POSCAR_KPOINTS(scaling_list, which_latt_vec, parent_POSCAR, parent_KPOINTS):
    scaled_latt_vec_list = [0, 0, 0]
    #the three elements represent lattice vector a, b and c.
    #0 denotes that the corresponding element won't be rescaled; 1 denotes that the corresponding element will be rescaled.
    #if all of them will be rescaled, the universal scaling will be rescaled rather than rescaling the three.
    which_latt_vec = which_latt_vec.lower()
    for ind, ele in enumerate(["x", "y", "z"]):
        if ele in which_latt_vec:
            scaled_latt_vec_list[ind] = 1
    assert sum(scaled_latt_vec_list) != 0, "Seems you don't want to optimize any lattice vector... Then, why do you run this script -_-!!"
    if sum(scaled_latt_vec_list) == 3:
        rescale_universal_scaling = True
    else:
        rescale_universal_scaling = False
        
        
     
    rescaled_POSCAR_list = []
    rescaled_KPOINTS_list = []
    parent_kmesh_list = [int(k_) for k_ in parent_KPOINTS[3].strip().split()]
    assert len(parent_kmesh_list) == 3, "Fail to read kmesh from parent_KPOINTS.\nParent_kpoints={}\nparsed kmesh={}".format(parent_KPOINTS, parent_kmesh_list)
    for scaling_factor in scaling_list:
        rescaled_POSCAR = copy.deepcopy(parent_POSCAR)
        rescaled_KPOINTS = copy.deepcopy(parent_KPOINTS)
        if rescale_universal_scaling:
            rescaled_POSCAR["universal scaling"] = rescaled_POSCAR["universal scaling"] * scaling_factor
            rescaled_POSCAR_list.append(rescaled_POSCAR)
            rescaled_KPOINTS[3] = "\t".join([str(round(1. * k_ / scaling_factor)) for k_ in parent_kmesh_list]) + "\n"
            rescaled_KPOINTS_list.append(rescaled_KPOINTS)
        else:
            rescaled_kmesh_list = []
            for is_latt_rescaled, latt_vec_key, k_ in zip(scaled_latt_vec_list, ["latt_a", "latt_b", "latt_c"], parent_kmesh_list):
                if is_latt_rescaled:
                    rescaled_POSCAR[latt_vec_key] =  [i*scaling_factor for i in rescaled_POSCAR[latt_vec_key]]
                    rescaled_kmesh_list.append(round(1. * k_ / scaling_factor))
                else:
                    rescaled_kmesh_list.append(k_)
            rescaled_POSCAR_list.append(rescaled_POSCAR)
            rescaled_KPOINTS[3] = "%d\t%d\t%d\n"  % tuple(rescaled_kmesh_list)
            rescaled_KPOINTS_list.append(rescaled_KPOINTS)
    return rescaled_POSCAR_list, rescaled_KPOINTS_list

def prepare_sub_dir_cal_VASP_inputs(POSCAR_list, INCAR_list, KPOINTS_list, sub_dirname_list):
    for case_ind, sub_dirname in enumerate(sub_dirname_list):
        if not os.path.isdir(sub_dirname):
            os.mkdir(sub_dirname)
    
        written_file_list = []
        where_to_write = sub_dirname
        if not os.path.isfile(os.path.join(where_to_write, "POSCAR")):
            write_POSCAR(POSCAR=POSCAR_list[case_ind], where_to_write=where_to_write)
            written_file_list.append("POSCAR")
        if not os.path.isfile(os.path.join(where_to_write, "INCAR")):
            write_INCAR(INCAR=INCAR_list[case_ind], where_to_write=where_to_write)
            written_file_list.append("INCAR")
        if not os.path.isfile(os.path.join(where_to_write, "KPOINTS")):
            write_KPOINTS(KPOINTS=KPOINTS_list[case_ind], where_to_write=where_to_write)
            written_file_list.append("KPOINTS")
        if not os.path.isfile(os.path.join(where_to_write, "POTCAR")):
            shutil.copyfile(src="POTCAR", dst=os.path.join(where_to_write, "POTCAR"))
            written_file_list.append("POTCAR")
        if not os.path.isfile(os.path.join(where_to_write, "OSZICAR")) and not os.path.isfile(os.path.join(where_to_write, "__ready__")) and not os.path.isfile(os.path.join(where_to_write, "__running__")):
            open(os.path.join(where_to_write, "__ready__"), "w").close()
            written_file_list.append("__ready__")
            
        if written_file_list:
            print("Under {}, create according to its parent file: {}".format(sub_dirname, written_file_list) )


# In[3]:


def are_all_cal_done(cal_folder_list):
    """coded for structural optimizations."""
    are_all_done = True
    for cal_folder in cal_folder_list:
        if not os.path.isfile(os.path.join(cal_folder, "__done__")):
            are_all_done = False
        else:
            is_it_opt_cal = False
            with open(os.path.join(cal_folder, "INCAR"), "r") as f:
                lines = [line.strip(" \n").split("#")[0] for line in f]
            for line in lines:
                if "NSW" in line and int(line.split("=")[1]) != 0:
                    is_it_opt_cal = True
                    break
            if is_it_opt_cal:
                are_all_done = False
                for error_folder_name in os.listdir(cal_folder):
                    error_folder = os.path.join(cal_folder, error_folder_name)
                    if os.path.isdir(error_folder) and error_folder_name.startswith("error_folder"):
                        os.rename(src=error_folder, dst=os.path.join(cal_folder, "relax_"+error_folder_name))
                for backup_file in ["INCAR", "POSCAR", "CONTCAR", "KPOINTS", "OSZICAR", "OUTCAR"]:
                    shutil.copyfile(os.path.join(cal_folder, backup_file), os.path.join(cal_folder, "relax_"+backup_file))
                if os.path.isfile(os.path.join(cal_folder, "out")):
                    shutil.copyfile(os.path.join(cal_folder, "out"), os.path.join(cal_folder, "relax_out"))
                print("under %s, the structural optimization finished. --> Backup the relevant input and output files/directories (prefix: relax_) and start scf cal." % cal_folder)
                shutil.move(os.path.join(cal_folder, "CONTCAR"), os.path.join(cal_folder, "POSCAR"))
                with open(os.path.join(cal_folder, "INCAR"), "w") as f:
                    for line in lines:
                        LINE = line.upper()
                        if "NSW" in LINE or "IBRION" in LINE or "ISIF" in LINE or "EDIFFG" in LINE:
                            continue
                        f.write(line + "\n")
                shutil.move(os.path.join(cal_folder, "__done__"), os.path.join(cal_folder, "__ready__"))
    return are_all_done
                    


# In[34]:


def make_interpolation(status_dict):
    energy_list = []
    for cal_folder in status_dict["cal folder list"]:
        energy_list.append(read_energy_from_OSZICAR(cal_folder))
    with open("Energy_summary.dat", "w") as f:
        for scaling_factor, energy in zip(status_dict["scaling list"], energy_list):
            f.write('%f    %f\n' % (scaling_factor, energy))
            
    tck = interpolate.splrep(status_dict["scaling list"], energy_list, s=0)
    
    max_scaling, min_scaling = max(status_dict["scaling list"]), min(status_dict["scaling list"])
    extension =  (max_scaling - min_scaling) / (len(status_dict["scaling list"]) - 1) / 2.5
    fine_scaling_list = np.arange(min_scaling-extension, max_scaling+extension, 0.0001)
    interpolated_energy_list = interpolate.splev(fine_scaling_list, tck, der=0)
    min_energy = min(interpolated_energy_list)
    scaling_factor_for_min_energy = fine_scaling_list[list(interpolated_energy_list).index(min_energy)]
    
    plt.plot(status_dict["scaling list"], energy_list, "o--", label="DFT data")
    plt.plot(fine_scaling_list, interpolated_energy_list, "r-", label="cubic spline interpolation" )
    plt.xlabel("scaling factor")
    plt.ylabel("energy")
    plt.title("scaling-E curve obtained by DFT calculations.")
    plt.legend()
    plt.tight_layout()
    plt.savefig("interpolation_fig_no_DFT_verification.png", format="png")
    
    #Check if the interpolation curve is monotonic/concave.
    is_interpolation_suspicious = False
    reduced_slope_sign_list = [100]
    for energy_0, energy_1 in zip(interpolated_energy_list[:-1], interpolated_energy_list[1:]):
        energy_diff = energy_1 - energy_0
        if energy_diff > 0:
            sign = 1
        elif energy_diff < 0:
            sign = -1
        else:
            sign = 0
        if sign != reduced_slope_sign_list[-1]:
            reduced_slope_sign_list.append(sign)
    reduced_slope_sign_list = reduced_slope_sign_list[1:]
    if reduced_slope_sign_list not in [[-1], [1], [-1, 1]]:
        is_interpolation_suspicious = True
        
    if reduced_slope_sign_list not in [[-1], [1]]:
        print("Since the interpolated curve is not monotonic, the search of the interpolated minimum is constrained in between the smallest and largest DFT-tested scaling factors.")
        min_energy_ind, min_energy = 0, max(energy_list)
        for scaling_ind, scaling in enumerate(fine_scaling_list):
            if min_scaling <= scaling <= max_scaling:
                if interpolated_energy_list[scaling_ind] < min_energy:
                    min_energy_ind, min_energy = scaling_ind, interpolated_energy_list[scaling_ind]
        scaling_factor_for_min_energy = fine_scaling_list[min_energy_ind]
    else:
        print("Since the interpolated curve is monotonic, the search scope for minium includes the extropolation range.")
    
    with open("interpolated_data.json", "w") as f:
        json.dump({"DFT data": {"scaling list": status_dict["scaling list"], "energy list": energy_list}, 
                   "interpolation data":{"scaling list": list(fine_scaling_list), "energy list": list(interpolated_energy_list), 
                                         "prediction": [scaling_factor_for_min_energy, min_energy]}}, f, indent=4)
    
    print("All DFT calculations at {} finished, based on which the interpolated optimal scaling factor and its interpolated energy are {} and {}, respectively".format(status_dict["scaling list"], scaling_factor_for_min_energy, min_energy))
    
    if is_interpolation_suspicious:
        open("__manual__", "w").close()
        print("However, the interpolation curve is neither monotonic nor concave. The reduced slope sign list is {}. Create __manual__ and go check.".format(reduced_slope_sign_list))
    
    return scaling_factor_for_min_energy, min_energy

def verify_interpolated_result(status_dict, tot_no_of_atoms):
    with open("interpolated_data.json", "r") as f:
        data_summary_dict = json.load(f)
    verified_energy = read_energy_from_OSZICAR(status_dict["verification folder"])
    
    #tot_tol in meV
    if status_dict["tol unit"] == "mev/atom":
        tot_tol = tot_no_of_atoms * status_dict["tol"]
    else:
        tot_tol = status_dict["tol"]
        
    energy_diff = abs(verified_energy - data_summary_dict["interpolation data"]["prediction"][1]) * 1000
    is_grd_state_found = (energy_diff <= tot_tol)
        
    plt.cla()
    plt.plot(data_summary_dict["interpolation data"]["prediction"][0], data_summary_dict["interpolation data"]["prediction"][1], "d", color="lime", label="interpolated optimal point")
    plt.plot(data_summary_dict["interpolation data"]["prediction"][0], verified_energy, "o", color="orange", label="DFT verification")
    plt.plot(status_dict["scaling list"], data_summary_dict["DFT data"]["energy list"], "o", color="red", label="DFT data")
    plt.plot(data_summary_dict["interpolation data"]["scaling list"], data_summary_dict["interpolation data"]["energy list"], "r-", label="cubic spline interpolation")
    plt.xlabel("scaling factor")
    plt.ylabel("energy")
    text_string = "scaling factor: %f\ninterpolation: %f\n DFT verification: %f" %     tuple(status_dict["interpolated result"] + [verified_energy])
    text_string += "\nabs(E$_{int}$-E$_{DFT}$) is %f meV %s tot_tol (%f meV)" % (energy_diff, "<=" if is_grd_state_found else ">", tot_tol)
    x = 0.5*(min(data_summary_dict["interpolation data"]["scaling list"]) + max(data_summary_dict["interpolation data"]["scaling list"]))
    y = 0.2*min(data_summary_dict["interpolation data"]["energy list"]) + 0.8*max(data_summary_dict["interpolation data"]["energy list"])
    plt.text(x=x, y=y, s=text_string, horizontalalignment="center")
    #plt.legend()
    plt.tight_layout()
    plt.savefig("interpolation_fig.png", format="png")
    
    print("The measure of the interpolated optimal scaling factor based on {} is as follows:".format(status_dict["scaling list"]))
    print("\t\t"+text_string)
    
    return is_grd_state_found


# In[ ]:


def opt_lattice_constant(scaling_list, opt_which_latt_vec, tol_setup):
    status_dict = read_cal_status()
    if status_dict["scaling list"] == []:# or status_dict["scaling list"] != scaling_list:
        status_dict["scaling list"] = sorted(scaling_list)#sorted(list(set(scaling_list + status_dict["scaling list"])))
        status_dict["opt which latt vec"] = opt_which_latt_vec
        status_dict.update(tol_setup)
    opt_which_latt_vec = status_dict["opt which latt vec"]
    
    parent_POSCAR = read_parent_POSCAR()
    parent_KPOINTS = read_parent_KPOINTS()
    POSCAR_list, KPOINTS_list = prepare_rescaled_POSCAR_KPOINTS(scaling_list=status_dict["scaling list"], which_latt_vec=opt_which_latt_vec, 
                                                                parent_POSCAR=parent_POSCAR, parent_KPOINTS=parent_KPOINTS)
    no_of_cases = len(POSCAR_list)
    INCAR_list = [read_parent_INCAR()]*no_of_cases
    sub_dirname_list = ["case_"+str(scaling_factor) for scaling_factor in status_dict["scaling list"]]
    prepare_sub_dir_cal_VASP_inputs(POSCAR_list=POSCAR_list, INCAR_list=INCAR_list, KPOINTS_list=KPOINTS_list, 
                                    sub_dirname_list=sub_dirname_list)
    status_dict["cal folder list"] = sub_dirname_list
    write_cal_status(status_dict=status_dict)
        
    if are_all_cal_done(status_dict["cal folder list"]) and status_dict["verification folder"] == None:
        #interpolated_scaling_factor and interpolated_result are scaling_factor_for_min_energy and min_energy, respectively.
        interpolated_scaling_factor, interpolated_result = make_interpolation(status_dict)
        parent_POSCAR = read_parent_POSCAR()
        parent_KPOINTS = read_parent_KPOINTS()
        POSCAR_list, KPOINTS_list = prepare_rescaled_POSCAR_KPOINTS(scaling_list=[interpolated_scaling_factor], which_latt_vec=opt_which_latt_vec, 
                                                                    parent_POSCAR=parent_POSCAR, parent_KPOINTS=parent_KPOINTS)
        INCAR_list = [read_parent_INCAR()]
        prepare_sub_dir_cal_VASP_inputs(POSCAR_list=POSCAR_list, INCAR_list=INCAR_list, 
                                        KPOINTS_list=KPOINTS_list, sub_dirname_list=["verification_folder"])
        status_dict["interpolated result"] = [interpolated_scaling_factor, interpolated_result]
        status_dict["verification folder"] = "verification_folder"
        write_cal_status(status_dict=status_dict)
        
        if interpolated_scaling_factor in status_dict["scaling list"]:
            sub_dirname = "case_"+str(interpolated_scaling_factor)
            shutil.copyfile(src=os.path.join(sub_dirname, "OSZICAR"), dst=os.path.join("verification_folder", "OSZICAR"))
            shutil.copyfile(src=os.path.join(sub_dirname, "INCAR"), dst=os.path.join("verification_folder", "INCAR"))
            os.rename(src=os.path.join("verification_folder", "__ready__"), dst=os.path.join("verification_folder", "__done__"))
            open(os.path.join("verification_folder", "__copy_incar_oszicar_from_{}__".format(sub_dirname)), "w").close()
            print("Since the interpolated scaling factor (Scal_inter) is already in the scaling factor list based on which Scal_inter is obtained,", end=" ")
            print("we do not need to repeat the same calculation. Just copy INCAR and OSZICAR from {} to verification_folder, ".format(sub_dirname), end=" ")
            print("and under folder verification_folder rename __ready__ to __done__ and create file __copy_incar_oszicar_from_{}__".format(sub_dirname))
    
    if status_dict["verification folder"]:
        if are_all_cal_done([status_dict["verification folder"]]) == False:
            return False
        
        if verify_interpolated_result(status_dict, tot_no_of_atoms=parent_POSCAR["tot_no_of_atoms"]):
            shutil.move("__sub_dir_cal__", "__done__")
            print("As indicated above, the lattice parameter optimization is completed. __sub_dir_cal__ --> __done__")
        else:
            if len(status_dict["scaling list"]) > status_dict["max_no_of_points"]:
                shutil.move("__sub_dir_cal__", "__manual__")
                print("oops! Although the optimal lattice parameter has not identified yet, the max number of testing points (%d) is hitted. __sub_dir_cal__ --> __manual__" % status_dict["max_no_of_points"])
                print("If you want to test more points. Increase 'max_no_of_points' in latt_param_opt_setup.json and reset __manual__ to __sub_dir_cal__")
            else:
                sub_dirname = "case_" + str(status_dict["interpolated result"][0])
                shutil.move(status_dict["verification folder"], sub_dirname)
                
                print("The interpolated scaling factor/lattice parameter is not accurate enough. There are %d testing points, less than the pre-defined max number (%d)." % (len(status_dict["scaling list"]), status_dict["max_no_of_points"]))
                print("Add the interpolated point to the scaling list and update it in latt_param_opt_setup.json")
                print("change folder name: %s --> %s" % (status_dict["verification folder"], sub_dirname))
                print("Let the script make a new interpolation based on the updated scaling list.")
                
                status_dict["scaling list"] = sorted(status_dict["scaling list"] + [status_dict["interpolated result"][0]])
                status_dict["verification folder"] = None
                status_dict["interpolated result"] = []
                
                write_cal_status(status_dict=status_dict) 
                
                


# In[ ]:


if __name__ == "__main__":
    scaling_list_length = int(sys.argv[1])
    scaling_list = [float(scaling) for scaling in sys.argv[2:2+scaling_list_length]]
    
    last_argv = sys.argv[-1].lower()
    if last_argv.endswith("mev") or last_argv.endswith("mev/atom"):
        try:
            tol_setup = {"tol": float(last_argv.split("mev")[0]), "tol unit": "mev" + last_argv.split("mev")[1]}
        except:
            print("Fail to parse 'tol' and 'tol unit' from {}".format(last_argv))
            raise
        opt_which_latt_vec = "".join(sys.argv[2+scaling_list_length:-1])
    else:
        opt_which_latt_vec = "".join(sys.argv[2+scaling_list_length:])
        tol_setup = {} #the default is provided in function read_cal_status
        
    opt_lattice_constant(scaling_list=scaling_list, opt_which_latt_vec=opt_which_latt_vec, tol_setup=tol_setup)

