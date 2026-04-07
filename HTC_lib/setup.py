#!/usr/bin/env python
# coding: utf-8

# In[6]:


import os, platform, json, time
from pathlib import Path


# In[4]:


if platform.system() == 'Windows':
    print("You are attempting to set up this package on *Windows*. Usually it should be on *Linux*.")
    setup = True if "yes" in input("Is this really what you want? yes or no: ").strip().lower() else False
else:
    setup = True
    
if setup == False:
    print("Quit.")


# In[5]:


with open("Version.json", "r") as f:
    package_info = json.load(f)


# In[12]:


output_strings = ["Start to install {} on {} on {}".format(package_info["version"], platform.node(), time.asctime())]
print(output_strings[-1])


# ## *The only thing we need to do to set up this package*
# 
# ### update HTC_package_path in all python files of this package. 

# In[13]:


if setup:
        
    new_HTC_package_path = os.path.split(os.getcwd())[0]
    
    for python_file in Path("VASP").glob("**/*.py"):
        if "__init__.py" == python_file:
            continue
        else:
            with open(python_file, "r") as f:
                lines = list(f)
    
            is_update_needed = False
            for line_ind in range(len(lines)):
                if "HTC_package_path =" in lines[line_ind]:
                    old_HTC_package_path = lines[line_ind].split("=")[1].strip().strip("\"")
                    if new_HTC_package_path != old_HTC_package_path:
                        lines[line_ind] = "HTC_package_path = \"{}\"\n".format(new_HTC_package_path)
                        is_update_needed = True
                    break
                
            if is_update_needed:
                with open(python_file, "w") as f:
                    for line in lines:
                        f.write(line)
                output_strings.append("***Successfully update HTC_package_path to {} in {}".format(new_HTC_package_path, python_file))
                print(output_strings[-1])
    
    output_strings.append("""\n***Successfully Installed The Package***
    
***Note on POTCAR***
    Due to the VASP license requirement, we are unable to distribute POTCAR. 
    Nevertheless, we provide a bash script named write_potcar.sh under /HTC_lib/VASP/POTCAR.
    write_potcar.sh reads the atomic species list from POSCAR, retrives POTCAR of each atomic species from a POTCAR folder, 
    and concatenates them into POTCAR in the same order as in POSCAR.
    You need to set variable 'POTCAR_loc' in write_potcar.sh to the absolute path to the POTCAR folder.
    Pls ensure that the POTCAR of each atomic species in the POTCAR folder is named as merely the name of that atomic species.
    e.g. O is the POTCAR associated with Oxygen; V is the POTCAR associated with Vanadium.
    If you want to use V_sv, also rename it as V.
    We prepared a bash script (/HTC_lib/VASP/POTCAR/vasp_recommended_paw_psp.sh) to faciliate the POTCAR preparation for each atomic species.

***Note on the main python script***
    Two versions of the main python sript are available: 'htc_main_mpi.py' and 'htc_main_ProcessPoolExecutor.py' under {}.
    * htc_main_mpi.py is based on mpi4py and parallelization applies to VASP input file preparation and calculation status update.
    * htc_main_ProcessPoolExecutor.py is based on python class ProcessPoolExecutor and parallelization applies to VASP input file preparation and calculation status update.
    Of course, if there is just one process allocated, neither would invoke parallelization.

***What's next***
    1. COPY htc_main_mpi.py or htc_main_ProcessPoolExecutor.py to the folder where the calculations are going to be run. After that, DO NOT move the main script.
    2. Set HTC_calculation_setup_file or HTC_calculation_setup_folder (preferred) under that folder to define the calculation workflow.
    3. Call these main scripts as follows:
        *`mpirun -n x python htc_main_mpi.py > htc_out 2>&1`, where x is the number of requested cpus/cores;
        *`python htc_main_ProcessPoolExecutor.py > htc_out 2>&1`. 'max_workers' in the setup of the first step specifies the number of requested cpus/cores for parallelization.
    Note that normally, you can not run the above command in the login node of a super computing cluster.
    Instead, you need to put the command into a script and submit it through a job scheduling system, e.g. PBS or LSF.

***Whenever this package is moved to another place, DO re-run this script (>>>python setup.py)!***

Bye Bye ^_^""".format(os.path.join(os.getcwd(), "VASP")))
    
print(output_strings[-1])

with open("installation_log", "w") as f:
    f.write("\n".join(output_strings))

