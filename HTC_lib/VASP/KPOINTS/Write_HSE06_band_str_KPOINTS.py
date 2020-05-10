
# coding: utf-8

# In[5]:


import re, os, sys


# In[21]:


def read_band_str_kpoints_from_OUTCAR(cal_loc):
    kpoint_list = []
    with open(os.path.join(cal_loc, "OUTCAR"), "r") as f:
        for line in f:
            if "k-point" in line and 'plane waves' in line:
                kpoint = line.split(":")[1].split("plane waves")[0]
                kpoint_list.append(re.findall("-*[\.0-9]+", kpoint))
    return kpoint_list
                
def read_scf_IBZKPT(cal_loc):
    with open(os.path.join(cal_loc, "IBZKPT"), "r") as f:
        kpoint_list = [line.strip() for line in f if line.strip()]
    no_of_kpoints = int(kpoint_list[1])
    #import pprint
    #pprint.pprint(kpoint_list[:no_of_kpoints+3])
    return kpoint_list[:no_of_kpoints+3]


# In[22]:


def write_HSE06_band_str_KPOINTS(IBZKPT, band_str_KPT):
    IBZKPT[1] = str(int(IBZKPT[1]) + len(band_str_KPT))
    with open("KPOINTS", "w") as f:
        for line in IBZKPT:
            f.write(line + "\n")
        for line in band_str_KPT:
            f.write("{}    {}    {}    ".format(*line) + "0\n")


# In[23]:


if __name__ == '__main__':
    #IBZKPT = read_scf_IBZKPT("data")
    #band_str_KPT = read_band_str_kpoints_from_OUTCAR("data/")
    IBZKPT = read_scf_IBZKPT(sys.argv[1])
    band_str_KPT = read_band_str_kpoints_from_OUTCAR(sys.argv[2])
    write_HSE06_band_str_KPOINTS(IBZKPT, band_str_KPT)

