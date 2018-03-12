
# coding: utf-8

# # created on Feb 18 2018

# In[1]:


import os, shutil, subprocess
import re

from Utilities import get_time_str
from Error_checker import Queue_std_files


# In[2]:


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


# In[3]:


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
        os.chdir(dir0)
        with open(self.log_txt, "a") as f:
            f.write("{} INFO: submit job via {}.\n".format(get_time_str(), self.firework["job_submission_command"]))
            f.write("\t\t\t move back to {}\n".format(dir0))
            
        try:
            self.find_queue_id()
        except:
            with open(self.log_txt, "a") as f:
                f.write("{} Error: {}\n".format(get_time_str(), self.cal_loc))
                if not os.path.isfile(os.path.join(self.cal_loc, "__fail_job_submission__")):
                    f.write("\t\t\tfail to submit the job for the first time\n")
                    f.write("\t\t\tcreate file named __fail_job_submission__\n")
                    open(os.path.join(self.cal_loc, "__fail_job_submission__"), "w").close()
                    return False
                else:
                    f.write("\t\t\tThis is the second time to fail the job submission\n")
                    os.rename(os.path.join(self.cal_loc, signal_file), os.path.join(self.cal_loc, "__error__"))
                    f.write("\t\t\t{} --> __error__\n".format(signal_file))
                    return False
                
        os.rename(os.path.join(self.cal_loc, signal_file), os.path.join(self.cal_loc, "__running__"))
        with open(self.log_txt, "a") as f:
            f.write("\t\t\t under {}\n".format(self.cal_loc))
            f.write("\t\t\t{} --> __running__\n".format(signal_file))
                    

