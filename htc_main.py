
# coding: utf-8

# In[1]:


import os, sys, time
import pprint

HTC_lib_path = #where do you put this HTC_lib
cif_file_folder = #where are cif files
cal_folder = #where to do the VASP calculations
HTC_calculation_setup = #where is file HTC_calculation_setup

if HTC_lib_path not in sys.path:
    sys.path.append(HTC_lib_path)

if os.path.join(HTC_lib_path, "HTC_lib") not in sys.path:
    sys.path.append(os.path.join(HTC_lib_path, "HTC_lib"))

from HTC_lib.Utilities import get_time_str
from HTC_lib.Parse_calculation_workflow import parse_calculation_workflow
from HTC_lib.Preprocess_and_Postprocess import pre_and_post_process
from HTC_lib.Check_and_update_calculation_status import check_calculations_status
from HTC_lib.Check_and_update_calculation_status import update_running_jobs_status
from HTC_lib.Check_and_update_calculation_status import update_killed_jobs_status
from HTC_lib.Submit_and_Kill_job import submit_jobs, kill_error_jobs


# In[2]:


if __name__ == "__main__":
    workflow = parse_calculation_workflow(HTC_calculation_setup_file)

    while True:
        cif_file_list = os.listdir(cif_file_folder)
        for cif_file in cif_file_list:
            cif_file_path = os.path.join(cif_file_folder, cif_file)
            pre_and_post_process(cif_filename=cif_file_path, cal_folder=cal_folder, workflow=workflow)

        cal_status = check_calculations_status(cal_folder=cal_folder)
        update_running_jobs_status(cal_status["running_folder_list"], workflow=workflow)
        update_killed_jobs_status(cal_status["killed_folder_list"], workflow=workflow)
        cal_status = check_calculations_status(cal_folder=cal_folder)
        ready_job_list = cal_status["prior_ready_folder_list"] + cal_status["ready_folder_list"]
        submit_jobs(ready_jobs=ready_job_list, workflow=workflow,max_jobs_in_queue=30)
        kill_error_jobs(error_jobs=cal_status["error_folder_list"], workflow=workflow)
        cal_status = check_calculations_status(cal_folder=cal_folder)
        
        #with open("htc_job_status.txt", "w") as f:
        #    f.write("{}\n".format(get_time_str()))
        #    for status, job_list in cal_status.items():
        #        f.write("\n{}:\n".format(status))
        #        for job in job_list:
        #            f.write("\t{}\n".format(job))

        print("\n{}".format(get_time_str()))
        pprint.pprint(cal_status)
        time.sleep(60)

