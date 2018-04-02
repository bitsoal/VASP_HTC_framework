
# coding: utf-8

# # created on March 31 2018

# In[1]:


import os, shutil

from pymatgen.io.vasp.sets import MPRelaxSet, MPNonSCFSet, MPStaticSet
from pymatgen import Structure
from pymatgen.symmetry.bandstructure import HighSymmKpath

from Utilities import get_time_str,  find_next_name, decorated_os_rename


# In[2]:


def Write_Vasp_KPOINTS(cal_loc, structure_filename, workflow):
    """
    Write or modify KPOINTS in cal_loc as follows:
        step I: Check the presence of file KPOINTS in folder cal_loc.
                If present, no need to write KPOINTS,
                If missing, write KPOINTS according to tag kpoints_tag
        step II: If KPOINTS is written and the system is 2D according to tag 2d_system, modify KPOINTS such that K_z = 0 for all kpoints
        step III: tag denser_kpoints defaults to (1, 1, 1). If denser_kpoints is set, then modfiy KPOINTS accordingly and save the old
                KPOINTS as KPOINTS.sparse. Note that this function is only active for automatically generated KPOINTS, namely,
                kpoints_type = "MPRelaxSet" or "MPStaticSet"
    Input arguments:
        cal_loc (str): the absolute path
        structure_filename (str): the file from which the structure is read using pymatgen.Structure.from_file
        workflow
    """
    vasp_kpoints = Vasp_Kpoints(cal_loc, structure_filename, workflow)
    firework = vasp_kpoints.current_firework
    
    #If file KPOINTS is present in cal_loc folder, no need to write KPOINTS
    if os.path.isfile(os.path.join(cal_loc, "KPOINTS")):
        kpoints_type = None 
    else:
        kpoints_type = vasp_kpoints.current_firework["kpoints_type"]
        
    if kpoints_type == "Line-mode":
        vasp_kpoints.Write_line_mode_KPOINTS(intersections=firework["intersections"], twoD_system=workflow[0]["2d_system"])
        with open(vasp_kpoints.log_txt, 'a') as f:
            f.write("{} INFO: write KPOINTS in the line mode based on pymatgen.symmetry.bandstructure.HighSymmKpath\n".format(get_time_str()))
            if workflow[0]["2d_system"]:
                f.write("\t\t\tKPOINTS is already suitable for 2D systems\n")
    elif kpoints_type == 'MPNonSCFSet_line':
        vasp_kpoints.Write_NONSCF_KPOINTS(mode="line", kpoints_line_density=firework["kpoints_line_density"])
    elif kpoints_type == "MPNonSCFSet_uniform":
        vasp_kpoints.Write_NONSCF_KPOINTS(mode="uniform", reciprocal_density=firework["reciprocal_density"])
    elif kpoints_type == "MPRelaxSet":
        vasp_kpoints.Write_MPRelax_KPOINTS(force_gamma=workflow[0]["force_gamma"])
    elif kpoints_type == "MPStaticSet":
        vasp_kpoints.Write_MPStatic_KPOINTS(force_gamma=workflow[0]["force_gamma"])
    
    if kpoints_type in ['MPNonSCFSet_line', "MPNonSCFSet_uniform", "MPRelaxSet", "MPStaticSet"]:
        with open(vasp_kpoints.log_txt, "a") as f:
            f.write("{} INFO: use pymatgen.io.vasp.{} ".format(get_time_str(),kpoints_type))
            f.write("to write KPOINTS under {}\n".format(vasp_kpoints.firework_name))
        
        if workflow[0]["2d_system"]:
            new_name = vasp_kpoints.modify_vasp_kpoints_for_2D(rename_old_kpoints="KPOINTS.pymatgen_"+kpoints_type)
            with open(vasp_kpoints.log_txt, "a") as f:
                f.write("\t\t\tKPOINTS is modified for 2D systems\n")
                f.write("\t\t\t\told KPOINTS --> {}\n".format(new_name))
    
    kpoints_type = firework["kpoints_type"]
    #tag denser_kpoints consists of integers by default. If this tag is set, the three numbers are float.
    if isinstance(firework["denser_kpoints"][0], float) and (kpoints_type in ["MPRelaxSet", "MPStaticSet"]):
        vasp_kpoints.make_KPOINTS_denser(denser_kpoints = firework["denser_kpoints"])
        with open(vasp_kpoints.log_txt, "a") as f:
            f.write("\t\t\ttag denser_kpoints has been set to {}\n".format(firework["denser_kpoints"]))
            f.write("\t\t\t\tSo change KPOINTS according to denser_kpoints\n")
            f.write("\t\t\t\told KPOINTS --> KPOINTS.sparse\n")
    


# In[3]:


class Vasp_Kpoints():
    
    def __init__(self, cal_loc, structure_filename, workflow):
        self.cal_loc, self.workflow = cal_loc, workflow
        self.log_txt_loc, self.firework_name = os.path.split(cal_loc)
        self.log_txt = os.path.join(self.log_txt_loc, "log.txt")
        self.structure = Structure.from_file(os.path.join(self.cal_loc, structure_filename))
        self.current_firework = self.get_current_firework()
        
    def get_current_firework(self):
        for firework in self.workflow:
            if self.firework_name == firework["firework_folder_name"]:
                return firework
            
            
    def Write_MPRelax_KPOINTS(self, **kwargs):
        """
        generate KPOINTS for scf or structural relaxations cal by pymatgen.io.vasp.set.MPRelaxSet.
        """
        vis = MPRelaxSet(structure=self.structure, **kwargs)
        vis.kpoints.write_file(os.path.join(self.cal_loc, "KPOINTS"))
            
    def Write_MPStatic_KPOINTS(self, **kwargs):
        """
        generate KPOINTS for scf cal by pymatgen.io.vasp.set.MPStaticSet.
        """
        vis = MPStaticSet(structure=self.structure, **kwargs)
        vis.kpoints.write_file(os.path.join(self.cal_loc, "KPOINTS"))
        
    def Write_NONSCF_KPOINTS(self, mode="line", nedos=601, reciprocal_density=100, sym_prec=0.1, 
                             kpoints_line_density=20, optics=False, **kwargs):
        """
        generate KPOINTS for DOS (mode="uniform") or band struture (mode="line") by pymatgen.io.vasp.set.MPNonSCFSet
        input arguments:
            -mode (str): 'line' or 'uniform'
            -nedos (int): default 601. Only valid at mode='uniform'
            -reciprocal_density (int): default 100. Only valid at mode='uniform'
            -sym_prec (float): default 0.1
            -kpoints_line_density (int): default 20. Only valid at mode='line'
            -optics (bool)
        """
        vis = MPNonSCFSet(structure=self.structure, mode=mode, nedos=nedos, reciprocal_density=reciprocal_density, 
                          sym_prec=sym_prec, kpoints_line_density=kpoints_line_density, optics=optics)
        vis.kpoints.write_file(os.path.join(self.cal_loc, "KPOINTS"))
        
    def Write_line_mode_KPOINTS(self, intersections, twoD_system=False):
        """
        Write a kpath along the high symmetry kpoints in the line mode into KPOINTS under dir cal_loc for the band structure calculation.
        input arguments:
            - intersections (int): For every segment, there are intersections equally spaced kpionts, including the starting and ending high symmetry k-points
            - twoD_system (bool): If True, the kpath only includes the kpoints whose z component are zero. Default: False
        see https://cms.mpi.univie.ac.at/vasp/vasp/Strings_k_points_bandstructure_calculations.html
        Note that the reciprocal coordinates are adopted.
        Note that if twoD_system is True, the vacuum layer is assumed to be along the Z direction and the lattice vector c must be normal to the surface.
        """
        kpath = HighSymmKpath(structure=self.structure).get_kpoints(line_density=1, coords_are_cartesian=False)
        kpoints = []
        for k_, k_label in zip(*kpath):
            if k_label:
                kpoints.append(list(k_) + [k_label])
    
        starting_kpoints = kpoints[::2]
        ending_kpoints = kpoints[1::2]
    
        with open(os.path.join(self.cal_loc, "KPOINTS"), "w") as f:
            f.write("k-points along high symmetry lines\n")
            f.write("{}\n".format(intersections))
            f.write("Line-mode\n")
            f.write("rec\n")
            for start_k, end_k in zip(starting_kpoints, ending_kpoints):
                if twoD_system and (abs(start_k[2])+abs(end_k[2])) > 1.0e-5:
                    continue
                
                f.write("    {}  {}  {}    {}\n".format(*start_k))
                f.write("    {}  {}  {}    {}\n".format(*end_k))
                f.write("\n")
                
    def make_KPOINTS_denser(self, denser_kpoints = []):
        """
        Modify KPOINTS such that the kpiont along the axes in certain directions is denser_kpoints denser. Rename old KPOINTS as KPOINTS.sparse
        input arguments:
            denser_kpoints (list of float): This tag is only active at kpoints_type='MPRelaxSet', 'MPStaticSet',
                                            namely only for automatically generated KPOINTS
            Note that denser_kpoints must consist of three float numbers:
                - The first number is associated to the 'x' axis
                - The second number is associated to the 'y' axis
                - The third number is associated to the 'z' axis
        """
        if self.current_firework["kpoints_type"] not in ['MPRelaxSet', 'MPStaticSet']:
            return False
        
        assert len(denser_kpoints) == 3, "Error: tag denser_kpoints must be three float/integer numbers separated by commas."
        
        with open(os.path.join(self.cal_loc, "KPOINTS"), "r") as f:
            kpoints = [line.strip() for line in f if line.strip()]
            
        assert "gam" in kpoints[2].lower() or "mon" in kpoints[2].lower(), "Error: fail to make KPOINTS denser at {}".format(self.cal_loc)
        nk_list = [int(k) for k in kpoints[3].split() if k]
        for i in range(3):
            nk_list[i] = int(round(nk_list[i]*denser_kpoints[i]))
            if nk_list[i] == 0:
                nk_list[i] = 1
                    
        kpoints[3] = "{} {} {}".format(*nk_list)
        decorated_os_rename(loc=self.cal_loc, old_filename="KPOINTS", new_filename="KPOINTS.sparse")
        
        with open(os.path.join(self.cal_loc, "KPOINTS"), "w") as f:
            for line in kpoints:
                f.write(line+"\n")
                
    def modify_vasp_kpoints_for_2D(self, rename_old_kpoints=True, tolerance=1.0e-5):
        """
        modify KPOINTS properly for 2D structures.
        support kpoints_type for KPOINTS modifications: 'MPRelaxSet', 'MPStaticSet', 'MPNonSCFSet_line', 'MPNonSCFSet_uniform', 'automatic'
                    - 'MPRelaxSet': pymatgen.io.vasp.sets.MPRelaxSet generates KPOINTS.
                    - 'MPStaticSet': pymatgen.io.vasp.sets.MPStaticSet generates KPOINTS.
                    - 'MPNonSCFSet_uniform': pymatgen.io.vasp.sets.MPNonSCFSet generates KPOINTS in the uniform mode for DOS
                    - 'MPNonSCFSet_line': pymatgen.io.vasp.sets.MPNonSCFSet generates KPOINTS in the line mode for band str
        input arguments:
            - rename_old_kpoints (bool or str):
                    - if it is True, rename the old KPOINTS like KPOINTS_0, KPOINTS_1, KPINTS_2, ...
                    - if it is False, the old KPOINTS will be overwritten
                    - if it a string, the string is the new name of the old KPOINTS
                    Default: True
            - tolerance (float): if abs(k_z) < tolerance for uniform and line modes, 
                            we think this kpoint is valid; otherwise remove it.
                            Default: 1.0e-5
        if old KPOINTS is saved, return the new name of the old KPOINTS.
        """
        
        kpoints_type = self.current_firework["kpoints_type"]
        
        if kpoints_type.strip() not in ['MPRelaxSet', 'MPStaticSet', 'MPNonSCFSet_line', 'MPNonSCFSet_uniform']:
            print("Error: for func modify_vasp_kpoints_for_2D, the input argument kpoints_tag must be on the those below:")
            print("'MPRelaxSet', 'MPStaticSet', 'MPNonSCFSet_line', 'MPNonSCFSet_uniform'")
            raise Exception("See above for the error information")
    
        with open(os.path.join(self.cal_loc, "KPOINTS"), "r") as f:
            kpoints = [line.strip() for line in f if line.strip()]
        
        if kpoints_type in ['MPRelaxSet', 'MPStaticSet']:
            assert "gam" in kpoints[2].lower() or "mon" in kpoints[2].lower(), "Error: fail to modify KPOINTS generated by pymatgen at {}".format(cal_loc)
            nk_list = [int(k) for k in kpoints[3].split()]
            if nk_list[2] != 1:
                nk_list[2] = 1
            kpoints[3] = "{} {} {}".format(*nk_list)
        else:
            assert "reci" in kpoints[2].lower(), "Error: fail to modify KPOINTS generated by pymatgen in the uniform/line mode at {}".format(cal_loc)
            new_kpoints = []
            for kpoint in kpoints[3:]:
                k = kpoint.split()
                k = [float(k[0]), float(k[1]), float(k[2]), int(k[3])]
                if abs(k[2]) < tolerance:
                    new_kpoints.append(kpoint)
            kpoints = kpoints[:3] + new_kpoints
            kpoints[1] = str(len(new_kpoints))
    
        if isinstance(rename_old_kpoints, bool):
            if rename_old_kpoints:
                new_name = find_next_name(cal_loc=self.cal_loc, orig_name="KPOINTS")["next_name"]
                shutil.move(os.path.join(self.cal_loc, "KPOINTS"), os.path.join(self.cal_loc, new_name))
        elif isinstance(rename_old_kpoints, str):
            shutil.move(os.path.join(self.cal_loc, "KPOINTS"), os.path.join(self.cal_loc, rename_old_kpoints))
        else:
            raise Exception("rename_old_kpoints must be either bool or str for func modify_vasp_kpoints_for_2D")
  
        with open(os.path.join(self.cal_loc, "KPOINTS"), "w") as f:
            for line in kpoints:
                f.write(line+"\n")
            
        if rename_old_kpoints == True:
            return new_name
        elif isinstance(rename_old_kpoints, str):
            return rename_old_kpoints
        

