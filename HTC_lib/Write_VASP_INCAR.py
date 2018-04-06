
# coding: utf-8

# # created on March 31 2018

# In[1]:


import os

from pymatgen.io.vasp.sets import MPRelaxSet
from pymatgen import Structure

from Utilities import get_time_str, find_next_name, decorated_os_rename, get_current_firework_from_cal_loc


# In[2]:


def Write_Vasp_INCAR(cal_loc, structure_filename, workflow):
    """
    Write or modify INCAR in folder cal_loc as follows:
        step I: If no INCAR in cal_loc, write INCAR using pymatgen.io.vasp.sets.MPRelaxSet
        step II: Modify INCAR according to new_incar_tags, comment_incar_tags and remove_incar_tags.
    Input arguments:
        cal_loc (str): the absolute path
        structure_filename (str): the file from which the structure is read using pymatgen.Structure.from_file
        workflow
    """
    
    firework = get_current_firework_from_cal_loc(cal_loc, workflow)
    log_txt_loc, firework_name = os.path.split(cal_loc)
    log_txt = os.path.join(log_txt_loc, "log.txt")
    
    write_INCAR = False
    if not os.path.isfile(os.path.join(cal_loc, "INCAR")):
        structure = Structure.from_file(os.path.join(cal_loc, structure_filename))
        vis = MPRelaxSet(structure=structure)
        vis.incar.write_file(filename=os.path.join(cal_loc, "INCAR"))
        write_INCAR = True
        with open(log_txt, "a") as f:
            f.write("{} INFO: no INCAR in {}\n".format(get_time_str(), firework_name))
            f.write("\t\t\tuse pymatgen.io.vasp.sets.MPRelaxSet to write INCAR\n")
      
    
    
    new_incar_tags = firework["new_incar_tags"]
    comment_incar_tags = firework["comment_incar_tags"]
    remove_incar_tags = firework["remove_incar_tags"]
    if new_incar_tags or comment_incar_tags or remove_incar_tags:
        if write_INCAR:
            modify_vasp_incar(cal_loc=cal_loc, new_tags=new_incar_tags, comment_tags=comment_incar_tags, 
                              rename_old_incar="INCAR.pymatgen", remove_tags=remove_incar_tags)
        else:
            modify_vasp_incar(cal_loc=cal_loc, new_tags=new_incar_tags, comment_tags=comment_incar_tags, 
                              remove_tags=remove_incar_tags)
        with open(log_txt, "a") as f:
            f.write("{} INFO: modify INCAR in {}\n".format(get_time_str(), firework_name))
            if new_incar_tags:
                f.write("\t\tnew incar tags:\n")
                [f.write("\t\t\t{}={}\n".format(key_, value_)) for key_, value_ in new_incar_tags.items()]
            if comment_incar_tags:
                f.write("\t\tcomment incar tags:")
                [f.write("{}\t".format(tag_)) for tag_ in comment_incar_tags]
                f.write("\n")
            if remove_incar_tags:
                f.write("\t\tremove incar tags: ")
                [f.write("{}\t".format(tag_)) for tag_ in remove_incar_tags]
                f.write("\n")
            if write_INCAR:
                f.write("\t\told INCAR --> INCAR.pymatgen\n")
    


# In[3]:


def modify_vasp_incar(cal_loc, new_tags={}, comment_tags=[], remove_tags=[], rename_old_incar=True):
    """
    add new tags and comment obsolete tags in incar.
    input arguments:
        - cal_loc (str): the location of INCAR to be modified, <--required
        - new_tags (dict): new tags to be added,
        - comment_tags (list): tags that will be obsolete by commenting them with "#"
        - remove_tags (list): incar tags that will be removed
        - rename_old_incar (bool or str): if rename_old_incar is True, rename the old INCAR as INCAR_0, INCAR_1, INCAR_2, etc.
                                        if rename_old_incar is False, the old INCAR will be overwritten by new INCAR.
                                        if rename_old_incar is a string, rename the old INCAR as the string.
                                        Default: True
    return the valid INCAR dictionary if no modification is made.
    """
    

    new_tags = {key.upper(): value for key, value in new_tags.items()}
    comment_tags = [tag.upper() for tag in comment_tags]
    remove_tags = [tag.upper() for tag in remove_tags]

    Valid_tags, Commented_tags = {}, {}
    Ordered_tags = []
    with open(os.path.join(cal_loc, "INCAR"), "r") as incar:
        for line in incar:
            items = [item.strip() for item in line.strip().split("=")]
            if len(items)>=2:
                if items[0].startswith("#"):
                    tag = items[0].strip("#").upper().strip()
                    if tag in remove_tags:
                        continue
                    Commented_tags[tag] = items[1]
                    Ordered_tags.append(tag)
                else:
                    tag = items[0].upper()
                    if tag in remove_tags:
                        continue
                    Valid_tags[items[0].upper()] = items[1]
                    Ordered_tags.append(tag)

    for new_tag, value in new_tags.items():
        Valid_tags[new_tag] = value
        if new_tag not in Ordered_tags:
            Ordered_tags.append(new_tag)

    for comment_tag in comment_tags:
        if comment_tag in Valid_tags.keys():
            Commented_tags[comment_tag] = Valid_tags[comment_tag]
            del Valid_tags[comment_tag]
            
    if new_tags == {} and comment_tags == [] and remove_tags == []:
        return Valid_tags

    if isinstance(rename_old_incar, bool):
        if rename_old_incar:
            rename_old_incar = find_next_name(cal_loc=cal_loc, orig_name="INCAR")["next_name"]
            decorated_os_rename(loc=cal_loc, old_filename="INCAR", new_filename=rename_old_incar)
            #shutil.copyfile(os.path.join(cal_loc, "INCAR"), os.path.join(cal_loc, rename_old_incar))
    elif isinstance(rename_old_incar, str):
        decorated_os_rename(loc=cal_loc, old_filename="INCAR", new_filename=rename_old_incar)
        #shutil.copyfile(os.path.join(cal_loc, "INCAR"), os.path.join(cal_loc, rename_old_incar))
    else:
        raise Exception("input argument rename_old_incar of modify_vasp_incar must be either bool or str.")
        
    
    with open(os.path.join(cal_loc, "INCAR"), "w") as incar:
        for tag in Ordered_tags:
            if tag in Valid_tags.keys():
                incar.write("{} = {}\n".format(tag, Valid_tags[tag]))
            else:
                incar.write("#{} = {}\n".format(tag, Commented_tags[tag]))



