#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os, sys, time, random

##############################################################################################################
##DO NOT change this part.
##../setup.py will update this variable
HTC_package_path = "C:/Users/tyang/Documents/Jupyter_workspace/HTC/python_3"
assert os.path.isdir(HTC_package_path), "Cannot find this VASP_HTC package under {}".format(HTC_package_path)
if HTC_package_path not in sys.path:
    sys.path.append(HTC_package_path)
##############################################################################################################


from HTC_lib.VASP.Miscellaneous.Utilities import get_time_str, decorated_os_rename, decorated_subprocess_check_output
from HTC_lib.VASP.Miscellaneous.Utilities import get_current_firework_from_cal_loc, write_cal_status
from HTC_lib.VASP.Miscellaneous.Execute_bash_shell_cmd import Execute_shell_cmd
from HTC_lib.VASP.Miscellaneous.change_signal_file import change_signal_file

from HTC_lib.VASP.Job_Management.Submit_and_Kill_job import Job_management, kill_error_jobs

from HTC_lib.VASP.Error_Checker.Error_checker import Write_and_read_error_tag
from HTC_lib.VASP.Error_Checker.Error_checker import Vasp_Error_Saver
from HTC_lib.VASP.Error_Checker.Error_checker import Queue_std_files
from HTC_lib.VASP.Error_Checker.Error_checker import Vasp_Error_checker


# In[5]:


def respond_to(signal_file, workflow):
    main_dir = workflow[0]["htc_cwd"]
    htc_job_status_file_path = os.path.join(main_dir, "htc_job_status.json")
    job_status_dict = check_calculations_status(cal_folder=workflow[0]["cal_folder"])
    
    if signal_file == "__update_now__":
        write_cal_status(cal_status=job_status_dict, filename=htc_job_status_file_path)
        os.remove(os.path.join(workflow[0]["htc_cwd"], "__update_now__"))
    elif signal_file == "__change_signal_file__":
        change_signal_file_path = os.path.join(main_dir, "__change_signal_file__")
        cal_status = change_signal_file(job_status_dict, change_signal_file_path)
        write_cal_status(cal_status, htc_job_status_file_path)
        os.remove(change_signal_file_path)
    else:
        raise Exception("argument signal_file of function respond_to must be either '__update_now__' or '__change_signal_file__'")


# In[6]:


def update_job_status(cal_folder, workflow, which_status='all', job_list=[], quick_response=True):
    """
    arguements:
        - cal_folder: the path to the folder under which high-throughput calculations are performed.
        - workflow: the workflow parsed by function read_HTC_calculation_setup_folder in HTC_lib/VASP/Preprocess_and_Postprocess/Parse_calculation_workflow.py
        - which_status: tell this function that the calculations labelled by which status are going to be updated.
                1. which_status could be 'running_folder_list', 'error_folder_list', 'killed_folder_list', 'sub_dir_cal_folder_list' and 'done_folder_list'
                2. which_status could also be 'all' --> update all calculations labelled by any status above.
                default: 'all'
        - job_list: if which_status is in condition 1, you must provide a list of to-be-updated calculations labelled by which_status.
                In the parallel mode, only process 0 checks the status of all calculations, evenly divides the to-be-updated calculations and send them to 
                different processes. This ensures each to-be-updated calculation to be updated by only one process.
                default: []
        - quick_response (boolean): whether this function quickly responds to signal file '__update_now__' and '__change_signal_file__'.
                While updating calculations labelled by others are very fast, updating calculations labelled by 'sub_dir_cal_folder_list' or 'done_folder_list'
                might be very slow because slow external commands can be involved. So
                1. In the former case, quick_response essentially means whether the function responds to '__update_now__' and '__change_signal_file__'
                    after ALL target calculations are updated.
                2. In the latter case, the function tries to respond to '__update_now__' and '__change_signal_file__' before continuing to update next target calculation.
                    The response period is set to 3 mins.
                In the paraell mode, this tag would allow these io-related operations to be conducted in process 0.
                default: True
    """
    stop_file_path = os.path.join(workflow[0]["htc_cwd"], "__stop__")
    htc_job_status_file_path = os.path.join(workflow[0]["htc_cwd"], "htc_job_status.json")
    update_now_file_path = os.path.join(workflow[0]["htc_cwd"], "__update_now__")
    change_signal_file_path = os.path.join(workflow[0]["htc_cwd"], "__change_signal_file__")
    quick_response_period = 120 #seconds
    
    if which_status == "all":
        job_status_dict = check_calculations_status(cal_folder=cal_folder)
        
        #update_running_jobs_status(running_jobs_list=job_status_dict["running_folder_list"], workflow=workflow)
        update_job_status(cal_folder, workflow, which_status="running_folder_list", 
                          job_list=job_status_dict["running_folder_list"], quick_response=quick_response)
        
        job_status_dict = check_calculations_status(cal_folder=cal_folder)
        #kill_error_jobs(error_jobs=job_status_dict["error_folder_list"], workflow=workflow)
        update_job_status(cal_folder, workflow, which_status="error_folder_list", 
                          job_list=job_status_dict["error_folder_list"], quick_response=quick_response)
        
        job_status_dict = check_calculations_status(cal_folder=cal_folder)
        
        #update_killed_jobs_status(killed_jobs_list=job_status_dict["killed_folder_list"], workflow=workflow)
        update_job_status(cal_folder, workflow, which_status="killed_folder_list", 
                          job_list=job_status_dict["killed_folder_list"], quick_response=quick_response)
        
        #update_sub_dir_cal_jobs_status(sub_dir_cal_jobs_list=job_status_dict["sub_dir_cal_folder_list"], workflow=workflow)
        update_job_status(cal_folder, workflow, which_status="sub_dir_cal_folder_list", 
                          job_list=job_status_dict["sub_dir_cal_folder_list"], quick_response=quick_response)
        
        #clean_analyze_or_update_successfully_finished_jobs(done_jobs_list=job_status_dict["done_folder_list"], workflow=workflow)
        update_job_status(cal_folder, workflow, which_status="done_folder_list", 
                          job_list=job_status_dict["done_folder_list"], quick_response=quick_response)
    elif which_status == "running_folder_list":
        for cal_loc in job_list:
            assert os.path.isfile(os.path.join(cal_loc, "__running__")), "The status of the following job is not __running__: {}".format(cal_loc)
        update_running_jobs_status(running_jobs_list=job_list, workflow=workflow)
    elif which_status == "error_folder_list":
        for cal_loc in job_list:
            assert os.path.isfile(os.path.join(cal_loc, "__error__")), "The status of the following job is not __error__: {}".format(cal_loc)
        kill_error_jobs(error_jobs=job_list, workflow=workflow)
    elif which_status == "killed_folder_list":
        for cal_loc in job_list:
            assert os.path.isfile(os.path.join(cal_loc, "__killed__")), "The status of the following job is not __killed__: {}".format(cal_loc)
        update_killed_jobs_status(killed_jobs_list=job_list, workflow=workflow)
    elif which_status == "sub_dir_cal_folder_list":
        if quick_response: t0 = time.time()
        for cal_loc in job_list:
            assert os.path.isfile(os.path.join(cal_loc, "__sub_dir_cal__")), "The status of the following job is not __sub_dir_cal__: {}".format(cal_loc)
            update_sub_dir_cal_jobs_status(sub_dir_cal_jobs_list=[cal_loc], workflow=workflow)
            if os.path.isfile(stop_file_path): #update_sub_dir_cal_jobs_status may involve very slow external commands.
                break  #This if clause ensures a quick response to __stop__ file
            if quick_response and (time.time() - t0) >= quick_response_period:
                if os.path.isfile(update_now_file_path): respond_to(signal_file="__update_now__", workflow=workflow)
                if os.path.isfile(change_signal_file_path): respond_to(signal_file="__change_signal_file__", workflow=workflow)
                t0 = time.time()
            if random.random() > 0.75:
                job_status_dict = check_calculations_status(cal_folder=cal_folder)
                no_of_ready_jobs = len(job_status_dict["prior_ready_folder_list"]) + len(job_status_dict["ready_folder_list"])
                del job_status_dict
                if no_of_ready_jobs >= workflow[0]["max_no_of_ready_jobs"]:
                    break
    elif which_status == "done_folder_list":
        if quick_response: t0 = time.time()
        for cal_loc in job_list:
            assert os.path.isfile(os.path.join(cal_loc, "__done__")), "The status of the following job is not __done__: {}".format(cal_loc)
            clean_analyze_or_update_successfully_finished_jobs(done_jobs_list=[cal_loc], workflow=workflow)
            if os.path.isfile(stop_file_path): #clean_analyze_or_update_successfully_finished_jobs may involve very slow external commands.
                break  #This if clause ensures a quick response to __stop__ file
            if quick_response and (time.time() - t0) >= quick_response_period:
                if os.path.isfile(update_now_file_path): respond_to(signal_file="__update_now__", workflow=workflow)
                if os.path.isfile(change_signal_file_path): respond_to(signal_file="__change_signal_file__", workflow=workflow)
                t0 = time.time()
    
    if quick_response:
        if os.path.isfile(update_now_file_path): respond_to(signal_file="__update_now__", workflow=workflow)
        if os.path.isfile(change_signal_file_path): respond_to(signal_file="__change_signal_file__", workflow=workflow)
    
        


# In[2]:


def check_calculations_status_0(cal_folder):
    """
    Check the status of all calculations under folder cal_folder 
    input argument:
        - cal_folder (str): Under cal_folder, a sub-folder will be created where a set of DFT calculations defined by workflow will be made.
                        Note that the absolute path should be provided.
    return a dictionary having keys below:
        - ready_folder_list (list): a list of absolute pathes where the calculations are ready.
                                    Note that the pathes where instead file __prior_ready__ exists will be put at the beginning
                                    of list read_folder_list.
        - running_folder_list (list): a list of absolute pathes where the calculations are ongoing.
        - done_folder_list (list): a list of absolute pathes where the calculations are done.
        - error_folder_list (list): a list of absolute pathes where the calculations encounter errors.
        - killed_folder_list (list): a list of absolute pathes where the calculation has been killed.
        - manual_folder_list (list): a list of absolute pathes where the error can not be fixed automatically.
        - vis_folder_list (list): a list of absolute pathes where the input files for calculations need to be prepared
    """
    signal_file_list = ["__manual__", "__test__", "__vis__", "__skipped__", "__ready__", "__prior_ready__", 
                        "__error__", "__running__", "__done__", "__killed__"]
    job_status_folder_list = ["manual_folder_list", "test_folder_list", "vis_folder_list", "skipped_folder_list", 
                              "ready_folder_list", "prior_ready_folder_list", "error_folder_list", "running_folder_list", 
                              "done_folder_list", "killed_folder_list", "other_folder_list"]
    job_status_dict = {key: [] for key in job_status_folder_list}
    if not os.path.isdir(cal_folder):
        return job_status_dict
        
    mater_folder_list = os.listdir(cal_folder)
    firework_folder_list = []
    for mater_folder in mater_folder_list:
        mater_folder_path = os.path.join(cal_folder, mater_folder)
        #in case any file appears in cal_folder.
        if not os.path.isdir(mater_folder_path):
            continue
        #ignore irrelevant files or folders
        firework_name_list = [firework_name for firework_name in os.listdir(mater_folder_path) if firework_name.startswith("step")]
        firework_folder_list += [os.path.join(mater_folder_path, firework_name) for firework_name in firework_name_list]
    
    #categorize fireworks
    for firework_folder in firework_folder_list:
        firework_belongs_to_other = True
        for signal_file_ind, signal_file in enumerate(signal_file_list):
            if os.path.isfile(os.path.join(firework_folder, signal_file)):
                job_status_dict[job_status_folder_list[signal_file_ind]].append(firework_folder)
                firework_belongs_to_other = False
                break
        if firework_belongs_to_other:
            job_status_dict["other_folder_list"].append(firework_folder)
       
    return job_status_dict


# In[2]:


def check_calculations_status(cal_folder):
    """
    Check the status of all calculations under folder cal_folder 
    input argument:
        - cal_folder (str): The absolute path to a directory under which the program creates a sub-directory for every to-be-calculated
                            materials. In the sub-directory, a series of DFT calculations predefined will be carried out.
                            This function checks the calculation status of all DFT calculations under the folder referenced by cal_folder/
    return a dictionary having keys below:
        - ready_folder_list (list): a list of absolute pathes where the calculations are ready.
                                    Note that the pathes where instead file __prior_ready__ exists will be put at the beginning
                                    of list read_folder_list.
        - running_folder_list (list): a list of absolute pathes where the calculations are ongoing.
        - done_folder_list (list): a list of absolute pathes where the calculations are done.
        - error_folder_list (list): a list of absolute pathes where the calculations encounter errors.
        - killed_folder_list (list): a list of absolute pathes where the calculation has been killed.
        - manual_folder_list (list): a list of absolute pathes where the error can not be fixed automatically.
        - vis_folder_list (list): a list of absolute pathes where the input files for calculations need to be prepared
        - ...
    """
    signal_file_list = ["__manual__", "__test__", "__vis__", "__skipped__", "__ready__", "__prior_ready__", "__sub_dir_cal__",
                        "__error__", "__running__", "__done__", "__done_cleaned_analyzed__", "__done_failed_to_clean_analyze__", "__killed__"]
    job_status_folder_list = ["manual_folder_list", "test_folder_list", "vis_folder_list", "skipped_folder_list", 
                              "ready_folder_list", "prior_ready_folder_list", "sub_dir_cal_folder_list", "error_folder_list", "running_folder_list", 
                              "done_folder_list", "done_cleaned_analyzed_folder_list", "done_failed_to_clean_analyze_folder_list", 
                              "killed_folder_list", "other_folder_list"]
    job_status_dict = {key: [] for key in job_status_folder_list}
    
    
    jobs_in_str = decorated_subprocess_check_output("find %s -type f -name INCAR" % cal_folder)[0]
    job_list = []
    for job in jobs_in_str.split("\n"):
        job = job.strip()
        if job and "step" in job and "error_folder" not in job:
            job_list.append(os.path.split(job)[0])
    
    for job in job_list:
        file_list = os.listdir(job)
        is_it_categorized = False
        for signal_file, status_type in zip(signal_file_list, job_status_folder_list):
            if signal_file in file_list:
                job_status_dict[status_type].append(job)
                is_it_categorized = True
                break
        if not is_it_categorized:
            file_belong_to_other = True
            #Also search for other unknown signal files starting and ending with double underscores ("__")
            for file_ in file_list:
                if file_.startswith("__") and file_.endswith("__"):
                    unknown_job_status = file_.strip("_") + "_folder_list"
                    if unknown_job_status not in job_status_dict.keys():
                        job_status_dict[unknown_job_status] = [job]
                    else:
                        job_status_dict[unknown_job_status].append(job)
                    file_belong_to_other = False
                    break
            if file_belong_to_other:
                job_status_dict["other_folder_list"].append(job)
                
    #Sort the ready jobs such that the series of jobs associated with one material can be run continuously
    job_status_dict["ready_folder_list"] = sorted(job_status_dict["ready_folder_list"])
    job_status_dict["prior_ready_folder_list"] = sorted(job_status_dict["prior_ready_folder_list"])
    
    return job_status_dict


# In[3]:


def update_running_jobs_status(running_jobs_list, workflow):
    """
    Update jobs's status. for the running jobs, if any errors are detected, change __running__ to __error__ and 
        the error type will be written into __error__.
    input arguments:
        - running_jobs_list (list): a list of absolute pathes of running jobs.
        - workflow:  the output of func Parse_calculation_workflow.parse_calculation_workflow
    """
    #Check_after_cal = ["__electronic_divergence__", "__positive_energy__", "__ionic_divergence__"]
    #Check_on_the_fly = ["__electronic_divergence__", "__positive_energy__"]
    
    job_status_str = Job_management.check_jobs_in_queue_system(workflow=workflow, return_a_str=True)
    #print()
    #print(get_time_str())
    #print(job_status_str)
    #job_status_str = ""
    #if job_status_list:
    #    for i in range(1, len(job_status_list)):
    #        job_status_str += job_status_list[i]
    
    for job_path in running_jobs_list:
        
        
        find_error = False
        if Queue_std_files(cal_loc=job_path, workflow=workflow).find_std_files() != [None, None]:
            #for func Vasp_Error_checker, error_type=["after_cal"] will automatically check errors after cal.
            #If found, __running__ --> __error__ and the error info will be written into __error__ and return False
            #If not found, return True
            if Vasp_Error_checker(error_type=["after_cal"], cal_loc=job_path, workflow=workflow):
                cal_name = os.path.split(job_path)[-1]
                with open(os.path.join(job_path, "log.txt"), "a") as f:
                    f.write("{} INFO: Calculation successfully finishes at {}\n".format(get_time_str(), cal_name))
                    f.write("\t\t\t__running__ --> __done__\n")
                    decorated_os_rename(loc=job_path, old_filename="__running__", new_filename="__done__")
                    #os.rename(os.path.join(job_path, "__running__"), os.path.join(job_path, "__done__"))
        else:
            #for func Vasp_Error_checker, error_type=["on_the_fly"] will automatically check errors on the fly.
            #If found, __running__ --> __error__ and the error info will be written into __error__ and return False
            #If not found, return True
            Vasp_Error_checker(error_type=["on_the_fly"], cal_loc=job_path, workflow=workflow)
            
        if os.path.isfile(os.path.join(job_path, "__running__")):
            if Queue_std_files(cal_loc=job_path, workflow=workflow).find_std_files() != [None, None]:
                continue
                
            
                    
                
            queue_id = Job_management(cal_loc=job_path, workflow=workflow).find_queue_id()
            #print(queue_id, queue_id in job_status_str)
            if queue_id not in job_status_str:
                if not os.path.isfile(os.path.join(job_path, "__no_of_times_not_in_queue__")):
                    with open(os.path.join(job_path, "__no_of_times_not_in_queue__"), "w") as f:
                        f.write("1")
                else:
                    with open(os.path.join(job_path, "__no_of_times_not_in_queue__"), "r") as f:
                        times = int(next(f).strip())
                    if times <= 5:
                        with open(os.path.join(job_path, "__no_of_times_not_in_queue__"), "w") as f:
                            f.write(str(times+1))
                        continue
                
                    cal_name = os.path.split(job_path)[-1]
                    with open(os.path.join(job_path, "log.txt"), "a") as f:
                        f.write("{} Queue Error: {}\n".format(get_time_str(), cal_name))
                        f.write("\t\t\tThe running job is not found in queue.\n")
                        f.write("\t\t\t__running__ --> __manual__\n")
                        f.write("\t\t\tCreate file __running_job_not_in_queue__.\n")
                        open(os.path.join(job_path, "__running_job_not_in_queue__"), "w").close()
                        decorated_os_rename(loc=job_path, old_filename="__running__", new_filename="__manual__")
                        #os.rename(os.path.join(job_path, "__running__"), os.path.join(job_path, "__manual__"))                
            else:
                if os.path.isfile(os.path.join(job_path, "__no_of_times_not_in_queue__")):
                    os.remove(os.path.join(job_path, "__no_of_times_not_in_queue__"))


# In[4]:


def update_killed_jobs_status(killed_jobs_list, workflow, max_error_times=5):
    """
    Update killed jobs's status. If the error in __killed__ can be fixed, fix it and __killed__ --> __ready__; 
        Ohterwise __killed__ --> __manual__
    input arguments:
        - killed_jobs_list (list): a list of absolute pathes of killed jobs.
        - workflow:  the output of func Parse_calculation_workflow.parse_calculation_workflow
        - max_error_times (int): the maximum error times. Beyond this value, __killed__ --> __manual__. Default: 5
    """
    
    #Error_type_dict = ["__unfinished_OUTCAR__", "__electronic_divergence__", 
    #                   "__ionic_divergence__", "__positive_energy__"]
    
    for killed_job in killed_jobs_list:
        #The killed job won't be processed until the stdout & stderr files of the queue system appear.
        if Queue_std_files(cal_loc=killed_job, workflow=workflow).find_std_files() == [None, None]:
            continue
        
        error_type = Write_and_read_error_tag(killed_job).read_error_tag("__killed__")
        error_checker = Vasp_Error_checker(cal_loc=killed_job, error_type=error_type, workflow=workflow)
        cal_name = os.path.split(killed_job)[-1]
        if Vasp_Error_Saver(cal_loc=killed_job, workflow=workflow).find_error_times() >= max_error_times:
            decorated_os_rename(loc=killed_job, old_filename="__killed__", new_filename="__manual__")
            #os.rename(os.path.join(killed_job, "__killed__"), os.path.join(killed_job, "__manual__"))
            with open(os.path.join(killed_job, "log.txt"), "a") as f:
                f.write("{} Killed: {}\n".format(get_time_str(), cal_name))
                f.write("\t\t\tThe error times hit the max_error_times ({})\n".format(max_error_times))
                f.write("\t\t\t__killed__ -> __manual__\n")
        elif error_checker.correct():
            #Queue_std_files(cal_loc=killed_job, workflow=workflow).remove_std_files()
            #to_be_removed = ["OUTCAR", "OSZICAR", workflow[0]["vasp.out"]]
            #for file_ in to_be_removed:
            #    if os.path.isfile(os.path.join(killed_job, file_)):
            #        os.remove(os.path.join(killed_job, file_))
                    
            os.remove(os.path.join(killed_job, "__killed__"))
            open(os.path.join(killed_job, "__ready__"), "w").close()
            with open(os.path.join(killed_job, "log.txt"), "a") as f:
                f.write("{} Killed: Successfully correct the error {} under {}\n".format(get_time_str(), error_type, cal_name))
                f.write("\t\t\t__killed__ --> __ready__\n")
            
        else:
            decorated_os_rename(loc=killed_job, old_filename="__killed__", new_filename="__manual__")
            #os.rename(os.path.join(killed_job, "__killed__"), os.path.join(killed_job, "__manual__"))
            with open(os.path.join(killed_job, "log.txt"), "a") as f:
                f.write("{} Killed: Fail to correct the error {} under {}\n".format(get_time_str(), error_type, cal_name))
                f.write("\t\t\t__killed__ --> __manual__\n")
            
    


# In[4]:


def update_sub_dir_cal_jobs_status(sub_dir_cal_jobs_list, workflow):
    """
    update the status of the sub-directoray calculations using the corresponding sub_dir_cal_cmd predefined in workflow.
    Note that sub_dir_cal_cmd should be responsible for the job status switching from __sub_dir_cal__ to either __done__ or __manual__.
    """
    
    for sub_dir_cal_path in sub_dir_cal_jobs_list:
        current_firework = get_current_firework_from_cal_loc(sub_dir_cal_path, workflow)
        
        Execute_shell_cmd(cal_loc=sub_dir_cal_path, user_defined_cmd_list=current_firework["sub_dir_cal_cmd"],
                          where_to_execute=sub_dir_cal_path, defined_by_which_htc_tag="sub_dir_cal_cmd")


# In[1]:


def clean_analyze_or_update_successfully_finished_jobs(done_jobs_list, workflow):
    """
    For a calculation labelled by __done__, the operations defined by HTC tag cmd_to_process_finished_jobs will be called to
    clean or analyze the calculation. After these operations are successfully called, __done__ --> __done_cleaned_analyzed__.
    If any error happens, __done__ --> __done_failed_to_clean_analyze__
    Of course, the calculation status remains at __done__ if no operation is defined by cmd_to_process_finished_jobs
    Note that if you are going to delete files/folders, please make sure the command(s) capable of ingoring non-existent files/folders.
    E.g. rm -rf file1 file2 file3 folder1
    """
    for cal_loc in done_jobs_list:      
        current_firework = get_current_firework_from_cal_loc(cal_loc, workflow)
        
        if not current_firework["cmd_to_process_finished_jobs"]:
            continue
        
        log_filename = os.path.join(cal_loc, "log.txt")
        
        status = Execute_shell_cmd(cal_loc=cal_loc, user_defined_cmd_list=current_firework["cmd_to_process_finished_jobs"], 
                                   where_to_execute=cal_loc, defined_by_which_htc_tag="cmd_to_process_finished_jobs")
        
        if status:
            decorated_os_rename(loc=cal_loc, old_filename="__done__", new_filename="__done_cleaned_analyzed__")
            with open(log_filename, "a") as log_f:
                log_f.write("\tSuccessfully cleaned or analyzed the calculation: __done__ --> __done_cleaned_analyzed__\n")
        else:
            decorated_os_rename(loc=cal_loc, old_filename="__done__", new_filename="__done_failed_to_clean_analyze__")
            os.remove(os.path.join(cal_loc, "__manual__")) #__manual__ is created by Execute_shell_cmd if an error happens
            with open(log_filename, "a") as log_f:
                log_f.write("\tFailed to clean or analyze the calculation. See above for the details\n")
                log_f.write("\tdelete __manual__ && __done__ --> __done_failed_to_clean_analyze__")

