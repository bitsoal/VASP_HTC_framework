#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os, sys, time, pprint, copy

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

from HTC_lib.VASP.Miscellaneous.Utilities import get_time_str, write_cal_status, divide_a_list_evenly
from HTC_lib.VASP.Miscellaneous.Backup_HTC_input_files import backup_htc_input_files, backup_a_file
from HTC_lib.VASP.Miscellaneous.change_signal_file import change_signal_file
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


# def divide_a_list_evenly(a_list, no_of_sublists):
#     """
#     Divide a list into no_of_sublists sublists as evenly as possible and return the list of divided sublists.
#     """
#     assert no_of_sublists >= 1, "Can not divide a list into {} sublists. no_of_sublists should be >= 1".format(no_of_sublists)
#     
#     a_list = list(a_list)
#     
#     list_length = len(a_list)
#     sublist_length = round(list_length / no_of_sublists, ndigits=None)
#     sublist_length = max([sublist_length, 1])
#     
#     sublist_list = []
#     ind_start = 0
#     while ind_start < list_length and len(sublist_list) < no_of_sublists:
#         ind_end = ind_start + sublist_length
#         if ind_end <= list_length:
#             sublist_list.append(a_list[ind_start:ind_end])
#         else:
#             sublist_list.append(a_list[ind_start:])
#         ind_start = ind_end
#         
#     sublist_length0 = len(sublist_list)
#     if sublist_length0 == no_of_sublists:
#         sublist_list[-1].extend(a_list[ind_start:])
#     else:
#         sublist_list.extend([[] for i in range(no_of_sublists - sublist_length0)])
#     
#     return sublist_list

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


# In[22]:


def merge_dicts(a_list_of_dicts):
    """
    Merge a set of the dicts whose value is of type list.
    """
    a_list_of_dicts = copy.deepcopy(a_list_of_dicts)
    merged_dict = a_list_of_dicts[0]
    for a_dict in a_list_of_dicts[1:]:
        for key, value in a_dict.items():
            if key in merged_dict.keys():
                merged_dict[key].extend(value)
            else:
                merged_dict[key] = value
    for key, value in merged_dict.items():
        merged_dict[key] = sorted(set(value))
    return merged_dict

def evenly_divide_a_dict(a_dict, no_of_subdicts):
    """
    a_dict is a dictionary whose values are all of type list.
    This function evenly divides a_dict into no_of_subdicts sub-dictionaries. Each value of a sub-dictionary is just a 1/no_of_subdicts 
    of the corresponding value of a_dict.
    Return no_of_subdicts in a list format, e.g. [sub_dict_1, sub_dict_2, sub_dict_3] at no_of_subdicts=3
    """
    subdict_list = [{} for i in range(no_of_subdicts)]
    for key, a_list in a_dict.items():
        sublist_list = divide_a_list_evenly(a_list=list(set(a_list)), no_of_sublists=no_of_subdicts)
        for i in range(no_of_subdicts):
            subdict_list[i][key] = sorted(sublist_list[i])
    return subdict_list


# In[28]:


def check_calculations_status_in_parallel_or_series(cal_folder, workflow, scatter=True):
    if size == 1:
        return check_calculations_status(cal_folder, workflow)
    else:
        mat_folder_name_sublist_list = divide_a_list_evenly(a_list=os.listdir(cal_folder), no_of_sublists=size)
        mat_folder_name_sublist = []
        if rank == 0:
            for ip in range(1, size):
                print("{}: process 0 is sending divided mat folder name list to process {}".format(get_time_str(), ip), flush=True)
                comm.send(mat_folder_name_sublist_list[ip], dest=ip, tag=ip)
            mat_folder_name_sublist = mat_folder_name_sublist_list[0]
        else:
            mat_folder_name_sublist = comm.recv(source=0, tag=rank)
            print("{}: process {} received the divided mat folder name list from process 0".format(get_time_str(), rank), flush=True)

        print("{}: process {} is checking the calculation status under the received material folders".format(get_time_str(), rank), flush=True)
        cal_status_dict = check_calculations_status(cal_folder, workflow, mat_folder_name_list=mat_folder_name_sublist)
        cal_status_dict_list = comm.gather(cal_status_dict, root=0)
        print("{}: The obtained calculation status dict is gathered by process 0 from process {}".format(get_time_str(), rank), flush=True)
        new_cal_status_dict_list = None
        if rank == 0:
            print("{}: Process 0 is merging gathered calculation status dicts".format(get_time_str()), flush=True)
            cal_status_dict = merge_dicts(a_list_of_dicts=cal_status_dict_list)
            
            if scatter:
                print("{}: Process 0 is dividing the gathered calculation status dict into {} sub dicts and then scatter them among all processes".format(get_time_str(), size), flush=True)
                new_cal_status_dict_list = evenly_divide_a_dict(a_dict=cal_status_dict, no_of_subdicts=size)
        
        if scatter:
            cal_status_dict = comm.scatter(new_cal_status_dict_list, root=0)
            print("{}: Process {} received the sub calculation dict.".format(get_time_str(), rank), flush=True)
        else:
            cal_status_dict = comm.bcast(cal_status_dict, root=0)
            print("{}: Process {} received the broadcasted calculation status dict from process 0".format(get_time_str(), rank), flush=True)
    
        return cal_status_dict


# In[1]:


if __name__ == "__main__":
    debugging = True
    
    if debugging: print("{}: process {} is reading the pre-defined calculation workflow".format(get_time_str(), rank), flush=True)
    workflow = read_workflow()
    if rank == 0: 
        if debugging: print("{}: process 0 starts the backup of htc files".format(get_time_str()), flush=True)
        backup_htc_files(workflow=workflow)
        if debugging: print("{}: process 0 finishes the backup of htc files".format(get_time_str()), flush=True)
    elif debugging: print("{}: process {} is waiting for process 0 to finish the backup of htc files".format(get_time_str(), rank), flush=True)
    synchron()
    
    structure_file_folder = workflow[0]["structure_folder"]
    cal_folder = workflow[0]["cal_folder"]
    max_running_job = workflow[0]["max_running_job"]
    
    no_of_structures = len(os.listdir(structure_file_folder))
    assert  no_of_structures >= size, "# of to-be-calculated structures {} should be >= # of requested cores/cpus {}.".format(no_of_structures, size)
    
    if rank == 0 and not os.path.isdir(cal_folder):
        os.mkdir(cal_folder)

    main_dir = os.getcwd()
    stop_file_path = os.path.join(main_dir, "__stop__")
    htc_job_status_file_path = os.path.join(main_dir, "htc_job_status.json")
    update_now_file_path = os.path.join(main_dir, "__update_now__")
    change_signal_file_path = os.path.join(main_dir, "__change_signal_file__")
    update_input_file_path = os.path.join(main_dir, "__update_input__")
    skip_signal_file_path = os.path.join(main_dir, "__skip__")
    
    if rank == 0: # calculation status is checked and updated only in process 0 (master process)
        no_of_same_cal_status, cal_status_0 = 0, {}
    
    if debugging: print("{}: process {} is entering the while loop.".format(get_time_str(), rank), flush=True)
    continue_running = True
    while continue_running:
        if os.path.isfile(stop_file_path):
            print(">>>Process {} detected file __stop__ in {}\n ---->stop this program in this process.".format(rank, main_dir),flush=True)
            break
            
        for which_status in ["running_folder_list", "error_folder_list", "killed_folder_list", 
                             "sub_dir_cal_folder_list", "done_folder_list"]:
            cal_status = check_calculations_status_in_parallel_or_series(cal_folder=cal_folder, workflow=workflow)
            ##if rank == 0:
            #    #cal_status = check_calculations_status(cal_folder=cal_folder, workflow=workflow)
            #    sub_job_lists = divide_a_list_evenly(cal_status[which_status], no_of_sublists=size)
            #    for i in range(1, size):
            #        if debugging: print("{}: process 0 starts to divide {} and send them to process {}".format(get_time_str(), which_status, i), flush=True)
            #        comm.send(sub_job_lists[i], dest=i, tag=i)
            #    sub_job_list = sub_job_lists[0]
            #else:
            #    sub_job_list = comm.recv(source=0, tag=rank)
            #    if debugging: print("{}: process {} received {} from process 0".format(get_time_str(), rank, which_status), flush=True)
            sub_job_list = cal_status[which_status]
            try:
                if debugging: print("{}: process {} starts updating {}".format(get_time_str(), rank, which_status), flush=True)
                update_job_status(cal_folder=cal_folder, workflow=workflow, which_status=which_status, 
                                  job_list=sub_job_list, quick_response= (rank == 0), rank=rank)
                if debugging: print("{}: process {} finished updating {}".format(get_time_str(), rank, which_status), flush=True)
                #allow process 0 to quickly respond to signal file __update_now__ and __change_signal_file__. response period = 3 mins
            except:
                continue_running = False
                raise                
            finally:
                if rank == 0:
                    if debugging: print("{}: process 0 receives update statuses from all other processes".format(get_time_str()), flush=True)
                    if False in [comm.recv(source=i, tag=i) for i in range(1, size)]:
                        continue_running = False
                    [comm.send(continue_running, dest=i, tag=i) for i in range(1, size)]
                    if debugging: print("{}: process 0 sent variable continue_running to all other processes".format(get_time_str()), flush=True)
                else:
                    if debugging: print("{}: process {} is sending the update status to process 0".format(get_time_str(), rank), flush=True)
                    comm.send(continue_running, dest=0, tag=rank)
                    continue_running = comm.recv(source=0, tag=rank) 
                    if debugging: print("{}: process {} received variable continue_running from process 0".format(get_time_str(), rank), flush=True)
            if continue_running == False: break
            if os.path.isfile(stop_file_path): break
            if debugging: print("{}: process {} finished updating {}".format(get_time_str(), rank, which_status), flush=True)
        if continue_running == False: break
        if os.path.isfile(stop_file_path): continue
            
        
        cal_status = check_calculations_status_in_parallel_or_series(cal_folder=cal_folder, workflow=workflow)
        if rank == 0:  
            structure_file_sublist_list = divide_a_list_evenly(a_list=os.listdir(structure_file_folder), no_of_sublists=size)            
            structure_file_sublist = structure_file_sublist_list[0]
            for i in range(1, size): # send structure file sublists to process 1, 2, ..., size-1
                if debugging: print("{}: process 0 is dispatching divided structure lists to process {}".format(get_time_str(), i), flush=True)
                comm.send(structure_file_sublist_list[i], dest=i, tag=i)
                if debugging: print("{}: process 0 sucessfully dispatched divided structure lists to process {}".format(get_time_str(), i), flush=True)
            #cal_status = check_calculations_status(cal_folder=cal_folder, workflow=workflow)
            max_no_of_ready_jobs = workflow[0]["max_no_of_ready_jobs"]/size - len(cal_status["ready_folder_list"]) - len(cal_status["prior_ready_folder_list"])
        else:
            if debugging: print("{}: process {} is receiving structure list from process 0".format(get_time_str(), rank), flush=True)
            structure_file_sublist = comm.recv(source=0, tag=rank) # receive structure file sublist from process 0
            if debugging: print("{}: process {} sucessfully received structure list from process 0".format(get_time_str(), rank), flush=True)
            max_no_of_ready_jobs = 0
        max_no_of_ready_jobs = comm.bcast(max_no_of_ready_jobs, root=0)
        #if debugging: print("{}: finished dispatch of structure lists to process {}".format(get_time_str(), rank), flush=True)
        
        if debugging: print("{}: process {} start to prepare vasp input files".format(get_time_str(), rank), flush=True)      
        t1, comm_period = time.time(), 300
        if os.path.isfile(skip_signal_file_path):
            print("{}: process {} finds __skip__ under HTC_CWD. Skip input file preparation".format(get_time_str(), rank), flush=True)
            structure_file_sublist = []
        synchron()
        for structure_file in structure_file_sublist:
            try:
                #pre_and_post_process returns the number of prepared calculations
                max_no_of_ready_jobs -= pre_and_post_process(structure_file, structure_file_folder, cal_folder=cal_folder, workflow=workflow)
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
            if continue_running == False: break
            if debugging: print("{}: process {} finished input preparation for {}".format(get_time_str(), rank, structure_file), flush=True)
            if os.path.isfile(stop_file_path): break

            if os.path.isfile(update_now_file_path):
                #cal_status = check_calculations_status(cal_folder=cal_folder, workflow=workflow)
                cal_status = check_calculations_status_in_parallel_or_series(cal_folder=cal_folder, workflow=workflow, scatter=False)
                if rank == 0:
                    write_cal_status(cal_status, htc_job_status_file_path)
                    os.remove(update_now_file_path)
            if os.path.isfile(change_signal_file_path):
                cal_status = check_calculations_status_in_parallel_or_series(cal_folder=cal_folder, workflow=workflow, scatter=False)
                #cal_status = check_calculations_status(cal_folder=cal_folder, workflow=workflow)
                if rank == 0:
                    write_cal_status(cal_status, htc_job_status_file_path)
                    os.remove(change_signal_file_path)
                    
            #Every process individually checks cal status instead of receiving from process 0 
            #--> Avoid a deadlock state in process 1, 2, ..., size-1 if process 0 encounters an error
            #if max_no_of_ready_jobs < 1:
            #    #cal_status = check_calculations_status(cal_folder=cal_folder, workflow=workflow)
            #    cal_status = check_calculations_status_in_parallel_or_series(cal_folder=cal_folder, workflow=workflow)
            #    write_cal_status(cal_status, htc_job_status_file_path)
            #    max_no_of_ready_jobs = (workflow[0]["max_no_of_ready_jobs"] - len(cal_status["ready_folder_list"]) - len(cal_status["prior_ready_folder_list"]))/size
            #    del cal_status
            #    if max_no_of_ready_jobs < 1: break

        if os.path.isfile(stop_file_path): continue
        if continue_running == False: break
        if debugging: print("{}: finished input file preparation in process {}".format(get_time_str(), rank), flush=True)
        
        synchron()
        
        cal_status = check_calculations_status_in_parallel_or_series(cal_folder=cal_folder, workflow=workflow, scatter=False)
        if rank == 0:
            if debugging: print("{}: process 0 starts submitting ready jobs".format(get_time_str()), flush=True)
            #cal_status = check_calculations_status(cal_folder=cal_folder, workflow=workflow)
            submit_jobs(cal_jobs_status=cal_status, workflow=workflow, max_jobs_in_queue=max_running_job)
        else:
            if debugging: print("{}: process {} is waiting for process 0 to finish job submission".format(get_time_str(), rank), flush=True)
        synchron()
        continue_running = comm.bcast(continue_running, root=0)
        if debugging: print("{}: Process {} found that process 0 completed job submission.".format(get_time_str(), rank), flush=True)
        if continue_running == False: break
            
        cal_status = check_calculations_status_in_parallel_or_series(cal_folder=cal_folder, workflow=workflow, scatter=False)
        if rank == 0:
            #cal_status = check_calculations_status(cal_folder=cal_folder, workflow=workflow)      
            write_cal_status(cal_status, htc_job_status_file_path)
            
            #check if all calculations are complete. If this is the case, stop. At the end, all calculations should be labeled by signal file __done__, __skipped__, __done_cleaned_analyzed__ and __done_failed_to_clean_analyze__
            no_of_ongoing_jobs = sum([len(job_list) for job_status, job_list in cal_status.items() if job_status not in ["done_folder_list", "skipped_folder_list", "done_cleaned_analyzed_folder_list", "done_failed_to_clean_analyze_folder_list"]])
            if no_of_ongoing_jobs == 0:
                output_str = "All calculations have finished --> Stop this program."
                print(output_str)
                with open(htc_job_status_file_path, "a") as f:
                    f.write("\n***" + output_str + "***")
                continue_running = False
        synchron()
        continue_running = comm.bcast(continue_running, root=0)
        if debugging: print("{}: Process {} found that process 0 completed job submission.".format(get_time_str(), rank), flush=True)
        if continue_running == False: break
        
        if rank == 0:
            #If cal_status is unchanged for the 1000 consecutive scannings, also stop.
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
        synchron()
        continue_running = comm.bcast(continue_running, root=0)
        if debugging: print("{}: Process 0 tells process {} that cal status is still updating.".format(get_time_str(), rank), flush=True)
        if continue_running == False: break
            
        if rank == 0:
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
                    os.remove(update_input_file_path)
                    break
                else:
                    time.sleep(10)
        synchron()
        if os.path.isfile(update_input_file_path):
            if debugging: print("{}: __update_input__ is found found in HTC_CWD. Process {} reads the newly pre-defined calculation workflow".format(get_time_str(), rank), flush=True)
            workflow = read_workflow()
            if rank == 0:
                os.remove(update_input_file_path)
                if debugging: print("{}: process 0 removes __update_input__".format(get_time_str()), flush=True)
                
        synchron()
        if debugging: print("\n{}: ***process {} arrives at the end of the while loop. Will enter the next round of iteration.***\n".format(get_time_str(), rank), flush=True)
        synchron()

