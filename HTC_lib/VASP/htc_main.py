#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os, sys, time, pprint

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
from HTC_lib.VASP.Preprocess_and_Postprocess.Parse_calculation_workflow import parse_calculation_workflow
from HTC_lib.VASP.Preprocess_and_Postprocess.new_Preprocess_and_Postprocess import pre_and_post_process, preview_HTC_vasp_inputs
from HTC_lib.VASP.Job_Management.Check_and_update_calculation_status import check_calculations_status, update_job_status
from HTC_lib.VASP.Job_Management.Submit_and_Kill_job import submit_jobs, kill_error_jobs


# In[6]:


def write_cal_status(cal_status, filename):
    to_be_written_status_list = ["manual_folder_list", "skipped_folder_list", "error_folder_list", "killed_folder_list", 
                                 "sub_dir_cal_folder_list", "running_folder_list"]
    last_written_status_list = ["vis_folder_list", "prior_ready_folder_list", "ready_folder_list", "done_folder_list"]
    for status_key in cal_status.keys():
        if status_key not in to_be_written_status_list and status_key not in last_written_status_list:
            to_be_written_status_list.append(status_key)
    to_be_written_status_list.extend(last_written_status_list)
    
    with open(filename, "w") as f:
        f.write("\n{}:".format(get_time_str()))
        for status_key in to_be_written_status_list:
            f.write("\n{}:\n".format(status_key))
            for folder in cal_status[status_key]:
                f.write("\t{}\n".format(folder))


# In[2]:


if __name__ == "__main__":
    assert os.path.isfile("HTC_calculation_setup_file"), "Error: No HTC_calculation_setup_file under {}".format(os.getcwd())
    workflow = parse_calculation_workflow("HTC_calculation_setup_file")
    
    #back up htc input files
    htc_input_backup_loc = workflow[0]["htc_input_backup_loc"]
    backup_a_file(src_folder=".", src_file="HTC_calculation_setup_file", dst_folder=htc_input_backup_loc, overwrite=False)
    other_htc_inputs = ["htc_main.py"] + list(workflow[0]["htc_input_backup"])
    backup_htc_input_files(src_folder=".", file_or_folder_list=other_htc_inputs, dst_folder=htc_input_backup_loc)
    
    
    
    structure_file_folder = workflow[0]["structure_folder"]
    cal_folder = workflow[0]["cal_folder"]
    max_running_job = workflow[0]["max_running_job"]
    
    if not os.path.isdir(cal_folder):
        os.mkdir(cal_folder)
    
    if workflow[0]["preview_vasp_inputs"]:
        preview_HTC_vasp_inputs(cif_filename=os.listdir(structure_file_folder)[0], cif_folder=structure_file_folder, workflow=workflow)


    main_dir = os.getcwd()
    no_of_same_cal_status, cal_status_0 = 0, {}
    while not workflow[0]["preview_vasp_inputs"]:
        os.chdir(main_dir)
        if os.path.isfile("__stop__"):
            print(">>>Detect file __stop__ in {}\n ---->stop this program.".format(main_dir))
            break
        
        update_job_status(cal_folder=cal_folder, workflow=workflow)
        for structure_file in os.listdir(structure_file_folder):
            cal_status = check_calculations_status(cal_folder=cal_folder)
            no_of_ready_jobs = len(cal_status["prior_ready_folder_list"]) + len(cal_status["ready_folder_list"])
            if no_of_ready_jobs >= workflow[0]["max_no_of_ready_jobs"]:
                break
            no_of_ready_jobs += pre_and_post_process(structure_file, structure_file_folder, cal_folder=cal_folder, workflow=workflow)
        cal_status = check_calculations_status(cal_folder=cal_folder)
        submit_jobs(cal_jobs_status=cal_status, workflow=workflow, max_jobs_in_queue=max_running_job)
        cal_status = check_calculations_status(cal_folder=cal_folder)      
        
        os.chdir(main_dir)
        write_cal_status(cal_status, "htc_job_status.dat")
                        
        #check if all calculations are complete. If this is the case, stop. At the end, all calculations should be labeled by signal file __done__ or __skipped__
        no_of_ongoing_jobs = sum([len(job_list) for job_status, job_list in cal_status.items() if job_status not in ["done_folder_list", "skipped_folder_list"]])
        if no_of_ongoing_jobs == 0:
            output_str = "All calculations have finished --> Stop this program."
            print(output_str)
            os.chdir(main_dir)
            with open("htc_job_status.dat", "a") as f:
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
            with open("htc_job_status.dat", "a") as f:
                f.write("\n***" + output_str + "***")
            break
        
        for i in range(60):
            if os.path.isfile("__stop__"):
                break
            elif os.path.isfile("__update_now__"):
                os.remove("__update_now__")
                break
            elif os.path.isfile("__change_signal_file__"):
                cal_status = change_signal_file(cal_status, "__change_signal_file__")
                os.remove("__change_signal_file__")
                write_cal_status(cal_status, "htc_job_status.dat")
            else:
                time.sleep(10)

