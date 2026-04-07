#!/usr/bin/env python
# coding: utf-8

# last edited on 9 Aug 2025  
# note: This script derives from and aims to replace new_Preprocess_and_Postprocess.py. Since postprocessing finished jobs are conducted by Check_and_update_calculation_status.py, it is more appropriate to name the present script "Preprocess" to truly relfect its role in (a) working out which calculation steps for a given material that are ready to be prepared and run; and (b) identifying the materials of which all calculations steps have been finished and so that should be tagged with signal file __complete__

# In[2]:


import os, pprint, sys, shutil, json

##############################################################################################################
##DO NOT change this part.
##../setup.py will update this variable
HTC_package_path = "C:/Users/tyang/Documents/Jupyter_workspace/HTC/python_3"
assert os.path.isdir(HTC_package_path), "Cannot find this VASP_HTC package under {}".format(HTC_package_path)
if HTC_package_path not in sys.path:
    sys.path.append(HTC_package_path)
##############################################################################################################

from pymatgen.core import Structure

from HTC_lib.VASP.Miscellaneous.Utilities import get_time_str, copy_and_move_files, decorated_os_rename
from HTC_lib.VASP.Miscellaneous.Execute_bash_shell_cmd import Execute_shell_cmd
from HTC_lib.VASP.Miscellaneous.Cal_status_dictionary_operation import Cal_status_dict_operation

from HTC_lib.VASP.Job_Management.Check_and_update_calculation_status import check_calculations_status

from HTC_lib.VASP.INCAR.modify_vasp_incar import modify_vasp_incar

from HTC_lib.VASP.INCAR.Write_VASP_INCAR import Write_Vasp_INCAR
from HTC_lib.VASP.KPOINTS.Write_VASP_KPOINTS import Write_Vasp_KPOINTS
from HTC_lib.VASP.POTCAR.Write_VASP_POTCAR import Write_Vasp_POTCAR
from HTC_lib.VASP.POSCAR.Write_VASP_POSCAR import Write_Vasp_POSCAR


# In[1]:


def preprocess(cif_filename, cif_folder, cal_folder, workflow):
    """
    Pre-process VASP calculations according to the input workflow
    input arguments:
        - cif_filename (str): the cif file of a structure.
        - cif_folder (str): the absolute path of the folder where cif_filename is stored.
        - cal_folder (str): Under cal_folder, a sub-folder will be created where a set of DFT calculations defined by workflow will be made.
                        Note that the absolute path should be provided.
        - workflow: the return of function parse_calculation_workflow, which define a set of DFT calculations and related pre-processes
    """       
    
    mater_folder_name = cif_filename.split(".")[0]
    mater_cal_folder = os.path.join(cal_folder, mater_folder_name)
    if not os.path.isdir(mater_cal_folder):
        os.mkdir(mater_cal_folder)
        
    if os.path.isfile(os.path.join(mater_cal_folder, "__complete__")):
        cal_status = check_calculations_status(cal_folder=cal_folder, workflow=workflow, cal_loc_list=[])
        cal_status_diff = Cal_status_dict_operation.diff_status_dict(cal_status, cal_status)
        return 0, cal_status_diff
    
    output = get_current_fireworks_and_present_states(mater_cal_folder=os.path.join(cal_folder, mater_folder_name), workflow=workflow)
    if output["all_completed"]:
        old_cal_status = check_calculations_status(cal_folder=cal_folder, workflow=workflow, 
                                                   mat_folder_name_list=[mater_folder_name], ignore_complete=True)
        open(os.path.join(mater_cal_folder, "__complete__"), "w").close()
        new_cal_status = {"complete_folder_list": [mater_cal_folder]}
        return 0, Cal_status_dict_operation.diff_status_dict(old_cal_status, new_cal_status)
        
    current_firework_list = output["current_fireworks"]
    cal_folder_list = [os.path.join(mater_cal_folder, current_firework["firework_folder_name"]) for current_firework in current_firework_list]
    old_cal_status = check_calculations_status(cal_folder=cal_folder, workflow=workflow, cal_loc_list=cal_folder_list)
    
    for current_firework in current_firework_list:
        prepare_input_files(cif_filename=cif_filename, cif_folder=cif_folder, mater_cal_folder=mater_cal_folder, 
                            current_firework=current_firework, workflow=workflow)
        #HTC tag user_defined_postprocess_cmd has been obsolete. So post_process will not work anymore. It has been replaced by
        #HTC tag cmd_to_process_finished_jobs, which process finished jobs in func clean_analyze_or_update_successfully_finished_jobs
        #in HTC_lib/VASP/Job_Management/Check_and_update_calculation_status.py
    
    new_cal_status = check_calculations_status(cal_folder=cal_folder, workflow=workflow, cal_loc_list=cal_folder_list)
    no_of_new_ready_jobs = len(new_cal_status["prior_ready_folder_list"]) + len(new_cal_status["ready_folder_list"])
    no_of_new_ready_jobs += len(new_cal_status["sub_dir_cal_folder_list"])
    no_of_new_ready_jobs -= len(old_cal_status["prior_ready_folder_list"])
    no_of_new_ready_jobs -= len(old_cal_status["ready_folder_list"])
    no_of_new_ready_jobs -= len(old_cal_status["sub_dir_cal_folder_list"])
    cal_status_diff = Cal_status_dict_operation.diff_status_dict(old_cal_status_dict=old_cal_status, new_cal_status_dict=new_cal_status)
    return no_of_new_ready_jobs, cal_status_diff


# In[6]:


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
                    
        if current_firework["copy_which_step"] == -1:
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
        if os.path.isfile(os.path.join(current_cal_loc, "__manual__")): return False
        Write_Vasp_INCAR(cal_loc=current_cal_loc, structure_filename="POSCAR", workflow=workflow)
        if os.path.isfile(os.path.join(current_cal_loc, "__manual__")): return False
        Write_Vasp_KPOINTS(cal_loc=current_cal_loc, structure_filename="POSCAR", workflow=workflow)
        if os.path.isfile(os.path.join(current_cal_loc, "__manual__")): return False
        
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
        
        
        if current_firework["is_fixed_incar_tags_on"]:
            incar_dict = modify_vasp_incar(cal_loc=current_cal_loc)
            fixed_incar_tags = {"is_fixed_incar_tags_on": True}
            for tag in current_firework["fixed_incar_tags"]:
                assert tag in incar_dict.keys(), "While fetching the fixed values of tag {} from INCAR, this tag does not exist in INCAR".format(tag)
                fixed_incar_tags[tag] = incar_dict[tag]
            with open(os.path.join(current_cal_loc, "fixed_incar_tags.json"), "w") as f:
                json.dump(fixed_incar_tags, f, indent=4)
            with open(os.path.join(current_cal_loc, "log.txt"), "a") as f:
                f.write("{} INFO: is_fixed_incar_tags_on is on &  fixed_incar_tags={}\n".format(get_time_str(), current_firework["fixed_incar_tags"]))
                f.write("\t\t\tFetch these values of these incar tags from the ready INCAR and save them into file fixed_incar_tags.json\n")
                for tag, value in fixed_incar_tags.items():
                    f.write("\t\t\t\t{}: {}\n".format(tag, value))
        
        if current_firework["sub_dir_cal"]:
            decorated_os_rename(loc=current_cal_loc, old_filename="__vis__", new_filename="__sub_dir_cal__")
            with open(os.path.join(current_cal_loc, "log.txt"), "a") as f:
                f.write("{} INFO: All VASP input files needed for sub-directory calculations are ready at {}\n".format(get_time_str(), current_firework["firework_folder_name"]))
                f.write("\t\t\t__vis__ --> __sub_dir_cal__\n")
            return True
        
        is_there_file_manual = False
        if os.path.isfile(os.path.join(current_cal_loc, "__non_spin_polarized_prev_cal__")):
            output_str = "But it seems that file __non_spin_polarized_prev_cal__ was created during the input file preparation. File __manual__ is created to ask you to check whether it is correct if the referenced previous step is non-spin polarized.\n"
            open(os.path.join(current_cal_loc, "__manual__"), "w").close()
            is_there_file_manual = True
            
        decorated_os_rename(loc=current_cal_loc, old_filename="__vis__", new_filename="__ready__")
        with open(os.path.join(current_cal_loc, "log.txt"), "a") as f:
            f.write("{} INFO: All VASP input files are ready at {}\n".format(get_time_str(), current_firework["firework_folder_name"]))
            f.write("\t\t\t__vis__ --> __ready__\n")
            if is_there_file_manual:
                f.write("\t\t\t"+output_str)
            


# In[7]:


def get_current_fireworks_and_present_states(mater_cal_folder, workflow):
    """
    find and return the present states of all calcualtion steps for a given material specified by mater_cal_folder
    input arguments:
        -mater_cal_folder: the path under which a sequence of DFT calculations will be done.
        -workflow: the return of function parse_calculation_workflow, which define a set of DFT calculations and related pre- and post- processes
    output:
        -a dict with three key-value pairs:
            *(1) key: "current_fireworks"; value: a sublist of workflow which are ready to be prepared and run
            *(2) key: "present_states"; value: a dict storing the present state of every calculation step, where the key is step_no and the value is 
                the corresponding integer-encoded present state. The integer could be -1, 0, 1, 2 and 22. if the present state of step_i_xxx is:
                    ** -1: the folder for step_i_xxx has not been prepared.
                    **  0: the folder for step_i_xxx exists but it has not reached its final successful state.
                    **  1: step_i_xxx (a) has reached its final successful state; or (b) has HTC tag skip_this_step activated.
                    **  2: step_i_xxx has been tagged by signal file __stop__
                    ** 22: step_i_xxx is a descendant step of a step tagged by signal file __stop__
                    **  3: step_i_xxx has signal file __skipped__ under its calculation folder
                where the final successful state of step_i_xxx corresponds to workflow[0]["firework_dependence_matrix"][0][i]. It tells what signal
                file should be existent under the calculation folder if step_i_xxx is succesfully completed:
                    ** workflow[0]["firework_dependence_matrix"][0][i] = 3: HTC tag skip_this_step is activated for step_i_xxx
                    ** workflow[0]["firework_dependence_matrix"][0][i] = 2: __done_cleaned_analyzed__
                    ** workflow[0]["firework_dependence_matrix"][0][i] = 1: __done__
            *(3) key: "all_completed"; value: True if all calculation steps' present states are > 0; Flase, otherwise.
    """
    firework_dependence_matrix = workflow[0]["firework_dependence_matrix"]
    workflow_size = len(workflow)
    
    present_states = {-1: 1} #for step_no=-1
    
    directory_contents = [folder_name for folder_name in os.listdir(mater_cal_folder) if folder_name.startswith("step_")]
    existing_fireworks = []
    for firework in workflow:
        if firework["firework_folder_name"] in directory_contents:
            assert firework["skip_this_step"] == False, "{}: HTC tag skip_this_step is activated. Therefore, this folder will in principle not be generated and should not exist.".format(os.path.join(mater_cal_folder, firework["firework_folder_name"]))
            existing_fireworks.append(firework)
            #The presence of this calculation folder indicates that all of its ancestor steps are completed successfully.
            for asc_step_no in range(1, firework["step_no"]):
                if asc_step_no not in present_states and firework_dependence_matrix[asc_step_no][firework["step_no"]]:
                    present_states[asc_step_no] = 1
        elif firework["skip_this_step"]: #equivalent to firework_dependence_matrix[0][firework["step_no"]] == 3
            #HTC tag skip_this_step is activated for this step. In principle, its calculation folder will not be created.
            #Useful if all materials need to have a calculation step skipped for later use.
            #See below for signal file __skipped__ for selected calculation steps of certain materials.
            present_states[firework["step_no"]] = 1
        else:
            present_states[firework["step_no"]] = -1
    
    for firework in existing_fireworks:
        step_no = firework["step_no"]
        if step_no in present_states:
            continue
        
        #if firework_dependence_matrix[0][step_no] == 3:
        #    #3: HTC tag skip_this_step is activated for this step. 
        #    #Useful if all materials need to have a calculation step skipped for later use.
        #    present_states[step_no] = 1
        if os.path.isfile(os.path.join(mater_cal_folder, firework["firework_folder_name"], "__skipped__")):
            #The present calcualtion step is unnecessary and can be skipped. Useful if only some materials need to have 
            #a calculation step skipped while the others need to have that step run.
            #In this case, all of its descendant steps will never be prepared and run.
            present_states[step_no] = 3
        elif os.path.isfile(os.path.join(mater_cal_folder, firework["firework_folder_name"], "__stop__")):
            present_states[step_no] = 2
            #If the present calculation step is tagged by signal file __stop__. So are all of its descendant calculation steps.
            for desc_step_no in range(step_no+1, workflow_size+1):
                if firework_dependence_matrix[step_no][desc_step_no]:
                    present_states[desc_step_no] = 22
        elif firework_dependence_matrix[0][step_no] == 2:
            #2: final state is __done_cleaned_analyzed__
            if os.path.isfile(os.path.join(mater_cal_folder, firework["firework_folder_name"], "__done_cleaned_analyzed__")):
                present_states[step_no] = 1
            else:
                present_states[step_no] = 0
        elif firework_dependence_matrix[0][step_no] == 1:
            #1: final state is __done__
            if os.path.isfile(os.path.join(mater_cal_folder, firework["firework_folder_name"], "__done__")):
                present_states[step_no] = 1
            else:
                present_states[step_no] = 0
        else:
            raise Exception("Every entry of the first row of firework_dependence_matrix should be 1, 2 or 3. But it's {}".format(firework_dependence_matrix[0]))

    #for debug
    missed_step_nos = [i for i in range(1, workflow_size+1) if i not in present_states]
    assert len(missed_step_nos) == 0, "failed to find the present states for step_no {}".format(missed_step_nos)
    
    current_fireworks = [] #by current, we mean that they are ready to be prepared and run
    for firework in workflow:
        if firework["skip_this_step"]:
            continue
        if present_states[firework["step_no"]] == 0:
            current_fireworks.append(firework)
        elif present_states[firework["step_no"]] == -1:
            #present_states[asc_step_no]==1 ensures that no descendant steps of a calculation step in state 2, 3 or 22 will be prepared.
            if all([present_states[asc_step_no]==1 for asc_step_no in 
                    [firework["copy_which_step"]] + list(firework["additional_cal_dependence"])]):
                current_fireworks.append(firework)
                
    all_completed = all([state > 0 for state in present_states.values()])

    return {"current_fireworks": current_fireworks, "present_states": present_states, "all_completed": all_completed}         

