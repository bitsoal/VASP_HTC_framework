
# coding: utf-8

# In[1]:


import os, sys, time, pprint

HTC_lib_path = "/home/e0001020/.HTC"

if HTC_lib_path not in sys.path:
    sys.path.append(HTC_lib_path)

if  os.path.join(HTC_lib_path, "HTC_lib") not in sys.path:
    sys.path.append(os.path.join(HTC_lib_path, "HTC_lib"))


from HTC_lib.Utilities import get_time_str
from HTC_lib.Parse_calculation_workflow import parse_calculation_workflow, old_parse_calculation_workflow
from HTC_lib.new_Preprocess_and_Postprocess import pre_and_post_process, preview_HTC_vasp_inputs
from HTC_lib.Check_and_update_calculation_status import check_calculations_status, update_job_status
from HTC_lib.Submit_and_Kill_job import submit_jobs, kill_error_jobs


# In[2]:


if __name__ == "__main__":
    assert os.path.isfile("HTC_calculation_setup_file"), "Error: No HTC_calculation_setup_file under {}".format(os.getcwd())
    workflow = parse_calculation_workflow("HTC_calculation_setup_file")
    
    structure_file_folder = workflow[0]["structure_folder"]
    cal_folder = workflow[0]["cal_folder"]
    max_running_job = workflow[0]["max_running_job"]
    
    if not os.path.isdir(cal_folder):
        os.mkdir(cal_folder)
    
    if workflow[0]["preview_vasp_inputs"]:
        preview_HTC_vasp_inputs(cif_filename=os.listdir(structure_file_folder)[0], cif_folder=structure_file_folder, workflow=workflow)


    main_dir = os.getcwd()
    while not workflow[0]["preview_vasp_inputs"]:
        os.chdir(main_dir)
        if os.path.isfile("__stop__"):
            print(">>>Detect file __stop__ in {}\n ---->stop this program.".format(main_dir))
            break
        
        update_job_status(cal_folder=cal_folder, workflow=workflow)
        for structure_file in os.listdir(structure_file_folder):
            pre_and_post_process(structure_file, structure_file_folder, cal_folder=cal_folder, workflow=workflow)
        cal_status = check_calculations_status(cal_folder=cal_folder)
        submit_jobs(cal_jobs_status=cal_status, workflow=workflow, max_jobs_in_queue=max_running_job)
        cal_status = check_calculations_status(cal_folder=cal_folder)
                
        #print("\n")
        #print(get_time_str())
        #pprint.pprint(cal_status)
        
        os.chdir(main_dir)    
        with open("htc_job_status.dat", "w") as f:
                f.write("\n{}:".format(get_time_str()))
                for status, folder_list in cal_status.items():
                    if status == "done_folder_list":
                        continue
                    f.write("\n{}:\n".format(status))
                    for folder in folder_list:
                        f.write("\t{}\n".format(folder))
                f.write("\n{}:\n".format("done_folder_list"))
                for folder in cal_status["done_folder_list"]:
                    f.write("\t{}\n".format(folder))
                        
        #check if all calculations are complete
        #At the end, all calculations should be labeled by signal file __done__ or __skipped__
        
        no_of_done_or_skipped_cal = len(cal_status["done_folder_list"]) + len(cal_status["skipped_folder_list"])
        no_of_ongoing_jobs = sum([len(job_list) for job_status, job_list in cal_status.items() 
                                  if job_status not in ["done_folder_list", "skipped_folder_list"]])
        if no_of_ongoing_jobs == 0:
            print("All calculations have finished --> Stop this program.")
            os.chdir(main_dir)
            with open("htc_job_status.dat", "a") as f:
                f.write("\n***All calculations have finished --> Stop this program.***")
            break
            
        time.sleep(600)

