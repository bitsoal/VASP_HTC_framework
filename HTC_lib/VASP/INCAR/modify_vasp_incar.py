#!/usr/bin/env python
# coding: utf-8

# In[11]:


import os, sys
HTC_package_path = "C:/Users/tyang/Documents/Jupyter_workspace/HTC/python_3"
if  os.path.isdir(HTC_package_path) and HTC_package_path not in sys.path:
    sys.path.append(HTC_package_path)

import pprint

from HTC_lib.VASP.Miscellaneous.Utilities import find_next_name, decorated_os_rename


# In[12]:


def return_duplicate(list_of_strs, excluded_strs = []):
    for a_str in list_of_strs:
        if a_str in excluded_strs:
            continue
        elif list_of_strs.count(a_str) > 1:
            return a_str
    return ""
            


# In[17]:


def modify_vasp_incar(cal_loc, new_tags={}, remove_tags=[], rename_old_incar=True, incar_template=[], valid_incar_tags=[]):
    """
    add new tags and remove obsolete tags in incar.
    input arguments:
        - cal_loc (str): the location of INCAR to be modified, <--required
        - new_tags (dict): new tags to be added,
        - remove_tags (list): incar tags that will be removed
        - rename_old_incar (bool or str): if rename_old_incar is True, rename the old INCAR as INCAR_0, INCAR_1, INCAR_2, etc.
                                        if rename_old_incar is False, the old INCAR will be overwritten by new INCAR.
                                        if rename_old_incar is a string, rename the old INCAR as the string.
                                        Default: True
        - incar_template (list or str): If it is a list, each entry of the list should be an incar tag or a empty string.
                                        If it is a string, it refers to a file of which each line is a incar tag or empty.
                                        The output INCAR will written in the same sequence as incar_template.
                                ***all incar tags in incar_template should in upper cases.***
                                All incar tags that are not in incar_template will be appended alphabetically.
                                        e.g. incar_template = ["SYSTEM", "", "ENCUT", "ISMEAR", "SIGMA", "", "IBRION", "ISIF", ""] and there is two more incar tags: PREC, LWAVE
                                        The output INCAR will have a format below
                                        -------------------------------
                                        SYSTEM = xxx
                                        
                                        ENCUT = xxx
                                        ISMEAR = xxx
                                        SIGMA = xxx
                                        
                                        IBRION = xxx
                                        ISIF = xxx
                                        
                                        PREC = xxx
                                        LWAVE = xxx
                                        -------------------------------
                                        default: []
                                        
        - valid_incar_tags(list or str): 
                                if valid_incar_tags is a string and not empty, all incar tags should be in valid_incar_tags; otherwise raise an error.
                                if valid_incar_tags is a str, it refers to a file of which there is a valid incar tag per line.
                                ***all incar tags in valid_incar_tags should in upper cases.***
                                This is useful to avoid spelling mistakes or unpredictable incar tags due to automic error corrections.
                                if valid_incar_tags is empty, this tag will do nothing.
                                default: []
    return:
        * the valid INCAR dictionary if no modification is made.
        * write INCAR under the folder specified by cal_loc otherwise.
    """
    

    new_tags = {key.upper(): value for key, value in new_tags.items()}
    remove_tags = [tag.upper() for tag in remove_tags]
    
    new_incar_tag_name = new_tags.keys()
    for tag in remove_tags:
        if tag in new_incar_tag_name:
            #import pprint
            print("\n\n**directory: {}".format(cal_loc))
            print("**new_tags:")
            pprint.pprint(new_tags)
            print("**remove_tags:")
            pprint.pprint(remove_tags)
            Error_info = "***You are gonna remove an INCAR tag {} via remove_tags.".format(tag)
            Error_info += "This contradicts the simultaneous attempt to set {} via new_tags**\n\n".format(tag)
            print(Error_info)
            raise Exception("See the error information above.")
            

    incar_dict = {}
    with open(os.path.join(cal_loc, "INCAR"), "r") as incar_f:
        lines = []
        for line in incar_f:
            pairs = line.strip().split("#")[0].strip().strip(";")
            if pairs == "":
                continue
            
            tag_value_pair_list = []
            
            no_of_equal_signs = pairs.count("=")
            no_of_semicolons = pairs.count(";")
            if no_of_equal_signs > 1:
                assert no_of_equal_signs == no_of_semicolons+1,                 "Fail to parse multiple tags in the following line in INCAR: \n{}\nline: {}\n".format(cal_loc, line) +                 "{} semicolons should be used to separate {} tag=value pairs.".format(no_of_equal_signs-1, no_of_equal_signs) +                 " But there are/is {} semicolons".format(no_of_semicolons)
            
            for tag_value_pair in pairs.split(";"):
                tag, value = tag_value_pair.strip().split("=")
                incar_dict[tag.upper().strip()] = value.strip()
                
    incar_dict.update(new_tags)
    for remove_tag in remove_tags:
        if remove_tag in incar_dict.keys():
            del incar_dict[remove_tag]
  


    if isinstance(valid_incar_tags, str):
        valid_incar_tags_str = valid_incar_tags
        with open(valid_incar_tags_str, "r") as valid_incar_tags_f:
            valid_incar_tags = [incar_tag.split("#")[0].strip().upper() for incar_tag in valid_incar_tags_f if incar_tag.strip()]
        duplicate = return_duplicate(valid_incar_tags)
        assert duplicate == "", "{} appears more than once in {}. Pls remove the duplicate".format(duplicate, valid_incar_tags_str)
    valid_incar_tags = [incar_tag.upper() for incar_tag in valid_incar_tags]
    duplicate = return_duplicate(valid_incar_tags)
    assert duplicate == "", "{} appears more than once in valid_incar_tags. Pls remove the duplicate".format(duplicate)
    
    
    
    if valid_incar_tags:
        for incar_tag in incar_dict.keys():
            assert incar_tag in valid_incar_tags, "under {}\n ".format(cal_loc) +             "When we are modifying INCAR as pre-defined, {} is not found in ".format(incar_tag) +             "the valid incar tags defined by valid_incar_tags in HTC_calculation_setup_file.\n" +             "If this is not a spelling error and you want to validize this incar tag, add it in the file specified by valid_incar_tags in HTC_calculation_setup_file."
    
    if new_tags == {} and remove_tags == []:
        return incar_dict

    if isinstance(rename_old_incar, bool):
        if rename_old_incar:
            rename_old_incar = find_next_name(cal_loc=cal_loc, orig_name="INCAR")["next_name"]
            decorated_os_rename(loc=cal_loc, old_filename="INCAR", new_filename=rename_old_incar)
    elif isinstance(rename_old_incar, str):
        decorated_os_rename(loc=cal_loc, old_filename="INCAR", new_filename=rename_old_incar)
    else:
        raise Exception("input argument rename_old_incar of modify_vasp_incar must be either bool or str.")
        

    if isinstance(incar_template, str):
        incar_template_str = incar_template
        with open(incar_template_str, "r") as incar_template_f:
            incar_template = [incar_tag.split("#")[0].strip().upper() for incar_tag in incar_template_f]
        duplicate = return_duplicate(incar_template, excluded_strs=[""])
        assert duplicate == "", "You set {} more than once in {}. Pls remove the duplicate".format(duplicate, incar_template_str)
    incar_template = [incar_tag.upper() for incar_tag in incar_template]
    duplicate = return_duplicate(incar_template, excluded_strs=[""])
    assert duplicate == "", "You set {} more than once in incar_template. Pls remove the duplicate".format(duplicate)
    #if len(incar_template) > 2:
    #    incar_template = [tag_1 for tag_1, tag_2 in zip(incar_template[:-1], incar_template[1:]) if tag_1 != "" or tag_2 != ""]
    
    
    
    to_be_written_incar_tags = incar_dict.keys()
    consumed_incar_tags = []
    output_incar_str = ""
    is_an_empty_line_allowed = True #ensure there is only one empty line between incar tag blocks
    for incar_tag in incar_template:
        if incar_tag in to_be_written_incar_tags:
            output_incar_str += "{} = {}\n".format(incar_tag, incar_dict[incar_tag])
            consumed_incar_tags.append(incar_tag)
            is_an_empty_line_allowed = True
        elif incar_tag == "" and is_an_empty_line_allowed:
            output_incar_str += "\n"
            is_an_empty_line_allowed = False

    left_incar_tags = set(to_be_written_incar_tags).difference(set(incar_template))
    if left_incar_tags: output_incar_str += "\n"
    for incar_tag in sorted(left_incar_tags):
        output_incar_str += "{} = {}\n".format(incar_tag, incar_dict[incar_tag])
        consumed_incar_tags.append(incar_tag)
    assert sorted(to_be_written_incar_tags) == sorted(consumed_incar_tags), "Something wrong with writing INCAR"    
    
            
    with open(os.path.join(cal_loc, "INCAR"), "w") as incar_f:
        incar_f.write(output_incar_str)


# In[19]:


if __name__ == "__main__":
    new_tags={"ISMEAR": "-5"}
    remove_tags= ["IBRION", "EDIFFG", "ISIF", "NSW"]
    rename_old_incar=True
    incar_template=["SYSTEM", "EnCUT","", "", "", "ISMEAR", "SIGMA","", "",  "EDIFF", "PREC", "", "ISPIN", "", "LWAVE", "LCHARG", "NPAR", "LREAL"]
    valid_incar_tags=["SYSTEM", "EnCUT", "ISMEAR", "SIGMA", "EDIFF", "PREC", "", "ISPIN", "", "LWAVE", "LCHARG", "NPAR", "lreal", "algo", "icharg", 
                      "nelm"]
    
    modify_vasp_incar(cal_loc="test/", new_tags=new_tags, remove_tags=remove_tags, rename_old_incar=True, incar_template=incar_template, 
                      valid_incar_tags=valid_incar_tags)

