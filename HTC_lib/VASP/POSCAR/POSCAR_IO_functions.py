#!/usr/bin/env python
# coding: utf-8

# In[4]:


import os, re, sys
import numpy as np


# In[2]:


def cal_angle_between_two_vectors(vec_1, vec_2):
    """calculate and return the angle between two vectors. The angle is in radians"""
    unit_vec_1 = vec_1 / np.linalg.norm(vec_1)
    unit_vec_2 = vec_2 / np.linalg.norm(vec_2)
    dot_product = np.dot(unit_vec_1, unit_vec_2)
    
    return np.arccos(dot_product) / np.pi * 180


# In[12]:


def get_lattice_properties(lattice_matrix):
    latt_prop_dict = {}
    latt_vec_a, latt_vec_b, latt_vec_c = lattice_matrix[0, :], lattice_matrix[1, :], lattice_matrix[2, :]
    latt_prop_dict["inv_lattice_matrix"] = np.linalg.inv(lattice_matrix)
    latt_prop_dict["lattice_constant_a"] = np.linalg.norm(latt_vec_a)
    latt_prop_dict["lattice_constant_b"] = np.linalg.norm(latt_vec_b)
    latt_prop_dict["lattice_constant_c"] = np.linalg.norm(latt_vec_c)
    #alpha: angle between latt_vec_b and latt_vec_c; 
    #beta: angle between latt_vec_a and latt_vec_c
    #gamma: angle between latt_vec_a and latt_vec_b
    #The above convention is adopted by pymatgen (https://github.com/materialsproject/pymatgen/blob/v2020.8.13/pymatgen/core/lattice.py)
    #as well as wikipedia (webpage: Crystal system)
    latt_prop_dict["alpha"] = cal_angle_between_two_vectors(latt_vec_b, latt_vec_c)
    latt_prop_dict["beta"] = cal_angle_between_two_vectors(latt_vec_a, latt_vec_c)
    latt_prop_dict["gamma"] = cal_angle_between_two_vectors(latt_vec_a, latt_vec_b)
    return latt_prop_dict


# In[3]:


def read_poscar(poscar_filename="POSCAR", cal_loc="."):
    full_poscar_filename = os.path.join(cal_loc, poscar_filename)
    poscar_dict = {}
    with open(full_poscar_filename) as poscar_f:
        poscar_dict["original_poscar"] = list(poscar_f)
    
    poscar_lines = [line.strip() for line in poscar_dict["original_poscar"]]
    
    scaling_factor = float(re.findall("[0-9\-\.]+", poscar_lines[1])[0])
    latt_vec_a = [float(num) for num in poscar_lines[2].split()[:3]]
    latt_vec_b = [float(num) for num in poscar_lines[3].split()[:3]]
    latt_vec_c = [float(num) for num in poscar_lines[4].split()[:3]]
    poscar_dict["lattice_matrix"] = np.array([latt_vec_a, latt_vec_b, latt_vec_c])
    if scaling_factor < 0: #if this value is negative it is interpreted as the total volume of the cell
        vol = abs(np.linalg.det(poscar_dict["lattice_matrix"]))
        scaling_factor = (-scaling_factor / vol) ** (1./3)
        poscar_dict["lattice_matrix"] = poscar_dict["lattice_matrix"] * scaling_factor
    else:
        poscar_dict["lattice_matrix"] = poscar_dict["lattice_matrix"] * scaling_factor
    poscar_dict["inv_lattice_matrix"] = np.linalg.inv(poscar_dict["lattice_matrix"])
    poscar_dict["lattice_constant_a"] = np.linalg.norm(poscar_dict["lattice_matrix"][0, :])
    poscar_dict["lattice_constant_b"] = np.linalg.norm(poscar_dict["lattice_matrix"][1, :])
    poscar_dict["lattice_constant_c"] = np.linalg.norm(poscar_dict["lattice_matrix"][2, :])
    #alpha: angle between latt_vec_b and latt_vec_c; 
    #beta: angle between latt_vec_a and latt_vec_c
    #gamma: angle between latt_vec_a and latt_vec_b
    #The above convention is adopted by pymatgen (https://github.com/materialsproject/pymatgen/blob/v2020.8.13/pymatgen/core/lattice.py)
    #as well as wikipedia (webpage: Crystal system)
    poscar_dict["alpha"] = cal_angle_between_two_vectors(latt_vec_b, latt_vec_c)
    poscar_dict["beta"] = cal_angle_between_two_vectors(latt_vec_a, latt_vec_c)
    poscar_dict["gamma"] = cal_angle_between_two_vectors(latt_vec_a, latt_vec_b)
    
    #parse the atomic species
    species_items = re.findall("[a-zA-Z]+", poscar_lines[5].split("#")[0])
    if species_items == []: #VASP4 POSCAR does not have this line
        print("Warning: {} does not have the line specifying the atomic species. \nIs this a VASP4 calculation? If it is, please ensure that atomic sequence in POSCAR be consistent with that in POTCAR. \nSuch a line must be present in POSCAR for a VASP5 calculation.".format(full_poscar_filename))
        line_ind_of_atom_no = 5
    else:
        line_ind_of_atom_no = 6
    #assert len(species_items) > 0, "{}: the 6th line must specify the constituting elements (in the order how they appear in the POTCAR file)".format(full_poscar_filename)    
    atom_no_items = [int(num) for num in re.findall("[0-9]+", poscar_lines[line_ind_of_atom_no].split("#")[0])]
    assert len(atom_no_items) > 0, "{}: the {}th line supplies the number of atoms per atomic species (one number for each atomic species)".format(full_poscar_filename, line_ind_of_atom_no+1)
    assert species_items == [] or len(species_items) == len(atom_no_items), "{}: line 6 (atomic species) and line 7 (the number of atoms per atomic species) should have the same length (1-1 correspondence)".format(full_poscar_filename)
    total_atom_no = sum(atom_no_items)
    
    species_list = []
    for atomic_species, atom_no in zip(species_items, atom_no_items):
        species_list.extend([atomic_species for i in range(atom_no)])
    poscar_dict["atomic_species"] = species_list #For VASP4 POSCAR, this would be an empty list.
    
    #If the first letter of line 7 or 8 is "s" or "S", the selective dynamics mode is activated
    #In this case, the first letter of line 8 or 9 determines the coordinate type of the atomic positions:
    #first letter@line 8 or 9 == "c", "C", "k" or "K" <--> Cartesian coordinate
    #first letter@line 8 or 9 == "d" or "D" <--> Direct coordinate
    first_letter = poscar_lines[line_ind_of_atom_no+1].strip()[0].lower()
    if first_letter == "s":
        poscar_dict["is_selective_dynamics_on"] = True
        first_letter = poscar_lines[line_ind_of_atom_no+2].strip()[0].lower() #Update first_letter with the coordinate type
        line_ind_of_1st_atomic_position = line_ind_of_atom_no + 3
    else:
        poscar_dict["is_selective_dynamics_on"] = False
        line_ind_of_1st_atomic_position = line_ind_of_atom_no + 2
        
    if first_letter in ["c", "k"]:
        coordinate_type = "cartesian"
    elif first_letter == "d":
        coordinate_type = "direct"
    else:
        raise Exception("{}: The first letter of the line specifying the coordinate type must be 'c', 'C', 'k' or 'K' for Cartesian, OR 'd' or 'D' for Direct".format(full_poscar_filename))
        
    coords, selective_dynamics_mode = [], []
    for line_ind in [line_ind_of_1st_atomic_position + i for i in range(total_atom_no)]:
        items = poscar_lines[line_ind].strip().split()
        coords.append([float(num) for num in items[:3]])
        if poscar_dict["is_selective_dynamics_on"]:
            selective_dynamics_mode.append(items[3:6])
        else:
            selective_dynamics_mode.append(["", "", ""])
    #if poscar_dict["is_selective_dynamics_on"]:
    poscar_dict["selective_dynamics_mode"] = selective_dynamics_mode
    
    if coordinate_type == "cartesian":
        cart_coords = np.array(coords) * scaling_factor #The universal scaling factor is applied to the atomic positions only if they are in cartesian coordinates.
        frac_coords = np.matmul(cart_coords, poscar_dict["inv_lattice_matrix"])
    else:
        frac_coords = np.array(coords)
        cart_coords = np.matmul(frac_coords, poscar_dict["lattice_matrix"])
    poscar_dict["cart_coords"] = cart_coords
    poscar_dict["frac_coords"] = frac_coords
    
    return poscar_dict


# In[13]:


def sort_poscar(by, key=None, reverse=False, poscar_filename="POSCAR", cal_loc="."):
    """
    Read and sort POSCAR.
    The python built-in function sorted(iterable, /, *, key=None, reverse=False) will be deployed to sort POSCAR.
    Arguments 'key' (default: None) and 'reverse' (default: False) will be passed to function sorted.
    As for 'iterable' of function sorted, it is provided by argument 'by' of the current function:
        This function passes a N-entry list as 'iterable' to function sorted to figure the new order to sort the whole POSCAR.
            N is the number of that quantities specified by argument 'by'. 
            The i-th entry (0-based index) is a 2-element list: [i, the i-th quantity]
            See below for the i-th quantity
    -by (str): It could be anyone below:
        * "atomic_species": the i-th quantity is the atomic species (str) of the i-th atom in the original POSCAR
        * "cart_coords": the i-th quantity is the cartesian coordinate (1D numpy array of length 3 and type float) of the i-th atom in the original POSCAR
        * "frac_coords": the i-th quantity is the fractional coordinate (1D numpy array of length 3 and type float) of the i-th atom in the original POSCAR
        * "selective_dynamics_mode": the i-th quantity is the selective mode (a list of 3 and type str) of the i-th atom in the original POSCAR
        * "lattice_matrix": the i-th quantity is the i-th lattice vector (1D numpy array of length 3 and type float) in the original POSCAR
    -poscar_filename (default: "POSCAR"): the filename of POSCAR
    -cal_loc (default: "."): the path to that POSCAR
    Return a sorted poscar dict whose format is the same as the output of function read_poscar.
    """
    available_by_list = ["atomic_species", "cart_coords", "frac_coords", "selective_dynamics_mode", "lattice_matrix"]
    assert by in available_by_list, 'Input argument "by" of fuction sort_poscar must be "atomic_species", "cart_coords", "frac_coords", "selective_dynamics_mode" or "lattice_matrix"'
    poscar_dict = read_poscar(poscar_filename=poscar_filename, cal_loc=cal_loc)
    
    sorted_index_list = [ind_value_pair[0] for ind_value_pair in sorted(iterable=enumerate(poscar_dict[by]), key=key, reverse=reverse)]
    if by in ["atomic_species", "cart_coords", "frac_coords", "selective_dynamics_mode"]:
        for quantity in ["atomic_species", "cart_coords", "frac_coords", "selective_dynamics_mode"]:
            poscar_dict[quantity] = [poscar_dict[quantity][ind] for ind in sorted_index_list]
    elif by == "lattice_matrix":
        new_lattice_matrix = [poscar_dict["lattice_matrix"][ind] for ind in sorted_index_list]
        poscar_dict["lattice_matrix"] = new_lattice_matrix
        poscar_dict.update(get_lattice_properties(new_lattice_matrix))
        for quantity in ["cart_coords", "frac_coords", "selective_dynamics_mode"]:
            for atom_ind, atom_quantity in enumerate(poscar_dict[quantity]):
                new_atom_quantity = [atom_quantity[ind] for ind in sorted_index_list]
                poscar_dict[quantity][atom_ind] = new_atom_quantity
    else:
        raise Exception("You should not arrive here!")
        
    return poscar_dict


# In[13]:


def cal_mae(item_a, item_b):
    return np.sum(np.abs(item_a - item_b))


# In[22]:


def test_all(folder_list_filename):
    from pymatgen import Structure
    
    with open(folder_list_filename) as f:
        folder_list = [line.strip() for line in f if line.strip()]
        
    tolerance = 1.0e-10
    for folder in folder_list:
        print("\n" + os.path.join(folder, "POSCAR"))
        try:
            struct = Structure.from_file(os.path.join(folder, "POSCAR"))
        except:
            print("pymatgen.Structure fails to read {}/POSCAR".format(folder))
            continue
            
        try:
            poscar = read_poscar(cal_loc=folder, poscar_filename="POSCAR")
            print("same as pymatgen.Structure?")
            print("a: ", abs(poscar["lattice_constant_a"] - struct.lattice.a) < tolerance)
            print("b: ", abs(poscar['lattice_constant_b'] - struct.lattice.b) < tolerance)
            print("c: ", abs(poscar["lattice_constant_c"] - struct.lattice.c) < tolerance)
            print("alpha: ", abs(poscar["alpha"] -  struct.lattice.alpha) < tolerance)
            print("beta: ", abs(poscar["beta"] - struct.lattice.beta) < tolerance)
            print("gamma: ", abs(poscar["gamma"] - struct.lattice.gamma) < tolerance)
            print("atomic species: ", poscar["atomic_species"] == [str(spe) for spe in struct.species])
            print("latt matrix: ", cal_mae(poscar["lattice_matrix"], struct.lattice.matrix) < tolerance)
            print("frac_coords: ", cal_mae(poscar["frac_coords"], struct.frac_coords) < tolerance)
            print("cart_coords: ", cal_mae(poscar["cart_coords"], struct.cart_coords) < tolerance)
        except:
            print("fail to read {}/POSCAR".format(folder))            


# In[23]:


def test_a_single_cal(folder):
    from pymatgen import Structure
    
    print(os.path.join(folder, "POSCAR"))
    struct = Structure.from_file(os.path.join(folder, "POSCAR"))

    poscar = read_poscar(cal_loc=folder, poscar_filename="POSCAR")
    print("same as pymatgen.Structure?")
    print("a: ", poscar["lattice_constant_a"], struct.lattice.a)
    print("b: ", poscar['lattice_constant_b'], struct.lattice.b)
    print("c: ", poscar["lattice_constant_c"], struct.lattice.c)
    print("alpha: ", poscar["alpha"], struct.lattice.alpha)
    print("beta: ", poscar["beta"], struct.lattice.beta)
    print("gamma: ", poscar["gamma"], struct.lattice.gamma)
    print("atomic species", poscar["atomic_species"] == [str(spe) for spe in struct.species])
    print("latt matrix: ", cal_mae(poscar["lattice_matrix"], struct.lattice.matrix))
    print("frac_coords: ", cal_mae(poscar["frac_coords"], struct.frac_coords))
    print("cart_coords: ", cal_mae(poscar["cart_coords"], struct.cart_coords))


# In[21]:


if __name__ == "__main__":
    if os.path.isfile(sys.argv[1]):
        test_all(sys.argv[1])
    else:
        test_a_single_cal(sys.argv[1])

