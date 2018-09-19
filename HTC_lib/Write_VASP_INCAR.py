
# coding: utf-8

# # created on March 31 2018

# In[4]:


import os, pprint

from pymatgen.io.vasp.sets import MPRelaxSet
from pymatgen import Structure

from Utilities import get_time_str, find_next_name, decorated_os_rename, get_current_firework_from_cal_loc
from Query_from_OUTCAR import find_incar_tag_from_OUTCAR


# In[3]:


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
    firework_name = os.path.split(cal_loc)[-1]
    log_txt = os.path.join(cal_loc, "log.txt")
    
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
    #Tags related to partial charge calculations.
    if firework["partial_charge_cal"]:
        new_incar_tags.update(get_partial_charge_tags(cal_loc=cal_loc, firework=firework, workflow=workflow))
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
                
    if firework["bader_charge"]:
        if firework["step_no"] == 1:
            with open(log_txt, "a") as f:
                f.write("{} INFO: in {}\n".format(get_time_str(), firework_name))
                f.write("\t\t\t'bader_charge' is on\n")
                f.write("\t\t\tBut this is the first step. Cannot find NGXF, NGYF, NGZF\n")
                f.write("\t\t\tLet's make a calculation without this INCAR tags first to get the default NGXF, NGYF and NGZF\n")
        else:
            prev_cal = os.path.join(os.path.split(cal_loc)[0], workflow[firework["copy_which_step"]-1]["firework_folder_name"])
            new_incar_tags = get_bader_charge_tags(cal_loc=prev_cal)
            modify_vasp_incar(cal_loc=cal_loc, new_tags=new_incar_tags, rename_old_incar="INCAR.no_bader_charge")
            with open(log_txt, "a") as f:
                f.write("{} INFO: in {}\n".format(get_time_str(), firework_name))
                f.write("\t\t\t'bader_charge' is on\n")
                f.write("\t\t\tretrieve NGXF, NGYF, NGZF from {} and double them\n".format(os.path.split(prev_cal)[1]))
                f.write("\t\tnew incar tags:\n")    
                [f.write("\t\t\t{}={}\n".format(key_, value_)) for key_, value_ in new_incar_tags.items()]
    


# In[18]:


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
    
    new_incar_tag_name = new_tags.keys()
    for tag in comment_tags + remove_tags:
        if tag in new_incar_tag_name:
            #import pprint
            print("\n\n**directory: {}".format(cal_loc))
            print("**new_tags:")
            pprint.pprint(new_tags)
            print("**comment_tags:")
            pprint.pprint(comment_tags)
            print("**remove_tags:")
            pprint.pprint(remove_tags)
            Error_info = "***You are gonna comment of remove an INCAR tag {} via comment_tags/remove_tags.".format(tag)
            Error_info += "This contradicts the simultaneous attempt to set {} via new_tags**\n\n".format(tag)
            print(Error_info)
            raise Exception("See the error information above.")
            

    
    with open(os.path.join(cal_loc, "INCAR"), "r") as incar_f:
        lines = []
        for line in incar_f:
            if line.strip() == "":
                continue
            pairs = line.strip().split("#")[0]
            pairs = pairs.strip().split("!")[0]
            #print(pairs, line)
            if "#" in line:
                comments = "#" + "#".join(line.strip().split("#")[1:])
            elif "!" in line:
                comments = "#" + "!".join(line.strip().split("!")[1:])
            else:
                comments = ""
            for pair in [pair.strip() for pair in pairs.split(";") if pair.strip()]:
                lines.append(pair)
            if len(comments.strip()) > 1:
                lines.append(comments)
                
                    
    incar = []
    for line in lines:
        if line.startswith("#"):
            incar.append(line)
        else:
            #print(line)
            key, value = line.split("=")
            key = key.strip().upper()
            value = value.strip()
            if key in remove_tags:
                continue
            elif key in comment_tags:
                incar.append("#"+line)
            else:
                incar.append([key, value])
                
    valid_tag_ind_dict = {}
    for line_ind, line in enumerate(incar):
        if isinstance(line, list):
            valid_tag_ind_dict[line[0]] = line_ind
            
    for key, value in new_tags.items():
        if key in valid_tag_ind_dict.keys():
            incar[valid_tag_ind_dict[key]][1] = value
        else:
            incar.append([key, value])
            
    #import pprint
    #pprint.pprint(incar)
    
    if new_tags == {} and comment_tags ==[] and remove_tags == []:
        return {item[0]: item[1] for item in incar if isinstance(item, list)}

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
        
    
    with open(os.path.join(cal_loc, "INCAR"), "w") as incar_f:
        for line in incar:
            if isinstance(line, list):
                incar_f.write("{} = {}\n".format(line[0], line[1]))
            elif isinstance(line, str):
                incar_f.write(line+"\n")


# In[18]:


def get_bader_charge_tags(cal_loc):
    """
    Find INCAR tags relevant to Bader Charge Calculations. 
    NGXF, NGYF and NGZF are retrieved from the OUTCAR under cal_loc and doubled
    input argument:
        cal_loc (str): the absolute path under which OUTCAR offers the default NGXF, NGYF, NGZF
    output - a dictionary of INCAR tags:
            LCHARG = .TRUE.
            LAECHG = .TRUE.
            NGXF   = 2 * default value
            NGYF   = 2 * default value
            NGZF   = 2 * default value
    """
    NGXF, NGYF, NGZF = find_incar_tag_from_OUTCAR(cal_loc=cal_loc, tag="NG_X_Y_Z_F")
    return {"LCHARG": ".TRUE.", 
            "LAECHG": ".TRUE.", 
            "NGXF": 2* NGXF, 
            "NGYF":2*NGYF, 
            "NGZF": 2*NGZF}


# In[4]:


def get_partial_charge_tags(cal_loc, firework, workflow):
    if firework["eint_wrt_cbm"] != None:
        step_folder_for_band_edge = workflow[firework["which_step_to_read_cbm_vbm"]-1]["firework_folder_name"]
        vbm_cbm_efermi_path = os.path.join(os.path.split(cal_loc)[0], step_folder_for_band_edge)
        VBM, CBM, VBM_occ, CBM_occ, efermi = read_CBM_VBM_Efermi_from_vasprun(cal_loc=vbm_cbm_efermi_path)
        CBM_ = CBM-efermi
        EINT_lower, EINT_top = firework["eint_wrt_cbm"]
        new_incar_tags = {"EINT": "{}  {}".format(EINT_lower+CBM_, EINT_top+CBM_), "NBMOD": -3, "LPARD": ".TRUE."}
        with open(os.path.join(cal_loc, "log.txt"), "a") as f:
            f.write("{} INFO: partial_charge_cal is set to Yes-->following actions are taken\n".format(get_time_str()))
            f.write("\t\tread band edge information and the Fermi level from {}\n".format(vbm_cbm_efermi_path))
            f.write("\t\tCBM={}\tVBM={}\tCBM_occ={}\tVBM_occ={}\tEfermi={}\n".format(CBM, VBM, CBM_occ, VBM_occ, efermi))
            f.write("\t\tbased on these and EINT_wrt_CBM={}, the following tags are generated and added:\n".format(str(EINT_lower)+"  "+str(EINT_top)))
            f.write("\t\t\tEINT={}\tNBMOD=-3\TLPARD=.TRUE.\n".format(new_incar_tags["EINT"]))
        return new_incar_tags
    elif firework["eint_wrt_vbm"] != None:
        step_folder_for_band_edge = workflow[firework["which_step_to_read_cbm_vbm"]-1]["firework_folder_name"]
        vbm_cbm_efermi_path = os.path.join(os.path.split(cal_loc)[0], step_folder_for_band_edge)
        VBM, CBM, VBM_occ, CBM_occ, efermi = read_CBM_VBM_Efermi_from_vasprun(cal_loc=vbm_cbm_efermi_path)
        VBM_ = VBM-efermi
        EINT_lower, EINT_top = firework["eint_wrt_vbm"]
        new_incar_tags = {"EINT": "{}  {}".format(EINT_lower+VBM_, EINT_top+VBM_), "NBMOD": -3, "LPARD": ".TRUE."}
        with open(os.path.join(cal_loc, "log.txt"), "a") as f:
            f.write("{} INFO: partial_charge_cal is set to Yes-->following actions are taken\n".format(get_time_str()))
            f.write("\t\tread band edge information and the Fermi level from {}\n".format(vbm_cbm_efermi_path))
            f.write("\t\tCBM={}\tVBM={}\tCBM_occ={}\tVBM_occ={}\tEfermi={}\n".format(CBM, VBM, CBM_occ, VBM_occ, efermi))
            f.write("\t\tbased on these and EINT_wrt_VBM={}, the following tags are generated and added:\n".format(str(EINT_lower)+"  "+str(EINT_top)))
            f.write("\t\t\tEINT={}\tNBMOD=-3\TLPARD=.TRUE.\n".format(new_incar_tags["EINT"]))
        return new_incar_tags
    else:
        return {}


# In[1]:


def read_CBM_VBM_Efermi_from_vasprun(cal_loc):
    energy_list, occ_list = [], []
    with open(os.path.join(cal_loc, "vasprun.xml"), "r") as f:
        read_energy_occ = False
        for line in f:
            if "efermi" in line and "name" in line:
                efermi = line.split(">")[1].split("<")[0].strip()
                efermi = float(efermi)
            if '<set comment="kpoint' in line:
                energy_list.append([])
                occ_list.append([])
                read_energy_occ = True
                continue
            if read_energy_occ:
                if "<r>" in line:
                    energy, occ = line.split(">")[1].split("<")[0].strip().split()
                    #print(line, energy, occ)
                    energy_list[-1].append(float(energy))
                    occ_list[-1].append(float(occ))
                else:
                    read_energy_occ = False
                    
    VBM, CBM = -1e10, 1e10
    for energy_list_a_kpoint, occ_list_a_kpoint in zip(energy_list, occ_list):
        for energy, occ in zip(energy_list_a_kpoint, occ_list_a_kpoint):
            if CBM > energy > efermi:
                CBM = energy
                CBM_occ = occ
            elif efermi > energy > VBM:
                VBM = energy
                VBM_occ = occ
    return VBM, CBM, VBM_occ, CBM_occ, efermi


# modify_vasp_incar(".", new_tags={"ISMEAR": 5}) #, remove_tags=["ISYM", "EDIFF", "ISMEARy"], comment_tags=["LWAVE", "IBRION"])

# help(pprint.pprint)
