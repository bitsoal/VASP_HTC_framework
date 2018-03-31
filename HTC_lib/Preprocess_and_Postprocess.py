
# coding: utf-8

# # created on Feb 18 2018

# In[1]:


import os, shutil

from pymatgen.io.vasp.sets import MPRelaxSet, MPNonSCFSet, MPStaticSet
from pymatgen import Structure
from pymatgen.symmetry.bandstructure import HighSymmKpath

from Utilities import get_time_str, copy_and_move_files, find_next_name, decorated_os_rename


# In[2]:


def pre_and_post_process(cif_filename, cal_folder, workflow):
    """
    Make pre-processes or post-processes of VASP calculations according to the input workflow
    input arguments:
        - cif_filename (str): the cif file of a structure.
        - cal_folder (str): Under cal_folder, a sub-folder will be created where a set of DFT calculations defined by workflow will be made.
                        Note that the absolute path should be provided.
        - workflow: the return of function parse_calculation_workflow, which define a set of DFT calculations and related pre- and post- processes
    """
    if not os.path.isdir(cal_folder):
        os.mkdir(cal_folder)
       
    
    mater_cal_folder = os.path.join(cal_folder, os.path.split(cif_filename)[-1].split(".")[0])
    if not os.path.isdir(mater_cal_folder):
        os.mkdir(mater_cal_folder)
        with open(os.path.join(mater_cal_folder, "log.txt"), "w") as f:
            f.write("{} INFO: Create this folder {}\n".format(get_time_str(), mater_cal_folder))
        
    current_firework_ind = get_current_firework_ind(mater_cal_folder, workflow)
    prepare_input_files(cif_filename, mater_cal_folder, current_firework_ind, workflow)
    post_process_after_cal(mater_cal_folder, current_firework_ind, workflow)


# In[3]:


def modify_vasp_incar(cal_loc, new_tags={}, comment_tags=[], remove_tags=[], rename_old_incar=True):
    """
    add new tags and comment obsolete tags in incar.
    input arguments:
        - cal_loc (str): the location of INCAR to be modified, <--required
        - new_tags (dict): new tags to be added,
        - comment_tags (list): tags that will be obsolete by commenting them with "#"
        - remove_tags (list): incar tags that will be removed
        - rename_old_incar (bool or str): if rename_old_incar is True, rename the old INCAR as INCAR_0, INCAR_1, INCAR_2, etc.
                                        if rename_old_incar is False, the old INCAR will be overwritten by new INCAR.
                                        if rename_old_incar is a string, rename the old INCAR as the string.
                                        Default: True
    return the modified INCAR dictionary.
    """
    

    new_tags = {key.upper(): value for key, value in new_tags.items()}
    comment_tags = [tag.upper() for tag in comment_tags]
    remove_tags = [tag.upper() for tag in remove_tags]

    Valid_tags, Commented_tags = {}, {}
    Ordered_tags = []
    with open(os.path.join(cal_loc, "INCAR"), "r") as incar:
        for line in incar:
            items = [item.strip() for item in line.strip().split("=")]
            if len(items)>=2:
                if items[0].startswith("#"):
                    tag = items[0].strip("#").upper().strip()
                    if tag in remove_tags:
                        continue
                    Commented_tags[tag] = items[1]
                    Ordered_tags.append(tag)
                else:
                    tag = items[0].upper()
                    if tag in remove_tags:
                        continue
                    Valid_tags[items[0].upper()] = items[1]
                    Ordered_tags.append(tag)

    for new_tag, value in new_tags.items():
        Valid_tags[new_tag] = value
        if new_tag not in Ordered_tags:
            Ordered_tags.append(new_tag)

    for comment_tag in comment_tags:
        if comment_tag in Valid_tags.keys():
            Commented_tags[comment_tag] = Valid_tags[comment_tag]
            del Valid_tags[comment_tag]
            
    if new_tags == {} and comment_tags == [] and remove_tags == []:
        return Valid_tags

    if isinstance(rename_old_incar, bool):
        if rename_old_incar:
            rename_old_incar = find_next_name(cal_loc=cal_loc, orig_name="INCAR")["next_name"]
            shutil.copyfile(os.path.join(cal_loc, "INCAR"), os.path.join(cal_loc, rename_old_incar))
    elif isinstance(rename_old_incar, str):
        shutil.copyfile(os.path.join(cal_loc, "INCAR"), os.path.join(cal_loc, rename_old_incar))
    else:
        raise Exception("input argument rename_old_incar of modify_vasp_incar must be either bool or str.")
        
    
    with open(os.path.join(cal_loc, "INCAR"), "w") as incar:
        for tag in Ordered_tags:
            if tag in Valid_tags.keys():
                incar.write("{} = {}\n".format(tag, Valid_tags[tag]))
            else:
                incar.write("#{} = {}\n".format(tag, Commented_tags[tag]))




# In[4]:


def prepare_input_files(cif_filename, mater_cal_folder, current_firework_ind, workflow):
    """
    prepare input files for dft calculations according to the defined firework in workflow at position current_firework_ind
    """
    firework = workflow[current_firework_ind]
    firework_folder = os.path.join(mater_cal_folder, firework["firework_folder_name"])
    if not os.path.isdir(firework_folder):
        os.mkdir(firework_folder)
        open(os.path.join(firework_folder, "__vis__"), "w").close()
        with open(os.path.join(mater_cal_folder, "log.txt"), "a") as f:
            f.write("\n\n***************************************************************************************\n")
            f.write("***************************************************************************************\n")
            f.write("{} INFO: create sub-folder {} under {}\n".format(get_time_str(), 
                                                                    firework["firework_folder_name"], mater_cal_folder))
        
    if os.path.isfile(os.path.join(firework_folder, "__vis__")):
        #print(firework_folder)
        write_kpoints = False
        
        if workflow[current_firework_ind]["extra_copy"]:
            with open(os.path.join(mater_cal_folder, 'log.txt'), "a") as f:
                f.write("{} INFO: extra copy to dst {}\n".format(get_time_str(), firework_folder))
                for file in workflow[current_firework_ind]["extra_copy"]:
                    filename = os.path.split(file)[1]
                    shutil.copyfile(src=file, dst=os.path.join(firework_folder, filename))
                    f.write("\t\t{}\n".format(file))
            
        if current_firework_ind == 0:
            Write_MPRelax_vasp_input_set(cif_filename=cif_filename, where_to_write=firework_folder, 
                                         sort_structure=workflow[0]["sort_structure"], 
                                         force_gamma=workflow[0]["force_gamma"])
            write_kpoints = True
            with open(os.path.join(mater_cal_folder, "log.txt"), "a") as f:
                f.write("{} INFO: VASP input sets generated by ".format(get_time_str()))
                f.write("pymatgen.io.vasp.sets.MPRelaxSet under folder {}\n".format(firework["firework_folder_name"]))
                if workflow[0]["sort_structure"] == False:
                    f.write("\t\t\tsort_structure is off, so POSCAR generated by pymatgen is overwritten by the copy below\n")
                    f.write("\t\t\tsrc: {}\n".format(cif_filename))
                    f.write("\t\t\tdst: {}\n".format(os.path.join(firework_folder, "POSCAR")))
            #if workflow[0]["2d_system"]:
            #    modify_vasp_kpoints_for_2D(cal_loc=firework_folder, kpoints_type=workflow[0]["kpoints_type"], rename_old_kpoints="KPOINTS.pymatgen")
            #    with open(os.path.join(mater_cal_folder, "log.txt"), "a") as f:
            #        f.write("{} INFO: Because it is a 2D system, KPONITS is modified so that K_z = 0 for all kpoints\n".format(get_time_str()))
            #        f.write("\t\t\tKPOINTS --> KPOINTS.pymatgen\n")
        else:
            copy_files = firework["copy_from_prev_cal"]
            move_files = firework["move_from_prev_cal"]
            contcar_to_poscar = firework["contcar_to_poscar"]
            src_step_name = "step_{}_".format(firework["copy_which_step"])
            for src_firework in workflow:
                if src_step_name in src_firework["firework_folder_name"]:
                    break
            src_dir = os.path.join(mater_cal_folder, src_firework["firework_folder_name"])
            non_existent_files = copy_and_move_files(src_dir=src_dir, dst_dir=firework_folder, copy_files=copy_files, move_files=move_files, contcar_to_poscar=contcar_to_poscar)
            with open(os.path.join(mater_cal_folder, "log.txt"), "a") as f:
                f.write("{} INFO: copy and move files from src folder to dst\n".format(get_time_str()))
                f.write("\t\t\tsrc: {}\n".format(src_dir))
                f.write("\t\t\tdst: {}\n".format(firework_folder))
                if copy_files:
                    f.write("\t\t\tcopy files:")
                    [f.write("{}\t".format(file_)) for file_ in copy_files]
                    f.write("\n")
                if non_existent_files["copy_files"]:
                    f.write("Error: fail to copy files below because they are not existent:")
                    [f.write("{}\t".format(file_)) for file_ in non_existent_files["copy_files"]]
                    
                if move_files:
                    f.write("\t\tmove files:")
                    [f.write("{}\t".format(file_)) for file_ in move_files]
                    f.write("\n")
                if non_existent_files["move_files"]:
                    f.write("Error: \t\tfail to move files below because they are not existent:")
                    [f.write("{}\t".format(file_)) for file_ in non_existent_files["copy_files"]]
                
                if contcar_to_poscar:
                    f.write("\t\trename CONTCAR as POSCAR under dst folder\n")
                    
        new_incar_tags = firework["new_incar_tags"]
        comment_incar_tags = firework["comment_incar_tags"]
        remove_incar_tags = firework["remove_incar_tags"]
        #print(new_incar_tags, comment_incar_tags, remove_incar_tags)
        if new_incar_tags or comment_incar_tags or remove_incar_tags:
            if current_firework_ind == 0:
                modify_vasp_incar(cal_loc=firework_folder, new_tags=new_incar_tags, comment_tags=comment_incar_tags, 
                                  rename_old_incar="INCAR.pymatgen", remove_tags=remove_incar_tags, )
            else:
                modify_vasp_incar(cal_loc=firework_folder, new_tags=new_incar_tags, comment_tags=comment_incar_tags, 
                                  remove_tags=remove_incar_tags)
                
            with open(os.path.join(mater_cal_folder, "log.txt"), "a") as f:
                f.write("{} INFO: modify INCAR:\n".format(get_time_str()))
                if new_incar_tags:
                    f.write("\t\tnew incar tags:\n")
                    [f.write("\t\t\t{}={}\n".format(key_, value_)) for key_, value_ in new_incar_tags.items()]
                if comment_incar_tags:
                    f.write("\t\tcomment incar tags:")
                    [f.write("{}\t".format(tag_)) for tag_ in comment_incar_tags]
                    f.write("\n")
                if remove_incar_tags:
                    f.write("\t\tremove incar tags: ")
                    [f.write("{}\t".format(tag_)) for tag_ in remove_incar_tags]
                    f.write("\n")
                        
        if not os.path.isfile(os.path.join(firework_folder, "KPOINTS")):
            if firework["kpoints_type"] == "Line-mode":
                Write_line_mode_KPOINTS(cal_loc=firework_folder, structure_filename=os.path.join(firework_folder, "POSCAR"), 
                                        intersections=firework["intersections"], twoD_system=workflow[0]["2d_system"])
                with open(os.path.join(mater_cal_folder, "log.txt"), "a") as f:
                    f.write("{} INFO: write KPOINTS in the line mode based on pymatgen.symmetry.bandstructure.HighSymmKpath\n".format(get_time_str()))
            elif firework["kpoints_type"] == "MPNonSCFSet_uniform":
                Write_NONSCF_KPOINTS(structure_filename=os.path.join(firework_folder, "POSCAR"), 
                                     mode="uniform", reciprocal_density=firework["reciprocal_density"])
                write_kpoints = True
            elif firework["kpoints_type"] == 'MPNonSCFSet_line':
                Write_NONSCF_KPOINTS(structure_filename=os.path.join(firework_folder, "POSCAR"), 
                                     mode="line", kpoints_line_density=firework["kpoints_line_density"])
                write_kpoints = True
            elif firework["kpoints_type"] == "MPRelaxSet" and firework["step_no"] != 1:
                Write_MPRelax_KPOINTS(structure_filename=os.path.join(firework_folder, "POSCAR"), force_gamma=workflow[0]["force_gamma"])
                write_kpoints = True
            elif firework["kpoints_type"] == "MPStaticSet":
                Write_MPStatic_KPOINTS(structure_filename=os.path.join(firework_folder, "POSCAR"), force_gamma=workflow[0]["force_gamma"])
                write_kpoints = True
            
            
        if write_kpoints and workflow[0]["2d_system"]:
            new_name = modify_vasp_kpoints_for_2D(cal_loc=firework_folder, kpoints_type=firework["kpoints_type"], 
                                                  rename_old_kpoints="KPOINTS.pymatgen_"+firework["kpoints_type"])
                
        if write_kpoints:
            with open(os.path.join(mater_cal_folder, "log.txt"), "a") as f:
                f.write("{} INFO: use pymatgen.io.vasp.{} ".format(get_time_str(),firework["kpoints_type"]))
                f.write("to write KPOINTS under {}\n".format(firework["firework_folder_name"]))
                if workflow[0]["2d_system"]:
                    f.write("{} INFO: Because it is a 2D system, KPOINTS is modified so that K_z = 0 for all kponits\n".format(get_time_str()))
                    f.write("\t\t\tKPOINTS --> {}\n".format(new_name))
                
                    
        if abs(firework["denser_kpoints"]-1) > 1.0e-4:
            new_name = modify_vasp_kpoints_for_2D(cal_loc=firework_folder, kpoints_type="automatic", rename_old_kpoints="KPOINTS.sparse", 
                                                  denser_kpoints=firework["denser_kpoints"])
            with open(os.path.join(mater_cal_folder, "log.txt"), "a") as f:
                f.write("{} INFO: for {}, tag denser_kpoints has been set to {}\n".format(get_time_str(), 
                                                                                          firework["firework_folder_name"], 
                                                                                          firework["denser_kpoints"]))
                f.write("\t\t\tChange KPOINTS according to denser_kpoints\n")
                f.write("\t\t\told KPOINTS --> {}\n".format(new_name))
                
            
        if workflow[current_firework_ind]["final_extra_copy"]:
            with open(os.path.join(mater_cal_folder, 'log.txt'), "a") as f:
                f.write("{} INFO: final extra copy to dst {}\n".format(get_time_str(), firework_folder))
                for file in workflow[current_firework_ind]["final_extra_copy"]:
                    filename = os.path.split(file)[1]
                    shutil.copyfile(src=file, dst=os.path.join(firework_folder, filename))
                    f.write("\t\t{}\n".format(file))
        
        decorated_os_rename(loc=firework_folder, old_filename="__vis__", new_filename="__ready__")
        #os.rename(os.path.join(firework_folder, "__vis__"), os.path.join(firework_folder, "__ready__"))
        with open(os.path.join(mater_cal_folder, "log.txt"), "a") as f:
            f.write("{} INFO: All VASP input files are ready at {}\n".format(get_time_str(), firework["firework_folder_name"]))
            f.write("\t\t\t__vis__ --> __ready__\n")


# In[5]:


def post_process_after_cal(mater_cal_folder, firework_ind, workflow):
    """
    Carry out the post-process defined in firework of workflow at index firework_ind.
    """
    firework = workflow[firework_ind]
    firework_folder = os.path.join(mater_cal_folder, firework["firework_folder_name"])
    if os.path.isfile(os.path.join(firework_folder, "__removed__")):
        return True
    
    if os.path.isfile(os.path.join(firework_folder, "__remove__")):
        remove_files =  firework["remove_after_cal"]
        with open(os.path.join(mater_cal_folder, "log.txt"), "a") as f:
            f.write("{} INFO: remove files from {}:\n\t\t".format(get_time_str(), firework_folder))
            [f.write("{}\t").format(file_) for file_ in remove_files]
            f.write("\n")
        for file in remove_files:
            if os.path.isfile(os.path.join(firework_folder, file)):
                os.remove(os.path.join(firework_folder, file))
        decorated_os_rename(loc=firework_folder, old_filename="__remove__", new_filename="__removed__")
        #os.rename(os.path.join(firework_folder, "__remove__"), os.path.join(firework_folder, "__removed__"))
    


# In[6]:


def get_current_firework_ind(mater_cal_folder, workflow):
    """
    find which firework we are and return the firework index starting from 0
    input arguments:
        -mater_cal_folder: the path under which a sequence of DFT calculations will be done.
        -workflow: the return of function parse_calculation_workflow, which define a set of DFT calculations and related pre- and post- processes
    """
    firework_folder_name_list = [firework["firework_folder_name"] for firework in workflow]
    existent_firework_folder_list = os.listdir(mater_cal_folder)
    for ind, firework_folder_name in enumerate(firework_folder_name_list):
        if firework_folder_name in existent_firework_folder_list:
            continue
        else:
            break
    if ind == 0:
        current_firework_ind = 0
    elif os.path.isfile(os.path.join(mater_cal_folder, firework_folder_name_list[ind-1], "__done__")):
        current_firework_ind = ind
    else:
        current_firework_ind = ind - 1
        
    return current_firework_ind


# In[7]:


def Write_MPRelax_vasp_input_set(cif_filename, where_to_write=".", sort_structure=True, **kwargs):
    """
    generate and write down the Vasp Input Set (VIS) for an input structure by pymatgen.io.vasp.sets.MPRelaxSet.
    input arguments:
        - cif_filename (str): path of the cif file.
        - where_to_write (str): the path to write down INCAR, POTCAR, KPOINTS, POSCAR.
        - sort_structure (bool): Sites are sorted by the electronegativity of the species if True,
                                If False, keep the original site order.
                                Default: True
                                Note that if False, the input structure specified by cif_filename should be in the format of 
                                    POSCAR, not cif.
    """
    struct = Structure.from_file(cif_filename).get_sorted_structure()
    vis = MPRelaxSet(struct, **kwargs)
    vis.write_input(where_to_write)
    
    if sort_structure == False:
        shutil.copyfile(cif_filename, os.path.join(where_to_write, "POSCAR"))
    #vis.incar.write_file(os.path.join(where_to_write, "INCAR"))
    #vis.poscar.write_file(os.path.join(where_to_write, "POSCAR"))
    #vis.kpoints.write_file(os.path.join(where_to_write, "KPOINTS"))


# In[8]:


def Write_MPRelax_KPOINTS(structure_filename="./POSCAR", **kwargs):
    """
    generate KPOINTS for scf cal by pymatgen.io.vasp.set.MPRelaxSet.
    input argument:
        -structure_filename: a file that can be understood by pymatgen.Structure.from_file.
    """
    struct = Structure.from_file(cif_filename)
    vis = MPRelaxSet(structure=struct, **kwargs)
    folder = os.path.split(structure_filename)[0]
    vis.kpoints.write_file(os.path.join(folder, "KPOINTS"))


# In[9]:


def Write_MPStatic_KPOINTS(structure_filename="./POSCAR", **kwargs):
    """
    generate KPOINTS for scf cal by pymatgen.io.vasp.set.MPStaticSet.
    input argument:
        -structure_filename: a file that can be understood by pymatgen.Structure.from_file.
    """
    struct = Structure.from_file(structure_filename)
    vis = MPStaticSet(structure=struct, **kwargs)
    folder = os.path.split(structure_filename)[0]
    vis.kpoints.write_file(os.path.join(folder, "KPOINTS"))


# Write_MPStatic_KPOINTS(structure_filename="7_H-MoTe2-CONTCAR_28_T-GeS2-CONTCAR_hetero.cif", force_gamma=True)

# Write_MPRelax_vasp_input_set(cif_filename="7_H-MoTe2-CONTCAR_28_T-GeS2-CONTCAR_hetero.cif", where_to_write=".", force_gamma=True)

# In[10]:


def Write_NONSCF_KPOINTS(structure_filename="./POSCAR", mode='line', nedos=601, 
                         reciprocal_density=100, sym_prec=0.1, kpoints_line_density=20, optics=False, **kwargs):
    """
    generate KPOINTS for DOS (mode="uniform") or band struture (mode="line") by pymatgen.io.vasp.set.MPNonSCFSet
    input arguments:
        -structure_filename (str): a file that can be understood by pymatgen.Structure.from_file.
        -mode (str): 'line' or 'uniform'
        -nedos (int): default 601. Only valid at mode='uniform'
        -reciprocal_density (int): default 100. Only valid at mode='uniform'
        -sym_prec (float): default 0.1
        -kpoints_line_density (int): default 20. Only valid at mode='line'
        -optics (bool)
    """
    #print(os.getcwd())
    #print(os.listdir())
    #print(structure_filename)
    struct = Structure.from_file(structure_filename)
    vis = MPNonSCFSet(structure=struct, mode=mode, nedos=nedos, reciprocal_density=reciprocal_density, sym_prec=sym_prec, 
                      kpoints_line_density=kpoints_line_density, optics=optics)
    folder = os.path.split(structure_filename)[0]
    vis.kpoints.write_file(os.path.join(folder, "KPOINTS"))


# In[1]:


def Write_line_mode_KPOINTS(cal_loc, structure_filename, intersections, twoD_system=False):
    """
    Write a kpath along the high symmetry kpoints in the line mode into KPOINTS under dir cal_loc for the band structure calculation.
    input arguments:
        - cal_loc (str): the calculation directory
        - structure_filename (str): Must be in a format that can be read by pytmatgen.Structure.from_file
        - intersections (int): For every segment, there are intersections equally spaced kpionts, including the starting and ending high symmetry k-points
        - twoD_system (bool): If True, the kpath only includes the kpoints whose z component are zero. Default: False
        see https://cms.mpi.univie.ac.at/vasp/vasp/Strings_k_points_bandstructure_calculations.html
    Note that the reciprocal coordinates are adopted.
    Note that if twoD_system is True, the vacuum layer is assumed to be along the Z direction and the lattice vector c must be normal to the surface.
    """
    structure = Structure.from_file(structure_filename)
    kpath = HighSymmKpath(structure=structure).get_kpoints(line_density=1, coords_are_cartesian=False)
    kpoints = []
    for k_, k_label in zip(*kpath):
        if k_label:
            kpoints.append(list(k_) + [k_label])
    
    starting_kpoints = kpoints[::2]
    ending_kpoints = kpoints[1::2]
    
    with open(os.path.join(cal_loc, "KPOINTS"), "w") as f:
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


# In[11]:


def modify_vasp_kpoints_for_2D(cal_loc, kpoints_type, denser_kpoints=1, rename_old_kpoints=True, tolerance=1.0e-5):
    """
    modify KPOINTS at cal_loc.
    input arguments:
        - cal_loc (str): the location of the calculation.
        - mode (str): 'MPRelaxSet', 'MPStaticSet', 'MPNonSCFSet_line', 'MPNonSCFSet_uniform', 'automatic'
                    - 'MPRelaxSet': pymatgen.io.vasp.sets.MPRelaxSet generates KPOINTS.
                    - 'MPStaticSet': pymatgen.io.vasp.sets.MPStaticSet generates KPOINTS.
                    - 'MPNonSCFSet_uniform': pymatgen.io.vasp.sets.MPNonSCFSet generates KPOINTS in the uniform mode for DOS
                    - 'MPNonSCFSet_line': pymatgen.io.vasp.sets.MPNonSCFSet generates KPOINTS in the line mode for band str
                    - 'automatic': This option indicates that KPOINTS is automatically generated 
                                    based on (gamma-centered) Monkhorst-Pack Scheme <--> 'MPRelaxSet', 'MPStaticSet'
                    - 'Line-mode': Since function Write_line_mode_KPOINTS can write KPOINTS for either 3D or 2D materials, file
                                    KPOINTS remains unchanged.
        - denser_kpoints (float): this tag is inactive at kpoints_type='MPNonSCFSet_uniform' or 'MPNonSCFSet_line'. Default: 1
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
    if kpoints_type.strip() not in ["automatic", 'MPRelaxSet', 'MPStaticSet', 'MPNonSCFSet_line', 'MPNonSCFSet_uniform', "Line-mode"]:
        print("Error: for func modify_vasp_kpoints_for_2D, the input argument kpoints_tag must be on the those below:")
        print("'MPRelaxSet', 'MPStaticSet', 'MPNonSCFSet_line', 'MPNonSCFSet_uniform', 'automatic'")
        raise Exception("See above for the error information")
    if kpoints_type == "Line-mode":
        return True
    
    with open(os.path.join(cal_loc, "KPOINTS"), "r") as f:
        kpoints = [line.strip() for line in f if line.strip()]
        
    if kpoints_type in ["automatic", 'MPRelaxSet', 'MPStaticSet']:
        assert "gam" in kpoints[2].lower() or "mon" in kpoints[2].lower(), "Error: fail to modify KPOINTS generated by pymatgen at {}".format(cal_loc)
        nk_list = [int(int(k)*denser_kpoints) for k in kpoints[3].split()]
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
            new_name = find_next_name(cal_loc=cal_loc, orig_name="KPOINTS")["next_name"]
            shutil.move(os.path.join(cal_loc, "KPOINTS"), os.path.join(cal_loc, new_name))
    elif isinstance(rename_old_kpoints, str):
        shutil.move(os.path.join(cal_loc, "KPOINTS"), os.path.join(cal_loc, rename_old_kpoints))
    else:
        raise Exception("rename_old_kpoints must be either bool or str for func modify_vasp_kpoints_for_2D")
  
    with open(os.path.join(cal_loc, "KPOINTS"), "w") as f:
        for line in kpoints:
            f.write(line+"\n")
            
    if rename_old_kpoints == True:
        return new_name
    elif isinstance(rename_old_kpoints, str):
        return rename_old_kpoints


# if __name__ == "__main__":
#     modify_vasp_kpoints_for_2D(cal_loc=".", mode="scf")
#     modify_vasp_kpoints_for_2D(cal_loc=".", mode="line")
#     modify_vasp_kpoints_for_2D(cal_loc=".", mode="uniform")
