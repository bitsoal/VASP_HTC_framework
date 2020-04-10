
# coding: utf-8

# # a series of functions to extract various data from VASP OUTCAR

# In[1]:


import re, os


# In[2]:


def find_lattice_vectors_from_OUTCAR(cal_loc="."):
    """
    Find the 3x3 lattice vector from VASP OUTCAR
    input arguments:
        -cal_loc (str): the location of the calculation. Default: "."
    output: a list of 3 entries. Each entry is also a list of 3 float numbers representing a lattice vector.
    """
    with open(os.path.join(cal_loc, "OUTCAR"), "r") as f:
        while True:
            line = next(f)
            if "direct lattice vectors" in line:
                break
                
        lattice_vectors = []
        for i in range(3):
            line = next(f)
            m = re.findall("[0-9\-\.]+", line)
            assert len(m) == 6, "Error: fail to parse lattice vectors from line below:\n%s" % line
            lattice_vectors.append([float(item) for item in m[:3]])
    return lattice_vectors


# In[3]:


def find_recp_lattice_vectors_from_OUTCAR(cal_loc="."):
    """
    Find the 3x3 reciprocal lattice vector from VASP OUTCAR
    output: a list of 3 entries. Each entry is also a list of 3 float numbers representing a reciprocal lattice vector.
    """
    with open(os.path.join(cal_loc, "OUTCAR"), "r") as f:
        while True:
            line = next(f)
            if " reciprocal lattice vectors" in line:
                break
                
        recp_lattice_vectors = []
        for i in range(3):
            line = next(f)
            m = re.findall("[0-9\-\.]+", line)
            assert len(m) == 6, "Error: fail to parse reciprocal lattice vectors from line below:\n%s" % line
            recp_lattice_vectors.append([float(item) for item in m[-3:]])
    return recp_lattice_vectors


# In[4]:


def find_vector_kpoints_from_OUTCAR(cal_loc="."):
    """
    Find the vector kpoints in reciprocal lattice from VASP OUTCAR
    input arguments:
        -cal_loc (str): the location of the calculation. Default: "."
    suppose Nk is the number of kpoints
    output: a list of length Nk. Each entry is a list of length 4, the first 3 float numbers of which denote the vector kpoint,
            while the last float number of which denotes the weigth of this kpoint.
    """
    with open(os.path.join(cal_loc, "OUTCAR"), "r") as f:
        while True:
            if "k-points in reciprocal lattice and weights:" in next(f):
                break
        
        kpoints = []
        for line in f:
            if not line.strip():
                break
            m = line.strip().split()
            assert len(m) == 4, "Error: fail to extract kpoint from line below:\n%s" % line
            kpoints.append([float(item) for item in m])
    return kpoints
        


# In[5]:


def find_Efermi_from_OUTCAR(cal_loc="."):
    """
    Find the Fermi level from VASP OUTCAR
    input arguments:
        -cal_loc (str): the location of the calculation. Default: "."
    output: a float number
    """
    with open(os.path.join(cal_loc, "OUTCAR"), "r") as f:
        for line in f:
            if "E-fermi" in line:
                break
    line = line.strip().split()
    return float(line[2])


# In[6]:


def find_LSORBIT_from_OUTCAR(cal_loc="."):
    """
    Find the value of tag LSORBIT.
    input arguments:
        -cal_loc (str): the location of the calculation. Default: "."
    output: return True if LSORBIT is switched on; return False otherwise
    """
    status = False
    with open(os.path.join(cal_loc, "OUTCAR"), "r") as f:
        for line in f:
            if "LSORBIT" in line:
                if "T" == line.split("=")[1].strip()[0]:
                    status = True
                    break
    return status


# In[7]:


def find_LORBIT_from_OUTCAR(cal_loc="."):
    """
    Find and return the integer value of tag LORBIT.
    input arguments:
        -cal_loc (str): the location of the calculation. Default: "."
    """
    with open(os.path.join(cal_loc, "OUTCAR"), "r") as f:
        for line in f:
            if "LORBIT" in line:
                break
                
    m = line.split("=")[1].strip()
    return int(m.split()[0].strip())


# In[8]:


def find_ISPIN_from_OUTCAR(cal_loc="."):
    """
    Find and return the integer value of tag ISPIN.
    input arguments:
        -cal_loc (str): the location of the calculation. Default: "."
    """
    with open(os.path.join(cal_loc, "OUTCAR"), "r") as f:
        for line in f:
            if "ISPIN" in line:
                break
                
    m = line.split("=")[1].strip()
    return int(m.split()[0].strip())


# In[9]:


def find_ion_types_from_OUTCAR(cal_loc="."):
    """
    input arguments:
        -cal_loc (str): the location of the calculation. Default: "."
    output: a list of ion types which have the same order as the atomic coordinates. Each entry of the list
            is a list of length, the first element of which is atomic species and the second of which is the
            integer number of that species.
    """
    with open(os.path.join(cal_loc, "OUTCAR"), "r") as f:
        ions_per_type = []
        ions_types = []
        
        for line in f:
            if "ions per type" in line:
                m = line.split("=")[1].strip().split()
                assert len(m) > 0, "Error: fail to extract ions per type from the line below:\n%s" % line
                ions_per_type = [int(item) for item in m]
                if len(ions_types) == len(ions_per_type):
                    break
                else:
                    continue
            
            if "TITEL" in line:
                m = line.strip().split()[-2]
                if "_" in m:
                    m = m.split("_")[0]
                ions_types.append(m)
                if len(ions_types) == len(ions_per_type):
                    break
    return [[ion_type, ions] for ion_type, ions in zip(ions_types, ions_per_type)]


# In[10]:


def find_all_ion_indexes_of(target_ion_type, cal_loc="."):
    """
    Given an ion type, find and return all indexes of the ions of that type.
    If target ion types are more than one, the input target_ion_type could be list.
    input arguments:
        -target_ion_type
        -cal_loc (str): the location of the calculation. Default: "."
    output: a list of integers. The ion index starts from 0
    """
    
    if type(target_ion_type) == list:
        target_indexes = []
        for target_type in target_ion_type:
            target_indexes += find_all_ion_indexes_of(target_type, cal_loc=cal_loc)
        return target_indexes
    
    ion_types = [ion_type for ion_type in find_ion_types_from_OUTCAR(cal_loc=cal_loc)]
    ion_type_list = [item[0] for item in ion_types]
    if target_ion_type not in ion_type_list:
        print("Error: the input ion type '%s' can not be found in " % target_ion_type)
        print(ion_types)
        return []
    else:
        target_ion_type_ind = ion_type_list.index(target_ion_type)
        
    offset = sum([ion_type[1] for ion_type in ion_types[:target_ion_type_ind]])
    return [offset+i for i in range(ion_types[target_ion_type_ind][1])]


# In[11]:


def find_cart_coords_from_OUTCAR(cal_loc="."):
    """
    Find the cartesian coordinates of atoms from OUTCAR.
    input arguments:
        -cal_loc (str): the location of the calculation. Default: "."
    output: a list whose each entry is a cartesian coordinate of the atom.
    """
    with open(os.path.join(cal_loc, "OUTCAR"), "r") as f:
        cart_coords = []
        while True:
            if " position of ions in cartesian coordinates  (Angst):" in next(f):
                break
        
        for line in f:
            if not line.strip():
                break
            coord = [float(item) for item in line.strip().split()]
            cart_coords.append(coord)
            
    return cart_coords


# In[12]:


def find_frac_coords_from_OUTCAR(cal_loc="."):
    """
    Find the fractional coordinates of atoms from OUTCAR.
    input arguments:
        -cal_loc (str): the location of the calculation. Default: "."
    output: a list whose each entry is a fractional coordinate of the atom.
    """
    with open(os.path.join(cal_loc, "OUTCAR"), "r") as f:
        frac_coords = []
        while True:
            if " position of ions in fractional coordinates (direct lattice)" in next(f):
                break
        
        for line in f:
            if not line.strip():
                break
            coord = [float(item) for item in line.strip().split()]
            frac_coords.append(coord)
            
    return frac_coords


# In[13]:


def find_NELM_from_OUTCAR(cal_loc="."):
    """
    Find NELM from OUTCAR.
    input arguments:
        -cal_loc (str): the location of the calculation. Default: "."
    return the corresponding value if found; otherwise, return None
    """
    
    with open(os.path.join(cal_loc, "OUTCAR"), "r") as f:
        for line in f:
            if "NELM" in line and "=" in line:
                break
                
    
    return int(line.split(";")[0].split("=")[-1].strip())
    
            
            


# In[14]:


def find_NBANDS_from_OUTCAR(cal_loc="."):
    """
    Find NBANDS from OUTCAR.
    input arguments:
        -cal_loc (str): the location of the calculation. Default: "."
    return the corresponding value if found; otherwise, return None
    """
    
    with open(os.path.join(cal_loc, "OUTCAR"), "r") as f:
        for line in f:
            if "NBANDS" in line and "=" in line and "k-points in BZ" in line:
                break
                
    return int(line.strip().split("=")[-1].strip())
            
            


# In[15]:


def find_NSW_from_OUTCAR(cal_loc="."):
    """
    Find NSW from OUTCAR.
    input arguments:
        -cal_loc (str): the location of the calculation. Default: "."
    return the corresponding value if found; otherwise, return None
    """
    
    with open(os.path.join(cal_loc, "OUTCAR"), "r") as f:    
        for line in f:
            if "NSW" in line and "=" in line:
                break
                
    items = [item.strip() for item in line.split(" ") if item.strip()]
    return int(items[2])  


# In[16]:


def find_IBRION_from_OUTCAR(cal_loc="."):
    """
    Find IBRION from OUTCAR.
    input arguments:
        -cal_loc (str): the location of the calculation. Default: "."
    return the corresponding value if found; otherwise, return None
    """
    
    with open(os.path.join(cal_loc, "OUTCAR"), "r") as f:    
        for line in f:
            if "IBRION" in line and "=" in line:
                break
                
    items = [item.strip() for item in line.split(" ") if item.strip()]
    return int(items[2]) 


# In[17]:


def find_EDIFF_from_OUTCAR(cal_loc="."):
    """
    Find EDIFF from OUTCAR.
    input arguments:
        -cal_loc (str): the location of the calculation. Default: "."
    return the corresponding value if found; otherwise, return None
    """
    
    with open(os.path.join(cal_loc, "OUTCAR"), "r") as f:
        for line in f:
            if "EDIFF " in line and "=" in line:
                break
                
    return float(line.split("=")[1].strip().split()[0])


# In[18]:


def find_EDIFFG_from_OUTCAR(cal_loc="."):
    """
    Find EDIFFG from OUTCAR.
    input arguments:
        -cal_loc (str): the location of the calculation. Default: "."
    return the corresponding value if found; otherwise, return None
    """
    
    with open(os.path.join(cal_loc, "OUTCAR"), "r") as f:
        for line in f:
            if "EDIFFG" in line and "=" in line:
                break
    return float(line.split("=")[1].strip().split()[0])


# In[19]:


def find_IALGO_from_OUTCAR(cal_loc="."):
    """
    Find IALGO from OUTCAR.
    input arguments:
        -cal_loc (str): the location of the calculation. Default: "."
    return the corresponding value if found; otherwise, return None
    """
    
    with open(os.path.join(cal_loc, "OUTCAR"), "r") as f:
        for line in f:
            if "IALGO" in line and "=" in line:
                break
    return int([item for item in line.strip().split()][2])


# In[20]:


def find_AMIX_from_OUTCAR(cal_loc="."):
    """
    Find IALGO from OUTCAR.
    input arguments:
        -cal_loc (str): the location of the calculation. Default: "."
    return the corresponding value if found; otherwise, return None
    """
    
    with open(os.path.join(cal_loc, "OUTCAR"), "r") as f:
        for line in f:
            if "AMIX" in line and "=" in line:
                break
                
    return int([item for item in line.strip().split()][2])


# In[22]:


def find_ICHARG_from_OUTCAR(cal_loc="."):
    """
    Find ICHARG from OUTCAR.
    input arguments:
        -cal_loc (str): the location of the calculation. Default: "."
    return the corresponding value if found; otherwise, return None
    """
    
    with open(os.path.join(cal_loc, "OUTCAR"), "r") as f:
        for line in f:
            if "ICHARG" in line and "=" in line:
                break
    return int(line.split()[2])


# In[ ]:


def find_FERMI_from_OUTCAR(cal_loc="."):
    """
    Find fermi from OUTCAR.
    input arguments:
        -cal_loc (str): the location of the calculation. Default: "."
    return the corresponding value if found; otherwise, return None
    """
    
    with open(os.path.join(cal_loc, "OUTCAR"), "r") as f:
        for line in f:
            if "E-fermi" in line:
                break
                
    return float(line.split()[2])


# In[ ]:


def find_LREAL_from_OUTCAR(cal_loc="."):
    """
    Find LREAL from OUTCAR.
    input arguments:
        -cal_loc (str): the location of the calculation. Default: "."
    return the corresponding value if found; otherwise, return None
    """
    
    with open(os.path.join(cal_loc, "OUTCAR"), "r") as f:
        for line in f:
            if line.strip().startswith("LREAL  ="):
                break
                
    return float(line.split()[2])


# In[ ]:


def find_NGXF_NGYF_NGZF_from_OUTCAR(cal_loc="."):
    """
    Find NGXF, NGYF and NGZF from OUTCAR.
    input arguments:
        -cal_loc (str): the location of the calculation. Default: "."
    return the corresponding value if found; otherwise, return None
    """
    with open(os.path.join(cal_loc, "OUTCAR"), "r") as f:
        for line in f:
            if "dimension x,y,z NGXF=" in line:
                break
                
    return [int(value) for value in re.findall("[0-9]+", line)]


# In[21]:


def find_incar_tag_from_OUTCAR(tag, cal_loc="."):
    """
    Find incar tag from OUTCAR.
    input arguments:
        -tag (str): incar tag
        -cal_loc (str): the location of the calculation. Default: "."
    return the corresponding value if found; otherwise, return None
    """
    
    find_func_dict = {"EDIFFG": find_EDIFFG_from_OUTCAR, 
                      "EDIFF": find_EDIFF_from_OUTCAR, 
                      "IBRION": find_IBRION_from_OUTCAR, 
                      "NSW": find_NSW_from_OUTCAR,
                      "NELM": find_NELM_from_OUTCAR,
                      "ISPIN": find_ISPIN_from_OUTCAR, 
                      "LORBIT": find_LORBIT_from_OUTCAR, 
                      "LSORBIT":find_LSORBIT_from_OUTCAR,
                      "IALGO": find_IALGO_from_OUTCAR,
                      "NBANDS": find_NBANDS_from_OUTCAR, 
                      "ICHARG": find_ICHARG_from_OUTCAR,
                      "FERMI": find_FERMI_from_OUTCAR, 
                      "LREAL": find_LREAL_from_OUTCAR, 
                      "NG_X_Y_Z_F": find_NGXF_NGYF_NGZF_from_OUTCAR
                     }
    tag = tag.upper()
    assert tag in find_func_dict.keys(), "Error: currently don't support the search for {} in OUTCAR".format(tag)
    return find_func_dict[tag](cal_loc)
        


# if __name__ == "__main__":
#     print(find_lattice_vectors_from_OUTCAR())
#     print(find_recp_lattice_vectors_from_OUTCAR())
#     print(find_Efermi_from_OUTCAR())
#     print(find_incar_tag_from_OUTCAR("LSORBIT"))
#     print(find_LSORBIT_from_OUTCAR())
#     print(find_incar_tag_from_OUTCAR("LORBIT"))
#     print(find_LORBIT_from_OUTCAR())
#     print(find_incar_tag_from_OUTCAR("ISPIN"))
#     print(find_ISPIN_from_OUTCAR())
#     print(find_ion_types_from_OUTCAR())
#     print(find_all_ion_indexes_of(target_ion_type="S"))
#     print(find_all_ion_indexes_of(target_ion_type="Se"))
#     print(find_all_ion_indexes_of(target_ion_type="Mo"))
#     print(find_all_ion_indexes_of(target_ion_type=['We', 'S', 'Mo', "We"]))
#     print(find_incar_tag_from_OUTCAR("NELM"))
#     print(find_NELM_from_OUTCAR())
#     print(find_incar_tag_from_OUTCAR("NSW"))
#     print(find_NSW_from_OUTCAR())
#     print(find_incar_tag_from_OUTCAR("EDIFF"))
#     print(find_EDIFF_from_OUTCAR())
#     print(find_incar_tag_from_OUTCAR("EDIFFG"))
#     print(find_EDIFFG_from_OUTCAR())
#     print(find_incar_tag_from_OUTCAR("IBRION"))
#     print(find_IBRION_from_OUTCAR())
#     #print(find_incar_tag_from_OUTCAR("NSW"))
#     #import pprint
#     #pprint.pprint(find_cart_coords_from_OUTCAR())
#     #pprint.pprint(find_frac_coords_from_OUTCAR())
#     #pprint.pprint(find_vector_kpoints_from_OUTCAR())
