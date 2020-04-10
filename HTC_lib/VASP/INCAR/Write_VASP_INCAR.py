#!/usr/bin/env python
# coding: utf-8

# In[13]:


import os, pprint,copy

from pymatgen.io.vasp.sets import MPRelaxSet
from pymatgen import Structure

from Utilities import get_time_str, find_next_name, decorated_os_rename, get_current_firework_from_cal_loc
from Query_from_OUTCAR import find_incar_tag_from_OUTCAR
from modify_vasp_incar import modify_vasp_incar


# In[3]:


def Write_Vasp_INCAR(cal_loc, structure_filename, workflow):
    """
    Write or modify INCAR in folder cal_loc as follows:
        step I: If no INCAR in cal_loc, write INCAR using pymatgen.io.vasp.sets.MPRelaxSet
        step II: Modify INCAR according to new_incar_tags and remove_incar_tags.
    Input arguments:
        cal_loc (str): the absolute path
        structure_filename (str): the file from which the structure is read using pymatgen.Structure.from_file
        workflow
    """
    
    firework = get_current_firework_from_cal_loc(cal_loc, workflow)
    firework_name = os.path.split(cal_loc)[-1]
    log_txt = os.path.join(cal_loc, "log.txt")
    
    incar_template_list, valid_incar_tags_list = workflow[0]["incar_template_list"], workflow[0]["valid_incar_tags_list"]

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
    if firework["ldau_cal"]:
        new_incar_tags.update(generate_Hubbard_U_J_INCAR_tags(cal_loc=cal_loc, U_J_table_filename=firework["ldau_u_j_table"]))
    if new_incar_tags or remove_incar_tags:
        if write_INCAR:
            modify_vasp_incar(cal_loc=cal_loc, new_tags=new_incar_tags, rename_old_incar="INCAR.pymatgen", remove_tags=remove_incar_tags_list, incar_template=incar_template_list, valid_incar_tags=valid_incar_tags_list)
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

