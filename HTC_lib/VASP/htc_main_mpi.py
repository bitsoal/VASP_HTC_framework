#!/usr/bin/env python
# coding: utf-8

# In[6]:


import os, sys, time, pprint

##############################################################################################################
##DO NOT change this part.
##../setup.py will update this variable
HTC_package_path = "C:/Users/tyang/Documents/Jupyter_workspace/HTC/python_3"
assert os.path.isdir(HTC_package_path), "Cannot find this VASP_HTC package under {}".format(HTC_package_path)
if HTC_package_path not in sys.path:
    sys.path.append(HTC_package_path)
##############################################################################################################

from pathlib import Path
from mpi4py import MPI
comm = MPI.COMM_WORLD
size = comm.Get_size()
rank = comm.Get_rank()

from HTC_lib.VASP.Miscellaneous.Utilities import get_time_str
from HTC_lib.VASP.Miscellaneous.Backup_HTC_input_files import backup_htc_input_files, backup_a_file
from HTC_lib.VASP.Miscellaneous.change_signal_file import change_signal_file
from HTC_lib.VASP.Preprocess_and_Postprocess.Parse_calculation_workflow import parse_calculation_workflow
from HTC_lib.VASP.Preprocess_and_Postprocess.new_Preprocess_and_Postprocess import pre_and_post_process
from HTC_lib.VASP.Job_Management.Check_and_update_calculation_status import check_calculations_status, update_job_status
from HTC_lib.VASP.Job_Management.Submit_and_Kill_job import submit_jobs, kill_error_jobs


# In[6]:


def write_cal_status(cal_status, filename):
    to_be_written_status_list = ["manual_folder_list", "skipped_folder_list", "error_folder_list", "killed_folder_list", 
                                 "sub_dir_cal_folder_list", "running_folder_list"]
    last_written_status_list = ["vis_folder_list", "prior_ready_folder_list", "ready_folder_list", "done_folder_list", 
                                "done_cleaned_analyzed_folder_list", "done_failed_to_clean_analyze_folder_list"]
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


# In[72]:


def divide_a_list_evenly(a_list, no_of_sublists):
    """
    Divide a list into no_of_sublists sublists as evenly as possible and return the list of divided sublists.
    """
    assert no_of_sublists >= 1, "Can not divide a list into {} sublists. no_of_sublists should be >= 1".format(no_of_sublists)
    
    a_list = list(a_list)
    
    list_length = len(a_list)
    sublist_length = round(list_length / no_of_sublists, ndigits=None)
    sublist_length = max([sublist_length, 1])
    
    sublist_list = []
    ind_start = 0
    while ind_start < list_length and len(sublist_list) < no_of_sublists:
        ind_end = ind_start + sublist_length
        if ind_end <= list_length:
            sublist_list.append(a_list[ind_start:ind_end])
        else:
            sublist_list.append(a_list[ind_start:])
        ind_start = ind_end
        
    sublist_length0 = len(sublist_list)
    if sublist_length0 == no_of_sublists:
        sublist_list[-1].extend(a_list[ind_start:])
    else:
        sublist_list.extend([[] for i in range(no_of_sublists - sublist_length0)])
    
    return sublist_list


# In[68]:


def synchron():
    buf = None
    if rank == 0:
        for ip in range(1,size):
            comm.send(buf,dest=ip)
            buf=comm.recv(source=ip)
        for ip in range(1,size):
            comm.send(buf,dest=ip)
    else:
        buf=comm.recv(source=0)
        comm.send(buf,dest=0)
        buf = comm.recv(source=0)


# In[2]:


if __name__ == "__main__":
    debugging = True
    
    workflow = read_workflow()
    if rank == 0: backup_htc_files(workflow=workflow)
    
    structure_file_folder = workflow[0]["structure_folder"]
    cal_folder = workflow[0]["cal_folder"]
    max_running_job = workflow[0]["max_running_job"]
    
    no_of_structures = len(os.listdir(structure_file_folder))
    assert  no_of_structures >= size, "# of to-be-calculated structures {} should be >= # of requested cores/cpus {}.".format(no_of_structures, size)
    
    if rank == 0 and not os.path.isdir(cal_folder):
        os.mkdir(cal_folder)

    main_dir = os.getcwd()
    stop_file_path = os.path.join(main_dir, "__stop__")
    htc_job_status_file_path = os.path.join(main_dir, "htc_job_status.dat")
    
    if rank == 0: # calculation status is checked and updated only in process 0 (master process)
        no_of_same_cal_status, cal_status_0 = 0, {}
    
    if debugging: print("{}: Before the while loop in process {}".format(get_time_str(), rank), flush=True)
    continue_running = True
    while continue_running:
        if os.path.isfile(stop_file_path):
            print(">>>Detect file __stop__ in {}\n ---->stop this program in process {}.".format(main_dir, rank))
            break
            
        for which_status in ["running_folder_list", "error_folder_list", "killed_folder_list", 
                             "sub_dir_cal_folder_list", "done_folder_list"]:
            if debugging: print("{}: start updating {} in process {}".format(get_time_str(), which_status, rank), flush=True)
            if rank == 0:
                cal_status = check_calculations_status(cal_folder=cal_folder)
                sub_job_lists = divide_a_list_evenly(cal_status[which_status], no_of_sublists=size)
                for i in range(1, size):
                    comm.send(sub_job_lists[i], dest=i, tag=i)
                sub_job_list = sub_job_lists[0]
            else:
                sub_job_list = comm.recv(source=0, tag=rank)

            try:
                update_job_status(cal_folder=cal_folder, workflow=workflow, which_status=which_status, 
                                  job_list=sub_job_list, stop_file_path=stop_file_path)
            except:
                continue_running = False
                raise                
            finally:
                if rank == 0:
                    if False in [comm.recv(source=i, tag=i) for i in range(1, size)]:
                        continue_running = False
                    [comm.send(continue_running, dest=i, tag=i) for i in range(1, size)]
                else:
                    comm.send(continue_running, dest=0, tag=rank)
                    continue_running = comm.recv(source=0, tag=rank) 
            if continue_running == False: break
            if os.path.isfile(stop_file_path): break
            if debugging: print("{}: end updating {} in process {}".format(get_time_str(),which_status, rank), flush=True)
        if continue_running == False: break
        if os.path.isfile(stop_file_path): continue
            
            
        if rank == 0:  
            if debugging: print("{}: dispatching structure lists from process 0 to others".format(get_time_str()), flush=True)
            structure_file_sublist_list = divide_a_list_evenly(a_list=os.listdir(structure_file_folder), no_of_sublists=size)            
            structure_file_sublist = structure_file_sublist_list[0]
            for i in range(1, size): # send structure file sublists to process 1, 2, ..., size-1
                comm.send(structure_file_sublist_list[i], dest=i, tag=i)
            t0 = time.time()
        else:
            if debugging: print("{}: receiving structure list from process 0 in process {}".format(get_time_str(), rank), flush=True)
            structure_file_sublist = comm.recv(source=0, tag=rank) # receive structure file sublist from process 0
        if debugging: print("{}: finished dispatch of structure lists to process {}".format(get_time_str(), rank), flush=True)
        
        if debugging: print("{}: start to prepare vasp input files in process {}".format(get_time_str(), rank), flush=True)
        t1, comm_period = time.time(), 300
        for structure_file in structure_file_sublist:
            try:
                pre_and_post_process(structure_file, structure_file_folder, cal_folder=cal_folder, workflow=workflow)
            except:
                continue_running = False
                time.sleep(comm_period + 10 - (time.time()-t1)) #additional 10 s ensure that the following if clause is always True
                raise
            finally:
                if time.time() - t1 >= comm_period or continue_running == False:
                    if rank == 0:
                        if False in [comm.recv(source=i, tag=i) for i in range(1, size)]:
                            continue_running = False
                        [comm.send(continue_running, dest=i, tag=i) for i in range(1, size)]
                    else:
                        comm.send(continue_running, dest=0, tag=rank)
                        continue_running = comm.recv(source=0, tag=rank)
                    t1 = time.time()
            if os.path.isfile(stop_file_path): break
            if continue_running == False: break
            if debugging: print("{}: finished input preparation for {} in process {}".format(get_time_str(), structure_file, rank), flush=True)
                
            #Every process individually checks cal status instead of receiving from process 0 
            #--> Avoid a deadlock state in process 1, 2, ..., size-1 if process 0 encounters an error
            cal_status = check_calculations_status(cal_folder=cal_folder) 
            if rank == 0 and time.time() - t0 > 180: #update htc_job_status.dat every 180 s.
                write_cal_status(cal_status, htc_job_status_file_path)
                t0 = time.time()
            no_of_ready_jobs = len(cal_status["prior_ready_folder_list"]) + len(cal_status["ready_folder_list"])
            del cal_status
            if no_of_ready_jobs >= workflow[0]["max_no_of_ready_jobs"]:
                break
        if os.path.isfile(stop_file_path): continue
        if continue_running == False: break
        if debugging: print("{}: finished input file preparation in process {}".format(get_time_str(), rank), flush=True)
        
        synchron()
        
        if rank == 0:
            if debugging: print("{}: start submitting ready jobs in process {}".format(get_time_str(), rank), flush=True)
            cal_status = check_calculations_status(cal_folder=cal_folder)
            submit_jobs(cal_jobs_status=cal_status, workflow=workflow, max_jobs_in_queue=max_running_job)
            cal_status = check_calculations_status(cal_folder=cal_folder)      
            write_cal_status(cal_status, htc_job_status_file_path)
            
            #check if all calculations are complete. If this is the case, stop. At the end, all calculations should be labeled by signal file __done__, __skipped__, __done_cleaned_analyzed__ and __done_failed_to_clean_analyze__
            no_of_ongoing_jobs = sum([len(job_list) for job_status, job_list in cal_status.items() if job_status not in ["done_folder_list", "skipped_folder_list", "done_cleaned_analyzed_folder_list", "done_failed_to_clean_analyze_folder_list"]])
            if no_of_ongoing_jobs == 0:
                output_str = "All calculations have finished --> Stop this program."
                print(output_str)
                with open(htc_job_status_file_path, "a") as f:
                    f.write("\n***" + output_str + "***")
                continue_running = False
        continue_running = comm.bcast(continue_running, root=0)
        if debugging: print("{}: completed job submission in process 0. Reported from process {}".format(get_time_str(), rank), flush=True)
        if continue_running == False: break
        
        if rank == 0:
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
                continue_running = False
        continue_running = comm.bcast(continue_running, root=0)
        if debugging: print("{}: process 0 find that cal status is still updating. Reported from process {}".format(get_time_str(), rank), flush=True)
        if continue_running == False: break
            
        if rank == 0:
            os.chdir(main_dir)
            for i in range(60):
                update_now_list = list(Path(main_dir).glob("**/__update_now__"))
                if os.path.isfile("__stop__"):
                    break
                elif update_now_list:
                    for update_now in update_now_list:
                        os.remove(update_now)
                    break
                elif os.path.isfile("__change_signal_file__"):
                    cal_status = change_signal_file(cal_status, "__change_signal_file__")
                    os.remove("__change_signal_file__")
                    write_cal_status(cal_status, "htc_job_status.dat")
                else:
                    time.sleep(10)
        synchron()
        if debugging: print("\n{}: ***process {} arrives at the end of the while loop. Will enter the next round of iteration.***\n".format(get_time_str(), rank), flush=True)
        synchron()

