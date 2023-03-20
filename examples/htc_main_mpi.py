#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os, sys, time, pprint, copy

##############################################################################################################
##DO NOT change this part.
##../setup.py will update this variable
HTC_package_path = "/hpctmp/phyv250/NUS_HPC_VASP_seminar_2023_Mar/htc_demo"
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


# In[3]:


def backup_htc_files(workflow):
    htc_input_backup_loc = workflow[0]["htc_input_backup_loc"]
    other_htc_inputs = ["htc_main.py"] + list(workflow[0]["htc_input_backup"])
    if os.path.isfile("HTC_calculation_setup_file"):
        backup_a_file(src_folder=".", src_file="HTC_calculation_setup_file", dst_folder=htc_input_backup_loc, overwrite=False)
    else:
        other_htc_inputs.append("HTC_calculation_setup_folder")
    backup_htc_input_files(src_folder=".", file_or_folder_list=other_htc_inputs, dst_folder=htc_input_backup_loc)    


# In[4]:


def synchron(comm, rank, size):
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


# def merge_dicts(a_list_of_dicts):
#     """
#     Merge a set of the dicts whose value is of type list.
#     """
#     a_list_of_dicts = copy.deepcopy(a_list_of_dicts)
#     merged_dict = a_list_of_dicts[0]
#     for a_dict in a_list_of_dicts[1:]:
#         for key, value in a_dict.items():
#             if key in merged_dict.keys():
#                 merged_dict[key].extend(value)
#             else:
#                 merged_dict[key] = value
#     for key, value in merged_dict.items():
#         merged_dict[key] = sorted(set(value))
#     return merged_dict
# 
# def evenly_divide_a_dict(a_dict, no_of_subdicts):
#     """
#     a_dict is a dictionary whose values are all of type list.
#     This function evenly divides a_dict into no_of_subdicts sub-dictionaries. Each value of a sub-dictionary is just a 1/no_of_subdicts 
#     of the corresponding value of a_dict.
#     Return no_of_subdicts in a list format, e.g. [sub_dict_1, sub_dict_2, sub_dict_3] at no_of_subdicts=3
#     """
#     subdict_list = [{} for i in range(no_of_subdicts)]
#     for key, a_list in a_dict.items():
#         sublist_list = divide_a_list_evenly(a_list=list(set(a_list)), no_of_sublists=no_of_subdicts)
#         for i in range(no_of_subdicts):
#             subdict_list[i][key] = sorted(sublist_list[i])
#     return subdict_list

# In[1]:


def check_calculations_status_in_parallel(comm, rank, size, cal_folder, workflow):
    debugging = (rank == 0)
    
    if rank == 0:
        mat_folder_name_sublist_list = divide_a_list_evenly(a_list=os.listdir(cal_folder), no_of_sublists=size)
    else:
        mat_folder_name_sublist_list = None
    if rank == 0 and debugging: print("{}: process 0 is broadcasting divided mat folder name list".format(get_time_str()), flush=True)
    mat_folder_name_sublist = comm.scatter(mat_folder_name_sublist_list, root=0)
    if debugging: print("{}: Process {} received divided mat folder name list broadcasted by process 0".format(get_time_str(), rank), flush=True)

    if debugging: print("{}: process {} is checking the calculation status under the received material folders".format(get_time_str(), rank), flush=True)
    cal_status_dict = check_calculations_status(cal_folder, workflow, mat_folder_name_list=mat_folder_name_sublist)
    cal_status_dict_list = comm.gather(cal_status_dict, root=0)
    if debugging: print("{}: The obtained calculation status dict is gathered by process 0 from process {}".format(get_time_str(), rank), flush=True)
    if rank == 0:
        if debugging: print("{}: Process 0 is merging gathered calculation status dicts".format(get_time_str()), flush=True)
        total_cal_status_dict = Cal_status_dict_operation.merge_dicts(a_list_of_dicts=cal_status_dict_list)
        
        if debugging: print("{}: Process 0 is dividing the gathered calculation status dict into {} sub dicts and then scatter them among all processes".format(get_time_str(), size), flush=True)
        scattered_cal_status_dict_list = Cal_status_dict_operation.evenly_divide_a_dict(a_dict=total_cal_status_dict, no_of_subdicts=size)
    else:
        total_cal_status_dict = None
        scattered_cal_status_dict_list = None
        
    scattered_cal_status_dict = comm.scatter(scattered_cal_status_dict_list, root=0)
    if debugging: print("{}: Process {} received the scattered sub calculation dict.".format(get_time_str(), rank), flush=True)
    total_cal_status_dict = comm.bcast(total_cal_status_dict, root=0)
    if debugging: print("{}: Process {} received the broadcasted calculation status dict from process 0".format(get_time_str(), rank), flush=True)
    
    return scattered_cal_status_dict, total_cal_status_dict


# In[2]:


def update_cal_status_in_parallel(comm, rank, size, scattered_cal_status, scattered_cal_status_diff, cal_folder, workflow):
    debugging = (rank == 0)
    
    scattered_cal_status = copy.deepcopy(scattered_cal_status)
    
    #print("{}: Process {} is checking these calculations which were just updated.".format(get_time_str(), rank), flush=True)
    #updated_cal_status = check_calculations_status(cal_folder=cal_folder, workflow=workflow, cal_loc_list=cal_loc_list)
    #print("{}: Process {} has obtained the new statuses of these calculations which were just updated.".format(get_time_str(), rank), flush=True)
    #updated_job_status_list = comm.gather(updated_cal_status, root=0)
    #print("{}: The new statues obtained in process {} have been gathered by process 0".format(get_time_str(), rank), flush=True)
    scattered_cal_status_diff_list = comm.gather(scattered_cal_status_diff, root=0)
    if debugging: print("{}: The scattered cal status diff dict in process {} has been gathered by process 0".format(get_time_str(), rank), flush=True)
    old_cal_status_list = comm.gather(scattered_cal_status, root=0)
    if debugging: print("{}: The old scattered cal status dict in process {} has been gathered by process 0".format(get_time_str(), rank), flush=True)
    if rank == 0:
        total_old_cal_status = Cal_status_dict_operation.merge_dicts(old_cal_status_list)
        total_scattered_cal_status_diff = Cal_status_dict_operation.merge_cal_status_diff(scattered_cal_status_diff_list)
        #total_updated_job_status = Cal_status_dict_operation.merge_dicts(updated_job_status_list)
        #cal_status_diff = Cal_status_dict_operation.diff_status_dict(old_cal_status_dict=total_old_cal_status, new_cal_status_dict=total_updated_job_status)
        new_total_cal_status = Cal_status_dict_operation.update_old_cal_status_dict(old_cal_status_dict=total_old_cal_status, cal_status_dict_diff=total_scattered_cal_status_diff)
        new_scattered_cal_status_list = Cal_status_dict_operation.evenly_divide_a_dict(a_dict=new_total_cal_status, no_of_subdicts=size)
    else:
        new_total_cal_status = None
        new_scattered_cal_status_list = None
            
    scattered_cal_status = comm.scatter(new_scattered_cal_status_list, root=0)
    if debugging: print("{}: Process {} received the scattered sub calculation dict.".format(get_time_str(), rank), flush=True)
    new_total_cal_status = comm.bcast(new_total_cal_status, root=0)
    if debugging: print("{}: Process {} received the broadcasted calculation status dict from process 0".format(get_time_str(), rank), flush=True)
    return scattered_cal_status, new_total_cal_status


# In[17]:


def handle_update_now_and_change_signal_file_in_parallel(comm, rank, size, total_cal_status_dict, scattered_cal_status_dict, workflow):
    debugging = (rank == 0)
    
    total_cal_status_dict = copy.deepcopy(total_cal_status_dict)
    scattered_cal_status_dict = copy.deepcopy(scattered_cal_status_dict)
    update_now_file_path = os.path.join(workflow[0]["htc_cwd"], "__update_now__")
    change_signal_file_path = os.path.join(workflow[0]["htc_cwd"], "__change_signal_file__")
    
    if os.path.isfile(update_now_file_path):
        if rank == 0:
            os.remove(update_now_file_path)
            print("{}: Process 0 removed __update_now__".format(get_time_str()), flush=True)
    
    if os.path.isfile(change_signal_file_path):
        if rank == 0:
            new_total_cal_status_dict = change_signal_file(total_cal_status_dict, change_signal_file_path)
            scattered_cal_status_dict_list = Cal_status_dict_operation.evenly_divide_a_dict(new_total_cal_status_dict, no_of_subdicts=size)
        else:
            new_total_cal_status_dict = None
            scattered_cal_status_dict_list = None
        if debugging: print("{}: Process {} is receiving new total cal status dict broadcasted by process 0".format(get_time_str(), rank), flush=True)
        new_total_cal_status_dict = comm.bcast(new_total_cal_status_dict, root=0)
        if debugging: print("{}: Process {} received new total cal status dict broadcasted by process 0".format(get_time_str(), rank), flush=True)
        if debugging: print("{}: Process {} is receiving new scattered cal status dict scattered by process 0".format(get_time_str(), rank), flush=True)
        scattered_cal_status_dict = comm.scatter(scattered_cal_status_dict_list, root=0)
        if debugging: print("{}: Process {} received new scattered cal status dict scattered by process 0".format(get_time_str(), rank), flush=True)

        if rank == 0:
            os.remove(change_signal_file_path)
            print("{}: Process 0 removed __change_signal_file__".format(get_time_str()), flush=True)
        return scattered_cal_status_dict, new_total_cal_status_dict
    else:
        return scattered_cal_status_dict, total_cal_status_dict


# In[1]:


if __name__ == "__main__":
    debugging = (rank == 0)
    scattered = False
    
    if debugging: print("{}: process {} is reading the pre-defined calculation workflow".format(get_time_str(), rank), flush=True)
    workflow = read_workflow()
    if rank == 0: 
        if debugging: print("{}: process 0 starts the backup of htc files".format(get_time_str()), flush=True)
        backup_htc_files(workflow=workflow)
        if debugging: print("{}: process 0 finishes the backup of htc files".format(get_time_str()), flush=True)
    elif debugging: print("{}: process {} is waiting for process 0 to finish the backup of htc files".format(get_time_str(), rank), flush=True)
    synchron(comm=comm, rank=rank, size=size)
    
    structure_file_folder = workflow[0]["structure_folder"]
    cal_folder = workflow[0]["cal_folder"]
    
    no_of_structures = len(os.listdir(structure_file_folder))
    assert  no_of_structures >= size, "# of to-be-calculated structures {} should be >= # of requested cores/cpus {}.".format(no_of_structures, size)
    
    if rank == 0 and not os.path.isdir(cal_folder):
        os.mkdir(cal_folder)

    main_dir = os.getcwd()
    stop_file_path = os.path.join(main_dir, "__stop__")
    htc_job_status_file_path = os.path.join(main_dir, "htc_job_status.json")
    scattered_htc_job_status_file_path = os.path.join(main_dir, "scattered_htc_job_status_process_{}.json".format(rank))
    update_now_file_path = os.path.join(main_dir, "__update_now__")
    change_signal_file_path = os.path.join(main_dir, "__change_signal_file__")
    update_input_file_path = os.path.join(main_dir, "__update_input__")
    go_to_sub_signal_file_path = os.path.join(main_dir, "__go_to_submission__")
    scan_all_file_path = os.path.join(main_dir, "__scan_all__")
    
    if rank == 0: # calculation status is checked and updated only in process 0 (master process)
        no_of_same_cal_status, total_cal_status_0 = 0, {}
        open(scan_all_file_path, "w").close()
        if debugging: 
            output_str = "{}: Process 0 created __scan_all__ to ask the program to scan the status of all calculations.\n".format(get_time_str())
            output_str += "\tLater scanning only involves those calculations which are automatically updated by the program.\n"
            output_str += "\tIf you manually changed some calculations' status, you need to create __scan_all__ to obtain all of these manually updated calculations' status"
            print(output_str, flush=True)
    
    if debugging: print("{}: process {} is entering the while loop.".format(get_time_str(), rank), flush=True)
    continue_running = True
    while_loop_period = 600 #seconds
    while continue_running:
        if rank == 0: while_loop_t0 = time.time()
        
        if os.path.isfile(stop_file_path):
            print(">>>Process {} detected file __stop__ in {}\n ---->stop this program in this process.".format(rank, main_dir),flush=True)
            break
            
        ##############################################################
        ##Start of "Update calculation status"
        synchron(comm=comm, rank=rank, size=size)
        if os.path.isfile(scan_all_file_path):
            scattered_cal_status, total_cal_status = check_calculations_status_in_parallel(comm=comm, rank=rank, size=size, cal_folder=cal_folder, workflow=workflow)
            if rank == 0:
                os.remove(scan_all_file_path)
                if debugging: print("{}: Process 0 removed __scan_all__".format(get_time_str()), flush=True)
        scattered_cal_status, total_cal_status = handle_update_now_and_change_signal_file_in_parallel(comm=comm, rank=rank, size=size, total_cal_status_dict=total_cal_status, 
                                                                                                      scattered_cal_status_dict=scattered_cal_status, workflow=workflow)
            
        if rank == 0: 
            Cal_status_dict_operation.write_cal_status(cal_status=total_cal_status, filename=htc_job_status_file_path)
            to_be_updated_status_list = Cal_status_dict_operation.get_to_be_updated_status_list(total_cal_status)
        else:
            to_be_updated_status_list = None
        to_be_updated_status_list = comm.bcast(to_be_updated_status_list, root=0)
        if scattered: Cal_status_dict_operation.write_cal_status(cal_status=scattered_cal_status, filename=scattered_htc_job_status_file_path)
        synchron(comm=comm, rank=rank, size=size)
        for which_status in to_be_updated_status_list:
            sub_job_list = scattered_cal_status[which_status]
            if os.path.isfile(go_to_sub_signal_file_path):
                print("{}: process {} finds __go_to_submission__ under HTC_CWD. Skip update of {}".format(get_time_str(), rank, which_status), flush=True)
                continue
            if which_status in ["sub_dir_cal_folder_list", "done_folder_list"]:
                #Updating them may involve very slow external commands. So we don't process all of them at once
                max_no_of_ready_jobs = int(workflow[0]["max_no_of_ready_jobs"]/size) - len(scattered_cal_status["ready_folder_list"]) - len(scattered_cal_status["prior_ready_folder_list"])
                max_no_of_ready_jobs = min([len(sub_job_list), max_no_of_ready_jobs])
                sub_job_list = sub_job_list[:max_no_of_ready_jobs]
            try:
                if debugging: print("{}: process {} starts updating {}".format(get_time_str(), rank, which_status), flush=True)
                scattered_cal_status_diff = update_job_status(cal_folder=cal_folder, workflow=workflow, which_status=which_status, job_list=sub_job_list, rank=rank)
                if debugging: print("{}: process {} finished update of {}".format(get_time_str(), rank, which_status), flush=True)
            except:
                continue_running = False
                raise                
            finally:
                synchron(comm=comm, rank=rank, size=size)
                continue_running_list = None
                if rank == 0 and debugging: print("{}: Process 0 is gathering the status of updating {} from all processes".format(get_time_str(), which_status), flush=True)
                continue_running_list = comm.gather(continue_running, root=0)
                if debugging: print("{}: Process 0 gathered the status of updating {} from process {}".format(get_time_str(), which_status, rank), flush=True)
                if rank == 0:
                    continue_running = all(continue_running_list)
                if debugging: print("{}: Process {} is receiving the status of updating {} broadcasted by process 0".format(get_time_str(), rank, which_status), flush=True)
                continue_running = comm.bcast(continue_running, root=0)
                if debugging: print("{}: Process {} received the status of updating {} broadcasted by process 0".format(get_time_str(), rank, which_status), flush=True)        
            if continue_running == False: break
            if os.path.isfile(stop_file_path): break
            scattered_cal_status, total_cal_status = update_cal_status_in_parallel(comm=comm, rank=rank, size=size, cal_folder=cal_folder, scattered_cal_status_diff=scattered_cal_status_diff,
                                                                                   scattered_cal_status=scattered_cal_status, workflow=workflow)
            scattered_cal_status, total_cal_status = handle_update_now_and_change_signal_file_in_parallel(comm=comm, rank=rank, size=size, total_cal_status_dict=total_cal_status, 
                                                                                                      scattered_cal_status_dict=scattered_cal_status, workflow=workflow)
            if rank == 0:
                Cal_status_dict_operation.write_cal_status(cal_status=total_cal_status, filename=htc_job_status_file_path)
            if scattered: Cal_status_dict_operation.write_cal_status(cal_status=scattered_cal_status, filename=scattered_htc_job_status_file_path)
            if debugging: print("{}: process {} finished updating {}".format(get_time_str(), rank, which_status), flush=True)
                
        if continue_running == False: break
        if os.path.isfile(stop_file_path): continue
        ##END of "Update calculation status"
        #########################################################################
            
        #########################################################################
        ##Start of "Prepare VASP input files"
        if rank == 0:  
            if debugging: print("{}: Process 0 is dividing the structure list".format(get_time_str()), flush=True)
            structure_file_sublist_list = divide_a_list_evenly(a_list=os.listdir(structure_file_folder), no_of_sublists=size)            
            max_no_of_ready_jobs = workflow[0]["max_no_of_ready_jobs"] - len(total_cal_status["ready_folder_list"]) - len(total_cal_status["prior_ready_folder_list"])
            max_no_of_ready_jobs = int(max_no_of_ready_jobs / size)
        else:
            max_no_of_ready_jobs = 0
            structure_file_sublist_list = None
        if rank == 0 and debugging: print("{}: Process 0 is broadcasting max_no_of_ready_jobs".format(get_time_str()), flush=True)
        max_no_of_ready_jobs = comm.bcast(max_no_of_ready_jobs, root=0)
        if debugging: print("{}: Process {} received max_no_of_ready_jobs broadcasted from process 0".format(get_time_str(), rank), flush=True)
        
        if debugging: print("{}: process {} start to prepare vasp input files".format(get_time_str(), rank), flush=True)      
        t1, comm_period = time.time(), 300
        if os.path.isfile(go_to_sub_signal_file_path):
            if debugging: print("{}: process {} finds __go_to_submission__ under HTC_CWD. Skip input file preparation".format(get_time_str(), rank), flush=True)
            structure_file_sublist = []
        elif max_no_of_ready_jobs <= 0:
            if debugging: print("{}: Process {} finds that the number of ready jobs already reaches the pre-defined max. Skip input file preparation".format(get_time_str(), rank), flush=True)
            structure_file_sublist = []
        else:
            if rank == 0 and debugging: print("{}: Process 0 is broadcasting divided structure list".format(get_time_str()), flush=True)
            structure_file_sublist = comm.scatter(structure_file_sublist_list, root=0)
            if debugging: print("{}: Process {} received divided structure list broadcasted from process 0".format(get_time_str(), rank), flush=True)
        synchron(comm, rank, size)
        
        scattered_cal_status_diff_list = []
        try:
            for structure_file in structure_file_sublist:
                no_of_new_ready_jobs, scattered_cal_status_diff = pre_and_post_process(structure_file, structure_file_folder, cal_folder=cal_folder, workflow=workflow)
                max_no_of_ready_jobs -= no_of_new_ready_jobs
                scattered_cal_status_diff_list.append(scattered_cal_status_diff)
                if debugging: print("{}: process {} finished input preparation for {}".format(get_time_str(), rank, structure_file), flush=True)
                if max_no_of_ready_jobs <= 0:
                    break
                if os.path.isfile(stop_file_path): break
                if os.path.isfile(update_now_file_path): break
                if os.path.isfile(change_signal_file_path): break
                if os.path.isfile(go_to_sub_signal_file_path): break
        except:
            continue_running = False
            if debugging: print("{}: Process {} encountered an error. See below.".format(get_time_str(), rank), flush=True)
            raise
        finally:
            synchron(comm=comm, rank=rank, size=size)
            continue_running_list = comm.gather(continue_running, root=0)
            if rank == 0:
                continue_running = all(continue_running_list)
            continue_running = comm.bcast(continue_running, root=0)
            
        synchron(comm=comm, rank=rank, size=size)
        if continue_running == False: break
        if os.path.isfile(stop_file_path): continue
        if debugging: print("{}: finished input file preparation in process {}".format(get_time_str(), rank), flush=True)
        scattered_cal_status_diff = Cal_status_dict_operation.merge_cal_status_diff(scattered_cal_status_diff_list)
        synchron(comm, rank, size)
        scattered_cal_status, total_cal_status = update_cal_status_in_parallel(comm=comm, rank=rank, size=size, cal_folder=cal_folder, scattered_cal_status_diff=scattered_cal_status_diff,
                                                                               scattered_cal_status=scattered_cal_status, workflow=workflow)
        scattered_cal_status, total_cal_status = handle_update_now_and_change_signal_file_in_parallel(comm=comm, rank=rank, size=size, total_cal_status_dict=total_cal_status, 
                                                                                                      scattered_cal_status_dict=scattered_cal_status, workflow=workflow)
        if rank == 0:
            Cal_status_dict_operation.write_cal_status(cal_status=total_cal_status, filename=htc_job_status_file_path)
        if scattered: Cal_status_dict_operation.write_cal_status(cal_status=scattered_cal_status, filename=scattered_htc_job_status_file_path)
        ## END of "Prepare VASP input files"
        ###############################################################################
        
        ###############################################################################
        ##Start of "Job submission"
        synchron(comm=comm, rank=rank, size=size)
        if rank == 0:
            if os.path.isfile(go_to_sub_signal_file_path): 
                os.remove(go_to_sub_signal_file_path)
                if debugging: print("{}: All processes reach the job submission section. Process 0 removed __go_to_submission__".format(get_time_str()), flush=True)
            if debugging: print("{}: process 0 starts submitting ready jobs".format(get_time_str()), flush=True)
            #cal_status = check_calculations_status(cal_folder=cal_folder, workflow=workflow)
            submitted_job_list = submit_jobs(cal_jobs_status=total_cal_status, workflow=workflow, max_jobs_in_queue=workflow[0]["max_running_job"])
            scattered_submitted_job_list = divide_a_list_evenly(a_list=submitted_job_list, no_of_sublists=size)
        else:
            if debugging: print("{}: process {} is waiting for process 0 to finish job submission".format(get_time_str(), rank), flush=True)
            scattered_submitted_job_list = None
        scattered_submitted_jobs = comm.scatter(scattered_submitted_job_list, root=0)
        old_scattered_cal_status = check_calculations_status(cal_folder=cal_folder, workflow=workflow, cal_loc_list=[])
        new_scattered_cal_status = check_calculations_status(cal_folder=cal_folder, workflow=workflow, cal_loc_list=scattered_submitted_jobs)
        scattered_cal_status_diff = Cal_status_dict_operation.diff_status_dict(old_cal_status_dict=old_scattered_cal_status, new_cal_status_dict=new_scattered_cal_status)
        scattered_cal_status, total_cal_status = update_cal_status_in_parallel(comm=comm, rank=rank, size=size, cal_folder=cal_folder, scattered_cal_status=scattered_cal_status, 
                                                                               scattered_cal_status_diff=scattered_cal_status_diff, workflow=workflow,)
        scattered_cal_status, total_cal_status = handle_update_now_and_change_signal_file_in_parallel(comm=comm, rank=rank, size=size, total_cal_status_dict=total_cal_status, 
                                                                                                      scattered_cal_status_dict=scattered_cal_status, workflow=workflow)
        if rank == 0: 
            Cal_status_dict_operation.write_cal_status(cal_status=total_cal_status, filename=htc_job_status_file_path)
        if scattered: Cal_status_dict_operation.write_cal_status(cal_status=scattered_cal_status, filename=scattered_htc_job_status_file_path)
        synchron(comm=comm, rank=rank, size=size)
        if debugging: print("{}: Process {} found that process 0 completed job submission.".format(get_time_str(), rank), flush=True)
        ##END of "Job submission"
        
        
        #check if all calculations are complete. If this is the case, stop. At the end, all calculations should be labeled by signal file __done__, __skipped__, __done_cleaned_analyzed__ and __done_failed_to_clean_analyze__
        no_of_ongoing_jobs = sum([len(job_list) for job_status, job_list in total_cal_status.items() if job_status not in ["done_folder_list", "skipped_folder_list", "done_cleaned_analyzed_folder_list", "done_failed_to_clean_analyze_folder_list"]])
        if no_of_ongoing_jobs == 0:
            output_str = "{}: Process {} finds that all calculations have finished --> Stop this program in process {}.".format(get_time_str(), rank, rank)
            print(output_str, flush=True)
            with open(htc_job_status_file_path, "a") as f:
                f.write("\n***" + output_str + "***")
            break
        else:
            if debugging: print("{}: Process {} finds that htc has not been complete yet".format(get_time_str(), rank), flush=True)
        synchron(comm=comm, rank=rank, size=size)
        
        if rank == 0:
            #If cal_status is unchanged for the 1000 consecutive scannings, also stop.
            if total_cal_status == total_cal_status_0:
                no_of_same_cal_status += 1
            else:
                total_cal_status_0 = total_cal_status
                no_of_same_cal_status = 0
            if no_of_same_cal_status == 1000:
                with open(htc_job_status_file_path, "a") as f:
                    f.write("\n***" + output_str + "***")
                continue_running = False
        synchron(comm, rank, size)
        continue_running = comm.bcast(continue_running, root=0)
        if continue_running == False: 
            if debugging: print("{}: Process {} finds that cal status remains unchanged for a long time. Stop this program in process {}.".format(get_time_str(), rank, rank), flush=True)
            break
        else:
            if debugging: 
                print("{}: Process {} finds that cal status is still updating.".format(get_time_str(), rank), flush=True)
            
        if rank == 0:
            while (time.time() - while_loop_t0) < while_loop_period:
                if os.path.isfile(stop_file_path):
                    break #Will be handled at the start of the external while loop
                elif os.path.isfile(update_now_file_path):
                    break #Will be handled at the start of the external while loop
                elif os.path.isfile(change_signal_file_path):
                    break #Will be handled at the start of the external while loop
                elif os.path.isfile(update_input_file_path):
                    break #Will be handled at the end of the external while loop
                elif os.path.isfile(scan_all_file_path):
                    break #Will be handled at the start of the external while loop
                else:
                    time.sleep(10)
                while os.path.isfile(os.path.join(main_dir, "__forced_sleep__")):
                    time.sleep(10) 
            while_loop_t0 = time.time()
        synchron(comm, rank, size)
        if os.path.isfile(update_input_file_path):
            if debugging: print("{}: __update_input__ is found found in HTC_CWD. Process {} reads the updated pre-defined calculation workflow".format(get_time_str(), rank), flush=True)
            workflow = read_workflow()
            if rank == 0:
                os.remove(update_input_file_path)
                if debugging: print("{}: process 0 removes __update_input__".format(get_time_str()), flush=True)
                
        synchron(comm, rank, size)
        if debugging: print("\n{}: ***process {} arrives at the end of the while loop. Will enter the next round of iteration.***\n".format(get_time_str(), rank), flush=True)
        synchron(comm, rank, size)

