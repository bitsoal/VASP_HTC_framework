#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os
import argparse
import time
import json


# In[16]:


__author__ = "Yang Tong"
__author_email__ = "yangtong@u.nus.edu"
__version__ = 20210512

__doc__ = """

* What it does

  * This is merely an mpi-aware python script derived from https://github.com/migueldiascosta/packjobs
  
  * With a proper setting (e.g.nnodes, mpiprocs and ompthreads) of a large queue job, running this script in parallel 
    allocates ompthreads cpus to each script. Then, each running scripts uses those cpus to run packed small jobs.

* How to use

  * Run python packjobs.py -h to see all the command line options
  
  * Put the paths of all packed small jobs into a file, one path each line. Let's call this file 'job_list_file'
    Target those small jobs you want to run with a signal file, say "__packed__"

  * Test run with e.g. 2 nodes, 12 procs per job, 2*24/12=4 simultaneous jobs | computational slots, 1 hour:
    Step 1. Set "select=2:ncpus=24:mpiprocs=2:ompthreads=12" and "walltime=01:00:00" in the job submission script of 
            the large queue job (Or equivalent settings for job schedulers other than PBS queues)
    Step 2. Add the command below to the job submission script:
        "mpirun -np 4 python packjobs.py --r vasp_std --ppj 12 --signal-file __packed__ --job-list-file job_list_file > log 2&1

  * Production run with e.g. 50 nodes, 4 procs per job, 50*24/4=300 simultaneous jobs | computational slots, 24 hours:
    Step 1. Set "select=50:ncpus=24:mpiprocs=6:ompthreads=4" and "walltime=24:00:00" in the job submission script of
            the large queue job (Or equivalent settings for job schedulers other than PBS queues)
    Step 2. Add the command below to the job submission script:
        "mpirun -np 300 python packjobs.py --r vasp_std --ppj 4 --signal-file __packed__ --job-list-file job_list_file > log 2&1

* Notes

  * When it is running, this sript introduces a temporary file valid_packed_jobs to store all valid targetted small jobs read 
    from file job_list_file. This is aimed to balance the job load across the multiple computational slots. When a computational
    slot finishes the last assigned targetted job, that slot re-reads file job_list_file and re-writes valid targetted small jobs into 
    file valid_packed_jobs. This way, the valid small jobs are evenly re-distributed across the multiple computational slots.

  * This script does not read and store all targetted small jobs from valid_packed_jobs at the beginning. Instead, it scans
    valid_packed_jobs, and finds and starts running the next targetted small job upon the accomplishment of the last job.
    This way, this script can respond to your update on job_list_file. To do so, just delete file valid_packed_jobs after 
    file job_list_file is updated. Do ensure that job_list_file be always there.

  * Do not simultaneously run multiple large queue jobs on the same job folder. One job folder for one large queue job.
    Otherwise, one targetted small job may be run more than once.
    
  * Ensure that the job list files of multiple large queue jobs do not overlap with one another. Given a job_list_file 
    containing N+n jobs, the following commands remove n duplicates and split them into N/100 sub-job list files, 100 jobs each.
    "sort job_list_file | uniq | split -l 100 -d - sub_packed_job_"
    
  * To stop a large queue job, create a file named as __stop__ on the same folder. It may take some time to wait for all
    running small jobs to finish.
    
  * After a queue job is killed or expires, you may need to clean the queue job, especially those interrupted packed jobs.
    To do so, run: >>python packjobs.py --clean --singal-file __packed__

"""


# In[23]:


running_status_file = "__packed_running__"
complete_status_file = "__packed_done__"
error_status_file = "__packed_error__"


# In[20]:


def parse_arguments():
    """Use argparse to get parameters from the command line"""

    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('-V', '--version', action='version', version='%%(prog)s %s' % __version__)
    
    parser.add_argument("-c", '--clean', action="store_true", dest="clean", 
                        help="if set, clean the previous large queue job, especially those interrupted packed small jobs")
    
    parser.add_argument("--cjlf", "--check-job-list-file", action="store_true", dest="check_job_list_file", 
                        help="if set, check packed jobs in the job list file specified by --jlf or --job-list-file")

    parser.add_argument('-r', '--run', dest='job_cmd', type=str, default="None",
                        help="job command (vasp_std, vasp_ncl or vasp_gam) (mandatory if -c or --clean is not set)")#, required=True)
    
    parser.add_argument("--sf", "--signal-file", dest="signal_file", type=str, 
                        help="file signifying that a VALID ready job (mandatory)", required=True)
    
    parser.add_argument("--jlf", "--job-list-file", dest="job_list_file", type=str, default="None",
                        help="file of which each line is a ready job (mandatory if -c or --clean is not set)")#, required=True)

    parser.add_argument('--ppj', '--procs-per-job', dest='procs_per_job', type=int, default=1,
                        help="number of mpi processes per job (default: 1)")
    
    parser.add_argument('--stdoutf', '--stdard-output-file', dest='stdout_file', type=str, default="",
                        help="file to which the standard output stream is directed (default: don't create it if not set)")
    
    parser.add_argument('--stderrf', '--stdard-error-file', dest='stderr_file', type=str, default="",
                        help="file to which the standard error stream is directed (default: don't create it if not set)")
    
    parser.add_argument("--job-id", dest="job_id", type=str, default="1234", 
                        help="The job identifier assigned to the job by the batch system (default: '1234')")
    
    args = parser.parse_args()
    
    if args.check_job_list_file:
        assert args.job_list_file != "None", "--cjlf or --check-job-list-file is set --> --jlf or --job-list-file must be set."
    elif not args.clean:
        assert args.job_cmd != "None", "-c or --clean is not set --> -r or --run must be set."
        assert args.job_list_file != "None", "-c or --clean is not set --> --jlf or --job-list-file must be set."
        
    if args.job_list_file != "None":
        assert os.path.isfile(args.job_list_file), "--jlf or --job-list-file refers to a non-existent file."
    
    return args


# def read_job_list_0(job_list_file, signal_file, job_list=[]):
#     """
#     args:
#         job_list_file (str): a file containing to-be-calculated jobs, one job per line
#         signal_file (str): a file, the presence of which under a job folder signifies that that to-be-calculated job is valid
#         job_list (list): a list of valid jobs that were previously identified by this function. Default: an empty list
#     What does this function do?
#         Step 1: read job_list_file and identify new valid jobs that do not exist in job_list.
#         Step 3: return job_list
#     """
#     with open(job_list_file, "r") as jlf_f:
#         for line in jlf_f:
#             job_path = line.split("#")[0].strip()
#             if os.path.isdir(job_path):
#                 if os.path.isfile(os.path.join(job_path, signal_file)):
#                     if job_path not in job_list:
#                         job_list.append(job_path)
#     return job_list

# In[2]:


def check_job_list_file(signal_file, job_list_file, print_summary=True):
    """
    Print a summary on valid packed jobs targetted with the signal file specified by argument signal_file in file job_list_file
    """
    with open(job_list_file, "r") as f:
        job_path_list = list(f)
    
    valid_jobs, invalid_jobs = [], []
    for jp in job_path_list:
        jp = jp.strip()
        if os.path.isdir(jp):
            if os.path.isfile(os.path.join(jp, signal_file)):
                valid_jobs.append(jp)
                continue
        invalid_jobs.append(jp)
    
    with open("valid_packed_jobs", "w") as f:
        for jp in valid_jobs:
            f.write(jp + "\n")
    
    with open("invalid_packed_jobs", "w") as f:
        for jp in invalid_jobs:
            f.write(jp + "\n")

    if print_summary:
        output_str = "Among the total of %d jobs in %s, %d are valid and targetted with %s. " % (len(job_path_list), job_list_file, len(valid_jobs), signal_file)
        output_str += "See 'valid_packed_jobs' and 'invalid_packed_jobs'"
        print(output_str, flush=True)


# In[1]:


def count_idle_ranks(main_dir, size, status_folder="rank_status"):
    no_of_idle_ranks = 0
    for rank in range(size):
        if os.path.isfile(os.path.join(main_dir, status_folder, "idle_rank_%d" % rank)):
            no_of_idle_ranks += 1
    
    return no_of_idle_ranks

def update_rank_status_file(main_dir, rank, new_status, job_path="", status_folder="rank_status"):
    assert new_status in ["idle", "running"], "new_status should be either 'idle' or 'running'"
    
    status_folder = os.path.join(main_dir, status_folder)
    if not os.path.isdir(status_folder):
        try:
            os.mkdir(status_folder)
        except FileExistsError:
            pass
    
    idle_rank_file = os.path.join(status_folder, "idle_rank_%d" % rank)
    running_rank_file = os.path.join(status_folder, "running_rank_%d" % rank)
    
    if new_status == "running":
        if os.path.isfile(idle_rank_file):
            os.remove(idle_rank_file)
        assert os.path.isdir(job_path), "Pls provide a valid job path which is going to be written into %s" % os.path.split(running_rank_file)[1]
        with open(running_rank_file, "w") as f:
            f.write(job_path + "\n")
    else:
        if os.path.isfile(running_rank_file):
            os.remove(running_rank_file)
        if not os.path.isfile(idle_rank_file):
            open(idle_rank_file, "w").close()


# In[1]:


def find_next_valid_packed_job(rank, size, signal_file, job_list_file):
    if os.path.isfile(job_list_file):
        with open(job_list_file, "r") as job_list_f:
            job_list = [jp.strip() for jp in job_list_f][rank::size]
        for jp in job_list:
            if os.path.isdir(jp):
                if os.path.isfile(os.path.join(jp, signal_file)):
                    return jp
    return None

def operate_stdout_stderr_files(job_path, stderr_file, stdout_file, action="clean"):
    """
    Clean or write the pseudo standard error and output files.
    args:
        * job_path: a packed calculation job path
        * stderr_file: the prefix or name of the standard error file
        * stdout_file: the prefix or name of the standard output file
        * action: either "clean" (default) or "write"
            * "clean": delete the standard error and output files if existent
            * "write": write the standard error and output files
    """
    assert action in ["clean", "write"], "Argument 'action' must be either 'clean' or 'write'"
    
    stderr_file, stdout_file = stderr_file.strip(), stdout_file.strip()
    
    if action == "clean":
        deleted_file_list = []
        if stderr_file:
            for file in os.listdir(job_path):
                if file.startswith(stderr_file):
                    os.remove(os.path.join(job_path, file))
                    deleted_file_list.append(file)
        if stdout_file:
            for file in os.listdir(job_path):
                if file.startswith(stdout_file):
                    os.remove(os.path.join(job_path, file))
                    deleted_file_list.append(file)
        return deleted_file_list
    else:
        if stderr_file:
            open(os.path.join(job_path, stderr_file), "w").close()
        if stdout_file:
            open(os.path.join(job_path, stdout_file), "w").close()
        
def operate_job_id_file(job_path, job_id, action="write"):
    """
    Write the job id specified by argument 'packed_job_id' into file 'job_id' under folder 'job_path'
    """
    with open(os.path.join(job_path, "packed_job_id"), "w") as f:
        f.write(job_id + "\n")

def operate_lock_file(action="write", lock_file="__locked_valid_packed_jobs_"):
    assert action in ["write", "clean"], "argument 'action' of function 'operate_lock_file' should be either 'write' or 'clean'"
    
    if action == "write":
        if os.path.isfile(lock_file):
            return False
        else:
            open(lock_file, "w").close()
            return True
    else:
        try: #avoid the case where multiple ranks simultaneously try to delete this file.
            os.remove(lock_file)
        except FileNotFoundError:
            pass


# In[25]:


def run_packed_vasp_jobs(rank, size, **kwargs):
    job_list_file = kwargs["job_list_file"]
    signal_file = kwargs["signal_file"]
    job_cmd = kwargs["job_cmd"]
    procs_per_job = kwargs["procs_per_job"]
    stdout_file = kwargs["stdout_file"]
    stderr_file = kwargs["stderr_file"]
    job_id = kwargs["job_id"]
    
    main_dir = os.getcwd()
    count_of_all_ranks_idle = 0
    while count_of_all_ranks_idle <= 5:
        if count_idle_ranks(main_dir, size) < size: #break if all ranks are idle.
            count_of_all_ranks_idle = 0
        else:
            count_of_all_ranks_idle += 1            
            
        if os.path.isfile(os.path.join(main_dir, "__stop__")):
            print("%s: __stop__ is detected --> rank %d stops" % (time.ctime(), rank), flush=True)
            break
        
        #job_path = find_next_valid_packed_job(rank, size, signal_file, job_list_file)
        job_path = find_next_valid_packed_job(rank, size, signal_file, "valid_packed_jobs")
        if job_path == None:
            update_rank_status_file(main_dir, rank, new_status="idle")
            if operate_lock_file(action="write"):
                check_job_list_file(signal_file=signal_file, job_list_file=job_list_file, print_summary=False)
                operate_lock_file(action="clean")
            else:
                time.sleep(30)
        else:
            update_rank_status_file(main_dir, rank, new_status="running", job_path=job_path)
            
            os.remove(os.path.join(job_path, signal_file))            
            open(os.path.join(job_path, running_status_file), "w").close()
            output_str = "%s: Rank %d starts running %s --> Change %s to %s" % (time.ctime(), rank, job_path, signal_file, running_status_file)
            deleted_file_list = operate_stdout_stderr_files(job_path, stderr_file, stdout_file, action="clean")
            output_str += " And deletes %s created by previous calculations." % ", ".join(deleted_file_list)
            print(output_str, flush=True)            
                   
            operate_job_id_file(job_path, job_id, action="write")
            os.chdir(job_path)
            error = os.system("mpirun -host $(hostname) -np %s %s > out 2> error" % (procs_per_job, job_cmd))
            os.chdir(main_dir)
            operate_stdout_stderr_files(job_path, stderr_file, stdout_file, action="write")
            os.remove(os.path.join(job_path, running_status_file))
            if not error:
                open(os.path.join(job_path, complete_status_file), 'w').close()
                print("%s: Rank %d finished %s --> Change %s to %s" % (time.ctime(), rank, job_path, running_status_file, complete_status_file), flush=True)
            else:
                open(os.path.join(job_path, error_status_file), "w").close()
                output_str = time.ctime() + ": Rank %d encountered an error when running %s" % (rank, job_path)
                output_str += "\n\tChange %s to %s\n\tFor more information about the error, " % (running_status_file, error_status_file)
                output_str += "check files 'out' and 'error' under the job folder"
                print(output_str, flush=True)
    
    if not os.path.isfile(os.path.join(main_dir, "__stop__")):
        print("\n%s: Rank %d finished all dispatched packed small jobs read from %s ^_^ Bye-bye\n" % (time.ctime(), rank, job_list_file), flush=True)


# In[26]:


def clean_previous_jobs(signal_file, status_folder="rank_status"):
    """
    What it does
    
        * Clean the previous large job:
        
            * For those interrupted packed jobs (targetted by running_status_file), reset running_status_file
                to that provided by argument 'signal_file'
                
            * Clean all rank status files under the folder specified by argument 'status_folder' (default: 'rank_status')
    """
    status_list = []
    for status in os.listdir(status_folder):
        if status.startswith("running_rank_") or status.startswith("idle_rank_"):
            status_list.append(status)
        else:
            print("Warning: %s under %s is not a rank status file. Skip it." % (status, status_folder))
    
    status_list = sorted(status_list, key=lambda status: int(status.split("_")[-1]))
    for status in status_list:
        if status.startswith("running_rank_"):            
            with open(os.path.join(status_folder, status)) as f:
                job_path = list(f)[0].strip()
            if os.path.isfile(os.path.join(job_path, running_status_file)):
                os.remove(os.path.join(job_path, running_status_file))
                open(os.path.join(job_path, signal_file), "w").close()
                print("%s: Found an interrupted job: %s --> Change %s to %s. Delete it." % (status, job_path, running_status_file, signal_file))
            else:
                print("%s: The latest job run on this rank finished. Delete it." % status)
        else:
            print("%s: Delete it" % status)
        os.remove(os.path.join(status_folder, status))
            
    if len(os.listdir(status_folder)) == 0:
        os.rmdir(status_folder)
        print("\nRemove empty %s" % status_folder)
    else:
        print("\n%s is not empty. You may go to check." % status_folder)
            
    print("\nFinished cleaning. Bye-bye.\n")


# In[ ]:


if __name__ == "__main__":
    from mpi4py import MPI
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()
    
    args_dict = vars(parse_arguments())
    
    if args_dict["check_job_list_file"]:
        check_job_list_file(signal_file=args_dict["signal_file"], job_list_file=args_dict["job_list_file"])
    elif args_dict["clean"]:
        if rank == 0:         
            clean_previous_jobs(signal_file=args_dict["signal_file"])
    else:
        run_packed_vasp_jobs(rank=rank, size=size, **args_dict)

