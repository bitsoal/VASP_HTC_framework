#!/usr/bin/env python
# coding: utf-8

# In[37]:


import os, math, re

from pymatgen import Structure


# In[98]:


class VaspAutomaticKMesh():
    
    def __init__(self, cal_loc, NL, kmesh_type="Auto", shift=[0, 0, 0], max_vacuum_thickness=[5, 5, 5], str_filename="POSCAR", symprec_latt_const = 0.1, symprec_angle = 1):
        """
        cal_loc (str): the absolute or relative path to the folder under which  POSCAR is read, and KPOINTS is read or written.
        NL (int or float): the product of the real space lattice constant (L) and the subdivision (N). NL should be the same or very close along the directions
            along which the periodic boundary condition (PBC) holds. This ensures that the k-points in the BZ is equally spaced.
        kmesh_type: either "Monkhorst-Pack", "Gamma" or "Auto"
                    If kmesh_type = "Auto", "Gamma" will be chosen if any of the calculated subdivisions along the pbc axes is odd; Otherwise, "Monkhorst-Pack"
                    Note that if the lattice is hexagonal, kmesh_type will be internally set to "Gamma".
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
                          "angles": (alpha, beta, gamma), 
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
        
        #hand the case like: [0.01, 0.98, 0.99]
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
    
    def get_kpoints_setup(self):
        """
        return a dictionary containing:
            subdivisions: a list of length 3 --> the subdivisions along the k_x, k_y and k_z
            kmesh_type: "Gamma" or "Monkhorst-Pack"
            shfit: a list of length 3
            NL: the product of the real lattice constant and the subdivision. It should be the same for (a, n_kx), (b, n_ky) and (c, n_kz)
            pbc_type_of_xyz: a boolean list of length 3. 
        """
        kpoints = {"subdivisions": []}
        for axis_ind in range(3):
            if self.pbc_type_of_xyz[axis_ind]:
                division = round(self.NL / self.structure_dict["lattice_constants"][axis_ind])
                division = max([division, 1])
            else:
                division = 1
            kpoints["subdivisions"].append(division)
        
        if self.structure_dict["is_it_hexagonal"]:
            kpoints["kmesh_type"] = "Gamma"
        elif self.kmesh_type == "auto":
            if  1 in [division % 2 for division, pbc_type in zip(kpoints["subdivisions"], self.pbc_type_of_xyz) if pbc_type]:
                kpoints["kmesh_type"] = "Gamma"
            else:
                kpoints["kmesh_type"] = "Monkhorst-Pack"
        else:
            kpoints["kmesh_type"] = self.kmesh_type
                
        kpoints["shift"] = self.shift
        kpoints["NL"] = self.NL
        kpoints["pbc_type_of_xyz"] = self.pbc_type_of_xyz
        
        return kpoints
    
    @classmethod
    def write_KPOINTS(cls, kpoints_setup, cal_loc, filename="KPOINTS"):
        """
        kpoints_setup has a format of the output dictionary of method get_kpoints_setup.
        Two optional keys:
            1. comment: if not provided, it is set to "a*n_kx, b*n_ky and c*n_kz are close to NL"
            2. shift: if not provided, it is set to [0, 0, 0]
        """
        
        with open(os.path.join(cal_loc, filename), "w") as kpoints:
            comment = ", ".join([product for product, pbc in zip(["a*n_kx", "b*n_ky", "c*n_kz"], kpoints_setup["pbc_type_of_xyz"]) if pbc])
            comment += " are close to {}".format(kpoints_setup["NL"])
            kpoints.write("{}\n".format(kpoints_setup.get("comment", comment)))
            kpoints.write("0\n")
            kpoints.write("{}\n".format(kpoints_setup["kmesh_type"]))
            kpoints.write("{}\t{}\t{}\n".format(*kpoints_setup["subdivisions"]))
            kpoints.write("{}\t{}\t{}\t\n".format(*kpoints_setup.get("shift", [0, 0, 0])))
            
    @classmethod
    def read_from_KPOINTS_and_POSCAR(cls, cal_loc, max_vacuum_thickness, KPOINTS_filename="KPOINTS", POSCAR_filename="POSCAR"):
        """
        max_vacuum_thickness is a list of length 3. We need this to tell if the periodic boundary condition (PBC) holds along the x-, y- and z- axis and thus calculate NL.
        If you think that PBC holds for all of x-, y- and z-axes, set max_vacuum_thickness = [1000, 1000, 1000].
        """
        struct = Structure.from_file(os.path.join(cal_loc, POSCAR_filename))
        latt_a, latt_b, latt_c = struct.lattice.a, struct.lattice.b, struct.lattice.c
        
        kpoints_setup = {}
        with open(os.path.join(cal_loc, KPOINTS_filename), "r") as kpoints:
            kpoints_setup["comment"] = next(kpoints).strip("\n")
            next(kpoints)
            
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
                
        
        pbc_type_of_xyz = VaspAutomaticKMesh.does_pbc_hold_along_xyz_axes(cal_loc, POSCAR_filename, max_vacuum_thickness)
        pbc_L = [latt_const for latt_const, pbc_type in zip([latt_a, latt_b, latt_c], pbc_type_of_xyz) if pbc_type]
        pbc_subdivisions = [subdivision for subdivision, pbc_type in zip(kpoints_setup["subdivisions"], pbc_type_of_xyz) if pbc_type]
        pbc_NL = [L*subdivision for L, subdivision in zip(pbc_L, pbc_subdivisions)]
        
        allowed_NL_list = []
        NL_step = 1
        pbc_NL_floor, pbc_NL_ceil = math.floor(min(pbc_NL)), math.ceil(max(pbc_NL)) + 1
        while allowed_NL_list == [] and NL_step >= 0.1:
            NL = pbc_NL_floor
            while NL <= pbc_NL_ceil:
                if pbc_subdivisions == [round(NL/L) for L in pbc_L]:
                    allowed_NL_list.append(NL)
                NL += NL_step
                
            NL_step -= 0.1
            
        return kpoints_setup, allowed_NL_list
            
