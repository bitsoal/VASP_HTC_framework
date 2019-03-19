
# coding: utf-8

# # created on Feb 18 2018

# In[1]:


import os


# In[2]:


class Read_Only_Dict(dict):
    def __init__(self, *args, **kwargs):
        super(Read_Only_Dict, self).__init__(*args, **kwargs)
        
    def __setitem__(self, key, value):
        raise Exception("{} instance is read-only and cannot be changed!".format(self.__class__.__name__))
    
    def __delitem__(self, key):
        raise Exception("{} instance is read-only and cannot be changed!".format(self.__class__.__name__))
        
    def update(self, *args, **kwargs):
        raise Exception("{} instance is read-only and cannot be changed!".format(self.__class__.__name__))
    
    @classmethod
    def from_dict(cls, dictionary):
        read_only_dictionary = {}
        for key, value in dictionary.items():
            if isinstance(value, list):
                value = tuple(value)   
            elif isinstance(value, dict):
                value = Read_Only_Dict.from_dict(value)
                
            read_only_dictionary[key] = value
            
        return Read_Only_Dict(**read_only_dictionary)


# In[3]:


def parse_calculation_workflow(filename="Calculation_setup"):
    """
    the input file describes a sequence of DFT calculations and modifications of vasp input files before calculations.
    """
    
    workflow = []
    
    with open(filename, "r") as f:
        lines = [line.strip() for line in f if line.strip()]
    
    firework_block_list = []
    for line in lines:
        line = line.split("#")[0].strip()
        if line:
            if line.startswith("**start"):
                firework_block_list.append([])
            else:
                if not line.startswith("**end"):
                    firework_block_list[-1].append(line)
    firework_block_list = [block for block in firework_block_list if block]
    
    firework_hierarchy_dict = {}
    for firework_block_ind, firework_block in enumerate(firework_block_list):
        step_no = firework_block_ind+1
        firework = parse_firework_block(block_str_list=firework_block, step_no=step_no)
        workflow.append(firework)
        if step_no == 1:
            firework_hierarchy_dict["-1"] = [firework["firework_folder_name"]]
        else:
            if firework["copy_which_step"] == -1:
                prev_firework_folder_name = "-1"
            else:
                prev_firework_folder_name = workflow[firework["copy_which_step"]-1]["firework_folder_name"]
            
            if prev_firework_folder_name not in firework_hierarchy_dict.keys():
                firework_hierarchy_dict[prev_firework_folder_name] = [firework["firework_folder_name"]]
            else:
                firework_hierarchy_dict[prev_firework_folder_name].append(firework["firework_folder_name"])
    
    firework_hierarchy_dict, workflow = reduce_additional_cal_dependence_and_correct_hierarchy(workflow, firework_hierarchy_dict)
    
    workflow[0]["firework_hierarchy_dict"] = firework_hierarchy_dict
    
    workflow = [Read_Only_Dict.from_dict(firework) for firework in workflow]
    
    #import pprint
    #pprint.pprint(workflow)
    
    import json
    with open("Parsed_HTC_setup.JSON", "w") as f:
        json.dump(workflow, f, indent=1)
                    
    return workflow              


# In[4]:


def cal_calculation_sequence_of_all_fireworks(firework_hierarchy_dict):
    """
    Calculate the calculation sequence of all fireworks. The sequence is represented by integers. The smaller the integer of a firework is,
            the earlier that firework starts. The first firework is labelled by 1
    Example: Suppose step 2 copies from (depends on ) step 1, and step 3 and 4 copy from (depend on) step 2. The calculation sequence should be:
            step 1 first starts and then step 2. Following step 2, step 3 and 4 start simultaneously.
            So step 1 <--> 1
                step 2 <--> 2
                step 3, 4 <--> 3
    """
    cal_sequence_dict = {}
    for firework_folder_name in firework_hierarchy_dict["-1"]:
        cal_sequence_dict[firework_folder_name] = 1
    firework_hierarchy_key_list = firework_hierarchy_dict.keys()
    current_firework_list = firework_hierarchy_dict["-1"]
    current_level = 1
    while True:
        next_firework_list = []
        for current_firework in current_firework_list:
            if current_firework in firework_hierarchy_key_list:
                next_firework_list.extend(list(firework_hierarchy_dict[current_firework]))
        for next_firework in next_firework_list:
            cal_sequence_dict[next_firework] = current_level + 1
        if next_firework_list == []:
            break
        else:
            current_firework_list = next_firework_list
            current_level += 1
    #print(cal_sequence_dict)
    return cal_sequence_dict


# In[5]:


def reduce_additional_cal_dependence_and_correct_hierarchy(workflow, firework_hierarchy_dict):
    """
    Reduce the redundant job dependence relations and correct the firework hierarchy. 
    Example: Suppose that both step 5 and step 3 copy from step 2, and step 5 additionally depends on the calculation outputs of step 3.
                In this case, step 5 enssentially should start after step 3, while in the hierarchy relation based on copy_from_which,
                step 5 is set to start after step 2. So to determine if step 5 should start, we just need to check if step 3 completes.
    """
    import copy
    new_hierarchy_dict = copy.deepcopy(firework_hierarchy_dict)
    for firework_ind, firework in enumerate(workflow):
        if firework["additional_cal_dependence"]==[] or firework["step_no"] == 1:
            continue
            
        cal_sequence_dict = cal_calculation_sequence_of_all_fireworks(new_hierarchy_dict)
        #import pprint
        #pprint.pprint(cal_sequence_dict)
        #pprint.pprint(new_hierarchy_dict)
        copy_step_folder_name = workflow[firework["copy_which_step"]-1]["firework_folder_name"]
        latest_dependent_firework_cal_level = 0
        latest_dependent_firework_list = []
        for dependent_firework_step_no in firework["additional_cal_dependence"]:
            dependent_firework_folder_name = workflow[dependent_firework_step_no-1]["firework_folder_name"]
            cal_level = cal_sequence_dict[dependent_firework_folder_name]
            if cal_level > latest_dependent_firework_cal_level:
                latest_dependent_firework_cal_level = cal_level
                latest_dependent_firework_list = [dependent_firework_folder_name]
            elif cal_level == latest_dependent_firework_cal_level:
                latest_dependent_firework_list.append(dependent_firework_folder_name)
        copy_step_cal_level = cal_sequence_dict[copy_step_folder_name]
        if copy_step_cal_level < latest_dependent_firework_cal_level:
            for current_step_folder_name, next_step_folder_name_list in new_hierarchy_dict.items():
                if firework["firework_folder_name"] in next_step_folder_name_list:
                    new_hierarchy_dict[current_step_folder_name].remove(firework["firework_folder_name"])
                    break
            new_dependent_firework_name_in_hierarchy = latest_dependent_firework_list.pop()
            if new_dependent_firework_name_in_hierarchy in new_hierarchy_dict.keys():
                new_hierarchy_dict[new_dependent_firework_name_in_hierarchy].append(firework["firework_folder_name"])
            else:
                new_hierarchy_dict[new_dependent_firework_name_in_hierarchy] = [firework["firework_folder_name"]]
        workflow[firework_ind]["additional_cal_dependence"] = latest_dependent_firework_list
        
    return new_hierarchy_dict, workflow
        
        
        
        
        


# In[7]:


def parse_firework_block(block_str_list, step_no):
    """
    parse the calculation setup for a firework.
    """
    #available htc tags
    htc_tag_list = ["structure_folder", "cal_folder", "step_no", "cal_name", "copy_from_prev_cal", 
                    "move_from_prev_cal", "contcar_to_poscar", "copy_which_step", "additional_cal_dependence",
                    "remove_after_cal", "extra_copy", "final_extra_copy", "comment_incar_tags", "remove_incar_tags",
                    "partial_charge_cal", "which_step_to_read_cbm_vbm", "EINT_wrt_CBM", "EINT_wrt_VBM", "bader_charge",
                    "ldau_cal", "ldau_u_j_table", "kpoints_type", "denser_kpoints", "reciprocal_density", "kpoints_line_density",
                    "intersections", "force_gamma", "2d_system", "sort_structure", "max_ionic_step", "user_defined_cmd", 
                    "final_user_defined_cmd", "user_defined_postprocess_cmd", "sub_dir_cal", "sub_dir_cal_cmd", "preview_vasp_inputs",
                    "job_submission_script", "job_submission_command", "job_name", "max_running_job", "where_to_parse_queue_id",
                    "re_to_parse_queue_id", "job_query_command", "job_killing_command", "queue_stdout_file_prefix", "queue_stdout_file_suffix",
                    "queue_stderr_file_prefix", "queue_stderr_file_suffix", "vasp.out"]
    htc_tag_list = [tag.lower() for tag in htc_tag_list]
    
    
    firework = {"new_incar_tags":{}}
    
    for line in block_str_list:
        if line.count("=") != 1 and "*begin(add_new_incar_tags)" not in line.lower() and "*end(add_new_incar_tags)" not in line.lower():
            raise Exception("Each line is supposed to have only one '=', while the line below has {}\n{}\n".format(line.count("="), line))
    
    incar_subblock = False
    for line in block_str_list:            
        if line.lower().startswith("*begin(add_new_incar_tags)"):
            incar_subblock = True
        elif line.lower().startswith("*end(add_new_incar_tags)"):
            incar_subblock = False
        else:
            tag, value = [item.strip() for item in line.split("=")]
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
            print("*"*20)
            print("step_no of firework {} must be set to {}.".format(step_no, step_no))
            print("Please change step_no to {} in the line below:".format(step_no))
            print("{}".format(line))
            print('*'*20)
            print("\n")
            raise Exception("See above for the error information")
    else:
        raise Exception("tag step_no is required for every firework. Please set step_n={} for firework {}".format(step_no, step_no))
    assert "cal_name" in firework.keys(), "Error: you should name each firework through tag cal_name!"
    firework["firework_folder_name"] = "step_" + str(step_no) + "_" + firework["cal_name"].replace(" ", "_")
         
        
    #2. tags involved in copying
    firework["copy_from_prev_cal"] = firework.get("copy_from_prev_cal", "")
    firework["copy_from_prev_cal"] = [item.strip() for item in firework["copy_from_prev_cal"].split(",") if item.strip()]
    if "copy_which_step" in firework.keys():
        firework["copy_which_step"] = int(firework["copy_which_step"])
        if firework["copy_which_step"] not in [-1]+[i for i in range(1, step_no)]:
            raise Exception("step {}: tag copy_which_step should be >=1 and <{}, or ==-1".format(step_no, step_no))
    else:
        if step_no == 1:
            firework["copy_which_step"] = -1
        else:
            firework["copy_which_step"] = step_no -1
    for tag in ["extra_copy", "final_extra_copy"]:
        firework[tag] = firework.get(tag, "")
        file_list = [file_.strip() for file_ in firework[tag].split(",") if file_.strip()]
        for file_ in file_list:
            assert os.path.isfile(file_), "the file below listed in tag {} doesn't exist.\n\t\t\t{}\n".format(tag, file_)
        firework[tag] = file_list

       
    
    #3. tags involved in moving, removing and renaming
    for tag in ["move_from_prev_cal", "remove_after_cal"]:
        firework[tag] = firework.get(tag, "")
        firework[tag] = [item.strip() for item in firework[tag].split(",") if item.strip()]
    firework["contcar_to_poscar"] = firework.get("contcar_to_poscar", "No").lower()
    firework["contcar_to_poscar"] = True if "y" in firework["contcar_to_poscar"] else False
               
        
    #4. INCAR related tags
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
    firework["which_step_to_read_cbm_vbm"] = int(firework.get("which_step_to_read_cbm_vbm", -1))
    if firework["partial_charge_cal"]:
        assert 0<firework["which_step_to_read_cbm_vbm"]<step_no, "For step {}, which_step_to_read_cbm_vbm should be >0 and <{}".format(step_no, step_no)
        assert firework["eint_wrt_vbm"] != None or firework["eint_wrt_cbm"] != None,         "For step {}, since the partial charge calculation is activated by partial_charge_cal, eith EINT_wrt_CBM or EINT_wrt_VBM shoud be set".format(step_no)
        
    firework["ldau_cal"] = firework.get("ldau_cal", "no").lower()
    if "y" in firework["ldau_cal"]:
        firework["ldau_cal"] = True
        assert os.path.isfile(firework["ldau_u_j_table"]), "Step {}: Since you want to carry out LDA+U calculation, you need to provide a file containing Hubbard U and J by tag ldau_u_j_table".format(step_no)
    else:
        firework["ldau_cal"] = False
        
        
    #5. KPOINTS related tags
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
        
       
    
    #6. cmd defined by users
    for tag in ["user_defined_cmd", "final_user_defined_cmd", "user_defined_postprocess_cmd"]:
        if tag in firework.keys(): 
            firework[tag] = [cmd_.strip() for cmd_ in firework[tag].split(",") if cmd_.strip()]
        else:
            firework[tag] = []
      

    #7. sub-directory calculation specification
    firework["sub_dir_cal"] = firework.get("sub_dir_cal", "no").lower()
    firework["sub_dir_cal"] = True if 'y' in firework["sub_dir_cal"] else False
    if firework["sub_dir_cal"]:
        assert "sub_dir_cal_cmd" in firework.keys(),         "step %d: Because the sub-directory calculation is invoked (tag: 'sub_dir_cal'), you must specify 'sub_dir_cal_cmd'" % step_no
        firework["sub_dir_cal_cmd"] = [cmd_.strip() for cmd_ in firework["sub_dir_cal_cmd"].split(",") if cmd_.strip()]
       
    #8. structural optimization related tags
    firework["max_ionic_step"] = int(firework.get("max_ionic_step", -1))
    assert firework["max_ionic_step"] >= 1 or firework["max_ionic_step"] == -1, "tag max_ionic_step should be set to a positive integer or -1 (default) to activate or deactivate this tag, respectively."
        
    # job submissions
    assert "job_submission_script" in firework.keys(), "Error: must specify job_submission_script for every firework."
    assert os.path.isfile(firework["job_submission_script"]), "Step {}: the specified job submission script does not exist.".format(step_no)
    assert "job_submission_command" in firework.keys(), "Error: must specify how to submit a job for every firework."
    
    #8. additional calculation dependence besides those specified by copy_which_step
    if "additional_cal_dependence" in firework.keys():
        additional_dependence_list = [int(job_step_no) for job_step_no in firework["additional_cal_dependence"].strip().split(",")]
        for job_step_no in additional_dependence_list:
            assert 1<=job_step_no<firework["step_no"], "For step {}, cal_dependence should be >=1 and < {}".format(step_no, step_no)
        firework["additional_cal_dependence"] = additional_dependence_list
    else:
        firework["additional_cal_dependence"] = []
    
      
        
    #tags only required for the first firework
    if step_no == 1:
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
            
        
                
                    
        #set the calculation folder, structure folder, max_running_job
        if "cal_folder" not in firework.keys():
            firework["cal_folder"] = os.path.join(os.getcwd(), "cal_folder")
                
        assert "structure_folder" in firework.keys(), "Error: Must specify tag 'structure_folder' containing to-be-calculated structures in the first firework."
        assert os.path.isdir(firework["structure_folder"]), "Error: The directory specified by tag 'structure_folder' in the first firework below does not exist:\n\t\t{}".format("structure_folder")

        firework["max_running_job"] = int(firework.get("max_running_job", 30))
        assert firework["max_running_job"] >= 0, "tag max_running_job must be 0 or a positive integer."
                
                   
    #return Read_Only_Dict.from_dict(firework)
    return firework


# parse_calculation_workflow("HTC_calculation_setup_file")

# workflow[4]
