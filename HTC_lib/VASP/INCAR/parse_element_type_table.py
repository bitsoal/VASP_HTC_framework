#!/usr/bin/env python
# coding: utf-8

# In[1]:


import json, os


# In[29]:


def parse_element_type_table():
    """1. Parse the element type table from a file named as "element_type_table" located in the same directory.
       The table categorize elements into sp-element, d-element and f-element and the file format as shown below:
       -----------------------------------------------
           sp-element: ele_1, ele_2, ele_3
           d-element: ele_4, ele_5, ele_6, ele_7
           f-element: ele_8, ele_9
       -----------------------------------------------
       2. Check whether any element is tabulated more than once. If this is the case, raise an error.
       3. Save the parsed table into a json file named as "element_type_table.json" so that Write_VASP_INCAR does not
           need to parse "element_type_table" repeatedly if "set_lmaxmix" is set to "Yes"
    """
    table_filename = "element_type_table"
    
    if not os.path.isfile(table_filename):
        print("In the current directory, file '%s', which describes the type of each element of interest, does not exist." % table_filename)
        print("We create '%s' with only H, He and Li specified for you. Please provide the type of other elements of interest." % table_filename)
        with open(table_filename, "w") as table_f:
            table_f.write("sp-element:H, He, Li\n")
            table_f.write("d-element:\n")
            table_f.write("f-element:\n")
        return 0
    
    with open(table_filename, "r") as table_f:
        lines = []
        for line in table_f:
            line = line.split("#")[0].strip()
            if line:
                lines.append(line)

    element_type_dict = {}
    for line in lines:
        if line.startswith("sp-element") or line.startswith("d-element") or line.startswith("f-element"):
            element_type, element_str = line.split(":")
            element_type_dict[element_type.strip()] = [ele.strip() for ele in element_str.split(",") if ele.strip()]
    all_element_list = []
    for element_type in ["sp-element", "d-element", "f-element"]:
        if element_type not in element_type_dict.keys():
            element_type_dict[element_type] = []
        else:
            all_element_list.extend(element_type_dict[element_type])
    print("Successfully parsed %s\nStart to check whether the type of an element is specified more than once..." % table_filename)
            
    for element in all_element_list:
        times = all_element_list.count(element) 
        assert times == 1, "You specify element %s %d times. Please remove all duplicates." % (element, times)
    print("Seems that the type of every element of interest is provided uniquely. The parsed table is as below:")
    print("-"*80)
    for element_type in ["sp-element", "d-element", "f-element"]:
        print(element_type + ":", element_type_dict[element_type])
    print("-"*80)
    
    with open(table_filename + ".json", "w") as table_f:
        json.dump(element_type_dict, table_f, indent=4)
    print("Save the parsed element type table into " + table_filename + ".json.")
    print("Now, this json file can be read by Write_VASP_INCAR to set LMAXMIX accordingly.")
    print("Done ^_^")
            
    
    


# In[30]:


if __name__ == "__main__":
    parse_element_type_table()


# with open("element_type_table.json", "r") as table_f:
#     element_type_dict = json.load(table_f)
# element_type_dict
