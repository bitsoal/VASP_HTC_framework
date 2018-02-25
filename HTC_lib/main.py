
# coding: utf-8

# In[1]:


import os, sys, time

if os.path.join(os.getcwd(), "HTC_lib") not in sys.path:
    sys.path.append(os.path.join(os.getcwd(), "HTC_lib/"))

from HTC_lib.Utilities import get_time_str
from HTC_lib.Parse_calculation_workflow import parse_calculation_workflow
from HTC_lib.Preprocess_and_Postprocess import pre_and_post_process
from HTC_lib.Check_and_update_calculation_status import check_calculations_status
from HTC_lib.Check_and_update_calculation_status import update_running_jobs_status
from HTC_lib.Check_and_update_calculation_status import update_killed_jobs_status
from HTC_lib.Submit_and_Kill_job import submit_jobs, kill_error_jobs


# In[2]:


if __name__ == "__main__":
    cif_file_folder = "/lustre/scratch/e0001020/Z_scheme/my_own_Z_scheme_high_throughput/cif_files"
    cal_folder = "/lustre/scratch/e0001020/Z_scheme/my_own_Z_scheme_high_throughput/cal_folder"
    workflow = parse_calculation_workflow("/lustre/scratch/e0001020/Z_scheme/my_own_Z_scheme_high_throughput/Calculation_setup")


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
        submit_jobs(ready_jobs=ready_job_list, workflow=workflow,max_jobs_in_queue=5)
        kill_error_jobs(error_jobs=cal_status["error_folder_list"], workflow=workflow)
        cal_status = check_calculations_status(cal_folder=cal_folder)
        
        import pprint
        print("\n")
        print(get_time_str())
        pprint.pprint(cal_status)
        
        time.sleep(60)

