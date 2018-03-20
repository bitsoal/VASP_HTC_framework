
# coding: utf-8

# In[5]:


import os, sys, time, pprint

HTC_lib_path = "/home/e0001020/.HTC"
cif_file_folder = "/lustre/scratch/e0001020/Z_scheme/my_own_Z_scheme_high_throughput/cif_files"
cal_folder = "/lustre/scratch/e0001020/Z_scheme/my_own_Z_scheme_high_throughput/cal_folder"
HTC_calculation_setup_file = "/lustre/scratch/e0001020/Z_scheme/my_own_Z_scheme_high_throughput/Calculation_setup_GRC"

if HTC_lib_path not in sys.path:
    sys.path.append(HTC_lib_path)

if  os.path.join(HTC_lib_path, "HTC_lib") not in sys.path:
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
        submit_jobs(ready_jobs=ready_job_list, workflow=workflow,max_jobs_in_queue=5)
        kill_error_jobs(error_jobs=cal_status["error_folder_list"], workflow=workflow)
        cal_status = check_calculations_status(cal_folder=cal_folder)
        
        
        
        
        
        to_be_cal_folders = []
        for folder_name, folder_list in cal_status.items():
            if folder_name != "done_folder_list":
                to_be_cal_folders += folder_list
                
        print("\n")
            print(get_time_str())
            pprint.pprint(cal_status)
            time.sleep(60)
            
        with open("htc_job_status.dat", "w") as f:
                f.write("\n{}:".format(get_time_str()))
                for status, folder_list in cal_status.items():
                    f.write("\n{}:\n".format(status))
                    for folder in folder_list:
                        f.write("\t{}\n".format(folder))
                        
        if to_be_cal_folders == []:
            print("All calculations have finished --> Stop this program.")
            with open("htc_job_status.dat", "w") as f:
                f.write("\n***All calculations have finished --> Stop this program.***")
            break
            

