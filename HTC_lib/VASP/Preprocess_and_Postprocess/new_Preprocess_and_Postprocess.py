#!/usr/bin/env python
# coding: utf-8

# In[2]:


import os, pprint, sys, shutil

##############################################################################################################
##DO NOT change this part.
##../setup.py will update this variable
HTC_package_path = "C:/Users/tyang/Documents/Jupyter_workspace/HTC/python_3"
assert os.path.isdir(HTC_package_path), "Cannot find this VASP_HTC package under {}".format(HTC_package_path)
if HTC_package_path not in sys.path:
    sys.path.append(HTC_package_path)
##############################################################################################################

from pymatgen import Structure

from HTC_lib.VASP.Miscellaneous.Utilities import get_time_str, copy_and_move_files, find_next_name, decorated_os_rename#, get_current_firework_from_cal_loc
from HTC_lib.VASP.Miscellaneous.Execute_bash_shell_cmd import Execute_shell_cmd
from HTC_lib.VASP.Miscellaneous.Cal_status_dictionary_operation import Cal_status_dict_operation

from HTC_lib.VASP.Job_Management.Check_and_update_calculation_status import check_calculations_status

from HTC_lib.VASP.INCAR.Write_VASP_INCAR import Write_Vasp_INCAR
from HTC_lib.VASP.KPOINTS.Write_VASP_KPOINTS import Write_Vasp_KPOINTS
from HTC_lib.VASP.POTCAR.Write_VASP_POTCAR import Write_Vasp_POTCAR
from HTC_lib.VASP.POSCAR.Write_VASP_POSCAR import Write_Vasp_POSCAR


# def preview_HTC_vasp_inputs(cif_filename, cif_folder, workflow):
#     """
#     Preview vasp inputs of each firework defined in workflow
#     input arguments:
#         - cif_filename (str): the cif file of a structure.
#         - cif_folder (str): the absolute path of the folder where cif_filename is stored.
#         - cal_folder (str): Under cal_folder, a sub-folder will be created where a set of DFT calculations defined by workflow will be made.
#                         Note that the absolute path should be provided.
#         - workflow: the return of function parse_calculation_workflow, which define a set of DFT calculations and related pre- and post- processes
#     """
#     preview_HTC_dir = os.path.join(os.getcwd(), "preview_HTC")
#     if os.path.isdir(preview_HTC_dir):
#         shutil.rmtree(preview_HTC_dir)
#     os.mkdir(preview_HTC_dir)
#     for current_firework in workflow:
#         try:
#             prepare_input_files(cif_filename=cif_filename, cif_folder=cif_folder, mater_cal_folder=preview_HTC_dir, 
#                                 current_firework=current_firework, workflow=workflow)
#         except:
#             pass
#         finally:
#             append_info_to_a_file(current_firework["firework_folder_name"], os.path.join(preview_HTC_dir, current_firework["firework_folder_name"]))
#     
#             
#     
# 
# def append_info_to_a_file(firework_name, cal_loc, file_list=["WAVECAR", "CHGCAR", "CONTCAR", "POSCAR", "KPOINTS", "INCAR"]):
#     shutil.copyfile(os.path.join(cal_loc, "POSCAR"), os.path.join(cal_loc, "CONTCAR"))
#     for filename in file_list:
#         with open(os.path.join(cal_loc, filename), "a") as f:
#             f.write("#{}: {} of {}\n".format(get_time_str(), filename, firework_name))
#     
# 

# In[1]:


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
    
    mater_cal_folder = os.path.join(cal_folder, cif_filename.split(".")[0])
    if not os.path.isdir(mater_cal_folder):
        os.mkdir(mater_cal_folder)
        #with open(os.path.join(mater_cal_folder, "log.txt"), "w") as f:
        #    f.write("{} INFO: Create this folder {}\n".format(get_time_str(), mater_cal_folder))
        
    if os.path.isfile(os.path.join(mater_cal_folder, "__complete__")):
        cal_status = check_calculations_status(cal_folder=cal_folder, workflow=workflow, cal_loc_list=[])
        cal_status_diff = Cal_status_dict_operation.diff_status_dict(cal_status, cal_status)
        return 0, cal_status_diff
        
    current_firework_list = get_current_firework(mater_cal_folder=mater_cal_folder, workflow=workflow)
    
    cal_folder_list = [os.path.join(mater_cal_folder, current_firework["firework_folder_name"]) for current_firework in current_firework_list]
    old_cal_status = check_calculations_status(cal_folder=cal_folder, workflow=workflow, cal_loc_list=cal_folder_list)
    
    for current_firework in current_firework_list:
        prepare_input_files(cif_filename=cif_filename, cif_folder=cif_folder, mater_cal_folder=mater_cal_folder, 
                            current_firework=current_firework, workflow=workflow)
        post_process(mater_cal_folder=mater_cal_folder, current_firework=current_firework, workflow=workflow)
    
    new_cal_status = check_calculations_status(cal_folder=cal_folder, workflow=workflow, cal_loc_list=cal_folder_list)
    no_of_new_ready_jobs = len(new_cal_status["prior_ready_folder_list"]) + len(new_cal_status["ready_folder_list"])
    no_of_new_ready_jobs += len(new_cal_status["sub_dir_cal_folder_list"])
    no_of_new_ready_jobs -= len(old_cal_status["prior_ready_folder_list"])
    no_of_new_ready_jobs -= len(old_cal_status["ready_folder_list"])
    no_of_new_ready_jobs -= len(old_cal_status["sub_dir_cal_folder_list"])
    cal_status_diff = Cal_status_dict_operation.diff_status_dict(old_cal_status_dict=old_cal_status, new_cal_status_dict=new_cal_status)
    return no_of_new_ready_jobs, cal_status_diff


# In[1]:


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
    
    current_cal_loc = os.path.join(mater_cal_folder, current_firework["firework_folder_name"])
    log_txt = os.path.join(current_cal_loc, "log.txt")
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
                f.write("{} INFO: copy defined by tag extra_copy to {}\n".format(get_time_str(), current_firework["firework_folder_name"]))
            for file in current_firework["extra_copy"]:
                filename = os.path.split(file)[1]
                shutil.copyfile(src=file, dst=os.path.join(current_cal_loc, filename))
                with open(log_txt, "a") as f:
                    f.write("\t\t\t{}\n".format(file))
                    
        if current_firework["step_no"] == 1:
            shutil.copy(src=os.path.join(cif_folder, cif_filename), dst=os.path.join(mater_cal_folder, cif_filename))
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
        
        
        input_args_list = {"cal_loc": current_cal_loc, "user_defined_cmd_list": current_firework["user_defined_cmd"],
                           "where_to_execute": current_cal_loc, "defined_by_which_htc_tag": "user_defined_cmd"}
        if not Execute_shell_cmd(**input_args_list):
            return False
        
        assert os.path.isfile(os.path.join(current_cal_loc, "POSCAR")), "Error: POSCAR is missing!"
        
        Write_Vasp_POTCAR(cal_loc=current_cal_loc, structure_filename="POSCAR", workflow=workflow)
        Write_Vasp_INCAR(cal_loc=current_cal_loc, structure_filename="POSCAR", workflow=workflow)
        Write_Vasp_KPOINTS(cal_loc=current_cal_loc, structure_filename="POSCAR", workflow=workflow)
            
        
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

        input_args_list = {"cal_loc": current_cal_loc, "user_defined_cmd_list": current_firework["final_user_defined_cmd"],
                           "where_to_execute": current_cal_loc, "defined_by_which_htc_tag": "final_user_defined_cmd"}
        if not Execute_shell_cmd(**input_args_list):
            return False
        
        if current_firework["sub_dir_cal"]:
            decorated_os_rename(loc=current_cal_loc, old_filename="__vis__", new_filename="__sub_dir_cal__")
            with open(os.path.join(current_cal_loc, "log.txt"), "a") as f:
                f.write("{} INFO: All VASP input files needed for sub-directory calculations are ready at {}\n".format(get_time_str(), current_firework["firework_folder_name"]))
                f.write("\t\t\t__vis__ --> __sub_dir_cal__\n")
            return True
        
        decorated_os_rename(loc=current_cal_loc, old_filename="__vis__", new_filename="__ready__")
        with open(os.path.join(current_cal_loc, "log.txt"), "a") as f:
            f.write("{} INFO: All VASP input files are ready at {}\n".format(get_time_str(), current_firework["firework_folder_name"]))
            f.write("\t\t\t__vis__ --> __ready__\n")


# In[4]:


def post_process(mater_cal_folder, current_firework, workflow):
    """
    Carry out the post-process defined in firework of workflow at index firework_ind.
    """
    current_cal_loc = os.path.join(mater_cal_folder, current_firework["firework_folder_name"])
    log_txt = os.path.join(current_cal_loc, "log.txt")
    
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
        
        
        input_args_list = {"cal_loc": current_cal_loc, "user_defined_cmd_list": current_firework["user_defined_postprocess_cmd"],
                           "where_to_execute": current_cal_loc, "defined_by_which_htc_tag": "user_defined_postprocess_cmd"}
        if not Execute_shell_cmd(**input_args_list):
            return False
    
        decorated_os_rename(loc=current_cal_loc, old_filename="__post_process__", new_filename="__post_process_done__")


# In[6]:


def get_current_firework(mater_cal_folder, workflow, current_firework_folder_name="-1"):
    """
    find and return the current firework
    input arguments:
        -mater_cal_folder: the path under which a sequence of DFT calculations will be done.
        -workflow: the return of function parse_calculation_workflow, which define a set of DFT calculations and related pre- and post- processes
        -current_firework_folder_name: default value: "-1"
    """
    firework_hierarchy_dict = workflow[0]["firework_hierarchy_dict"]
    next_firework_list = []
    for next_firework_folder_name in firework_hierarchy_dict.get(current_firework_folder_name, []):
        if True in [os.path.isfile(os.path.join(mater_cal_folder, next_firework_folder_name, target_file)) 
                    for target_file in ["__done__", "__skipped__", "__done_cleaned_analyzed__", "__done_failed_to_clean_analyze__"]]:
        #os.path.isfile(os.path.join(mater_cal_folder, next_firework_folder_name, "__done__")) or \
        #os.path.isfile(os.path.join(mater_cal_folder, next_firework_folder_name, "__skipped__")) or \
        #os.path.isfile(os.path.join(mater_cal_folder, next_firework_folder_name, "__done_cleaned_analyzed__")) or \
        #os.path.isfile(os.path.join(mater_cal_folder, next_firework_folder_name, "__done_failed_to_clean_analyze__")):
            next_firework_list.extend(get_current_firework(mater_cal_folder, workflow, current_firework_folder_name=next_firework_folder_name))
        else:
            next_firework_step_no = int(next_firework_folder_name.split("_")[1])
            all_dependent_fireworks_are_complete = True
            for dependent_firework_folder_name in workflow[next_firework_step_no-1]["additional_cal_dependence"]:
                if True not in [os.path.isfile(os.path.join(mater_cal_folder, dependent_firework_folder_name, target_file)) 
                                for target_file in ["__done__", "__skipped__", "__done_cleaned_analyzed__", "__done_failed_to_clean_analyze__"]]:
                #if not os.path.isfile(os.path.join(mater_cal_folder, dependent_firework_folder_name, "__done__")) and not \
                #os.path.isfile(os.path.join(mater_cal_folder, dependent_firework_folder_name, "__skipped__")):
                    all_dependent_fireworks_are_complete = False
                    break
            if all_dependent_fireworks_are_complete:
                next_firework_list.append(workflow[next_firework_step_no-1])
    return next_firework_list        
            

