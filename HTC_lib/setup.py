#!/usr/bin/env python
# coding: utf-8

# In[2]:


import os, platform
from pathlib import Path


# In[8]:


if platform.system() == 'Windows':
    print("We find that you are trying to set up this package on *Windows*. Usually it should be on *Linux*.")
    setup = True if "yes" in input("Is this really what you want? yes or no: ").strip().lower() else False
else:
    setup = True
    
if setup == False:
    print("Quit.")


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
                print("***Successfully update HTC_package_path to {} in {}".format(new_HTC_package_path, python_file))
    
    print("\n***Done***\n")
    
    print("***Note that due to the requirement of the VASP license, we are unable to distribute POTCAR.")
    print("Nevertheless, we provide a bash script named write_potcar.sh under /HTC_lib/VASP/POTCAR.")
    print("write_potcar.sh reads the atomic species list from POSCAR, retrives POTCAR of each atomic species from a POTCAR folder", end=" ")
    print("and concatenates them into POTCAR in the same order as in POSCAR.")
    print("You need to set variable 'POTCAR_loc' in write_potcar.sh to the absolute path to the POTCAR folder")
    print("Pls ensure that the POTCAR of each atomic species in the POTCAR folder is named as merely the name of that atomic species.")
    print("e.g. O is the POTCAR associated with Oxygen; V is the POTCAR associated with Vanadium")
    print("If you want to use V_sv, also rename it as V.")
    print("We prepared a bash script (/HTC_lib/VASP/POTCAR/vasp_recommended_paw_psp.sh) to faciliate the POTCAR preparation for each atomic species.\n")
        
    print("You can find the main python sript htc_main_mpi.py or htc_main_ProcessPoolExecutor.py under {}".format(os.path.join(os.getcwd(), "VASP")))
    print("\t*htc_main_mpi.py is based on mpi4py and parallelization applies to VASP input file preparation and calculation status update.")
    print("\t*htc_main_ProcessPoolExecutor.py is based on python class ProcessPoolExecutor and parallelization applies to VASP input file preparation and calculation status update.")
    print("\tOf course, if there is just one process allocated, neither would invoke parallelization.")
    print("What's next:")
    print("\t1. COPY htc_main_mpi.py or htc_main_ProcessPoolExecutor.py to the folder where the calculations are going to be run. After that, DO NOT move the main script.")
    print("\t2. Set HTC_calculation_setup_file or HTC_calculation_setup_folder (preferred) under that folder to define the calculation workflow.")
    print("\t3. Call these main scripts as follows:")
    print("\t\t*`mpirun -n x python htc_main_mpi.py > htc_out 2>&1`, where x is the number of requested cpus/cores")
    print("\t\t*`python thtc_main_ProcessPoolExecutor.py > htc_out 2>&1`. 'max_workers' in the setup of the first step specifies the number of requested cpus/cores for parallelization.")
    print("\t Note that normally, you can not run the above command in the login node of a super computing cluster.")
    print("\tYou need to put the command into a script and submit it through a job scheduling system, e.g. PBS or LSF.")
    print("\n***Note that whenever this package is moved to another place, DO re-run this script (>>>python setup.py)!***\n")
    print("Bye Bye ^_^")

