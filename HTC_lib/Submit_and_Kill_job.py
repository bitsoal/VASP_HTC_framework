
# coding: utf-8

# # created on Feb 18 2018

# In[2]:


import os, shutil, subprocess
import re

from Utilities import get_time_str
from Error_checker import Queue_std_files


# In[ ]:


def submit_jobs(ready_jobs, workflow, max_jobs_in_queue=30):
    """
    submit jobs.
    input arguments:
        - ready_jobs (list): a list of absolute pathes where the calculation are ready to carry out.
        - workflow: the return of function parse_calculation_workflow, which define a set of DFT calculations and 
            related pre- and post- processes
        - max_jobs_in_queue (int): default 30
    """
    available_submissions = max_jobs_in_queue - len(Job_management.check_jobs_in_queue_system(workflow=workflow))
    if available_submissions > len(ready_jobs):
        available_submissions = len(ready_jobs)
    if available_submissions < 0:
        available_submissions = 0
        
    for i in range(available_submissions):
        cal_loc = ready_jobs[i]
        Job_management(cal_loc, workflow).submit()


# In[5]:


def kill_error_jobs(error_jobs, workflow):
    """
    kill error jobs.
    input arguments:
        - error_jobs (list): a list of absolute pathes where errors have been detected.
        - workflow: the return of function parse_calculation_workflow, which define a set of DFT calculations and 
            related pre- and post- processes
    """
    for cal_loc in error_jobs:
        Job_management(cal_loc, workflow).kill()


# def check_jobs_in_queue_system(cmd=["bjobs", "-w"]):
#     """
#     check and return jobs' status in queue.
#     """
#     result = subprocess.check_output(cmd)
#     lines = [line.strip() for line in result.split("\n") if line.strip()]
#     if len(lines) == 0:
#         return []
#     else:
#         return lines

# In[4]:


class Job_management():
    """
    Manage the job under under directory cal_loc.
    input arguments:
        - cal_loc (str): the location of the calculation.
        - workflow: the return of function parse_calculation_workflow, which define a set of DFT calculations and 
            related pre- and post- processes
    Operation:
        - If __ready__ exists under cal_loc, submit job and __ready__ --> __running__
        - If __kill__ exists under cal_loc, kill the job and __kill__ --> __killed__
        - check_jobs_in_queue_system method will return a dictionary where the keys are queue ids and values are job status.
        - is_in_queue method will check whether the calculation under cal_loc is in queue. 
                return queue id if found; otherwise return False
    """
    
    def __init__(self, cal_loc, workflow):
        self.cal_loc = cal_loc
        self.log_txt_loc, self.firework_name = os.path.split(cal_loc)
        self.log_txt = os.path.join(self.log_txt_loc, "log.txt")
        self.workflow = workflow
        self.firework = self.find_firework_from_workflow()
        
        self.job_query_cmd = workflow[0]["job_query_command"].split("@")
        self.job_killing_cmd = workflow[0]["job_killing_command"]
        self.queue_id_file = workflow[0]["where_to_parse_queue_id"]
        self.queue_id_file = os.path.join(self.cal_loc, self.queue_id_file)
        self.re_to_queue_id = workflow[0]["re_to_parse_queue_id"]
    
    def find_firework_from_workflow(self):
        for firework in self.workflow:
            if firework["firework_folder_name"] == self.firework_name:
                return firework
    
    @classmethod
    def check_jobs_in_queue_system(cls, workflow):
        job_query_cmd = workflow[0]["job_query_command"].split("@")
        
        result = subprocess.check_output(job_query_cmd)
        lines = [line.strip() for line in result.split("\n") if line.strip()]
        if len(lines) == 0:
            return []
        else:
            return lines[1:]
    
    def find_queue_id(self):
        #if not os.path.isfile(os.path.join(self.cal_loc, "__running__")):
        #    with open(self.log_txt, "a") as f:
        #        f.write("{} Error: no __running__ under {}".format(get_time_str(), self.firework_name))
        #       f.write(" --> the calculation has not started yet and cannot find queue id")
        #        f.write("\t\t\t create __error__\n")
        #        open(os.path.join(self.cal_loc, "__error__"), "w").close()
        #    return None
        assert os.path.isfile(self.queue_id_file), "Error: cannot find {} to parse queue id under {}".format(self.queue_id_file, self.cal_loc)
        with open(self.queue_id_file, "r") as f:
            for line in f:
                m = re.findall(self.re_to_queue_id, line)
                assert len(m)==1, "Error: fail to parse queue ID Given {}".format(self.re_to_queue_id)
                return m[0]
        raise Exception("Cannot find queue id in {}".format(self.cal_loc))
        
    def is_cal_in_queue(self):
        queue_id = self.find_queue_id()
        for job_summary in Job_management.check_jobs_in_queue_system(self.workflow):
            if queue_id in job_summary:
                return True
        return False
    
    def kill(self):
        queue_id = self.find_queue_id()
        if self.is_cal_in_queue():
            if not os.path.isfile(os.path.join(self.cal_loc, "__error__")):
                print("Folder: {}".format(self.cal_loc))
                print("\t\t\tThe job encounters errors.")
                print("\t\t\tTo kill this running job, __error__ must be present.")
                raise Exception("See error information above.")
                
            dir0 = os.getcwd()
            os.chdir(self.cal_loc)
            os.system(self.job_killing_cmd +" "+ queue_id)
            os.rename("__error__", "__killed__")
            os.chdir(dir0)
            with open(self.log_txt, "a") as f:
                f.write("{} Kill: move to {}\n".format(get_time_str(), self.firework_name))
                f.write("\t\t\tkill the job via cmd {}\n".format(self.job_killing_cmd + " " + queue_id))
                f.write("\t\t\t __error__ --> __killed__\n")
                f.write("\t\t\tmove back to {}\n".format(dir0))
        else:
            os.rename(os.path.join(self.cal_loc, "__error__"), os.path.join(self.cal_loc, "__killed__"))
            with open(self.log_txt, "a") as f:
                f.write("{} Kill: the job has be terminated under {}\n".format(get_time_str(), self.firework_name))
                f.write("\t\t\tSo no need to kill\n")
                f.write("\t\t\t__error__ --> __killed__\n")
                
    def submit(self):
        if os.path.isfile(os.path.join(self.cal_loc, self.workflow[0]["where_to_parse_queue_id"])) and self.is_cal_in_queue():
            with open(self.log_txt, "a") as f:
                f.write("{} INFO: at {}\n".format(get_time_str(), self.firework_name))
                f.write("\t\t\tThe job has been found in the queue system. No need to submit again.\n")
            return True
        
        error_checking_files = ["OUTCAR", "OSZICAR", self.workflow[0]["vasp.out"]]
        with open(self.log_txt, "a") as f:
            f.write("{} Submission: at {}\n".format(get_time_str(), self.firework_name))
            f.write("\t\t\tBefore the job submission, remove certain VASP files from which error checkers check errors.\n")
            for file_ in error_checking_files:
                if os.path.isfile(os.path.join(self.cal_loc, file_)):
                    os.remove(os.path.join(self.cal_loc, file_))
                    f.write("\t\t\t\tremove {}\n".format(file_))
            f.write("\t\t\t\tremove the queue stdout and stderr files if found\n")
            Queue_std_files(cal_loc=self.cal_loc, workflow=self.workflow).remove_std_files()
        
        dir0 = os.getcwd()
        os.chdir(self.cal_loc)
        with open(self.log_txt, "a") as f:
            f.write("{} INFO: move to {}\n".format(get_time_str(), self.firework_name))
        assert os.path.isfile("INCAR"), "Error: no INCAR under {}".format(job_folder)
        assert os.path.isfile("POTCAR"), "Error: no POTCAR under {}".format(job_folder)
        assert os.path.isfile("KPOINTS"), "Error: no KPOINTS under {}".format(job_folder)
        assert os.path.isfile("POSCAR"), "Error: no POSCAR under {}".format(job_folder)
        
        job_submission_script = os.path.split(self.firework["job_submission_script"])[1]
        if not os.path.isfile(job_submission_script):
            if os.path.isfile(self.firework["job_submission_script"]):
                shutil.copyfile(self.firework["job_submission_script"], job_submission_script)
                with open(self.log_txt, "a") as f:
                    f.write("{} INFO: copy {} from {}\n".format(get_time_str(), job_submission_script, self.firework["job_submission_script"]))
            else:
                assert 1 == 2, "Error: Cannot find job submission script"
                
        os.system(self.firework["job_submission_command"])
        signal_file = "__ready__" if os.path.isfile("__ready__") else "__prior_ready__"
        os.rename(signal_file, "__running__")
        os.chdir(dir0)
        with open(self.log_txt, "a") as f:
            f.write("{} INFO: submit job via {}.\n".format(get_time_str(), self.firework["job_submission_command"]))
            f.write("\t\t\t{} --> __running__\n".format(signal_file))
            f.write("\t\t\t move back to {}\n".format(dir0))        


# def submit_jobs(ready_folder_list, workflow, max_jobs_in_queue=30, check_queue_cmd=["bjobs", "-w"]):
#     """
#     Submit jobs.
#     input arguments:
#         - ready_folder_list (list): a list of absolute pathes where the calculations are ready.
#         - max_jobs_in_quene (int): the maximum number of jobs in queue. Default: 30
#         - workflow: the return of function parse_calculation_workflow, which define a set of DFT calculations and 
#             related pre- and post- processes
#         - check_queue_cmd (str): the command to check calculations in the queue system. Default: "bjobs -w"
#     """
#     
#     jobs_in_queue = check_jobs_in_queue_system(check_queue_cmd)
#     available_submissions = max_jobs_in_queue - len(jobs_in_queue)
#     if len(ready_folder_list) < available_submissions:
#         available_submissions = len(ready_folder_list)
#     
#     firework_folder_name_list = [firework["firework_folder_name"] for firework in workflow]
#     dir0 = os.getcwd()
# 
#     for job_folder in ready_folder_list[:available_submissions]:
#         os.chdir(job_folder)
#         log_txt_loc = os.path.split(job_folder)[0]
#         with open(os.path.join(log_txt_loc, "log.txt"), "a") as f:
#             f.write("{} INFO: move to {}\n".format(get_time_str(), os.path.split(job_folder)[1]))
#         assert os.path.isfile("INCAR"), "Error: no INCAR under {}".format(job_folder)
#         assert os.path.isfile("POTCAR"), "Error: no POTCAR under {}".format(job_folder)
#         assert os.path.isfile("KPOINTS"), "Error: no KPOINTS under {}".format(job_folder)
#         assert os.path.isfile("POSCAR"), "Error: no POSCAR under {}".format(job_folder)
#         for firework_ind, firework_folder in enumerate(firework_folder_name_list):
#             if firework_folder in job_folder:
#                 break
#         job_submission_script = workflow[firework_ind]["job_submission_script"]
#         script_name = os.path.split(job_submission_script)[-1]
#         if not os.path.isfile(os.path.split(job_submission_script)[1]):
#             shutil.copyfile(workflow[firework_ind]["job_submission_script"], script_name)
#         os.system(workflow[firework_ind]["job_submission_command"])
#         os.rename("__ready__", "__running__")
#         os.chdir(dir0)
#         with open(os.path.join(log_txt_loc, "log.txt"), "a") as f:
#             #f.write("{} INFO: move to {}\n".format(get_time_str(), job_folder))
#             f.write("{} INFO: submit job via {}.\n".format(get_time_str(), workflow[firework_ind]["job_submission_command"]))
#             f.write("\t\t\t__ready__ --> __running__\n".format(get_time_str()))
#             f.write("{} INFO: move to its parent folder {}\n".format(get_time_str(), dir0))
# 

# class Kill_a_job(object):
#         
#     def __init__(self, cal_loc):
#         self.cal_loc = cal_loc
#         self.log_txt_loc, self.firework_name = os.path.split(cal_loc)
#         self.parse_queue_id_fun_dict = {"GRC": self.parse_queue_id_GRC,"NSCC": None}
#         
#     def kill(self, parse_queue_id_fun_type="GRC", cmd="bkill ", queue_id_file="job_id", prefix=["ls", "ls"], suffix=[".o", ".e"]):
#         """
#         Kill the running VASP job at cal_loc via the input cmd, log the job killing and create file __killed__ under cal_loc.
#         input arguments:
#             -cal_loc (str): the location of the calculation.
#             -parse_queue_id_fun (function): a function to parse queue id from some file under cal_loc.
#             -cmd: the command to kill the running job. Default: "bkill "
#             -queue_id_file (str): the file holding the queue id under folder cal_loc. default: "job_id"
#             -prefix (list): a list of strings
#             -suffix (list): a list of strings. 
#             len(prefix) == len(suffix). Remove the files under cal_loc whose prefix and suffix appear 
#                                         in the prefix list and the suffix list at the same position.
#         """
#         queue_id = self.parse_queue_id_fun_dict[parse_queue_id_fun_type](cal_loc, queue_id_file)
#         
#         if queue_id == False:
#             with open(os.path.join(log_txt_loc, "log.txt"), "a") as f:
#                 f.write("{} Error: fail to kill the calculation under {}\n".format(get_time_str(), cal_loc))
#                 f.write("\t\t\t create __fail_to_kill__ under this folder\n")
#             open(os.path.join(cal_loc, "__fail_to_kill__"), "w").close()
#             return False
#     
#         dir0 = os.getcwd()
#         os.chdir(cal_loc)
#         with open(os.path.join(log_txt_loc, "log.txt"), "a") as f:
#             f.write("{} Error: move to {}\n".format(get_time_str(), firework_name))
#         
#         os.system(cmd + str(queue_id))
#         
#         #for prf, suf in enumerate(prefix, suffix)：
#             #os.remove(search_file(cal_loc=self.cal_loc, prefix=))
#         
#     
#         open(os.path.join(cal_loc, "__killed__"), "w").close()
#         
#     
#         os.chdir(dir0)
#         with open(os.path.join(log_txt_loc, "log.txt"), "a") as f:
#             f.write("\t\t\tkill this calculation by calling {} {}\n".format(cmd, queue_id))
#             f.write("\t\t\tcreate file __killed__\n")
#             f.write("\t\tmove back to {}\n".format(dir0))
#         
#     def parse_queue_id_GRC(self, cal_loc, queue_id_file="job_id"):
#         """
#         parse return the intger queue id in file queue_id_file under folder cal_loc.
#         input arguments:
#             -cal_loc (str): the location of the calculation.
#             -queue_id_file (str): the file holding the queue id under folder cal_loc. default: "job_id"
#         """
#         log_txt_loc, firework_name = os.path.split(cal_loc)
#     
#         if not os.path.isfile(os.path.join(cal_loc, queue_id_file)):
#             with open(os.path.join(log_txt_loc, "log.txt"), "a") as f:
#                 f.write("{} Error: no {} under {}\n".format(get_time_str(), firework_name))
#             return False
#         
#         queue_id = None
#         with open(os.path.join(cal_loc, queue_id_file), "r") as f:
#             for line in f:
#                 if "<" in line and ">" in line:
#                     m = re.search("<([0-9]+)>", line)
#                     if m:
#                         queue_id = int(m.group(1))
#                     
#         if queue_id == None:
#             with open(os.path.join(log_txt_loc, "log.txt"), "a") as f:
#                 f.write("Error: fail to parse queue id from file {} under {}".format(queue_id_file, firework_name))
#             return False
#     
#         return queue_id
