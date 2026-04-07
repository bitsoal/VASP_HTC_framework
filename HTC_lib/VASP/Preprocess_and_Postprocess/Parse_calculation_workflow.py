#!/usr/bin/env python
# coding: utf-8

# last edited on 18 Aug 2025

# In[1]:


import os, re, copy, json
import numpy as np


# In[11]:


class Read_Only_Dict():
    def __init__(self, org_dict):
        self.org_dict = copy.deepcopy(org_dict)
        self.unchangeable_tags = tuple(set(org_dict.keys()))
        
    def __setitem__(self, key, value):
        if key in self.unchangeable_tags:
            raise Exception("key '{}' of {} instance is read-only and cannot be reset!".format(key, self.__class__.__name__))
        else:
            self.org_dict[key] = value
    
    def __delitem__(self, key):
        if key in self.unchangeable_tags:
            raise Exception("key '{}' of {} instance is read-only and cannot be deleted!".format(key, self.__class__.__name__))
        else:
            del self.org_dict[key]
    
    def __getitem__(self, key, default=None):
        return self.org_dict.get(key, default)
    
    def __str__(self):
        return self.org_dict.__str__()
    
    def __repr__(self):
        return self.org_dict.__repr__()
    
    def __len__(self):
        return self.org_dict.__len__()
    
    def __contains__(self, key):
        return (key in self.org_dict)
    
    def __iter__(self):
        return self.org_dict.__iter__()
        
    #def update(self, *args, **kwargs):
    #    raise Exception("{} instance is read-only and cannot be changed!".format(self.__class__.__name__))
        
    def get(self, key, default=None):
        return self.org_dict.get(key, default)
    
    def items(self):
        return self.org_dict.items()
    
    def keys(self):
        return self.org_dict.keys()
    
    @classmethod
    def from_dict(cls, dictionary):
        read_only_dictionary = {}
        for key, value in dictionary.items():
            if isinstance(value, list) or isinstance(value, set):
                value = tuple(value)   
            elif isinstance(value, dict):
                value = Read_Only_Dict.from_dict(value)
                
            read_only_dictionary[key] = value
            
        return Read_Only_Dict(read_only_dictionary)


# In[3]:


def read_HTC_calculation_setup_folder(foldername="HTC_calculation_setup_folder"):
    
    ################################################################################################################################
    #identify those files named as step_n_xxx under foldername. File named as step_n_xxx uniquely defines the calculation at step n.
    firework_block_filename_list = []
    for filename in [file for file in os.listdir(foldername) if os.path.isfile(os.path.join(foldername, file))]:
        if re.match("step_\d+_", filename): #The calculation at step n is defined by an unique file named as step_n_xxx
            firework_block_filename_list.append(filename)
    firework_block_filename_list = sorted(firework_block_filename_list, key=lambda filename: int(filename.split("_")[1]))
    
    #Check if the file defining the calculation at step n is uniquely existent.
    step_no_list = [int(filename.split("_")[1]) for filename in firework_block_filename_list]
    for step_no in range(1, len(firework_block_filename_list) + 1):
        count = step_no_list.count(step_no)
        #print(step_no, count)
        if count > 1:
            raise Exception("You have more than 1 files named as step_{}_xxx. I don't know to which one you are referring the calculation at step {}".format(step_no, step_no))
        elif count == 0:
            raise Exception("There isn't a file named as step_{}_xxx --> You have not defined the calculation at step {}.".format(step_no, step_no))
    #print(firework_block_filename_list)
    #####################################################################################################################################
        
    #####################################################################################################################################
    #read setup from files and put them into firework_block_list
    firework_block_list = []
    for firework_block_filename in firework_block_filename_list:
        with open(os.path.join(foldername, firework_block_filename)) as f:
            lines = []
            for line in f:
                line = line.split("#")[0].strip()
                if line: lines.append(line)
        no_of_start_line, no_of_end_line = 0, 0
        for line_ind, line in enumerate(lines):
            if line.startswith("**start"):
                start_line_ind = line_ind
                no_of_start_line += 1
            elif line.startswith("**end"):
                end_line_ind = line_ind
                no_of_end_line += 1
        assert no_of_start_line == 1, "In a firework/calculation setup file, line '**start' should be unique and indicate the beginning of the firework/calculation setup. But there are|is {} '**start' in file {}".format(no_of_start_line, firework_block_filename)
        assert no_of_end_line == 1, "In a firework/calculation setup file, line '**end' should be unique and indicate the end of the firework/calculation setup. But there are|is {} '**end' in file {}".format(no_of_end_line, firework_block_filename)
        #assert start_line_ind != -100, "In file {}, the effective setup starts from that line '**start'. But there is no such a line".format(firework_block_filename)
        #assert end_line_ind != -100, "In file {}, the effective setup ends at that line '**end'. But there is no such a line".format(firework_block_filename)
        assert start_line_ind < end_line_ind, "In a firework/calculation setup file, the firework/calculation setup is in between line '**start' and line '**end'. The former should appear earlier than the latter in file {}".format(firework_block_filename)
        firework_block_list.append(lines[start_line_ind+1:end_line_ind])
                
    return firework_block_filename_list, firework_block_list


# In[4]:


def check_dependent_step_names(workflow):
    """
    What it does:
        I. check if every calculation step copies from the correct parent calculation step (tag: copy_which_step)
        II. check if every calculation step has an array of correct additional depdendent steps (tag: additional_cal_dependence)
        If there is an error, raise it; Otherwise, return True
    """
    if len(workflow) > 1:   
        cal_name_list = [firework["firework_folder_name"] for firework in workflow if not firework["skip_this_step"]]
        
        #Task I @ copy_which_step
        for firework in workflow[1:]:
            if firework["skip_this_step"]:
                continue
            if firework["copy_which_step_full_name"] == "None": 
                #this is the case where it is not the first step but creates its vasp input files from scratch.
                continue
            assert firework["copy_which_step_full_name"] in cal_name_list,             "tag copy_which_step in {} refers to a non-existent or skip_this_step-activated parent step: {}".format(firework["firework_folder_name"], 
                                                                                           firework["copy_which_step_full_name"])
        
        #Task II @ additional_cal_dependence
        for firework in workflow[1:]:
            if firework["skip_this_step"]:
                continue
            for dep_cal_name in firework["additional_dependence_full_name"]:
                assert dep_cal_name in cal_name_list,                 "tag additional_cal_dependence in {} refers to a non-existent or skip_this_step-activated additional dependent calculation step: {}".format(
                    firework["firework_folder_name"], dep_cal_name)
                
    return True
    


# In[7]:


def get_dependence_matrix(workflow, verbose=True):
    """
    The dependence between different calculation steps is represented using an integer matrix, DM. This is aimed to replace 
    'firework_hierarchy_dict' generated by func cal_calculation_sequence_of_all_fireworks and func 
    reduce_additional_cal_dependence_and_correct_hierarchy, yet in a more simplified/clearer manner.
    
    Representation of the dependence matrix DM.
    1. Dimension: a (N+1)x(N+1) square matrix, where N is the total number of calcultation steps defined by workflow and 
                the extra 1 corresponds to "step_no = -1". For the first calculation step(s) defined by workflow, copy_which_step=-1
    2. The 0-based i-th column/row corresponds to step_i_xxx.
    3. For step_i_xxx (i>0), DM[i, j] (j<i) denotes the depdendence of step_i_xxx on the previous (i-1) steps:
        3.1. DM[i, j] = 0 if step_i_xxx is independent of step_j_yyy.
        3.2. DM[i, j] = 1, 2, or 3 if step_i_xxx is dependent on step_j_yyy. Here 1, 2 or 3 encodes the final state in which step_j_yyy
            should be. See below for detailed explanations.
    4. DM[0, j] denotes the final state in which step_j_yyy should be. It could be either of 1, 2 or 3.
    5. encoded successful final states - 1, 2 or 3
        * 1: step_j_yyy is successfully completed and marked by magic signal file "__done__"
        * 2: step_j_yyy is successfully completed and marked by magic signal file "__done_cleaned_analyzed__"
        * 3: step_j_yyy is skipped because HTC tag "skip_this_step=Yes" for this step
    6. DM[0, 0] is always 1. It carries no meaning.
    7. DM[i, j] (i>0 & j>i) denotes if step_j_yyy is either directly or indirectly dependent on step_i_xxx:
        7.1. DM[i, j] != 0: step_j_yyy is dependent on step_i_xxx, either directly or indirectly.
        7.2. DM[i, j] == 0: step_j_yyy is completely independent of step_i_xxx.
        
    input argument:
        - workflow: a list of calcualtion setups/fireworks, each of which is generated by func parse_firework_block
        - verbose (boolean, default: True): whether to print out the parsed final state of each calculation step/firework and its dependence.
    
    return:
        - A (N+1)x(N+1) integer square matrix
    """
    workflow_size = len(workflow)
    debug = False
    
    DM = np.zeros(shape=(workflow_size+1, workflow_size+1), dtype=int)
    DM[0, 0] = 1
    for firework in workflow:
        if firework["skip_this_step"]:
            DM[0, firework["step_no"]] = 3
        elif firework["cmd_to_process_finished_jobs"]:
            DM[0, firework["step_no"]] = 2
        else:
            DM[0, firework["step_no"]] = 1
    assert np.min(DM[0]) > 0, "func get_dependence_matrix fails to find the final states of all calculation steps/fireworks: {}".format(DM[0])
    
    for firework in workflow:
        if firework["skip_this_step"]:
            continue
        if firework["copy_which_step"] == -1:
            DM[firework["step_no"], 0] = DM[0, 0]
        else:
            DM[firework["step_no"], firework["copy_which_step"]] = DM[0, firework["copy_which_step"]]
        for add_dep_step_no in firework["additional_cal_dependence"]:
            DM[firework["step_no"], add_dep_step_no] = DM[0, add_dep_step_no]
    if debug:
        print("Dependence matrix: Before the upper triangle is filled:\n{}".format(DM), flush=True)
    
    #Fill the upper triangle with all direct or indirect descendant steps. We do it BACKWARDS so that all descendant steps
    #for a given step can be filled at once.
    for firework in workflow[-1:0:-1]:
        if firework["skip_this_step"]:
            continue
        step_no = firework["step_no"]
        for parent_step_no in [firework["copy_which_step"]] + firework["additional_cal_dependence"]:
            if parent_step_no == -1:
                continue
            DM[parent_step_no, step_no:] += DM[step_no, step_no:]
            DM[parent_step_no, step_no]  += 1
        if debug:
            print("Dependence matrix: after filling the parent-child relationship in the upper triangle for step_no={}:\n{}".format(step_no, DM), flush=True)
            
    if verbose:
        print("Dependence matrix: Below is the finally parsed dependence between calculation steps/fireworks", flush=True)
        print("Dependence matrix: The encoded dependence matrix (DM):\n{}".format(DM), flush=True)
        print("Dependence matrix: Meaning for the upper right triangle, exclusive of diagonal entries", flush=True)
        print("Dependence matrix: \tstep_j_yyy is directly or indirectly dependent on step_i_xxx (i<j) if DM[i, j] != 0; Otherwise, completely independent", flush=True)
        print("Dependence matrix: Meaning for the lower left triangle, exclusive of diagonal entries", flush=True)
        step_name_arr = np.array(["-1"] + [firework["firework_folder_name"] for firework in workflow])
        for firework in workflow:
            i = firework["step_no"]
            dependent_step_arr = step_name_arr[:i][DM[i, :i] > 0]
            if DM[0, i] == 3:
                print("Dependence matrix: {} has skip_this_step activated. It is fully independent".format(firework["firework_folder_name"]), flush=True)
            elif DM[0, i] == 2:
                print("Dependence matrix: {} should have a final state of __done_cleaned_analyzed__. It dependes on {}".format(firework["firework_folder_name"], 
                                                                                                                            dependent_step_arr), flush=True)
            else:
                print("Dependence matrix: {} should have a final state of __done__ . It dependes on {}".format(firework["firework_folder_name"], 
                                                                                                               dependent_step_arr), flush=True)
    
    
    return DM.tolist()


# In[8]:


def parse_calculation_workflow(filename_or_foldername, HTC_lib_loc):
    """
    Parse the pre-defined VASP calculation workflow from a file or a set of files named as step_n_xxx under a folder.
    """
    
    workflow = []
    
    is_it_a_foldername = False
    if os.path.isfile(filename_or_foldername):
        with open(filename_or_foldername, "r") as f:
            lines = [line.strip() for line in f if line.strip()]
        
        is_it_in_cal_blk = False
        firework_block_list = []
        for line_ind, line in enumerate(lines):
            line = line.split("#")[0].strip()
            if line:
                if line.startswith("**start"):
                    assert is_it_in_cal_blk == False, "Each calculation block should end with '**end'. But it is missing somewhere above line %d" % line_ind
                    firework_block_list.append([])
                    is_it_in_cal_blk = True
                else:
                    if line.startswith("**end"):
                        is_it_in_cal_blk = False
                    if is_it_in_cal_blk:
                        firework_block_list[-1].append(line)
        firework_block_list = [block for block in firework_block_list if block]
    elif os.path.isdir(filename_or_foldername):
        is_it_a_foldername = True
        firework_block_filename_list, firework_block_list = read_HTC_calculation_setup_folder(foldername=filename_or_foldername)
    
    for firework_block_ind, firework_block in enumerate(firework_block_list):
        step_no = firework_block_ind+1
        firework = parse_firework_block(block_str_list=firework_block, step_no=step_no, HTC_lib_loc=HTC_lib_loc)
        workflow.append(firework)
    workflow[0]["firework_dependence_matrix"] = get_dependence_matrix(workflow, verbose=True)
    
    #firework_hierarchy_dict = {}
    #for firework_block_ind, firework_block in enumerate(firework_block_list):
    #    step_no = firework_block_ind+1
    #    firework = parse_firework_block(block_str_list=firework_block, step_no=step_no, HTC_lib_loc=HTC_lib_loc)
    #    workflow.append(firework)
    #    if step_no == 1:
    #        firework_hierarchy_dict["-1"] = [firework["firework_folder_name"]]
    #    else:
    #        if firework["copy_which_step"] == -1:
    #            prev_firework_folder_name = "-1"
    #        else:
    #            prev_firework_folder_name = workflow[firework["copy_which_step"]-1]["firework_folder_name"]
    #        
    #        if prev_firework_folder_name not in firework_hierarchy_dict.keys():
    #            firework_hierarchy_dict[prev_firework_folder_name] = [firework["firework_folder_name"]]
    #        else:
    #            firework_hierarchy_dict[prev_firework_folder_name].append(firework["firework_folder_name"])
    #
    #firework_hierarchy_dict, workflow = reduce_additional_cal_dependence_and_correct_hierarchy(workflow, firework_hierarchy_dict)
    #workflow[0]["firework_hierarchy_dict"] = firework_hierarchy_dict
    
        
    with open("Parsed_HTC_setup.JSON", "w") as f:
        json.dump(workflow, f, indent=1) 
        #This must be done before we convert workflow entries to read-only format. Because the latter is not Json Serializable
        
    workflow = [Read_Only_Dict.from_dict(firework) for firework in workflow]
    check_dependent_step_names(workflow)
    
    if is_it_a_foldername:
        for firework_block_filename, firework in zip(firework_block_filename_list, workflow):
            assert firework_block_filename == firework["firework_folder_name"], "firework_folder_name constructed based on step_no and cal_name should be the same as the filename of the file defining the firework/calculation. {} V.S. {}".format(firework_block_filename, firework["firework_folder_name"])
                              
    return workflow              


# def cal_calculation_sequence_of_all_fireworks(firework_hierarchy_dict):
#     """
#     Calculate the calculation sequence of all fireworks. The sequence is represented by integers. The smaller the integer of a firework is,
#             the earlier that firework starts. The first firework is labelled by 1
#     Example: Suppose step 2 copies from (depends on ) step 1, and step 3 and 4 copy from (depend on) step 2. The calculation sequence should be:
#             step 1 first starts and then step 2. Following step 2, step 3 and 4 start simultaneously.
#             So step 1 <--> 1
#                 step 2 <--> 2
#                 step 3, 4 <--> 3
#     """
#     cal_sequence_dict = {}
#     for firework_folder_name in firework_hierarchy_dict["-1"]:
#         cal_sequence_dict[firework_folder_name] = 1
#     firework_hierarchy_key_list = firework_hierarchy_dict.keys()
#     current_firework_list = firework_hierarchy_dict["-1"]
#     current_level = 1
#     while True:
#         next_firework_list = []
#         for current_firework in current_firework_list:
#             if current_firework in firework_hierarchy_key_list:
#                 next_firework_list.extend(list(firework_hierarchy_dict[current_firework]))
#         for next_firework in next_firework_list:
#             cal_sequence_dict[next_firework] = current_level + 1
#         if next_firework_list == []:
#             break
#         else:
#             current_firework_list = next_firework_list
#             current_level += 1
#     #print(cal_sequence_dict)
#     return cal_sequence_dict

# def reduce_additional_cal_dependence_and_correct_hierarchy(workflow, firework_hierarchy_dict):
#     """
#     Reduce the redundant job dependence relations and correct the firework hierarchy. 
#     Example: Suppose that both step 5 and step 3 copy from step 2, and step 5 additionally depends on the calculation outputs of step 3.
#                 In this case, step 5 enssentially should start after step 3, while in the hierarchy relation based on copy_from_which,
#                 step 5 is set to start after step 2. So to determine if step 5 should start, we just need to check if step 3 completes.
#     """
#     import copy
#     new_hierarchy_dict = copy.deepcopy(firework_hierarchy_dict)
#     for firework_ind, firework in enumerate(workflow):
#         if firework["additional_cal_dependence"]==[] or firework["step_no"] == 1:
#             continue
#             
#         cal_sequence_dict = cal_calculation_sequence_of_all_fireworks(new_hierarchy_dict)
#         #import pprint
#         #pprint.pprint(cal_sequence_dict)
#         #pprint.pprint(new_hierarchy_dict)
#         copy_step_folder_name = workflow[firework["copy_which_step"]-1]["firework_folder_name"]
#         latest_dependent_firework_cal_level = 0
#         latest_dependent_firework_list = []
#         for dependent_firework_step_no in firework["additional_cal_dependence"]:
#             dependent_firework_folder_name = workflow[dependent_firework_step_no-1]["firework_folder_name"]
#             cal_level = cal_sequence_dict[dependent_firework_folder_name]
#             if cal_level > latest_dependent_firework_cal_level:
#                 latest_dependent_firework_cal_level = cal_level
#                 latest_dependent_firework_list = [dependent_firework_folder_name]
#             elif cal_level == latest_dependent_firework_cal_level:
#                 latest_dependent_firework_list.append(dependent_firework_folder_name)
#         copy_step_cal_level = cal_sequence_dict[copy_step_folder_name]
#         if copy_step_cal_level < latest_dependent_firework_cal_level:
#             for current_step_folder_name, next_step_folder_name_list in new_hierarchy_dict.items():
#                 if firework["firework_folder_name"] in next_step_folder_name_list:
#                     new_hierarchy_dict[current_step_folder_name].remove(firework["firework_folder_name"])
#                     break
#             #Here just pick up one dependent firework to ensure that every firework can be uniquelly referred to.
#             #The other depdendence of the firework will be stored in "additional_cal_dependence"
#             new_dependent_firework_name_in_hierarchy = latest_dependent_firework_list.pop()
#             if new_dependent_firework_name_in_hierarchy in new_hierarchy_dict.keys():
#                 new_hierarchy_dict[new_dependent_firework_name_in_hierarchy].append(firework["firework_folder_name"])
#             else:
#                 new_hierarchy_dict[new_dependent_firework_name_in_hierarchy] = [firework["firework_folder_name"]]
#         workflow[firework_ind]["additional_cal_dependence"] = latest_dependent_firework_list
#         
#     return new_hierarchy_dict, workflow   

# In[8]:


def parse_firework_block(block_str_list, step_no, HTC_lib_loc):
    """
    parse the calculation setup for a firework.
    """
    #available htc tags
    htc_tag_list = ["structure_folder", "cal_folder", "step_no", "cal_name", "copy_from_prev_cal", 
                    "move_from_prev_cal", "contcar_to_poscar", "copy_which_step", "additional_cal_dependence", "error_backup_files", 
                    "htc_input_backup", "htc_input_backup_loc", "max_no_of_ready_jobs",
                    "remove_after_cal", "extra_copy", "final_extra_copy", "comment_incar_tags", "remove_incar_tags",
                    "set_ispin_based_on_prev_cal", "set_lmaxmix",
                    "partial_charge_cal", "which_step_to_read_cbm_vbm", "EINT_wrt_CBM", "EINT_wrt_VBM", "bader_charge",
                    "ldau_cal", "ldau_u_j_table", "incar_template", "valid_incar_tags", 
                    "is_fixed_incar_tags_on", "fixed_incar_tags",
                    "kpoints_type", "denser_kpoints", "reciprocal_density", "kpoints_line_density",
                    "intersections", "force_gamma", "2d_system", "sort_structure", "max_ionic_step", "update_kpoints_every_round",
                    "user_defined_cmd", "final_user_defined_cmd", "user_defined_postprocess_cmd", 
                    "incar_cmd", "kpoints_cmd", "poscar_cmd", "potcar_cmd", "cmd_to_process_finished_jobs",
                    "sub_dir_cal", "sub_dir_cal_cmd", "preview_vasp_inputs",
                    "skip_this_step",
                    "max_workers",
                    "job_submission_script", "job_submission_command", "job_name", "max_running_job", "where_to_parse_queue_id",
                    "re_to_parse_queue_id", "job_query_command", "job_killing_command", "queue_stdout_file_prefix", "queue_stdout_file_suffix",
                    "queue_stderr_file_prefix", "queue_stderr_file_suffix", "vasp.out", 
                    "jobs_treated_like_running_jobs"]
    htc_tag_list = [tag.lower() for tag in htc_tag_list]
    
    
    firework = {"new_incar_tags":{}}
    
    for line in block_str_list:
        if line.count("=") != 1 and "*begin(add_new_incar_tags)" not in line.lower() and "*end(add_new_incar_tags)" not in line.lower():
            raise Exception("Each line is supposed to have only one '=', while the line below has {}\n{}\n".format(line.count("="), line))
    
    
    current_directory = os.getcwd()
    incar_subblock = False
    for line in block_str_list:            
        if line.lower().startswith("*begin(add_new_incar_tags)"):
            incar_subblock = True
        elif line.lower().startswith("*end(add_new_incar_tags)"):
            incar_subblock = False
        else:
            tag, value = [item.strip() for item in line.split("=")]
            value = value.replace("${HTC_CWD}", current_directory)
            value = value.replace("${HTC_LIB_LOC}", HTC_lib_loc)
            if incar_subblock:
                firework["new_incar_tags"][tag.upper()] = value
            else:
                assert tag.lower() in htc_tag_list, "Step %d: tag %s has not been defined. Please check!" % (step_no, tag)
                firework[tag.lower()] = value             
    
    
    #Check the validity of the setting and assign default values to unspecified tags
    
    #1. step_no and calculation name
    if "step_no" in firework.keys():
        if step_no == int(firework["step_no"]):
            firework["step_no"] = step_no
        else:
            print("\n")
            print("*"*100)
            print("step_no of firework/calculation {} must be set to {}. Please reset step_no".format(step_no, step_no))
            print('*'*100)
            print("\n")
            raise Exception("See above for the error information")
    else:
        raise Exception("tag step_no is required for every firework. Please set step_no={} for firework {}".format(step_no, step_no))
    assert "cal_name" in firework.keys(), "Error: you should name each firework through tag cal_name!"
    firework["firework_folder_name"] = "step_" + str(step_no) + "_" + firework["cal_name"].replace(" ", "_")
         
    #2. Tags related to quick creation of temporary skipped steps
    #By parsing tag skip_this_step right after HTC tag "step_no" and "cal_name", only the latter two tags are compulsory if
    #the former tag is activated.
    firework["skip_this_step"] = True if 'y' in firework.get("skip_this_step", "No").lower() else False
    if firework["skip_this_step"]:
        if firework["step_no"] == 1:
            raise Exception("The first step cannot be skipped. Please remove tag skip_this_step from the first step.")
        else:
            return firework
        
    #3. tags involved in copying
    firework["copy_from_prev_cal"] = firework.get("copy_from_prev_cal", "")
    firework["copy_from_prev_cal"] = [item.strip() for item in firework["copy_from_prev_cal"].split(",") if item.strip()]
    if step_no == 1:
        firework["copy_which_step"] = -1
    else:
        assert "copy_which_step" in firework.keys(), "You forgot to set 'copy_from_prev_cal' in step {}. This tag was optional but is now mandatory if it is not the 1st step.".format(step_no)
        if firework["copy_which_step"] == "-1":
            firework["copy_which_step"] = -1
            firework["copy_which_step_full_name"] = "None"
        else:
            if not firework["copy_which_step"].startswith("step_"):
                output_str = "In step {}: We ask you to now set the full step name (step_i_xxx) to 'copy_which_step' ".format(step_no)
                output_str += "rather than a step no that was adopted previously. "
                output_str += "This change will help to check if you are copying essential vasp input and output files "
                output_str += "from the correct parent calculation step. This is useful especially"
                output_str += " when you make big changes to the calculation workflow, i.e. insert more steps"
                output_str += " between existing cal steps or rename some cal steps."
                output_str += "\n Current setting: {}".format(firework["copy_which_step"])
                raise Exception(output_str)
            firework["copy_which_step_full_name"] = firework["copy_which_step"]
            firework["copy_which_step"] = int(firework["copy_which_step"].split("_")[1])
            assert 1 <= firework["copy_which_step"] < step_no, "step {}: tag 'copy_which_step should be in >= 1 and < {}, or == -1'".format(step_no, step_no)   
            
    for tag in ["extra_copy", "final_extra_copy"]:
        firework[tag] = firework.get(tag, "")
        file_list = [file_.strip() for file_ in firework[tag].split(",") if file_.strip()]
        for file_ in file_list:
            assert os.path.isfile(file_), "the file below listed in tag {} doesn't exist.\n\t\t\t{}\n".format(tag, file_)
        firework[tag] = file_list
    if step_no == 1:
        firework["error_backup_files"] = firework.get("error_backup_files", 
                                                      "INCAR, POSCAR, CONTCAR, KPOINTS, XDATCAR, OUTCAR, OSZICAR")
    else:
        firework["error_backup_files"] = firework.get("error_backup_files", "")
    firework["error_backup_files"] = [item.strip() for item in firework["error_backup_files"].split(",") if item.strip()]    
    
    #4. tags involved in moving, removing and renaming
    for tag in ["move_from_prev_cal", "remove_after_cal"]:
        firework[tag] = firework.get(tag, "")
        firework[tag] = [item.strip() for item in firework[tag].split(",") if item.strip()]
    firework["contcar_to_poscar"] = firework.get("contcar_to_poscar", "No").lower()
    firework["contcar_to_poscar"] = True if "y" in firework["contcar_to_poscar"] else False           
        
    #5. INCAR related tags
    set_ispin_based_on_prev_cal = firework.get("set_ispin_based_on_prev_cal", "")
    if set_ispin_based_on_prev_cal != "":
        try:
            mag_threshold_str, prev_cal_step = [item.strip() for item in set_ispin_based_on_prev_cal.split("@") if item.strip()]
            mag_threshold_str = mag_threshold_str.lower()
            if mag_threshold_str.endswith("/atom"):
                firework["set_ispin_based_on_prev_cal"] = {"mag": float(mag_threshold_str.strip("/atom")), 
                                                           "mag_type": "per_atom", "prev_cal_step": prev_cal_step, 
                                                           "set_ispin_based_on_prev_cal_str": set_ispin_based_on_prev_cal}
            elif mag_threshold_str.endswith("tot"):
                firework["set_ispin_based_on_prev_cal"] = {"mag": float(mag_threshold_str.strip("tot")), 
                                                           "mag_type": "tot", "prev_cal_step": prev_cal_step, 
                                                           "set_ispin_based_on_prev_cal_str": set_ispin_based_on_prev_cal}
            else:
                raise Exception
            assert firework["set_ispin_based_on_prev_cal"]["mag"] >= 0, "the threshold should be >= 0."
        except:
            output_str = "Failed to parse 'set_ispin_based_on_prev_cal={}' at {}\n".format(set_ispin_based_on_prev_cal, firework["firework_folder_name"])
            output_str += "The correct format should be: \n\t\t\ta float number + /atom OR tot + @ + previous calculation step name\n"
            output_str += "where 'number' should be >= 0 since we only compare the magnitude.\n"
            output_str += "\t\t\te.g. I. 0.02/atom@step_1_str_opt <--> If the calculated magnetic moment at step_1_str_opt <= (>) 0.02 Bohr magneton/atom, set ISPIN of the current step to 1 (2)\n"
            output_str += "\t\t\te.g. II. 0.02tot@step_1_str_opt <--> If the calculated total magnetic moment at step_1_str_opt <= (>) 0.02 Bohr magneton, set ISPIN of the current step to 1 (2)\n"
            raise Exception(output_str)
    else:
        firework["set_ispin_based_on_prev_cal"] = {}
        
    is_fixed_incar_tags_on = firework.get("is_fixed_incar_tags_on", "Yes").lower()
    firework["is_fixed_incar_tags_on"] = True if "y" in is_fixed_incar_tags_on else False
    fixed_incar_tags = firework.get("fixed_incar_tags", "")
    firework["fixed_incar_tags"] = [tag.strip().upper() for tag in fixed_incar_tags.split(",") if tag.strip()] + ["EDIFF"]
    firework["fixed_incar_tags"] = list(set(firework["fixed_incar_tags"]))
        
    
    if "comment_incar_tags" in firework.keys():
        raise Exception("HTC tag 'comment_incar_tags' has been obsolete. Only use 'remove_incar_tags' to deactivate INCAR tags.")
    for tag in ["remove_incar_tags"]:
        firework[tag] = firework.get(tag, "")
        firework[tag] = [item.strip().upper() for item in firework[tag].split(",") if item.strip()]
    
    firework["bader_charge"] = firework.get("bader_charge", "No").lower()
    firework["bader_charge"] = True if "y" in firework["bader_charge"] else False
    
    firework["partial_charge_cal"] = firework.get("partial_charge_cal", "No").lower()
    firework["partial_charge_cal"] = True if "y" in firework["partial_charge_cal"] else False
    if "eint_wrt_cbm" in firework.keys():
        firework["eint_wrt_cbm"] = [float(value) for value in firework["eint_wrt_cbm"].split()]
    else:
        firework["eint_wrt_cbm"] = None
    if "eint_wrt_vbm" in firework.keys():
        firework["eint_wrt_vbm"] = [float(value) for value in firework["eint_wrt_vbm"].split()]
    else:
        firework["eint_wrt_vbm"] = None
    #firework["which_step_to_read_cbm_vbm"] = int(firework.get("which_step_to_read_cbm_vbm", -1))
    firework["which_step_to_read_cbm_vbm"] = firework.get("which_step_to_read_cbm_vbm", "")
    if firework["partial_charge_cal"]:
        #automatically add which_step_to_read_cbm_vbm to "additional_cal_dependence" and "additional_dependence_full_name" later
        assert firework["which_step_to_read_cbm_vbm"].startswith("step_"), "For step {}: since 18 Aug. 2025, we ask you to set the full step name (i.e. step_i_xxx) to 'which_step_to_read_cbm_vbm'".format(step_no)
        parsed_step_no = int(firework["which_step_to_read_cbm_vbm"].split("_")[1])
        #assert 0<firework["which_step_to_read_cbm_vbm"]<step_no, "For step {}, which_step_to_read_cbm_vbm should be >0 and <{}".format(step_no, step_no)
        assert 0 < parsed_step_no < step_no, "For step {}, step_i_xxx specified via HTC tag 'which_step_to_read_cbm_vbm' should be 0 < i < {}".format(step_no, step_no)
        assert firework["eint_wrt_vbm"] != None or firework["eint_wrt_cbm"] != None,         "For step {}, since the partial charge calculation is activated by partial_charge_cal, eith EINT_wrt_CBM or EINT_wrt_VBM shoud be set".format(step_no)
        
    firework["set_lmaxmix"] = firework.get("set_lmaxmix", "no").lower()
    if "y" in firework["set_lmaxmix"]:
        firework["set_lmaxmix"] = True
    else:
        firework["set_lmaxmix"] = False
    
    firework["ldau_cal"] = firework.get("ldau_cal", "no").lower()
    if "y" in firework["ldau_cal"]:
        firework["ldau_cal"] = True
        assert os.path.isfile(firework["ldau_u_j_table"]), "Step {}: Since you want to carry out LDA+U calculation, you need to provide a file containing Hubbard U and J by tag ldau_u_j_table".format(step_no)
    else:
        firework["ldau_cal"] = False
        
        
    #6. KPOINTS related tags
    if "kpoints_type" not in firework.keys():
        print("\nYou don't set tag kpoints_type for step {}".format(step_no))
        print("kpoints_type option: MPRelaxSet, MPStaticSet, MPNonSCFSet_line, MPNonSCFSet_uniform, Line-mode")
        print("\t\tFor MPRelaxSet, MPStaticSet, float denser_kpoints (three float/int numbers) can be set to make kpoints denser. Default: 1, 1, 1")
        print("\t\tFor MPNonSCFSet_line, kpoints_line_density can be set. Default: 40")
        print("\t\tFor MPNonSCFSet_uniform, reciprocal_density can be set. Default: 1000")
        print("\t\tFor Line-mode, intersections can be set. Default: 20\n")
        raise Exception("See above for the error information")
    elif firework["kpoints_type"] not in ["MPRelaxSet", "MPStaticSet", "MPNonSCFSet_line", "MPNonSCFSet_uniform", "Line-mode"]:
        raise Exception("kpoints_type must be one of MPRelaxSet, MPStaticSet, MPNonSCFSet_line, MPNonSCFSet_uniform or Line-mode @ step {}".format(step_no))
                
    firework["reciprocal_density"] = int(firework.get("reciprocal_density", 1000))
    firework["kpoints_line_density"] = int(firework.get("kpoints_line_density", 40))
    firework["intersections"] = int(firework.get("intersections", 20))
         
    firework["denser_kpoints"] = firework.get("denser_kpoints", (1, 1, 1))
    if isinstance(firework["denser_kpoints"], str):
        firework["denser_kpoints"] = [float(k_multiple) for k_multiple in firework["denser_kpoints"].split(",") if k_multiple.strip()]
        assert len(firework["denser_kpoints"])==3, "Error: tag denser_kpoints must be three float/integer numbers separated by commas at step {}.".format(step_no)           
        
       
    
    #7. cmd defined by users
    for tag in ["user_defined_cmd", "final_user_defined_cmd", "user_defined_postprocess_cmd", "incar_cmd", "kpoints_cmd", "poscar_cmd", 
                "potcar_cmd", "cmd_to_process_finished_jobs"]:
        if tag in firework.keys(): 
            if tag == "user_defined_postprocess_cmd":
                raise Exception("{}: HTC tag 'user_defined_postprocess_cmd' has been obsolete. Now, we provide HTC tag 'cmd_to_process_finished_jobs'".format(firework["firework_folder_name"]))
            firework[tag] = [cmd_.strip() for cmd_ in firework[tag].split(",") if cmd_.strip()]
        else:
            firework[tag] = []
    
      

    #8. sub-directory calculation specification
    firework["sub_dir_cal"] = firework.get("sub_dir_cal", "no").lower()
    firework["sub_dir_cal"] = True if 'y' in firework["sub_dir_cal"] else False
    if firework["sub_dir_cal"]:
        assert "sub_dir_cal_cmd" in firework.keys(),         "step %d: Because the sub-directory calculation is invoked (tag: 'sub_dir_cal'), you must specify 'sub_dir_cal_cmd'" % step_no
        firework["sub_dir_cal_cmd"] = [cmd_.strip() for cmd_ in firework["sub_dir_cal_cmd"].split(",") if cmd_.strip()]
       
    #9. structural optimization related tags
    firework["max_ionic_step"] = int(firework.get("max_ionic_step", -1))
    assert firework["max_ionic_step"] >= 1 or firework["max_ionic_step"] == -1, "tag max_ionic_step should be set to a positive integer or -1 (default) to activate or deactivate this tag, respectively."
    firework["update_kpoints_every_round"] = firework.get("update_kpoints_every_round", "no").lower()
    firework["update_kpoints_every_round"] = True if 'y' in firework["update_kpoints_every_round"] else False
    if firework["update_kpoints_every_round"]:
        if firework["sub_dir_cal"]:
            output_str = "Contradictory Setup at step %d: both 'update_kpoints_every_round' and 'sub_dir_cal' are set to 'Yes'. " % step_no
            output_str += "But it is currently not supported to update KPOINTS according to 'kpoints_cmd' after every round of correction."
            raise Exception(output_str)
        if firework["kpoints_cmd"] == []:
            output_str = "Contradictory Setup at step %d: 'update_kpoints_every_round' is set to 'Yes'. " % step_no
            output_str = "Therefore, KPOINTS is supposed to update as per tag 'kpoints_cmd' after every round of correction."
            output_str = " But tag 'kpoints_cmd' is not set or set to empty."
            raise Exception(output_str)
        
    # job submissions
    assert "job_submission_script" in firework.keys(), "Error: must specify job_submission_script for every firework."
    assert os.path.isfile(firework["job_submission_script"]), "Step {}: the specified job submission script does not exist.".format(step_no)
    assert "job_submission_command" in firework.keys(), "Error: must specify how to submit a job for every firework."
    
    #10. additional calculation dependence besides those specified by copy_which_step
    if "additional_cal_dependence" in firework.keys():
        additional_dependence_list, additional_dependence_full_name_list = [], []
        for cal_name in firework["additional_cal_dependence"].strip().split(","):
            cal_name = cal_name.strip()
            if cal_name == "": continue
            if not cal_name.startswith("step_"):
                output_str = "In step {}: We ask you to now provide the full step name (step_i_xxx, step_j_yyy) to 'additional_cal_dependence' ".format(step_no)
                output_str += "rather than a step no that was adopted previously. "
                output_str += "This change will help to check if you are referring to the correct additional dependent"
                output_str += " calculation step(s). This is useful especially"
                output_str += " when you make big changes to the calculation workflow, i.e. insert more steps"
                output_str += " between existing cal steps or rename some cal steps."
                output_str += "\n current setting: {}".format(firework["additional_cal_dependence"])
                raise Exception(output_str)
            else:
                dependent_step_no = int(cal_name.split("_")[1])
                assert 1<=dependent_step_no<step_no, "For step {}, cal_dependence should be >=1 and < {}".format(step_no, step_no)
                additional_dependence_list.append(dependent_step_no)
                additional_dependence_full_name_list.append(cal_name)
        firework["additional_cal_dependence"] = additional_dependence_list
        firework["additional_dependence_full_name"] = additional_dependence_full_name_list
        assert firework["additional_cal_dependence"], "In step {}: Parse nothing from tag additional_cal_dependence. Pls go check.".format(step_no)
    else:
        firework["additional_cal_dependence"] = []
        firework["additional_dependence_full_name"] = []
    #add which_step_to_read_cbm_vbm to "additional_cal_dependence" and "additional_dependence_full_name" if the former is valid.
    if firework["partial_charge_cal"] and firework["which_step_to_read_cbm_vbm"] not in firework["additional_dependence_full_name"]:
        firework["additional_cal_dependence"].append(int(firework["which_step_to_read_cbm_vbm"].split("_")[1]))
        firework["additional_dependence_full_name"].append(firework["which_step_to_read_cbm_vbm"])
        
        
    #tags only required and optional for the first firework
    if step_no == 1:
        firework["htc_cwd"] = current_directory
        assert "job_query_command" in firework.keys(), "Error: must specify job_query_command in the first firework. (e.g. 'bjobs -w' on GRC)"
        assert "job_killing_command" in firework.keys(), "Error: must specify job_killing_command by job_killing_command in the first firework. (e.g. 'bkill' on GRC)"
        assert "where_to_parse_queue_id" in firework.keys(), "Error: must specify which file to parse queue id by where_to_parse_queue_id in the first firework. (e.g. if job_submission_command is 'bsub < vasp.lsf > job_id', it is 'job_id')"
        assert "re_to_parse_queue_id" in firework.keys(), "Error: must specify the regular expression by tag re_to_parse_queue_id to parse queue id in the first firework. (e.g. '<([0-9]+)>' on GRC)"
        firework["queue_stdout_file_prefix"] = firework.get("queue_stdout_file_prefix", "")
        firework["queue_stdout_file_suffix"] = firework.get("queue_stdout_file_suffix", "")
        firework["queue_stderr_file_prefix"] = firework.get("queue_stderr_file_prefix", "")
        firework["queue_stderr_file_suffix"] = firework.get("queue_stderr_file_suffix", "")
        pref_suf_sum = firework["queue_stdout_file_prefix"] + firework["queue_stdout_file_suffix"]
        pref_suf_sum += firework["queue_stderr_file_prefix"] + firework["queue_stderr_file_suffix"]
        if pref_suf_sum == "":
            print("Error: must specify at least one of the tags below in the first firework:")
            print("\t\tqueue_stdout_file_prefix, queue_stdout_file_suffix, queue_stderr_file_prefix, queue_stderr_file_suffix")
            raise Exception("See above for the error information.")
         
        firework["job_name"] = firework.get("job_name", "")
        
        if "vasp.out" not in firework.keys():
            print("Error: vasp.out must be specified in the first firework")
            print("\t\tIn the job submission script,")
            print("\t\t\t\t-If vasp_cmd is 'mpirun -n 16 vasp_std > out', then vasp.out = out")
            print("\t\t\t\t-If vasp_cmd is 'mpirun -n 16 vasp_ncl', then vasp.out=vasp.out")
            raise Exception("Error: vasp.out must be specified in the first firework")
        
        firework["force_gamma"] = firework.get("force_gamma", "No").lower()
        firework["2d_system"] = firework.get("2d_system", "No").lower()
        firework["sort_structure"] = firework.get("sort_structure", "Yes").lower()
        firework["preview_vasp_inputs"] = firework.get("preview_vasp_inputs", "No").lower()
        for tag in ["force_gamma", "2d_system", "sort_structure", "preview_vasp_inputs"]:
            firework[tag] = True if 'y' in firework[tag] else False
        if firework["preview_vasp_inputs"]:
            print("preview_vasp_inputs has been obsolete. Reset it to False|No")
            print("The best way to check whether your HTC_calculation_setup works is to feed a cheap|small system to it, and see if it really works.")
           
        #If class ProcessPoolExecutor is called for parallel computing, 'max_workers' defines the max number of processes which can be deployed.
        #If this is not the case, 'max_workers' should not be provided and defaults to None
        #Note that we do not check if explicitly setting 'max_workers' is right. The htc main script will do this job.
        if "max_workers" in firework.keys():
            firework["max_workers"] = int(firework["max_workers"])
        else:
            firework["max_workers"] = None
                    
        #set the calculation folder, structure folder, max_running_job
        if "cal_folder" not in firework.keys():
            firework["cal_folder"] = os.path.join(os.getcwd(), "cal_folder")
                
        assert "structure_folder" in firework.keys(), "Error: Must specify tag 'structure_folder' containing to-be-calculated structures in the first firework."
        assert os.path.isdir(firework["structure_folder"]), "Error: The directory specified by tag 'structure_folder' in the first firework below does not exist:\n\t\t{}".format("structure_folder")

        firework["max_running_job"] = int(firework.get("max_running_job", 30))
        assert firework["max_running_job"] >= 0, "tag max_running_job must be 0 or a positive integer."
        
        #set incar_template, valid_incar_tags
        incar_template = []
        if "incar_template" in firework.keys():
            assert os.path.isfile(firework["incar_template"]), "Fail to find a file specified by tag incar_template"
            with open(firework["incar_template"], "r") as incar_template_f:
                incar_template = [incar_tag.split("#")[0].split("=")[0].strip().upper() for incar_tag in incar_template_f]
            for incar_tag in incar_template:
                if incar_tag != "":
                    assert incar_template.count(incar_tag) == 1,                     "You set {} more than once in {}. Pls remove the duplica".format(incar_tag, firework["incar_template"])
        if len(incar_template) <= 2: 
            firework["incar_template_list"] = incar_template
        else:
            firework["incar_template_list"] = [tag_1 for tag_1, tag_2 in zip(incar_template[:-1], incar_template[1:]) if tag_1 != "" or tag_2 != ""]
            
        
        valid_incar_tags = []
        if "valid_incar_tags" in firework.keys():
            assert os.path.isfile(firework["valid_incar_tags"]), "Fail to find a file specified by tag valid_incar_tags"
            with open(firework["valid_incar_tags"], "r") as valid_incar_tags_f:
                valid_incar_tags = [incar_tag.split("#")[0].split("=")[0].strip().upper() for incar_tag in valid_incar_tags_f if incar_tag.strip()]
            for incar_tag in valid_incar_tags:
                assert valid_incar_tags.count(incar_tag) == 1,                 "You set {} more than once in {}. Pls reomve the duplica".format(incar_tag, firework["valid_incar_tags"])
        firework["valid_incar_tags_list"] = valid_incar_tags
        
        #htc_input_backup
        firework["htc_input_backup"] = firework.get("htc_input_backup", "")
        firework["htc_input_backup"] = [htc_input.strip() for htc_input in firework["htc_input_backup"].split(",") if htc_input.strip()]
        for htc_input in firework["htc_input_backup"]:
            assert os.path.isfile(os.path.join(current_directory, htc_input)) or os.path.isdir(os.path.join(current_directory, htc_input)),             "Make sure that {} is a file or folder, and exists under HTC root directory ({})".format(htc_input, current_directory)
        firework["htc_input_backup_loc"] = firework.get("htc_input_backup_loc", "htc_input_backup_folder")
        
        try:
            firework["max_no_of_ready_jobs"] = int(firework.get("max_no_of_ready_jobs", 50))
            assert firework["max_no_of_ready_jobs"] > 0
        except:
            raise Exception("\nmax_no_of_ready_jobs in step 1 defines the maximum number of jobs tagged by __ready__ or __prior_ready__. It should be a positive integer.\n")
            
        
        #define signal files with which jobs are examined on the fly just like running jobs.
        jobs_treated_like_running_jobs = []
        firework["job_folder_list_treated_like_running_folder_list"] = []
        for job in firework.get("jobs_treated_like_running_jobs", "").split(","):
            job = job.strip()
            if job:
                assert job.startswith("__") and job.endswith("__"), "Error in step 1: The signal file name provided to 'jobs_treated_like_running_jobs' does not follow the signal file format, i.e., starting and ending with a double underscore: {}".format(job)
                jobs_treated_like_running_jobs.append(job)
                firework["job_folder_list_treated_like_running_folder_list"].append(job.strip("_") + "_folder_list")
        firework["jobs_treated_like_running_jobs"] = jobs_treated_like_running_jobs
    #return Read_Only_Dict.from_dict(firework)
    
    return firework


# In[9]:


if __name__ == "__main__":
    #wf_1 = parse_calculation_workflow("HTC_calculation_setup_file")
    wf_2 = parse_calculation_workflow("HTC_calculation_setup_folder", HTC_lib_loc=".")
    #print(wf_1 == wf_2)

