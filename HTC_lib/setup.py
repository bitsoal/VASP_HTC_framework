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
        
    print("You can find the main python sript htc_main.py under {}".format(os.path.join(os.getcwd(), "VASP")))
    print("What's next:")
    print("\t1. COPY htc_main.py to the folder where the calculations are going to be run. DO NOT move htc_main.py.")
    print("\t2. set HTC_calculation_setup_file under that folder to define the calculation workflow.")
    print("\t3. A. run `nohup python htc_main.py >htc_out 2>&1&` on the command line to run it as a nohupping backgrounded job.")
    print("\t   B. Or put `python htc_main.py >htc_out 2>&1 in a script`and submit it to the batch scheduler (Use 1 cpu and 1 thread only).")
    print("\n***Note that whenever this package is moveed to another place, DO re-run this script (>>>python setup.py)!***\n")
    print("Bye Bye ^_^")

