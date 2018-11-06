
# coding: utf-8

# Application: coded for lattice constant optimization using the sub-dir calculations. Optimize and calculate the energy of a strcuture with serveral different lattice constants, and make a cubic spline interpolation to obtain the optimal lattice constants.
# 
# How to use it: 
# >>>python optimize_lattice_constant_VASP no_of_points scaling_1 scaling_2 scaling_3 ... scaling_no_of_points [x] [y] [z]
# Note that this script will read the POSCAR in the same folder where this script is run. So there must be a POSCAR as a parent POSCAR based on which a series of strucures by scaling the lattice vectors of the parent structure will be created for sub-dir calculations
# arguments:
#     no_of_points: an integer, the number of structures with different lattice constants that will be calculated for the subsequent cubic spline interpolation for the optimal lattice constant estimation
#     scaling_1, scaling_2, ..., scaling_no_of_points: a list of scaling factors that will be applied to the universal scaling or lattice vector a, b or c
#     x y z: any combination of x, y and z. determine which lattice vector(s) is(are) scaled. If all the three are chosen, the universal scaling in POSCAR will be scaled rather than the three lattice vectors.
#     
# e.g.
# rescale the lattice vector a by multiplying it with 0.96, 0.98, 1.0, 1.02 and 1.04
# >>>python optimize_lattice_constant_VASP 5 0.96 0.98 1.0 1.02 1.04 x
# 
# rescale the lattice vector a and b by multiplying them with 0.94, 0.96, 0.98, 1.0, 1.02 and 1.04
# >>>python optimize_lattice_constant_VASP 6 0.94 0.96 0.98 1.0 1.02 1.04 x y
# 
# rescale the univeral scaling in the parent POSCAR by multiplying it with 0.98, 1.0, 1.02 and 1.04
# >>>python optimize_lattice_constant_VASP 4 0.98 1.0 1.02 1.04 x y z

# In[1]:


import sys, os, json, copy, shutil
from scipy import interpolate
import numpy as np
import matplotlib.pyplot as plt


# In[29]:


def read_sub_dir_cal_status():
    is_empty = True
    with open("__sub_dir_cal__", "r") as f:
        lines = [line.strip() for line in f if line.strip()]
    if lines:
        with open("__sub_dir_cal__", "r") as f:
            status_dict = json.load(f)
    else:
        status_dict = {"scaling list": [], 
                       "cal folder list": [], 
                       "interpolated result": [], 
                       "verification folder": None}
    return status_dict

def write_sub_dir_cal_status(status_dict):
    with open("__sub_dir_cal__", "w") as f:
        json.dump(status_dict, f)
        
def read_parent_POSCAR():
    with open("POSCAR", "r") as f:
        lines = list(f)
    universal_scaling = float(lines[1].strip(" \n"))
    latt_a = [float(i) for i in lines[2].strip(" \n").split()]
    latt_b = [float(i) for i in lines[3].strip(" \n").split()]
    latt_c = [float(i) for i in lines[4].strip(" \n").split()]
    return {"comment": lines[0], "universal scaling": universal_scaling, "latt_a": latt_a, "latt_b": latt_b, "latt_c": latt_c, "others": lines[5:]}

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


# In[15]:


def prepare_rescaled_POSCAR(scaling_list, which_latt_vec, parent_POSCAR):
    scaled_latt_vec_list = [0, 0, 0]
    #the three elements represent lattice vector a, b and c.
    #0 denotes that the corresponding element won't be rescaled; 1 denotes that the corresponding element will be rescaled.
    #if all of them will be rescaled, the universal scaling will be rescaled rather than rescaling the three.
    which_latt_vec = which_latt_vec.lower()
    for ind, ele in enumerate(["x", "y", "z"]):
        if ele in which_latt_vec:
            scaled_latt_vec_list[ind] = 1
    assert sum(scaled_latt_vec_list) != 0, "Seems you don't want to optimize any lattice vectors. If so, why do you invoke me?"
    if sum(scaled_latt_vec_list) == 3:
        rescale_universal_scaling = True
    else:
        rescale_universal_scaling = False
        
        
     
    rescaled_POSCAR_list = []
    for scaling_factor in scaling_list:
        rescaled_POSCAR = copy.deepcopy(parent_POSCAR)
        if rescale_universal_scaling:
            rescaled_POSCAR["universal scaling"] = rescaled_POSCAR["universal scaling"] * scaling_factor
            rescaled_POSCAR_list.append(rescaled_POSCAR)
        else:
            for is_latt_rescaled, latt_vec_key in zip(scaled_latt_vec_list, ["latt_a", "latt_b", "latt_c"]):
                if is_latt_rescaled:
                    rescaled_POSCAR[latt_vec_key] =  [i*scaling_factor for i in rescaled_POSCAR[latt_vec_key]]
            rescaled_POSCAR_list.append(rescaled_POSCAR)
    return rescaled_POSCAR_list

def prepare_sub_dir_cal_VASP_inputs(POSCAR_list, INCAR_list, KPOINTS_list, sub_dirname_list, status_dict):
    status_dict["cal folder list"] = []
    for case_ind, sub_dirname in enumerate(sub_dirname_list):
        if not os.path.isdir(sub_dirname):
            os.mkdir(sub_dirname)
    
        where_to_write = sub_dirname
        if not os.path.isfile(os.path.join(where_to_write, "POSCAR")):
            write_POSCAR(POSCAR=POSCAR_list[case_ind], where_to_write=where_to_write)
        if not os.path.isfile(os.path.join(where_to_write, "INCAR")):
            write_INCAR(INCAR=INCAR_list[case_ind], where_to_write=where_to_write)
        if not os.path.isfile(os.path.join(where_to_write, "POTCAR")):
            write_KPOINTS(KPOINTS=KPOINTS_list[case_ind], where_to_write=where_to_write)
        if not os.path.isfile(os.path.join(where_to_write, "POTCAR")):
            shutil.copyfile(src="POTCAR", dst=os.path.join(where_to_write, "POTCAR"))
        if not os.path.isfile(os.path.join(where_to_write, "OSZICAR")) and not os.path.isfile(os.path.join(where_to_write, "__ready__")):
            open(os.path.join(where_to_write, "__ready__"), "w").close()
        status_dict["cal folder list"].append(where_to_write)
    return status_dict


# In[16]:


def are_all_cal_done(cal_folder_list):
    """coded for structural optimizations."""
    are_all_done = True
    for cal_folder in cal_folder_list:
        if not os.path.isfile(os.path.join(cal_folder, "__done__")):
            are_all_done = False
            continue
        else:
            is_opt_cal = False
            with open(os.path.join(cal_folder, "INCAR"), "r") as f:
                lines = [line.strip(" \n").split("#")[0] for line in f]
            for line in lines:
                if "NSW" in line and int(line.split("=")[1]) != 0:
                    is_opt_cal = True
                    break
            if is_opt_cal:
                are_all_done = False
                for backup_file in ["INCAR", "POSCAR", "KPOINTS", "OSZICAR", "OUTCAR"]:
                    shutil.copyfile(os.path.join(cal_folder, backup_file), os.path.join(cal_folder, "relax_"+backup_file))
                shutil.move(os.path.join(cal_folder, "CONTCAR"), os.path.join(cal_folder, "POSCAR"))
                with open(os.path.join(cal_folder, "INCAR"), "w") as f:
                    for line in lines:
                        LINE = line.upper()
                        if "NSW" in LINE or "IBRION" in LINE or "ISIF" in LINE or "EDIFFG" in LINE:
                            continue
                        f.write(line + "\n")
                shutil.move(os.path.join(cal_folder, "__done__"), os.path.join(cal_folder, "__ready__"))
    return are_all_done
                    


# In[28]:


def make_interpolation(status_dict):
    energy_list = []
    for cal_folder in status_dict["cal folder list"]:
        energy_list.append(read_energy_from_OSZICAR(cal_folder))
    with open("Energy_summary.dat", "w") as f:
        for scaling_factor, energy in zip(status_dict["scaling list"], energy_list):
            f.write('%f    %f\n' % (scaling_factor, energy))
    tck = interpolate.splrep(status_dict["scaling list"], energy_list, s=0)
    fine_scaling_list = np.arange(status_dict["scaling list"][0], status_dict["scaling list"][-1], 0.001)
    interpolated_energy_list = interpolate.splev(fine_scaling_list, tck, der=0)
    min_energy = min(interpolated_energy_list)
    scaling_factor_for_min_energy = fine_scaling_list[list(interpolated_energy_list).index(min_energy)]
    
    with open("interpolated_data.dat", "w") as f:
        json.dump({"DFT data": {"scaling list": status_dict["scaling list"], "energy list": energy_list}, 
                   "interpolation data":{"scaling list": list(fine_scaling_list), "energy list": list(interpolated_energy_list), 
                                         "prediction": [scaling_factor_for_min_energy, min_energy]}}, f)
    
    return scaling_factor_for_min_energy, min_energy

def verify_interpolated_result(status_dict):
    with open("interpolated_data.dat", "r") as f:
        data_summary_dict = json.load(f)
    verified_energy = read_energy_from_OSZICAR(status_dict["verification folder"])
        
    plt.cla()
    plt.plot(status_dict["scaling list"], data_summary_dict["DFT data"]["energy list"], "d", label="DFT data")
    plt.plot(data_summary_dict["interpolation data"]["scaling list"], data_summary_dict["interpolation data"]["energy list"], "r-", label="cubic spline interpolation")
    plt.xlabel("scaling factor")
    plt.ylabel("energy")
    text_string = "scaling factor: %f\ninterpolation: %f\n DFT verification: %f" %     tuple(status_dict["interpolated result"] + [verified_energy])
    x = 0.5*(min(data_summary_dict["DFT data"]["scaling list"]) + max(data_summary_dict["DFT data"]["scaling list"]))
    y = 0.5*(min(data_summary_dict["DFT data"]["energy list"]) + max(data_summary_dict["DFT data"]["energy list"]))
    plt.text(x=x, y=y, s=text_string, horizontalalignment="center")
    plt.tight_layout()
    plt.savefig("interpolation_fig.png", format="png")
    return False
    
    


# In[20]:


def opt_lattice_constant(scaling_list, opt_which_latt_vec):
    status_dict = read_sub_dir_cal_status()
    if status_dict["scaling list"] == []:# or status_dict["scaling list"] != scaling_list:
        status_dict["scaling list"] = sorted(scaling_list)#sorted(list(set(scaling_list + status_dict["scaling list"])))
    parent_POSCAR = read_parent_POSCAR()
    POSCAR_list = prepare_rescaled_POSCAR(scaling_list=scaling_list, which_latt_vec=opt_which_latt_vec, parent_POSCAR=parent_POSCAR)
    no_of_cases = len(POSCAR_list)
    INCAR_list = [read_parent_INCAR()]*no_of_cases
    KPOINTS_list = [read_parent_KPOINTS()]*no_of_cases
    sub_dirname_list = ["case_"+str(scaling_factor) for scaling_factor in status_dict["scaling list"]]
    prepare_sub_dir_cal_VASP_inputs(POSCAR_list=POSCAR_list, INCAR_list=INCAR_list, KPOINTS_list=KPOINTS_list, 
                                    sub_dirname_list=sub_dirname_list, status_dict=status_dict)
    write_sub_dir_cal_status(status_dict=status_dict)
        
    if are_all_cal_done(status_dict["cal folder list"]) and status_dict["verification folder"] == None:
        interpolated_scaling_factor, interpolated_result = make_interpolation(status_dict)
        parent_POSCAR = read_parent_POSCAR()
        POSCAR_list = prepare_rescaled_POSCAR(scaling_list=[interpolated_scaling_factor], which_latt_vec=opt_which_latt_vec, parent_POSCAR=parent_POSCAR)
        INCAR_list = [read_parent_INCAR()]
        KPOINTS_list = [read_parent_KPOINTS()]
        prepare_sub_dir_cal_VASP_inputs(POSCAR_list=POSCAR_list, INCAR_list=INCAR_list, 
                                        KPOINTS_list=KPOINTS_list, sub_dirname_list=["verification_folder"], status_dict=status_dict)
        status_dict["interpolated result"] = [interpolated_scaling_factor, interpolated_result]
        status_dict["verification folder"] = "verification_folder"
        write_sub_dir_cal_status(status_dict=status_dict)
    
    if status_dict["verification folder"]:
        if are_all_cal_done([status_dict["verification folder"]]) == False:
            return False
        if not verify_interpolated_result(status_dict):
            shutil.move("__sub_dir_cal__", "__manual__")
        


# In[25]:


if __name__ == "__main__":
    scaling_list_length = int(sys.argv[1])
    scaling_list = [float(scaling) for scaling in sys.argv[2:2+scaling_list_length]]
    opt_which_latt_vec = "".join(sys.argv[2+scaling_list_length:])
    opt_lattice_constant(scaling_list=scaling_list, opt_which_latt_vec=opt_which_latt_vec)

