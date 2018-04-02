
# coding: utf-8

# # created on March 31 2018

# In[1]:


import os, shutil

from pymatgen import Structure

from Utilities import get_time_str, copy_and_move_files, find_next_name, decorated_os_rename

from Write_VASP_INCAR import Write_Vasp_INCAR
from Write_VASP_KPOINTS import Write_Vasp_KPOINTS
from Write_VASP_POTCAR import Write_Vasp_POTCAR
from Write_VASP_POSCAR import Write_Vasp_POSCAR


# In[2]:


def pre_and_post_process(cif_filename, cif_folder, cal_folder, workflow):
    """
    Make pre-processes or post-processes of VASP calculations according to the input workflow
    input arguments:
        - cif_filename (str): the cif file of a structure.
        - cif_folder (str): the absolute path of the folder where cif_filename is stored.
        - cal_folder (str): Under cal_folder, a sub-folder will be created where a set of DFT calculations defined by workflow will be made.
                        Note that the absolute path should be provided.
        - workflow: the return of function parse_calculation_workflow, which define a set of DFT calculations and related pre- and post- processes
    """
    if not os.path.isdir(cal_folder):
        os.mkdir(cal_folder)
       
    
    mater_cal_folder = os.path.join(cal_folder, cif_filename.split(".")[0])
    if not os.path.isdir(mater_cal_folder):
        os.mkdir(mater_cal_folder)
        with open(os.path.join(mater_cal_folder, "log.txt"), "w") as f:
            f.write("{} INFO: Create this folder {}\n".format(get_time_str(), mater_cal_folder))
        
    current_firework = get_current_firework(mater_cal_folder=mater_cal_folder, workflow=workflow)
    prepare_input_files(cif_filename=cif_filename, cif_folder=cif_folder, mater_cal_folder=mater_cal_folder, 
                        current_firework=current_firework, workflow=workflow)
    post_process(mater_cal_folder=mater_cal_folder, current_firework=current_firework, workflow=workflow)


# In[3]:


def prepare_input_files(cif_filename, cif_folder, mater_cal_folder, current_firework, workflow):
    """
    prepare input files for dft calculations according to the defined firework in workflow at position current_firework_ind
    Input arguments:
        -cif_filename (str): the file from which the to-be-calculated structure is read using pymatgen.Structure.from_file
                        Of course, it might not be a cif file. Other formats supported by pymatgen.Structure.from_file are available
        -cif_folder (str): the absolute path of the folder where structure named cif_filename can be accessed.
        -mater_cal_folder (str): the absolute path of the folder where a series of sub-folders will be created to make a series of
                                calculations defined in workflow for the structure stored in file cif_filename
        -current_firework, workflow
            
    """
    log_txt = os.path.join(mater_cal_folder, "log.txt")
    current_cal_loc = os.path.join(mater_cal_folder, current_firework["firework_folder_name"])
    if not os.path.isdir(current_cal_loc):
        os.mkdir(current_cal_loc)
        open(os.path.join(current_cal_loc, "__vis__"), "w").close()
        with open(log_txt, "a") as f:
            f.write("\n\n***************************************************************************************\n")
            f.write("***************************************************************************************\n")
            f.write("{} INFO: under {}\n".format(get_time_str(), mater_cal_folder))
            f.write("\t\tCreate sub-folder {}\n".format(current_firework["firework_folder_name"]))
            f.write("\t\tcreate __vis__ under {}\n".format(current_firework["firework_folder_name"]))
    

        
    if os.path.isfile(os.path.join(current_cal_loc, "__vis__")):
        
        if current_firework["extra_copy"]:
            with open(log_txt, "a") as f:
                f.write("{} INFO: copy defined by tag extra_tag to {}\n".format(get_time_str(), current_firework["firework_folder_name"]))
            for file in current_firework["extra_copy"]:
                filename = os.path.split(file)[1]
                shutil.copyfile(src=file, dst=os.path.join(current_cal_loc, filename))
                with open(log_txt, "a") as f:
                    f.write("\t\t\t{}\n".format(file))
                    
        if current_firework["step_no"] == 1:
            Write_Vasp_POSCAR(cal_loc=current_cal_loc, structure_filename=cif_filename, structure_file_folder=cif_folder, 
                              workflow=workflow)
        else:
            copy_files = current_firework["copy_from_prev_cal"]
            move_files = current_firework["move_from_prev_cal"]
            contcar_to_poscar = current_firework["contcar_to_poscar"]
            prev_firework = workflow[current_firework["copy_which_step"]-1]
            prev_cal_loc = os.path.join(mater_cal_folder, prev_firework["firework_folder_name"])
            non_existent_files = copy_and_move_files(src_dir=prev_cal_loc, dst_dir=current_cal_loc, copy_files=copy_files,
                                                     move_files=move_files, contcar_to_poscar=contcar_to_poscar)
            file_dict = {"copy files: ": copy_files, "move files: ": move_files,
                         "Fail to move files below because they are not existent: ": non_existent_files}
            with open(log_txt, "a") as f:
                f.write("{} INFO: copy and move files from src to dst\n".format(get_time_str()))
                f.write("\t\t\tsrc: {}\n".format(prev_firework["firework_folder_name"]))
                f.write("\t\t\tdst: {}\n".format(current_firework["firework_folder_name"]))
                for file_type, file_list in file_dict.items():
                    if file_list:
                        f.write("\t\t\t{}".format(file_type))
                        [f.write("{}\t".format(file_)) for file_ in file_list]
                        f.write("\n")
                if contcar_to_poscar:
                    f.write("\t\t\tCONTCAR --> POSCAR under dst folder\n")
        assert os.path.isfile(os.path.join(current_cal_loc, "POSCAR")), "Error: POSCAR is missing!"
        
        Write_Vasp_INCAR(cal_loc=current_cal_loc, structure_filename="POSCAR", workflow=workflow)
        Write_Vasp_KPOINTS(cal_loc=current_cal_loc, structure_filename="POSCAR", workflow=workflow)
        Write_Vasp_POTCAR(cal_loc=current_cal_loc, structure_filename="POSCAR", workflow=workflow)
            
        
        if current_firework["final_extra_copy"]:
            with open(log_txt, "a") as f:
                f.write("{} INFO: tag final_extra_copy is not empty for {}\n".format(get_time_str(), 
                                                                                     current_firework["firework_folder_name"]))
                f.write("\t\tSo copy files listed below to {}:\n".format(current_firework["firework_folder_name"]))
            for file in current_firework["final_extra_copy"]:
                filename = os.path.split(file)[1]
                shutil.copyfile(src=file, dst=os.path.join(current_cal_loc, filename))
                with open(log_txt, "a") as f:
                    f.write("\t\t\t{}\n".format(file))
            
        
        decorated_os_rename(loc=current_cal_loc, old_filename="__vis__", new_filename="__ready__")
        with open(os.path.join(mater_cal_folder, "log.txt"), "a") as f:
            f.write("{} INFO: All VASP input files are ready at {}\n".format(get_time_str(), current_firework["firework_folder_name"]))
            f.write("\t\t\t__vis__ --> __ready__\n")


# In[4]:


def post_process(mater_cal_folder, current_firework, workflow):
    """
    Carry out the post-process defined in firework of workflow at index firework_ind.
    """
    current_cal_loc = os.path.join(mater_cal_folder, current_firework["firework_folder_name"])
    log_txt = os.path.join(mater_cal_folder, "log.txt")
    
    if os.path.isfile(os.path.join(current_cal_loc, "__post_process_done__")):
        return True
    
    if os.path.isfile(os.path.join(current_cal_loc, "__post_process__")):
        remove_files =  current_firework["remove_after_cal"]
        with open(log.txt, "a") as f:
            f.write("{} INFO: remove files from {}:\n\t\t\t".format(get_time_str(), current_firework["firework_folder_name"]))
            [f.write("{}\t").format(file_) for file_ in remove_files]
            f.write("\n")
        for file in remove_files:
            if os.path.isfile(os.path.join(current_cal_loc, file)):
                os.remove(os.path.join(current_cal_loc, file))
        decorated_os_rename(loc=current_cal_loc, old_filename="__post_process__", new_filename="__post_process_done__")
    


# In[5]:


def get_current_firework(mater_cal_folder, workflow):
    """
    find and return the current firework
    input arguments:
        -mater_cal_folder: the path under which a sequence of DFT calculations will be done.
        -workflow: the return of function parse_calculation_workflow, which define a set of DFT calculations and related pre- and post- processes
    """
    firework_folder_name_list = [firework["firework_folder_name"] for firework in workflow]
    existent_firework_folder_list = []
    for folder_name in os.listdir(mater_cal_folder):
        if os.path.isdir(os.path.join(mater_cal_folder, folder_name)):
            existent_firework_folder_list.append(folder_name)
            
    for ind, firework_folder_name in enumerate(firework_folder_name_list):
        if firework_folder_name in existent_firework_folder_list:
            if os.path.isfile(os.path.join(mater_cal_folder, firework_folder_name, "__done__")):
                continue
        return workflow[ind]
    
    return workflow[-1]

