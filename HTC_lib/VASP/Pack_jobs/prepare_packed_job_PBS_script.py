#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os


# In[2]:


##################################################################################################################
##################################################################################################################
#Create a set of PBS scripts in which a certain number of jobs are packed into one.
#In principle, you only need to change the parameters in the current block.

#Enter the filename of which each line is a absolute path to a cacluation which is goning to be packed.
filename = "input_data/packed_cal_list"

#if is_it_a_test = True, we don't check whether the calculatoin path listed in filename exists or not.
is_it_a_test = True #True or False

#How many of the total requested cpus/cores would you like to allocate to each job? (eneter a positive integer and DON'T waste resources!)
ncpus_for_each_subjob = 24

#How many calculations would you like to pack into one job submission script (enter a positive integer)
no_of_subjobs = 30

vasp_cmd = "vasp_std" #"vasp_std", "vasp_gam" or "vasp_ncl"

#The header lines contain the PBS scheduler setup (i.e. no of cpus, walltime, queue name ...)
header_lines = """
#!/bin/sh
#PBS -q normal
#PBS -N "zl_htc_77"
#PBS -l select=25:ncpus=24:mpiprocs=24:ompthreads=1:mem=96g
#PBS -l walltime=24:00:00
##PBS -j oe
#PBS -l place=scatter

# change directory to the one where the job was submitted
cd ${PBS_O_WORKDIR}

module purge
module load VASP/5.4.4-intel-2018b_vdw_2drelax

"""
##################################################################################################################
##################################################################################################################
header_lines = header_lines.strip() + "\n" * 3

ending_bash_cmd = """
cd ${PBS_O_WORKDIR}
while true
do
        if [ `jobs | wc -l` -eq 0 ]
        then
                break
        else
                echo > jobs_log
                date >> jobs_log
                jobs >> jobs_log
                sleep 60
        fi
done

"""


# In[3]:


with open(filename, "r") as f:
    cal_path_list = []
    for line in [line.strip() for line in f if line.strip()]:
        if is_it_a_test:
            cal_path_list.append(line)
        else:
            if os.path.isdir(line):
                cal_path_list.append(line)
            else:
                print("Cannot find a directory named {}".format(line))


count = 1
script_ind = 1
for cal_path in cal_path_list:
    if count == 1:
        packed_job_folder = "packed_job_{}".format(script_ind)
        if not os.path.isdir(packed_job_folder):
            os.mkdir(packed_job_folder)
        script_name = os.path.join(packed_job_folder, "packed_jobs_script_{}.pbs".format(script_ind))
        with open(script_name, "w") as f:
            for line in header_lines:
                f.write(line)
    


    with open(script_name, "a") as f:
        f.write("\n#This is sub-job {}\n".format(count))
        f.write("cd {}\n".format(cal_path))
        f.write("echo ${PBS_JOBID} > job_id\nmv __packed__ __packed_running__\n")
        f.write("mpirun -np {} {} > out ".format(ncpus_for_each_subjob, vasp_cmd))
        f.write("&& touch ${PBS_JOBNAME}.o ${PBS_JOBSNAME}.e && mv __packed_running__ __running__&\n")

    count += 1
    if count > no_of_subjobs:
        count = 1
        script_ind += 1
        with open(script_name, "a") as f:
            f.write(ending_bash_cmd)

