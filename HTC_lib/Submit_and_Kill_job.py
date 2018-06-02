
# coding: utf-8

# # created on Feb 18 2018

# In[1]:


import os, shutil, subprocess
import re

from Utilities import get_time_str, decorated_os_rename
from Error_checker import Queue_std_files


# In[2]:


def submit_jobs(cal_jobs_status, workflow, max_jobs_in_queue=30):
    """
    submit jobs.
    input arguments:
        - ready_jobs (list): a list of absolute pathes where the calculation are ready to carry out.
        - workflow: the return of function parse_calculation_workflow, which define a set of DFT calculations and 
            related pre- and post- processes
        - max_jobs_in_queue (int): default 30
    """
    no_of_running_jobs, current_no_of_jobs_in_queue = Job_management.count_running_jobs(workflow=workflow)
    
    if no_of_running_jobs < max_jobs_in_queue:
        available_submissions = max_jobs_in_queue - no_of_running_jobs
    else:
        available_submissions = 0
        
    print("{} jobs are running, you can submit {} jobs; {} jobs in queue already".format(no_of_running_jobs, available_submissions, current_no_of_jobs_in_queue))
    
    ready_jobs = cal_jobs_status["prior_ready_folder_list"] + cal_jobs_status["ready_folder_list"]
    available_submissions = min([available_submissions, len(ready_jobs)])
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
    def check_jobs_in_queue_system(cls, workflow, max_times=10):
        job_query_cmd = workflow[0]["job_query_command"].split()
        
        result_list, error_list = [], []
        for i in range(max_times):
            try:
                result = subprocess.check_output(job_query_cmd)
            except subprocess.CalledProcessError as err:
                result_list.append(None)
                error_list.append(err)
            else:
                result_list.append(result)
                error_list.append(None)
                break
                
        if result_list[-1] == None:
            raise Exception("Fail to check job statuses via '{}' for {} tries.             Make sure this command is correct!".format(job_query_cmd, max_times))
        else:
            result = result_list[-1]
        
        lines = [line.strip() for line in result.split("\n") if line.strip()]
        return lines
    
    @classmethod
    def count_running_jobs(cls, workflow):
        if not os.path.isdir(workflow[0]["cal_folder"]):
            return 0
        else:
            jobs_in_queue = cls.check_jobs_in_queue_system(workflow)
            current_no_of_jobs_in_queue = len(jobs_in_queue)
            jobs_in_queue_str = ""
            for job_ in jobs_in_queue:
                jobs_in_queue_str += ("\n"+job_)
                
            running_job_count = 0
            cal_folder = workflow[0]["cal_folder"]
            job_id_file = workflow[0]["where_to_parse_queue_id"]
            for material_folder in os.listdir(cal_folder):
                material_folder = os.path.join(cal_folder, material_folder)
                for firework_folder in os.listdir(material_folder):
                    firework_folder = os.path.join(material_folder, firework_folder)
                    if os.path.isfile(os.path.join(firework_folder, job_id_file)):
                        is_potentially_running = True
                        for signal_file in ["__done__", "__ready__", "__prior_ready__"]:
                            if os.path.isfile(os.path.join(firework_folder, signal_file)):
                                is_potentially_running = False
                                break
                        if is_potentially_running and Job_management(cal_loc=firework_folder, workflow=workflow).find_queue_id() in jobs_in_queue_str:
                            running_job_count += 1
            return running_job_count, current_no_of_jobs_in_queue

        
    def is_cal_in_queue(self):
        queue_id = self.find_queue_id()
        for job_summary in Job_management.check_jobs_in_queue_system(self.workflow):
            if queue_id in job_summary:
                return True
        return False
    
    def find_queue_id(self):
        assert os.path.isfile(self.queue_id_file), "Error: cannot find {} to parse queue id under {}".format(self.queue_id_file, self.cal_loc)
        with open(self.queue_id_file, "r") as f:
            line = next(f)
        m = re.findall(self.re_to_queue_id, line)
        assert len(m)==1, "Error: {}\n\t\t\tfail to parse queue ID Given {}".format(self.cal_loc, self.re_to_queue_id)
        return m[0]
        

    
    def kill(self):
        queue_id = self.find_queue_id()
        if Queue_std_files(cal_loc=self.cal_loc, workflow=self.workflow).find_std_files() == [None, None]:
            if not os.path.isfile(os.path.join(self.cal_loc, "__error__")):
                print("\n{} Kill: {}".format(get_time_str(), self.cal_loc))
                print("\t\t\tTo kill this running job, file named __error__ must be present.\n")
                raise Exception("See error information above.")
                
            exist_status_list, error_list = self._decorated_os_system(cmd=self.job_killing_cmd +" "+ queue_id)
            stdout_file, stderr_file = Queue_std_files(cal_loc=self.cal_loc, workflow=self.workflow).find_std_files()
            ind_dict = {0: "1st", 1: "2nd", 2: "3rd"}
            ind_dict.update({i: '{}th'.format(i+1) for i in range(3, 10)})
            with open(self.log_txt, "a") as f:
                f.write("{} Kill: move to {}\n".format(get_time_str(), self.firework_name))
                f.write("\t\ttry to kill job via cmd {}\n".format(self.job_killing_cmd + " " + queue_id))
                for ind, exist_status in enumerate(exist_status_list):
                    f.write("\t\t\t{} try:\n".format(ind_dict[ind]))
                    f.write("\t\t\t\t\texist-status: {}\n".format(exist_status))
                    f.write("\t\t\t\t\terror: {}\n".format(error_list[ind]))
                if exist_status_list[-1] == 0:
                    f.write("\t\t\tSuccessfully kill the job.\n")
                    f.write("\t\t\t__error__ --> __killed__\n")
                else:
                    f.write("\t\t\tThe cmd execution hits the maximum times (10)\n")
                    if [stdout_file, stderr_file] != [None, None]:
                        f.write("\t\t\tBut ")
                        [f.write("{} ".format(f_name)) for f_name in [stdout_file, stderr_file] if f_name != None]
                        f.write("is|are detected. So the job has been killed somehow...\n")
                        f.write("\t\t\t__error__ --> __killed__\n")
                        f.write("***Let's create __manual__ for test purpose***\n")
                        open(os.path.join(self.cal_loc, "__manual__"), "w").close()
                    else:
                        f.write("\t\t\t__error__ --> __manual__\n")
                f.write("\t\t\tmove back\n")
            if exist_status_list[-1] == 0 or [stdout_file, stderr_file] != [None, None]:
                decorated_os_rename(loc=self.cal_loc, old_filename="__error__", new_filename="__killed__")
            else:
                decorated_os_rename(loc=self.cal_loc, old_filename="__error__", new_filename="__manual__")
        else:
            decorated_os_rename(loc=self.cal_loc, old_filename="__error__", new_filename="__killed__")
            #os.rename(os.path.join(self.cal_loc, "__error__"), os.path.join(self.cal_loc, "__killed__"))
            with open(self.log_txt, "a") as f:
                f.write("{} Kill: the job has been terminated under {}\n".format(get_time_str(), self.firework_name))
                f.write("\t\t\tSo no need to kill\n")
                f.write("\t\t\t__error__ --> __killed__\n")
                
    def _decorated_os_system(self, cmd, max_times=10):
        """
        decorated os.system to tackle the cases where the cmd is not successfully executed.
        input argument:
            - cmd (str): required.
            - max_times (int): the maximum times to try to execute cmd. 
        cmd will be executed continuously until the exist status is 0 (successful).
        output:
            a tuple of length 2:
                - first entry: a list of exist statuses. If error happens, it is None
                - second entry: a list of error information. If no error, it is None
        """
        dir0 = os.getcwd()
        os.chdir(self.cal_loc)
        exist_status_list, error_list = [], []
        for i in range(max_times):
            try:
                status = os.system(cmd)
            except Exception as err:
                error_list.append(err)
                exist_status_list.append(None)
            else:
                error_list.append(None)
                exist_status_list.append(status)
                if status == 0:
                    break
        os.chdir(dir0)
        return exist_status_list, error_list
                
                
    def submit(self):
        if os.path.isfile(os.path.join(self.cal_loc, self.workflow[0]["where_to_parse_queue_id"])):
            try:
                if self.is_cal_in_queue():
                    signal_file = "__ready__" if os.path.isfile(os.path.join(self.cal_loc, "__ready__")) else "__prior_ready__"
                    decorated_os_rename(loc=self.cal_loc, old_filename=signal_file, new_filename="__running__")
                    with open(self.log_txt, "a") as f:
                        f.write("{} Submit: at {}\n".format(get_time_str(), self.firework_name))
                        f.write("\t\t\tThe job has been found in the queue system. No need to submit again.\n")
                        f.write("\t\t\t{} --> __running__\n".format(signal_file))
                    return True
            except Exception as err:
                with open(self.log_txt, "a") as f:
                    f.write("{} Submit: at {}\n".format(get_time_str(), self.firework_name))
                    f.write("\t\t\tAn error raises: {}\n".format(err))
                    f.write("\t\t\tcreate __manual__\n")
                open(os.path.join(self.cal_loc, "__manual__"), "w").close()
                return False
        
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
        assert os.path.isfile("INCAR"), "Error: no INCAR under {}".format(job_folder)
        assert os.path.isfile("POTCAR"), "Error: no POTCAR under {}".format(job_folder)
        assert os.path.isfile("KPOINTS"), "Error: no KPOINTS under {}".format(job_folder)
        assert os.path.isfile("POSCAR"), "Error: no POSCAR under {}".format(job_folder)
        os.chdir(dir0)
        
        
        job_submission_script = os.path.split(self.firework["job_submission_script"])[1]
        if not os.path.isfile(os.path.join(self.cal_loc, job_submission_script)):
            if os.path.isfile(self.firework["job_submission_script"]):
                shutil.copyfile(self.firework["job_submission_script"], os.path.join(self.cal_loc, job_submission_script))
                with open(self.log_txt, "a") as f:
                    f.write("{} INFO: copy {} from {}\n".format(get_time_str(), job_submission_script, self.firework["job_submission_script"]))
            else:
                assert 1 == 2, "Error: Cannot find job submission script"
        
        signal_file = "__ready__" if os.path.isfile(os.path.join(self.cal_loc, "__ready__")) else "__prior_ready__"
        exist_status_list, error_list = self._decorated_os_system(cmd=self.firework["job_submission_command"])
        ind_dict = {0: "1st", 1: "2nd", 2: "3rd"}
        ind_dict.update({i: '{}th'.format(i+1) for i in range(3, 10)})
        with open(self.log_txt, "a") as f:
            f.write("{} Submit: move to {}\n".format(get_time_str(), self.firework_name))
            f.write("\t\ttry to submit job via cmd {}\n".format(self.firework["job_submission_command"]))
            for ind, exist_status in enumerate(exist_status_list):
                f.write("\t\t\t{} try:\n".format(ind_dict[ind]))
                f.write("\t\t\t\t\texist-status: {}\n".format(exist_status))
                f.write("\t\t\t\t\terror: {}\n".format(error_list[ind]))
            if exist_status_list[-1] == 0:
                f.write("\t\t\tSuccessfully submit the job.\n")
                f.write("\t\t\t{} --> __running__\n".format(signal_file))
            else:
                f.write("\t\t\tThe cmd execution hits the maximum times (10)\n")
                f.write("\t\t\t{} --> __manual__\n".format(signal_file))
            f.write("\t\t\tmove back\n")
        if exist_status_list[-1] == 0:
            decorated_os_rename(loc=self.cal_loc, old_filename=signal_file, new_filename="__running__")
        else:
            decorated_os_rename(loc=self.cal_loc, old_filename=signal_file, new_filename="__manual__")
            return False
            
        try:
            self.find_queue_id()
        except:
            with open(self.log_txt, "a") as f:
                f.write("{} Error: {}\n".format(get_time_str(), self.cal_loc))
                if not os.path.isfile(os.path.join(self.cal_loc, "__fail_to_find_job_id__")):
                    f.write("\t\t\tCannot find job id in {} after the job submission for the first time\n".format(self.workflow[0]["vasp.out"]))
                    f.write("\t\t\tcreate file named __fail_to_find_job_id__\n")
                    open(os.path.join(self.cal_loc, "__fail_to_find_job_id__"), "w").close()
                else:
                    f.write("\t\t\tThis is the second time to fail to dinf the job id in {} after job submissions\n".format(self.workflow[0]["vasp.out"]))
                    decorated_os_rename(loc=self.cal_loc, old_filename="__running__", new_filename="__error__")
                    #os.rename(os.path.join(self.cal_loc, signal_file), os.path.join(self.cal_loc, "__error__"))
                    f.write("\t\t\t__running__ --> __error__\n".format(signal_file))
            return False
                
        
                    

