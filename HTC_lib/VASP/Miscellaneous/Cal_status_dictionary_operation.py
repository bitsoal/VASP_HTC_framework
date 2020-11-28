#!/usr/bin/env python
# coding: utf-8

# In[1]:


from Utilities import divide_a_list_evenly
import json


# In[2]:


class Cal_status_dict_operation():
    
    @classmethod
    def merge_dicts(cls, a_list_of_dicts):
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
    
    @classmethod
    def evenly_divide_a_dict(cls, a_dict, no_of_subdicts):
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
    
    @classmethod
    def reverse_cal_status_dict(cls, cal_status_dict):
        reversed_cal_status_dict = {}
        for status, job_list in cal_status_dict.items():
            for job in job_list:
                reversed_cal_status_dict[job] = status
        return reversed_cal_status_dict

    @classmethod
    def get_cal_status_dict_from_reversed(cls, reversed_cal_status_dict, status_list):
        cal_status_dict = {status: [] for status in status_list}
        for job, status in reversed_cal_status_dict.items():
            if status not in cal_status_dict.keys():
                cal_status_dict[status] = [job]
            else:
                cal_status_dict[status].append(job)
        return cal_status_dict
    
    @classmethod
    def diff_status_dict(cls, old_cal_status_dict, new_cal_status_dict): 
        old_job_status_set = set([(job, status) for job, status in cls.reverse_cal_status_dict(old_cal_status_dict).items()])
        new_job_status_set = set([(job, status) for job, status in cls.reverse_cal_status_dict(new_cal_status_dict).items()])
        status_set = set(list(old_cal_status_dict.keys()) + list(new_cal_status_dict.keys()))
        
        updated_dict = {}
        for job_status_pair in new_job_status_set.difference(old_job_status_set):
            updated_dict[job_status_pair[0]] = job_status_pair[1]
            
        removed_job_list = [job_status_pair[0] for job_status_pair in old_job_status_set.difference(new_job_status_set)]
        
        return {"updated": updated_dict, "removed": removed_job_list, "status_list": list(status_set)}
    
    @classmethod
    def update_old_cal_status_dict(cls, old_cal_status_dict, cal_status_dict_diff):
        reversed_old_cal_status_dict = cls.reverse_cal_status_dict(old_cal_status_dict)
        
        for removed_job in cal_status_dict_diff["removed"]:
            reversed_old_cal_status_dict.pop(removed_job)
        reversed_old_cal_status_dict.update(cal_status_dict_diff["updated"])
        
        return cls.get_cal_status_dict_from_reversed(reversed_old_cal_status_dict, status_list=cal_status_dict_diff["status_list"])
    
    @classmethod
    def write_cal_status(cls, cal_status, filename):
        with open(filename, "w") as f:
            f.write("#{}\n".format(get_time_str()))
            json.dump(cal_status, f, indent=4)
            
        folder_name = filename.replace(".json", "") + "_folder"
        if os.path.isdir(folder_name):
            for file_ in os.listdir(folder_name):
                try:
                    os.remove(os.path.join(folder_name, file_))
                except:
                    print("Fail to remove %s. Does it really exist?" % os.path.join(folder_name, file_))
        else:
            os.mkdir(folder_name)
        
        for status, job_list in cal_status.items():
            if job_list:
                with open(os.path.join(folder_name, status), "w") as f:
                    f.write("#{}\n".format(get_time_str()))
                    for job in job_list:
                        f.write(job + "\n")


# def merge_dicts(a_list_of_dicts):
#     """
#     Merge a set of the dicts whose value is of type list.
#     """
#     a_list_of_dicts = copy.deepcopy(a_list_of_dicts)
#     merged_dict = a_list_of_dicts[0]
#     for a_dict in a_list_of_dicts[1:]:
#         for key, value in a_dict.items():
#             if key in merged_dict.keys():
#                 merged_dict[key].extend(value)
#             else:
#                 merged_dict[key] = value
#     for key, value in merged_dict.items():
#         merged_dict[key] = sorted(set(value))
#     return merged_dict

# def evenly_divide_a_dict(a_dict, no_of_subdicts):
#     """
#     a_dict is a dictionary whose values are all of type list.
#     This function evenly divides a_dict into no_of_subdicts sub-dictionaries. Each value of a sub-dictionary is just a 1/no_of_subdicts 
#     of the corresponding value of a_dict.
#     Return no_of_subdicts in a list format, e.g. [sub_dict_1, sub_dict_2, sub_dict_3] at no_of_subdicts=3
#     """
#     subdict_list = [{} for i in range(no_of_subdicts)]
#     for key, a_list in a_dict.items():
#         sublist_list = divide_a_list_evenly(a_list=list(set(a_list)), no_of_sublists=no_of_subdicts)
#         for i in range(no_of_subdicts):
#             subdict_list[i][key] = sorted(sublist_list[i])
#     return subdict_list

# def reverse_cal_status_dict(cal_status_dict):
#     reversed_cal_status_dict = {}
#     for status, job_list in cal_status_dict.items():
#         for job in job_list:
#             reversed_cal_status_dict[job] = status
#     return reversed_cal_status_dict
# 
# def get_cal_status_dict_from_reversed(reversed_cal_status_dict, status_list):
#     cal_status_dict = {status: [] for status in status_list}
#     for job, status in reversed_cal_status_dict.items():
#         if status not in cal_status_dict.keys():
#             cal_status_dict[status] = [job]
#         else:
#             cal_status_dict[status].append(job)
#     return cal_status_dict

# def diff_status_dict(old_cal_status_dict, new_cal_status_dict): 
#     old_job_status_set = set([(job, status) for job, status in reverse_cal_status_dict(old_cal_status_dict).items()])
#     new_job_status_set = set([(job, status) for job, status in reverse_cal_status_dict(new_cal_status_dict).items()])
#     status_set = set(list(old_cal_status_dict.keys()) + list(new_cal_status_dict.keys()))
#     
#     
#     updated_dict = {}
#     for job_status_pair in new_job_status_set.difference(old_job_status_set):
#         updated_dict[job_status_pair[0]] = job_status_pair[1]
#         
#     removed_job_list = [job_status_pair[0] for job_status_pair in old_job_status_set.difference(new_job_status_set)]
#     
#     return {"updated": updated_dict, "removed": removed_job_list, "status_list": list(status_set)}

# def update_old_cal_status_dict(old_cal_status_dict, cal_status_dict_diff):
#     reversed_old_cal_status_dict = reverse_cal_status_dict(old_cal_status_dict)
#     
#     for removed_job in cal_status_dict_diff["removed"]:
#         reversed_old_cal_status_dict.pop(removed_job)
#     reversed_old_cal_status_dict.update(cal_status_dict_diff["updated"])
#     
#     return get_cal_status_dict_from_reversed(reversed_old_cal_status_dict, status_list=cal_status_dict_diff["status_list"])

# In[6]:


if __name__ == "__main__":
    a_dict = {"a": [1, 2], "b": [3], "c": [5, 6]}
    b_dict = {"a":[1], "b": [2, 3], "d": [4]}

    dict_diff = Cal_status_dict_operation.diff_status_dict(a_dict, b_dict)
    print(dict_diff)
    
    print(Cal_status_dict_operation.update_old_cal_status_dict(old_cal_status_dict=a_dict, cal_status_dict_diff=dict_diff))

