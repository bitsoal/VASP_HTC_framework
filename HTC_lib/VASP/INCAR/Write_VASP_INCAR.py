#!/usr/bin/env python
# coding: utf-8

# In[3]:


import pprint,copy, json

import os, sys
HTC_package_path = "C:/Users/tyang/Documents/Jupyter_workspace/HTC/python_3"
if  os.path.isdir(HTC_package_path) and HTC_package_path not in sys.path:
    sys.path.append(HTC_package_path)

from pymatgen.io.vasp.sets import MPRelaxSet
from pymatgen.core import Structure

from HTC_lib.VASP.Miscellaneous.Utilities import get_time_str, find_next_name, decorated_os_rename, get_current_firework_from_cal_loc
from HTC_lib.VASP.Miscellaneous.Query_from_OUTCAR import find_incar_tag_from_OUTCAR
from HTC_lib.VASP.INCAR.modify_vasp_incar import modify_vasp_incar
from HTC_lib.VASP.INCAR.choose_ispin_based_on_prev_cal import choose_ispin_based_on_prev_cal
from HTC_lib.VASP.Miscellaneous.Execute_bash_shell_cmd import Execute_shell_cmd


# In[5]:


def Write_Vasp_INCAR(cal_loc, structure_filename, workflow):
    """
    Write or modify INCAR in folder cal_loc as follows:
        step I: run commands defined by incar_cmd. Of course, there might be no commands to run if incar_cmd is not set
        step II: If no INCAR in cal_loc, write INCAR using pymatgen.io.vasp.sets.MPRelaxSet
        step III: Modify INCAR according to new_incar_tags and remove_incar_tags.
    Input arguments:
        cal_loc (str): the absolute path
        structure_filename (str): the file from which the structure is read using pymatgen.Structure.from_file
        workflow
    """
    
    firework = get_current_firework_from_cal_loc(cal_loc, workflow)
    firework_name = os.path.split(cal_loc)[-1]
    log_txt = os.path.join(cal_loc, "log.txt")
    
    incar_template_list, valid_incar_tags_list = workflow[0]["incar_template_list"], workflow[0]["valid_incar_tags_list"]
    
    if firework["incar_cmd"] != []:
        #The relevant logs will be written by Execute_shell_cmd
        status = Execute_shell_cmd(cal_loc=cal_loc, user_defined_cmd_list=firework["incar_cmd"], where_to_execute=cal_loc, 
                                   defined_by_which_htc_tag="incar_cmd")
        if status == False: return False #If the commands failed to run, stop running the following codes.

    write_INCAR = False
    if not os.path.isfile(os.path.join(cal_loc, "INCAR")):
        structure = Structure.from_file(os.path.join(cal_loc, structure_filename))
        vis = MPRelaxSet(structure=structure)
        vis.incar.write_file(filename=os.path.join(cal_loc, "INCAR"))
        write_INCAR = True
        with open(log_txt, "a") as f:
            f.write("{} INFO: no INCAR in {}\n".format(get_time_str(), firework_name))
            f.write("\t\t\tuse pymatgen.io.vasp.sets.MPRelaxSet to write INCAR\n")
    
    
    
    new_incar_tags = dict([(incar_tag, incar_value) for incar_tag, incar_value in firework["new_incar_tags"].items()])
    remove_incar_tags = firework["remove_incar_tags"]
    #Tags related to partial charge calculations.
    if firework["partial_charge_cal"]:
        new_incar_tags.update(get_partial_charge_tags(cal_loc=cal_loc, firework=firework, workflow=workflow))
    if firework["set_lmaxmix"]:
        lmaxmix = get_lmaxmix(cal_loc)
        if lmaxmix == False: #False means there is something wrong
            return False
        new_incar_tags.update({"LMAXMIX": lmaxmix})
    if firework["ldau_cal"]:
        new_incar_tags.update(generate_Hubbard_U_J_INCAR_tags(cal_loc=cal_loc, U_J_table_filename=firework["ldau_u_j_table"]))
    if "NBANDS" in new_incar_tags:
        new_incar_tags["NBANDS"] = get_nbands(cal_loc=cal_loc, nbands_in_add_new_incar_tags_subblk=new_incar_tags["NBANDS"])
    if "EMAX" in new_incar_tags:
        new_incar_tags["EMAX"] = cal_emax_or_emin(cal_loc=cal_loc, emax_or_emin_setup=new_incar_tags["EMAX"], incar_tag="EMAX")
    if "EMIN" in new_incar_tags:
        new_incar_tags["EMIN"] = cal_emax_or_emin(cal_loc=cal_loc, emax_or_emin_setup=new_incar_tags["EMIN"], incar_tag="EMIN")
    if new_incar_tags or remove_incar_tags:
        if write_INCAR:
            modify_vasp_incar(cal_loc=cal_loc, new_tags=new_incar_tags, rename_old_incar="INCAR.pymatgen", remove_tags=remove_incar_tags, incar_template=incar_template_list, valid_incar_tags=valid_incar_tags_list)
        else:
            modify_vasp_incar(cal_loc=cal_loc, new_tags=new_incar_tags, remove_tags=remove_incar_tags, incar_template=incar_template_list, valid_incar_tags=valid_incar_tags_list)
        with open(log_txt, "a") as f:
            f.write("{} INFO: modify INCAR in {}\n".format(get_time_str(), firework_name))
            if new_incar_tags:
                f.write("\t\tnew incar tags:\n")
                [f.write("\t\t\t{}={}\n".format(key_, value_)) for key_, value_ in new_incar_tags.items()]
            if remove_incar_tags:
                f.write("\t\tremove incar tags: ")
                [f.write("{}\t".format(tag_)) for tag_ in remove_incar_tags]
                f.write("\n")
            if write_INCAR:
                f.write("\t\told INCAR --> INCAR.pymatgen\n")
                
    #set ispin based on a previous calculation step
    set_ispin_based_on_prev_cal = firework["set_ispin_based_on_prev_cal"]
    if set_ispin_based_on_prev_cal:
        result = choose_ispin_based_on_prev_cal(current_cal_loc=cal_loc, prev_cal_step=set_ispin_based_on_prev_cal["prev_cal_step"],
                                                mag_threshold=set_ispin_based_on_prev_cal, workflow=workflow)
        if result == False:
            return False #The relevant information has been written into log.txt by the above function.
        else:
            ispin, tot_mag = result
        modify_vasp_incar(cal_loc=cal_loc, new_tags={"ISPIN": str(ispin)}, incar_template=incar_template_list, valid_incar_tags=valid_incar_tags_list)
        with open(log_txt, "a") as f:
            f.write("{} INFO: set_ispin_based_on_prev_cal is set to {} in {}\n".format(get_time_str(), set_ispin_based_on_prev_cal["set_ispin_based_on_prev_cal_str"], firework_name))
            f.write("\t\t\t The calculated total magnetic moment from {} is {}, ".format(set_ispin_based_on_prev_cal["prev_cal_step"], tot_mag))
            if ispin == 1:
                f.write("whose magnitude is smaller than or equal to the prescribed threshold.\n")
            else:
                f.write("which is larger than the prescribed threshold.\n")
            f.write("\t\t\t So set ISPIN to {} in INCAR\n".format(ispin))
                
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
            modify_vasp_incar(cal_loc=cal_loc, new_tags=new_incar_tags, rename_old_incar="INCAR.no_bader_charge", incar_template=incar_template_list, valid_incar_tags=valid_incar_tags_list)
            with open(log_txt, "a") as f:
                f.write("{} INFO: in {}\n".format(get_time_str(), firework_name))
                f.write("\t\t\t'bader_charge' is on\n")
                f.write("\t\t\tretrieve NGXF, NGYF, NGZF from {} and double them\n".format(os.path.split(prev_cal)[1]))
                f.write("\t\tnew incar tags:\n")    
                [f.write("\t\t\t{}={}\n".format(key_, value_)) for key_, value_ in new_incar_tags.items()]
                    


# In[14]:


def get_nbands(cal_loc, nbands_in_add_new_incar_tags_subblk):
    """
    Find and Return NBANDS according to nbands_in_add_new_incar_tags_subblk. Let's denote the returned NBANDS as NBANDS_f
    arguments:
        -cal_loc: the absolute path to the calculation folder
        -nbands_in_add_new_incar_tags_subblk: the value passed to tag 'NBANDS' in add_new_incar_tags sub-block (see Manual).
            Two types of values are accepted by this argument
                1. an integer. E.g. nbands_in_add_new_incar_tags_subblk = 52 --> NBANDS_f = 52
                2. number X step_x. E.g. 1.5 X step_1_xyz --> find NBANDS in the OUTCAR of the previous calculation folder named as step_1_xyz, 
                    which is denoted as NBANDS@step_1. In this case, NBANDS_f = the closest integer to 1.5 * NBANDS@step_1
                    Note that "1.5", "X" and "step_1_xyz" must be separated by a white space
                Note that in both cases, the specified number must be equal to or greater than 1.
    """
    nbands_items = nbands_in_add_new_incar_tags_subblk.strip().split()
    if len(nbands_items) == 1:
        nbands = int(nbands_items[0])
        assert nbands >= 1, "The integer set in nbands_in_add_new_incar_tags_subblk must be equal to or greater than 1. See case 1 below for more details\n" + get_nbands.__doc__
        with open(os.path.join(cal_loc, "log.txt"), "a") as log_f:
            log_f.write("{} Parse NBANDS in add_new_incar_tags sub-block: NBANDS={}\n".format(get_time_str(), nbands_in_add_new_incar_tags_subblk))
            log_f.write("\t\tIt is just an integer. So NBANDS = {}\n".format(nbands))
    elif len(nbands_items) == 3:
        multiplier = float(nbands_items[0])
        assert multiplier >= 1, "The number set in nbands_in_add_new_incar_tags_subblk must be equal to or greater than 1. See case 2 below for more details\n" + get_nbands.__doc__
        prev_cal_loc = os.path.join(os.path.split(cal_loc)[0], nbands_items[2])
        try:
            prev_nbands = find_incar_tag_from_OUTCAR(tag="NBANDS", cal_loc=prev_cal_loc)
        except:
            print("According to the prescribed calculation setup, NBANDS should be set to {}*NBANDS of {} for the calculation {}".format(multiplier, nbands_items[2], cal_loc))
            print("However, the error below happens:")
            raise
        nbands = round(multiplier * prev_nbands)
        with open(os.path.join(cal_loc, "log.txt"), "a") as log_f:
            log_f.write("{} Parse NBANDS in add_new_incar_tags sub-block: NBANDS={}\n".format(get_time_str(), nbands_in_add_new_incar_tags_subblk))
            log_f.write("\t\tMultipler and NBANDS in the previous calculation step {} are parsed to be {} and {}, respectively\n".format(nbands_items[2], multiplier, prev_nbands))
            log_f.write("\t\tSo NBANDS = {} * {} ~ {} \n".format(multiplier, prev_nbands, nbands))
    else:
        raise Exception("Invalid format of argument nbands_in_add_new_incar_tags_subblk of function get_nbands. See below for more details\n" + get_nbands.__doc__)
    
    return nbands


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
            f.write("\t\t\tEINT={}\tNBMOD=-3\tLPARD=.TRUE.\n".format(new_incar_tags["EINT"]))
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


# In[2]:


def read_Hubbard_U_J_table(U_J_table):
    with open(U_J_table, "r") as f:
        lines = [line.split("#")[0].strip() for line in f if line.split("#")[0].strip()]
    assert "ldautype" in lines[0].lower(), "You must specify LDAUTYPE in the first line of %s.\n e.g. LDAUTYPE=1 | 2 | 4" % U_J_table
    LDAUTYPE = lines[0].split("=")[1].strip()
    assert LDAUTYPE in ["1", "2", "4"], "LDAUTYPE must be 1, 2 or 4 in %s" % U_J_table
    
    U_J_dict = {}
    for line in lines[1:]:
        ele, orbital_type, U, J = line.split()
        try:
            float(U)
            float(J)
        except:
            raise Exception("Hubbard U and J should be integers or float numbers, while it is not for the line below:\n%s" % line)
        ele_dict = {"LDAUU": U, "LDAUJ": J, "LMAXMIX": 2}
        if orbital_type == 'p':
            ele_dict["LDAUL"] = '1'
        elif orbital_type == 'd':
            ele_dict["LDAUL"] = '2'
            ele_dict["LMAXMIX"] = 4
        elif orbital_type == 'f':
            ele_dict["LDAUL"] = '3'
            ele_dict["LMAXMIX"] = 6
        else:
            raise Exception("The orbital-type should be 'p', 'd' or 's', while an unkown value is set for the below line\n '%s'" % line)
        U_J_dict[ele] = ele_dict
    
    return LDAUTYPE, U_J_dict
            
def generate_Hubbard_U_J_INCAR_tags(cal_loc, U_J_table_filename):
    LDAUTYPE, U_J_dict = read_Hubbard_U_J_table(U_J_table_filename)
    with open(os.path.join(cal_loc, "POSCAR"), "r") as f:
        ele_list = list(f)[5]
    try:
        ele_list = ele_list.strip().split()
    except:
        raise Exception("Error in reading POSCAR under %s. VASP-5 formated POSCAR should be used, namely atomic spieces list in the 6th line." % cal_loc)
    
    Hubbard_U_tags = {"LDAUL": "", "LDAUU": "", "LDAUJ": "", "LMAXMIX": 2, "LDAUTYPE": LDAUTYPE, "LDAU": ".TRUE."}
    Hubbard_U_corrected_ele_list = U_J_dict.keys()
    for ele in ele_list:
        if ele not in Hubbard_U_corrected_ele_list:
            Hubbard_U_tags["LDAUL"] = Hubbard_U_tags["LDAUL"] + " -1"
            Hubbard_U_tags["LDAUU"] = Hubbard_U_tags["LDAUU"] + " 0"
            Hubbard_U_tags["LDAUJ"] = Hubbard_U_tags["LDAUJ"] + " 0"
        else:
            Hubbard_U_tags["LDAUL"] = Hubbard_U_tags["LDAUL"] + " " + U_J_dict[ele]["LDAUL"]
            Hubbard_U_tags["LDAUU"] = Hubbard_U_tags["LDAUU"] + " " + U_J_dict[ele]["LDAUU"]
            Hubbard_U_tags["LDAUJ"] = Hubbard_U_tags["LDAUJ"] + " " + U_J_dict[ele]["LDAUJ"]
            Hubbard_U_tags["LMAXMIX"] = max([Hubbard_U_tags["LMAXMIX"], U_J_dict[ele]["LMAXMIX"]])
    if " 1" not in Hubbard_U_tags["LDAUL"] and "2" not in Hubbard_U_tags["LDAUL"] and "3" not in Hubbard_U_tags["LDAUL"]:
        return {}
    else:
        return Hubbard_U_tags


# In[4]:


def get_lmaxmix(cal_loc):
    """
    Read the user-customized element types from under HTC_lib/VASP/INCAR/element_type_table.json and POSCAR, and return:
    I. 6 if there is (are) f-element(s).
    II. 4 if there is no f-element but there is (are) d-element(s).
    III. 2 if there are only sp-elements.
    IV. False if an error occurs.
    
    Note that HTC_lib/VASP/INCAR/element_type_table.json is generated by HTC_lib/VASP/INCAR/parse_element_type_table.py.
    """
    element_type_table_filename = os.path.join(HTC_package_path, "HTC_lib", "VASP", "INCAR", "element_type_table.json")
    assert os.path.isfile(element_type_table_filename), "For the calculation below, set_lmaxmix is set to 'Yes'. However, %s does not exist, from which the user-customized element types are supposed to read." % element_type_table_filename
    
    with open(element_type_table_filename, "r") as table_f:
        element_type_dict = json.load(table_f)

    with open(os.path.join(cal_loc, "POSCAR"), "r") as f:
        ele_list = list(f)[5]
    try:
        ele_list = ele_list.strip().split()
    except:
        with open(os.path.join(cal_loc, "log.txt"), "a") as log_f:
            log_f.write("{}: Error in reading POSCAR under {}. VASP-5 formated POSCAR should be used, namely atomic spieces list in the 6th line.\n".format(get_time_str(), cal_loc))
            log_f.write("\t\t\tCreate __manual__\n")
        open(os.path.join(cal_loc, "__manual__"), "w").close()
        return False
        
    ele_type_list = []
    for ele in ele_list:
        categorized = False
        for element_type in element_type_dict.keys():
            if ele in element_type_dict[element_type]:
                ele_type_list.append(element_type)
                categorized = True
        if categorized == False:
            with open(os.path.join(cal_loc, "log.txt"), "a") as error_f:
                error_f.write("{}: Please provide the type of {} in HTC_lib/VASP/INCAR/element_type_table and run 'python parse_element_type_table.py' under that directory\n".format(get_time_str(), ele))
                error_f.write("\t\t\tCreate __manual__\n")
            open(os.path.join(cal_loc, "__manual__"), "w").close()
            return False
    
    with open(os.path.join(cal_loc, "log.txt"), "a") as log_f:
        log_f.write("{}: lmaxmix is set to 'Yes'\n".format(get_time_str()))
        log_f.write("\t\t\tThe atomic elements parsed from POSCAR are: {}. According to HTC_lib/VASP/INCAR/element_type_table.json, their types are:\n".format(ele_list))
        output_str = ""
        for ele, ele_type in zip(ele_list, ele_type_list):
            output_str += ele + " <-> " + ele_type + "; "
        log_f.write("\t\t\t" + output_str + "\n")
    
    if "f-element" in ele_type_list:
        with open(os.path.join(cal_loc, "log.txt"), "a") as log_f:
            log_f.write("\t\t\tSo LMAXMIX will be set to 6\n")
        return 6
    elif "d-element" in ele_type_list:
        with open(os.path.join(cal_loc, "log.txt"), "a") as log_f:
            log_f.write("\t\t\tSo LMAXMIX will be set to 4\n")
        return 4
    else:
        with open(os.path.join(cal_loc, "log.txt"), "a") as log_f:
            log_f.write("\t\t\tSo LMAXMIX will be set to 2 (Default value)\n")
        return 2
    


# In[1]:


def cal_emax_or_emin(cal_loc, emax_or_emin_setup, incar_tag):
    """
    People are usually interested in the density of states around the Fermi level. But materials may significantly differ in the 
    Fermi level from one to another. As such, it is hard to set EMAX and EMIN to specific numbers. This function would allow us 
    to set EMAX and EMIN with respect to the Fermi level decided from the previous calculation step.
    *cal_loc (str): the absolute path to the calculation
    *emax_or_emin_setup (str): It is the value assigned to EMAX or EMIN, and has any of below formats: 
        EMAX = Efermi@step_x_xyz + 5 #The Fermi level of step_x_xyz will be read and used to decide EMAX
        EMIN = Efermi@step_w_lmn - 4 #The Fermi level of step_w_lmn will be read and used to decide EMIN
        Note: Sign "+", "-", "*" and "/" will be used to split emax_or_emin_setup and identify the previous calculation step
                
        EMAX = number #This function has nothing to do with EMAX
        EMIN = number #This function has nothing to do with EMIN
    
    *incar_tag (str): either "EMIN" or "EMAX"
        
    return:
        The calculated EMAX or EMIN will be returned in a float format
    """
    
    if "Efermi@step" not in emax_or_emin_setup:
        return float(emax_or_emin_setup)
    
    prev_step_name = emax_or_emin_setup.strip()
    for sign in ["+", "-", "*", "/"]:
        for item in prev_step_name.split(sign):
            item = item.strip()
            if "Efermi@" in item:
                prev_step_name = item
                break
    prev_step_name = prev_step_name.split("@")[1]
    
    mater_folder = cal_loc
    while True:
        mater_folder, tail = os.path.split(mater_folder)
        if tail.startswith("step_"):
            break
    
    with open(os.path.join(cal_loc, "log.txt"), "a") as log_f:
        log_f.write("{}: We notice that {} has been set to {}.\n".format(get_time_str(), incar_tag, emax_or_emin_setup))
        log_f.write("\t\t\tTrying to parse Efermi from {}.\n".format(os.path.join(mater_folder, prev_step_name, "OUTCAR")))
    
    target_line = ""
    with open(os.path.join(mater_folder, prev_step_name, "OUTCAR"), "r") as f:
        for line in f:
            if "E-fermi" in line and "XC(G=0)" in line and "alpha+bet" in line:
                Efermi = line.split("XC")[0].split(":")[1]
                target_line = line
    
    updated_emax_or_emin_setup = emax_or_emin_setup.replace("Efermi@{}".format(prev_step_name), Efermi)
    EMAX_or_EMIN = eval(updated_emax_or_emin_setup)
    
    with open(os.path.join(cal_loc, "log.txt"), "a") as log_f:
        log_f.write("\t\t\tThe line containing E-fermi is identified: {}\n".format(target_line))
        log_f.write("\t\t\tEfermi is parsed as {}\n".format(Efermi))
        log_f.write("\t\t\t{} = {} = {} = {}\n".format(incar_tag, emax_or_emin_setup, updated_emax_or_emin_setup, EMAX_or_EMIN))
        
    return EMAX_or_EMIN

