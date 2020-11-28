#!/usr/bin/env python
# coding: utf-8

# In[4]:


from Utilities import divide_a_list_evenly


# In[5]:


def merge_dicts(a_list_of_dicts):
    """
    Merge a set of the dicts whose value is of type list.
    """
    a_list_of_dicts = copy.deepcopy(a_list_of_dicts)
    merged_dict = a_list_of_dicts[0]
    for a_dict in a_list_of_dicts[1:]:
        for key, value in a_dict.items():
            if key in merged_dict.keys():
                merged_dict[key].extend(value)
            else:
                merged_dict[key] = value
    for key, value in merged_dict.items():
        merged_dict[key] = sorted(set(value))
    return merged_dict


# In[6]:


def evenly_divide_a_dict(a_dict, no_of_subdicts):
    """
    a_dict is a dictionary whose values are all of type list.
    This function evenly divides a_dict into no_of_subdicts sub-dictionaries. Each value of a sub-dictionary is just a 1/no_of_subdicts 
    of the corresponding value of a_dict.
    Return no_of_subdicts in a list format, e.g. [sub_dict_1, sub_dict_2, sub_dict_3] at no_of_subdicts=3
    """
    subdict_list = [{} for i in range(no_of_subdicts)]
    for key, a_list in a_dict.items():
        sublist_list = divide_a_list_evenly(a_list=list(set(a_list)), no_of_sublists=no_of_subdicts)
        for i in range(no_of_subdicts):
            subdict_list[i][key] = sorted(sublist_list[i])
    return subdict_list


# In[10]:


def diff_status_dict(old_cal_status_dict, new_cal_status_dict):
    pass


# In[11]:


def update_an_old_cal_status_dict(old_cal_status_dict, cal_status_dict_diff):
    pass

