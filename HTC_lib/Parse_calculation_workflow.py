
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


# In[16]:


def parse_calculation_workflow(filename="Calculation_setup"):
    """
    the input file describes a sequence of DFT calculations and modifications of vasp input files before calculations.
    """
    
    workflow = []
    
    with open(filename, "r") as f:
        lines = [line.strip() for line in f if line.strip()]
    valid_lines = []
    for line in lines:
        if line.startswith("#"):
            continue
        elif "#" in line:
            valid_lines.append(line.split("#")[0])
        else:
            valid_lines.append(line)
    lines = valid_lines
    
    line_ind, line_ind_max = 0, len(lines)-1
    while line_ind <= line_ind_max:
        line = lines[line_ind].lower()
        line_ind += 1
            
        if line.startswith("**start"):
            firework = {}
        elif line.startswith("**end"):
            assert "step_no" in firework.keys(), "Error: Must specify tag step_no starting from 1."
            firework["step_no"] = int(firework["step_no"])
            if firework["step_no"] > 1:
                if firework["step_no"] != workflow[-1]["step_no"]+1:
                    print("the step_no of the nearest previous step must be 1 less than the step_no of the current step.")
                    print("e.g.")
                    print("\t\tfor the first firework, step_no=1")
                    print("\t\tfor the second firework, step_no=2")
                    print("\t\tfor the third firework, step_no=3")
                    print("\t\tfor the fourth firework, step_no=4")
                    raise Exception("See above for the error information")
                    
            assert "cal_name" in firework.keys(), "Error: you should name each calculation through tag cal_name!"
            firework["firework_folder_name"] = "step_" + str(firework["step_no"]) + "_" + firework["cal_name"].replace(" ", "_")
            
            if firework["step_no"] == 1:
                #Some tags must be specified in the first firework and they will be used for all fireworks.
                #firework["initial_vasp_input_set"] = firework.get("initial_vasp_input_set", "pymatgen")
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
                
                if "vasp.out" not in firework.keys():
                    print("Error: vasp.out must be specified in the first firework")
                    print("\t\tIn the job submission script,")
                    print("\t\t\t\t-If vasp_cmd is 'mpirun -n 16 vasp_std > out', then vasp.out = out")
                    print("\t\t\t\t-If vasp_cmd is 'mpirun -n 16 vasp_ncl', then vasp.out=vasp.out")
                    raise Exception("Error: vasp.out must be specified in the first firework")
                
                if "force_gamma" in firework.keys():
                    if "y" in firework["force_gamma"].lower():
                        firework["force_gamma"] = True
                    else:
                        firework["force_gamma"] = False
                else:
                    firework["force_gamma"] = False
                    
                if "2d_system" in firework.keys():
                    if "y" in firework["2d_system"].lower():
                        firework["2d_system"] = True
                    else:
                        firework["2d_system"] = False
                else:
                    firework["2d_system"] = False
                    
                if "sort_structure" in firework.keys():
                    if "n" in firework["sort_structure"].lower():
                        firework["sort_structure"] = False
                    else:
                        firework["sort_structure"] = True
                else:
                    firework["sort_structure"] = True
                   
                
            firework["copy_from_prev_cal"] = firework.get("copy_from_prev_cal", [])
            firework["move_from_prev_cal"] = firework.get("move_from_prev_cal", [])
            firework["contcar_to_poscar"] = firework.get("contcar_to_poscar", "no")
            if "y" in firework["contcar_to_poscar"].lower():
                firework["contcar_to_poscar"] = True
            else:
                firework["contcar_to_poscar"] = False
            firework["remove_after_cal"] = firework.get("remove_after_cal", [])
            firework["new_incar_tags"] = firework.get("new_incar_tags", {})
            firework["comment_incar_tags"] = firework.get("comment_incar_tags", [])
            firework["remove_incar_tags"] = firework.get("remove_incar_tags", [])
            firework["copy_from_prev_cal"] = firework.get("copy_from_prev_cal", [])
            if len(workflow) == 0:
                firework["copy_which_step"] = -1
            else:
                firework["copy_which_step"] = int(firework.get("copy_which_step", workflow[-1]["step_no"]))
            
            firework["extra_copy"] = firework.get("extra_copy", [])
            firework["final_extra_copy"] = firework.get("final_extra_copy", [])
            
            
            if "kpoints_type" not in firework.keys():
                print("\nYou don't set tag kpoints_type for step {}".format(firework["step_no"]))
                print("kpoints_type option: MPRelaxSet, MPStaticSet, MPNonSCFSet_line, MPNonSCFSet_uniform")
                print("\t\tFor MPRelaxSet, MPStaticSet, float denser_kpoints (default int 1) can be set to make kpoints denser")
                print("\t\tFor MPNonSCFSet_line, kpoints_line_density can be set. Default: 40")
                print("\t\tFor MPNonSCFSet_uniform, reciprocal_density can be set. Default: 1000\n")
                raise Exception("See above for the error information")
            elif firework["kpoints_type"] not in ["MPRelaxSet", "MPStaticSet", "MPNonSCFSet_line", "MPNonSCFSet_uniform", "Line-mode"]:
                raise Exception("kpoints_type must be one of MPRelaxSet, MPStaticSet, MPNonSCFSet_line, MPNonSCFSet_uniform or Line-mode @ step {}".format(firework["step_no"]))
                
            firework["reciprocal_density"] = int(firework.get("reciprocal_density", 1000))
            firework["kpoints_line_density"] = int(firework.get("kpoints_line_density", 40))
            firework["intersections"] = int(firework.get("intersections", 20))
            

            
            firework["denser_kpoints"] = firework.get("denser_kpoints", (1, 1, 1))
            if isinstance(firework["denser_kpoints"], str):
                firework["denser_kpoints"] = [float(k_multiple) for k_multiple in firework["denser_kpoints"].split(",") if k_multiple.strip()]
                assert len(firework["denser_kpoints"])==3, "Error: tag denser_kpoints must be three float/integer numbers separated by commas at step {}.".format(firework["step_no"])
            
            assert "job_submission_script" in firework.keys(), "Error: must specify job_submission_script for every calculation."
            assert "job_submission_command" in firework.keys(), "Error: must specify how to submit job for every calculation."
            
            firework = Read_Only_Dict.from_dict(firework)
            workflow.append(firework)
        elif line.startswith("*begin(add_new_incar_tags)"):
            new_incar_tags = {}
            while True:
                line = lines[line_ind]
                line_ind += 1
                if line.lower().startswith("*end(add_new_incar_tags)"):
                    firework["new_incar_tags"] = new_incar_tags
                    break
                        
                items = line.split("=")
                items = [item.strip() for item in items]
                if len(items) == 2:
                    new_incar_tags[items[0]] = items[1]
        else:
            items = lines[line_ind-1].split("=")
            items = [item.strip() for item in items]
            if "comment_incar_tags" in line:
                tags = [tag.strip().upper() for tag in items[1].split(",")]
                firework["comment_incar_tags"] = tags
            elif "remove_incar_tags" in line:
                tags = [tag.strip().upper() for tag in items[1].split(",")]
                firework["remove_incar_tags"] = tags
            elif "remove_after_cal" in line:
                files = [file.strip() for file in items[1].split(",")]
                firework["remove_after_cal"] = files
            elif "move_from_prev_cal" in line:
                files = [file.strip() for file in items[1].split(",")]
                firework["move_from_prev_cal"] = files
            elif "copy_from_prev_cal" in line:
                files = [file.strip() for file in items[1].split(",")]
                firework["copy_from_prev_cal"] = files
            elif "final_extra_copy" in line:
                files = [file.strip() for file in items[1].split(",")]
                for file in files:
                    assert os.path.isfile(file), "Error: file {} specifized in tag final_extra_copy does not exists.".format(file)
                firework["final_extra_copy"] = files
            elif "extra_copy" in line:
                files = [file.strip() for file in items[1].split(",")]
                for file in files:
                    assert os.path.isfile(file), "Error: file {} specifized in tag extra_copy does not exists.".format(file)
                firework["extra_copy"] = files
            elif "kpoints_type" in line:
                firework["kpoints_type"] = items[1]
            else:
                firework[items[0].lower()] = items[1]
                    
    return workflow              


# workflow = parse_calculation_workflow("Calculation_setup_GRC")
# workflow

# workflow[4]
