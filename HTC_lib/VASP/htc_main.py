#!/usr/bin/env python
# coding: utf-8

# In[1]:


raise Exception("htc_main.py will be updated later. Now you can try the parallel version, i.e. htc_main_mpi.py")

import os, sys, time, pprint, copy

##############################################################################################################
##DO NOT change this part.
##../setup.py will update this variable
HTC_package_path = "C:/Users/tyang/Documents/Jupyter_workspace/HTC/python_3"
assert os.path.isdir(HTC_package_path), "Cannot find this VASP_HTC package under {}".format(HTC_package_path)
if HTC_package_path not in sys.path:
    sys.path.append(HTC_package_path)
##############################################################################################################


from HTC_lib.VASP.Miscellaneous.Utilities import get_time_str
from HTC_lib.VASP.Miscellaneous.Backup_HTC_input_files import backup_htc_input_files, backup_a_file
from HTC_lib.VASP.Miscellaneous.change_signal_file import change_signal_file
from HTC_lib.VASP.Miscellaneous.Cal_status_dictionary_operation import Cal_status_dict_operation, divide_a_list_evenly

from HTC_lib.VASP.Preprocess_and_Postprocess.Parse_calculation_workflow import parse_calculation_workflow
from HTC_lib.VASP.Preprocess_and_Postprocess.new_Preprocess_and_Postprocess import pre_and_post_process
from HTC_lib.VASP.Job_Management.Check_and_update_calculation_status import check_calculations_status, update_job_status
from HTC_lib.VASP.Job_Management.Submit_and_Kill_job import submit_jobs, kill_error_jobs


# In[2]:


def read_workflow():
    workflow = []
    if os.path.isfile("HTC_calculation_setup_file"):
        workflow.append(parse_calculation_workflow("HTC_calculation_setup_file", HTC_lib_loc=HTC_package_path))
    if os.path.isdir("HTC_calculation_setup_folder"):
        workflow.append(parse_calculation_workflow("HTC_calculation_setup_folder", HTC_lib_loc=HTC_package_path))
    
    if workflow == []:
        raise Exception("Error: No HTC_calculation_setup_file or HTC_calculation_setup_folder under {}".format(os.getcwd()))
    elif len(workflow) == 1:
        workflow = workflow[0]
    else:
        for wf_ind in range(len(workflow[0])):
            assert workflow[0][wf_ind] == workflow[1][wf_ind], "Error: the {}st|nd|th firework/calculation setup parsed from 'HTC_calculation_setup_file' is not identical to that from 'HTC_calculation_setup_folder'".format(wf_ind+1)
        workflow = workflow[0]
        
    return workflow


# In[4]:


def backup_htc_files(workflow):
    htc_input_backup_loc = workflow[0]["htc_input_backup_loc"]
    other_htc_inputs = ["htc_main.py"] + list(workflow[0]["htc_input_backup"])
    if os.path.isfile("HTC_calculation_setup_file"):
        backup_a_file(src_folder=".", src_file="HTC_calculation_setup_file", dst_folder=htc_input_backup_loc, overwrite=False)
    else:
        other_htc_inputs.append("HTC_calculation_setup_folder")
    backup_htc_input_files(src_folder=".", file_or_folder_list=other_htc_inputs, dst_folder=htc_input_backup_loc)    


# In[2]:


if __name__ == "__main__":
    workflow = read_workflow()
    backup_htc_files(workflow=workflow)
    
    structure_file_folder = workflow[0]["structure_folder"]
    cal_folder = workflow[0]["cal_folder"]
    max_running_job = workflow[0]["max_running_job"]
    
    if not os.path.isdir(cal_folder):
        os.mkdir(cal_folder)

    main_dir = os.getcwd()
    stop_file_path = os.path.join(main_dir, "__stop__")
    htc_job_status_file_path = os.path.join(main_dir, "htc_job_status.json")
    update_now_file_path = os.path.join(main_dir, "__update_now__")
    change_signal_file_path = os.path.join(main_dir, "__change_signal_file__")
    update_input_file_path = os.path.join(main_dir, "__update_input__")
    
    no_of_same_cal_status, cal_status_0 = 0, {}
    while True:
        if os.path.isfile(stop_file_path):
            print(">>>Detect file __stop__ in {}\n ---->stop this program.".format(main_dir))
            break
        
        update_job_status(cal_folder=cal_folder, workflow=workflow)
        cal_status = check_calculations_status(cal_folder=cal_folder, workflow=workflow)
        max_no_of_ready_jobs = workflow[0]["max_no_of_ready_jobs"] - len(cal_status["prior_ready_folder_list"]) - len(cal_status["ready_folder_list"])
        if os.path.isfile(stop_file_path): break
        for structure_file in os.listdir(structure_file_folder):
            #pre_and_post_process returns the number of prepared calculations
            max_no_of_ready_jobs -= pre_and_post_process(structure_file, structure_file_folder, cal_folder=cal_folder, workflow=workflow)
            if os.path.isfile(update_now_file_path):
                cal_status = check_calculations_status(cal_folder=cal_folder, workflow=workflow)
                write_cal_status(cal_status, htc_job_status_file_path)
                os.remove(update_now_file_path)
            if os.path.isfile(change_signal_file_path):
                cal_status = check_calculations_status(cal_folder=cal_folder,workflow=workflow)
                write_cal_status(cal_status, htc_job_status_file_path)
                os.remove(change_signal_file_path)    
            if max_no_of_ready_jobs < 1:
                cal_status = check_calculations_status(cal_folder=cal_folder, workflow=workflow)
                write_cal_status(cal_status, htc_job_status_file_path)
                max_no_of_ready_jobs = workflow[0]["max_no_of_ready_jobs"] - len(cal_status["ready_folder_list"]) - len(cal_status["prior_ready_folder_list"])
                del max_no_of_ready_jobs
                if max_no_of_ready_jobs < 1: break
            if os.path.isfile(stop_file_path): break
        if os.path.isfile(stop_file_path): continue
            
        cal_status = check_calculations_status(cal_folder=cal_folder, workflow=workflow)
        submit_jobs(cal_jobs_status=cal_status, workflow=workflow, max_jobs_in_queue=max_running_job)
        cal_status = check_calculations_status(cal_folder=cal_folder, workflow=workflow)      
        
        write_cal_status(cal_status, htc_job_status_file_path)
                        
        #check if all calculations are complete. If this is the case, stop. At the end, all calculations should be labeled by signal file __done__, __skipped__, __done_cleaned_analyzed__ and __done_failed_to_clean_analyze__
        no_of_ongoing_jobs = sum([len(job_list) for job_status, job_list in cal_status.items() if job_status not in ["done_folder_list", "skipped_folder_list", "done_cleaned_analyzed_folder_list", "done_failed_to_clean_analyze_folder_list"]])
        if no_of_ongoing_jobs == 0:
            output_str = "All calculations have finished --> Stop this program."
            print(output_str)
            with open(htc_job_status_file_path, "a") as f:
                f.write("\n***" + output_str + "***")
            break
        #If cal_status is unchanged for the 5 consecutive scannings, also stop.
        if cal_status == cal_status_0:
            no_of_same_cal_status += 1
        else:
            cal_status_0 = cal_status
            no_of_same_cal_status = 0
        if no_of_same_cal_status == 1000:
            output_str = "The status of all calculations remains unchanged for around one week --> Stop this program."
            print(output_str)
            with open(htc_job_status_file_path, "a") as f:
                f.write("\n***" + output_str + "***")
            break
        
        #os.chdir(main_dir)
        for i in range(60):
            if os.path.isfile(stop_file_path):
                break  
            elif os.path.isfile(update_now_file_path):
                os.remove(update_now_file_path)
                break
            elif os.path.isfile(change_signal_file_path):
                cal_status = change_signal_file(cal_status, change_signal_file_path)
                write_cal_status(cal_status, htc_job_status_file_path)
                os.remove(change_signal_file_path)
            elif os.path.isfile(update_input_file_path):
                workflow = read_workflow()
                os.remove(update_input_file_path)
                break
            else:
                time.sleep(10)

