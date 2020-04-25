#!/usr/bin/env python
# coding: utf-8

# In[2]:


import os, sys, re, math
HTC_package_path = "C:/Users/tyang/Documents/Jupyter_workspace/HTC/python_3"
if  os.path.isdir(HTC_package_path) and HTC_package_path not in sys.path:
    sys.path.append(HTC_package_path)
    
from HTC_lib.VASP.INCAR.modify_vasp_incar import modify_vasp_incar

from pymatgen import Structure


# In[135]:


class VaspAutomaticKMesh():
    
    def __init__(self, cal_loc, NL, kmesh_type="Auto", shift=[0, 0, 0], max_vacuum_thickness=[5, 5, 5], str_filename="POSCAR",
                 symprec_latt_const = 0.1, symprec_angle = 1, *argvs, **kwargvs):
        """
        cal_loc (str): the absolute or relative path to the folder under which  POSCAR is read, and KPOINTS is read or written.
        NL (int or float): the product of the real space lattice constant (L) and the subdivision (N). NL should be the same or very close along the directions
            along which the periodic boundary condition (PBC) holds. This ensures that the k-points in the BZ is equally spaced.
        kmesh_type: either "Monkhorst-Pack", "Gamma" or "Auto"
                    If kmesh_type = "Auto", "Gamma" will be chosen if any of the calculated subdivisions along the pbc axes is odd; Otherwise, "Monkhorst-Pack"
                    In the following cases, kmesh_type will be internally set to "Gamma" regardless of the input value:
                        1. The lattice is hexagonal
                        2. The calculated subdivisions are (1, 1, 1)
                        3. ISMEAR = -5 in INCAR
                    Default: "Auto"
        shift (list of length 3): the shift of the k-mesh
                    Default: [0, 0, 0]
        max_vacuum_thickness (list of length 3): the max thickness of the vacuum layer along the x-, y- and z-axis. 
                    The unit is Angstrom
                    If max_vacuum_thickness[i] is smaller than that found along the i-th axis, we think PBC doesn't hold along this axis and the subdivision is always set to 1
                    Default: [5, 5, 5]
        str_file (str): Default: "POSCAR"
        symprec_latt_const (int or float): the tolerance used to tell if any two of the lattice constants are euqal.
                                            The unit is Angstrom.
                                            ***This argument together with symprec_angle are used to tell if the lattice is hexagonal. If it is, set Gamma-centered k-mesh***
                                            Default: 0.1
        symprec_angle (int or float): the tolerance used to tell if any of the lattice angles is equal to 60 or 120 degrees.
                                            The unit is degree.
                                            ***This argument together with symprec_angle are used to tell if the lattice is hexagonal. If it is, set Gamma-centered k-mesh***
                                            Default: 1
        
        """
        self.cal_loc = cal_loc
        self.NL = NL
        self.kmesh_type = kmesh_type.lower()
        self.shift = shift
        self.max_vacuum_thickness = max_vacuum_thickness
        self.str_filename = str_filename
        self.symprec_latt_const = symprec_latt_const
        self.symprec_angle = symprec_angle
        self.structure_dict = self._read_strcutre_info()
        self.pbc_type_of_xyz = VaspAutomaticKMesh.does_pbc_hold_along_xyz_axes(cal_loc, str_filename, max_vacuum_thickness)
        
    def _read_strcutre_info(self):
        struct = Structure.from_file(os.path.join(self.cal_loc, self.str_filename))
        latt_a, latt_b, latt_c = struct.lattice.a, struct.lattice.b, struct.lattice.c
        alpha, beta, gamma = struct.lattice.alpha, struct.lattice.beta, struct.lattice.gamma
        
        structure_dict = {"lattice_constants": (latt_a, latt_b, latt_c), 
                          "lattice_angles": (alpha, beta, gamma), 
                          "frac_coords": struct.frac_coords, 
                          "lattice_matrix": struct.lattice.matrix}
        
        if abs(latt_a - latt_b) <= self.symprec_latt_const and abs(abs(gamma - 90) - 30) <= self.symprec_angle:
            structure_dict["is_it_hexagonal"] = True
        elif abs(latt_b - latt_c) <= self.symprec_latt_const and abs(abs(alpha - 90) - 30) <= self.symprec_angle:
            structure_dict["is_it_hexagonal"] = True
        elif abs(latt_c - latt_a) <= self.symprec_latt_const and abs(abs(beta - 90) - 30) <= self.symprec_angle:
            structure_dict["is_it_hexagonal"] = True
        else:
            structure_dict["is_it_hexagonal"] = False
        
        return structure_dict
    
    @classmethod
    def get_pbc_sublist(cls, a_list, pbc_type_of_xyz):
        return [item for item, pbc_type in zip(a_list, pbc_type_of_xyz) if pbc_type]
    
    @classmethod
    def does_pbc_hold_along_xyz_axes(cls, cal_loc, str_filename="POSCAR", max_vacuum_thickness=[5, 5, 5]):
        struct = Structure.from_file(os.path.join(cal_loc, str_filename))
        latt_a, latt_b, latt_c = struct.lattice.a, struct.lattice.b, struct.lattice.c
        frac_coords = struct.frac_coords
        
        frac_max_vacuum_thickness_x = max_vacuum_thickness[0] * 1. / latt_a
        frac_max_vacuum_thickness_y = max_vacuum_thickness[1] * 1. / latt_b
        frac_max_vacuum_thickness_z = max_vacuum_thickness[2] * 1. / latt_c
        
        sorted_frac_x_list = sorted([VaspAutomaticKMesh.map_to_0_1(frac_coord[0]) for frac_coord in frac_coords])
        sorted_frac_y_list = sorted([VaspAutomaticKMesh.map_to_0_1(frac_coord[1]) for frac_coord in frac_coords])
        sorted_frac_z_list = sorted([VaspAutomaticKMesh.map_to_0_1(frac_coord[2]) for frac_coord in frac_coords])
        
        #handle the case like: [0.49, 0.50, 0.51]
        max_diff_frac_x = max([x_2 - x_1 for x_1, x_2 in zip(sorted_frac_x_list[:-1], sorted_frac_x_list[1:])])
        max_diff_frac_y = max([y_2 - y_1 for y_1, y_2 in zip(sorted_frac_y_list[:-1], sorted_frac_y_list[1:])])
        max_diff_frac_z = max([z_2 - z_1 for z_1, z_2 in zip(sorted_frac_z_list[:-1], sorted_frac_z_list[1:])])
        
        #handle the case like: [0.01, 0.98, 0.99]
        max_diff_frac_x = max([max_diff_frac_x, 1 - sorted_frac_x_list[-1], sorted_frac_x_list[0]])
        max_diff_frac_y = max([max_diff_frac_y, 1 - sorted_frac_y_list[-1], sorted_frac_y_list[0]])
        max_diff_frac_z = max([max_diff_frac_z, 1 - sorted_frac_z_list[-1], sorted_frac_z_list[0]])
        
        return [max_diff_frac_x <= frac_max_vacuum_thickness_x, 
                max_diff_frac_y <= frac_max_vacuum_thickness_y, 
                max_diff_frac_z <= frac_max_vacuum_thickness_z]
        
    
    @classmethod
    def map_to_0_1(cls, number):
        """
        map the input number into [0, 1)
        """
        if number >= 1:
            return number - math.floor(number)
        elif number < 0:
            return number - math.floor(number)
        else:
            return number
        
    @classmethod
    def get_subdivisions(cls, NL, latt_constants, pbc_type_of_xyz=[True, True, True]):
        subdivisions, dNL = [], []
        for axis_ind in range(len(latt_constants)):
            if pbc_type_of_xyz[axis_ind]:
                division = max([round(NL / latt_constants[axis_ind]), 1])
                dnl = NL - division * latt_constants[axis_ind]
            else:
                division = 1
                dnl = 0
            subdivisions.append(division)
            dNL.append(dnl)
        return {"subdivisions": subdivisions, "dNL": dNL}
    
    @classmethod
    def get_possible_NL(cls, subdivisions, latt_constants, pbc_type_of_xyz=[True, True, True]):
        pbc_type_of_xyz = pbc_type_of_xyz[:len(latt_constants)]
        if True not in pbc_type_of_xyz:
            return []
        
        pbc_subdivisions = VaspAutomaticKMesh.get_pbc_sublist(subdivisions, pbc_type_of_xyz)
        pbc_latt_constants = VaspAutomaticKMesh.get_pbc_sublist(latt_constants, pbc_type_of_xyz)
        
        pbc_NL = [division * latt_constant for division, latt_constant in zip(pbc_subdivisions, pbc_latt_constants)]
        pbc_NL_floor, pbc_NL_ceil = math.floor(min(pbc_NL)), math.ceil(max(pbc_NL))+1
        possible_NL_list = []
        NL_step = 1
        while possible_NL_list == [] and NL_step >= 0.1:
            NL = pbc_NL_floor
            while NL <= pbc_NL_ceil:
                if pbc_subdivisions == VaspAutomaticKMesh.get_subdivisions(NL, pbc_latt_constants)["subdivisions"]:
                    possible_NL_list.append(NL)
                NL += NL_step
            NL_step -= 0.1
        
        if possible_NL_list == []:
            print("Warning: No possible NL given the below input parameters:")
            print("\tsubdivisions = [{}, {}, {}]".format(*subdivisions))
            print("\tlatt_constants = [{}, {}, {}]".format(*latt_constants))
            print("\tpbc_type_of_xyz = [{}, {}, {}]".format(*pbc_type_of_xyz))
            print("\treturn: []")
        return possible_NL_list
    
    @classmethod
    def optimize_NL(cls, NL, latt_constants, pbc_type_of_xyz=[True, True, True]):
        """
        Given an NL, the subdivisions can be caluclated and rounded to integers based on the lattice constants and the pbc type of the x-, y- and z-axis.
        However, there might be more than one NL given a set of subdivision (n_kx, n_ky, n_kz).
        This class method optimizes NL in such a way that min(abs(max(n_ki*latt_i-NL))) w.r.t NLs corresponding to the same (n_kx, n_ky, n_kz). If the minimum is 
            degenerate, minimize p-norm of (abs(NL-n_kx*a), abs(NL-n_ky*b), abs(NL-n_kz*c)) from p=1 until the minimum is unique. 
            This optimization is only w.r.t. the pbc axis/axes.
        return a dictionary with the key and value being NL and the corresponding (NL-n_kx*a, NL-n_ky*b, NL-n_kz*c)
        """
        subdivisions = VaspAutomaticKMesh.get_subdivisions(NL=NL, latt_constants=latt_constants, pbc_type_of_xyz=pbc_type_of_xyz)["subdivisions"]
        pbc_subdivisions = VaspAutomaticKMesh.get_pbc_sublist(subdivisions, pbc_type_of_xyz)
        pbc_L = VaspAutomaticKMesh.get_pbc_sublist(latt_constants, pbc_type_of_xyz)
        possible_NL_list = VaspAutomaticKMesh.get_possible_NL(subdivisions=pbc_subdivisions, latt_constants=pbc_L)
        
        min_dNL_ind_list, dNL_list, min_dNL = [], [], 1000
        for NL_ind, NL in enumerate(possible_NL_list):
            dNL_list.append([abs(NL - division * L) for division, L in zip(pbc_subdivisions, pbc_L)])
            if min_dNL > max(dNL_list[-1]):
                min_dNL = max(dNL_list[-1])
                min_dNL_ind_list = [NL_ind]
            elif min_dNL == max(dNL_list[-1]):
                min_dNL_ind_list.append(NL_ind)
        
        p = 1
        while len(min_dNL_ind_list) > 1 and p < 5:
            min_p_norm, new_min_dNL_ind_list = 1000, []
            for dNL_ind in min_dNL_ind_list:
                p_norm = pow(sum([abs(dnl)**p for dnl in dNL_list[dNL_ind]]), 1./p)
                if p_norm < min_p_norm:
                    min_p_norm = p_norm
                    new_min_dNL_ind_list.append(dNL_ind)
            min_dNL_ind_list = new_min_dNL_ind_list
            p += 1
            
        if p == 5 and len(min_dNL_ind_list) > 1:
            print("Warning: Fail to find the best unique NL given the below parameters")
            print("\tsubdivisions: [{}, {}, {}]".format(*subdivisions))
            print("\tpbc_type_of_xyz: [{}, {}, {}]".format(*self.pbc_type_of_xyz))
            print("All possilbe NLs: " + ", ".join([str(NL) for NL in possible_NL_list]))
            print(", ".join([str(possible_NL_list[dNL_ind]) for dNL_ind in min_dNL_ind_list]) + "are the best.")
        
        optimal_NL_dict = {}
        for dNL_ind in min_dNL_ind_list:
            NL = possible_NL_list[dNL_ind]
            optimal_NL_dict[NL] = VaspAutomaticKMesh.get_subdivisions(NL=NL, latt_constants=latt_constants, pbc_type_of_xyz=pbc_type_of_xyz)["dNL"]
        return optimal_NL_dict
        
    
    def get_kpoints_setup(self):
        """
        return a dictionary containing:
            subdivisions: a list of length 3 --> the subdivisions along the k_x, k_y and k_z
            kmesh_type: "Gamma" or "Monkhorst-Pack"
            shfit: a list of length 3
            NL: the product of the real lattice constant and the subdivision. It should be the same for (a, n_kx), (b, n_ky) and (c, n_kz)
            pbc_type_of_xyz: a boolean list of length 3. 
            is_it_hexagonal: bool
            equivalent_NL: a list of NLs giving the same subdivisions
            optimal_NL: a dictionary with the key and value being the optimal NL and the corresponding deviation of the subdivisions
            VaspAutomaticKMesh_input_arguments: a dictionary including all input arguments to VaspAutomaticKMesh
            
        """
        kpoints = VaspAutomaticKMesh.get_subdivisions(self.NL, self.structure_dict["lattice_constants"], self.pbc_type_of_xyz)
        
        incar_dict = modify_vasp_incar(cal_loc=self.cal_loc)
        
        if self.structure_dict["is_it_hexagonal"] or kpoints["subdivisions"] == [1, 1, 1] or incar_dict["ISMEAR"] == "-5":
            kpoints["kmesh_type"] = "Gamma"
        elif self.kmesh_type == "auto":
            if 1 in [division % 2 for division in VaspAutomaticKMesh.get_pbc_sublist(kpoints["subdivisions"], self.pbc_type_of_xyz)]:
                kpoints["kmesh_type"] = "Gamma"
            else:
                kpoints["kmesh_type"] = "Monkhorst-Pack"
        else:
            kpoints["kmesh_type"] = self.kmesh_type
        
                
        kpoints["shift"] = self.shift
        kpoints["NL"] = self.NL
        kpoints["pbc_type_of_xyz"] = self.pbc_type_of_xyz
        
        kpoints["equivalent_NL"] = VaspAutomaticKMesh.get_possible_NL(subdivisions=kpoints["subdivisions"], 
                                                                      latt_constants=self.structure_dict["lattice_constants"], 
                                                                      pbc_type_of_xyz=self.pbc_type_of_xyz)
        kpoints["optimal_NL"] = VaspAutomaticKMesh.optimize_NL(NL=self.NL, 
                                                               latt_constants=self.structure_dict["lattice_constants"], 
                                                               pbc_type_of_xyz=self.pbc_type_of_xyz)
        
    
        kpoints["VaspAutomaticKMesh_input_arguments"] = {}
        for key in ["NL", "kmesh_type", "shift", "max_vacuum_thickness", "str_filename", "symprec_latt_const", "symprec_angle"]:
            kpoints["VaspAutomaticKMesh_input_arguments"][key] = self.__dict__[key]

        
        return kpoints
    
    
    @classmethod
    def write_KPOINTS(cls, kpoints_setup, cal_loc, filename="KPOINTS"):
        """
        Write KPOINTS under cal_loc according to kpoints_setup.
    
        kpoints_setup could be any dictionary containing at least the key-value pairs:
            1. pbc_type_of_xyz: a bool list of length 3 indicating if the Periodic Boundary Condition holds along the x-, y- and z-axis
            2. NL: a number -- the product of the subdivision along k_i and the lattice constant along the i-th axis. It should be the same or similiar for all PBC axis(axes).
            3. kmesh_type: "Monkhorst-Pack" or "Gamma"
            4. subdivisions: a integer list of length 3 indicating the subdivision along the k_x, k_y and k_z dirction.
            The above information must be provided
        Two optional keys:
            1. comment: if not provided, it is set to "a*n_kx, b*n_ky and c*n_kz are close to NL"
            2. shift: if not provided, it is set to [0, 0, 0]
        has a format of the output dictionary of method get_kpoints_setup.
        """
        
        with open(os.path.join(cal_loc, filename), "w") as kpoints:
            comment = ", ".join(VaspAutomaticKMesh.get_pbc_sublist(["a*n_kx", "b*n_ky", "c*n_kz"], kpoints_setup["pbc_type_of_xyz"]))
            comment += " are close to {}".format(kpoints_setup["NL"])
            kpoints.write("{}\n".format(kpoints_setup.get("comment", comment)))
            kpoints.write("0\n")
            kpoints.write("{}\n".format(kpoints_setup["kmesh_type"]))
            kpoints.write("{}  {}  {}\n".format(*kpoints_setup["subdivisions"]))
            kpoints.write("{}  {}  {}\n".format(*kpoints_setup.get("shift", [0, 0, 0])))
            
    @classmethod
    def read_from_KPOINTS_and_POSCAR(cls, cal_loc, max_vacuum_thickness, KPOINTS_filename="KPOINTS", POSCAR_filename="POSCAR"):
        """
        max_vacuum_thickness is a list of length 3. We need this to tell if the periodic boundary condition (PBC) holds along the x-, y- and z- axis and thus calculate NL.
        If you think that PBC holds for all of x-, y- and z-axes, set max_vacuum_thickness = [1000, 1000, 1000].
        """
        struct = Structure.from_file(os.path.join(cal_loc, POSCAR_filename))
        latt_a, latt_b, latt_c = struct.lattice.a, struct.lattice.b, struct.lattice.c
        alpha, beta, gamma = struct.lattice.alpha, struct.lattice.beta, struct.lattice.gamma
        
        kpoints_setup = {"lattice_constants": [latt_a, latt_b, latt_c], "lattice_angles": [alpha, beta, gamma]}
        with open(os.path.join(cal_loc, KPOINTS_filename), "r") as kpoints:
            kpoints_setup["comment"] = next(kpoints).strip("\n")
            assert next(kpoints).strip().startswith("0"), "The second line in KPOINTS must be soley '0' indicating an automatic k-mesh grid.\nDir: {}".format(cal_loc)
            
            kmesh_type = next(kpoints).strip("\n").strip().lower()
            if kmesh_type.startswith("g"):
                kpoints_setup["kmesh_type"] = "Gamma"
            elif kmesh_type.startswith("m"):
                kpoints_setup["kmesh_type"] = "Monkhorst-Pack"
            else:
                raise Exception("Fail to parse kmesh type from {}\n I am only able to parse automatic-type k-mesh".format(os.path.join(cal_loc, KPOINTS_filename)))
            
            kpoints_setup["subdivisions"] = [int(division) for division in re.findall("[0-9]+", next(kpoints))[:3]]
            
            line = next(kpoints).strip("\n")
            if line.strip() == "":
                kpoints_setup["shift"] = ["0", "0", "0"]
            else:
                try:
                    kpoints_setup["shift"] = [division for division in re.findall("[0-9\.]+", line)[:3]]
                except:
                    raise Exception("Fail to parse the shift in the fifth line from {}\n I am only able to parse the automatic-type k-mesh".format(os.path.join(cal_loc, KPOINTS_filename)))
                
        
        kpoints_setup["max_vacuum_thickness"] = max_vacuum_thickness
        pbc_type_of_xyz = VaspAutomaticKMesh.does_pbc_hold_along_xyz_axes(cal_loc, POSCAR_filename, max_vacuum_thickness)
        kpoints_setup["equivalent_NL"] = VaspAutomaticKMesh.get_possible_NL(subdivisions=kpoints_setup["subdivisions"], 
                                                                            latt_constants=[latt_a, latt_b, latt_c], 
                                                                            pbc_type_of_xyz=pbc_type_of_xyz)
        if len(kpoints_setup["equivalent_NL"]) == 0:
            kpoints_setup["optimal_NL"] = {}
        elif len(kpoints_setup["equivalent_NL"]) == 1:
            kpoints_setup["optimal_NL"] = kpoints_setup["equivalent_NL"]
        else:
            kpoints_setup["optimal_NL"] = VaspAutomaticKMesh.optimize_NL(NL=kpoints_setup["equivalent_NL"][0], 
                                                                         latt_constants=[latt_a, latt_b, latt_c], 
                                                                         pbc_type_of_xyz=pbc_type_of_xyz)
        return kpoints_setup
            


# poscar_path = "test/twoD_rectangular/rectangular_NiNC_POSCAR"
# cal_loc, poscar_name = os.path.split(poscar_path)
# input_arguments = {
#     "cal_loc": cal_loc, 
#     "NL": 55, 
#     "kmesh_type": "Monkhorst-Pack", 
#     "shift": [0, 0, 0], 
#     "max_vacuum_thickness":[0.1, 0.01, 0.001], 
#     "str_filename": poscar_name, 
#     'symprec_latt_const': 0.1, 
#     "symprec_angle": 1.
# }
# kmesher = VaspAutomaticKMesh(**input_arguments)
# VaspAutomaticKMesh.write_KPOINTS(kmesher.get_kpoints_setup(), cal_loc=cal_loc)
# kmesher.get_kpoints_setup()

# VaspAutomaticKMesh.read_from_KPOINTS_and_POSCAR(cal_loc=cal_loc, POSCAR_filename=poscar_name, max_vacuum_thickness=[5, 10, 5])
