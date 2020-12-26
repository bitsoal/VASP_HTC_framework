#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os


# In[2]:


def get_trimed_oszicar(cal_loc, original_oszicar, output_oszicar):
    with open(os.path.join(cal_loc, original_oszicar), "r") as oszicar_f:
        oszicar_lines = list(oszicar_f)
        
    last_eff_line_ind = 0
    for line_ind, line in enumerate(oszicar_lines):
        if "E0=" in line and "F=" in line:
            last_eff_line_ind = line_ind
    
    if last_eff_line_ind == 0:
        return False
    else:
        with open(os.path.join(cal_loc, output_oszicar), "w") as oszicar_f:
            for line in oszicar_lines[:last_eff_line_ind+1]:
                oszicar_f.write(line)
        return True


# In[5]:


if __name__ == "__main__":
    print(get_trimed_oszicar(".", "OSZICAR", "OSZICAR_111"))

