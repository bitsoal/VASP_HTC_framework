#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os, re


# In[25]:


class Potcar(object):
    
    def __init__(self, filename="POTCAR", cal_loc="."):
        self.filename = filename
        self.cal_loc = cal_loc
        self.potcar_path = os.path.join(cal_loc, filename)
        
    def get_atomic_species(self):
        atomic_species = []
        with open(self.potcar_path, "r") as potcar_f:
            for line in potcar_f:
                if "VRHFIN" in line:
                    atomic_species.append(line.split("=")[1].split(":")[0].strip())
        assert atomic_species, "Failed to find atomic species from {}".format(self.potcar_path)
        return atomic_species
    
    def get_enmax_enmin(self):
        enmax_list = []
        enmin_list = []
        with open(self.potcar_path, "r") as potcar_f:
            for line in potcar_f:
                if "ENMAX" in line and "ENMIN" in line:
                    m = re.findall("[0-9\.]+", line)
                    assert len(m) == 2, "Failed to parse ENMAX & ENMIN from {} in {}".format(line.strip("\n"), self.potcar_path)
                    enmax_list.append(m[0])
                    enmin_list.append(m[1])
        atomic_species = self.get_atomic_species()
        assert len(atomic_species) == len(enmax_list), "The number of atomic species parsed from VRHFIN is not equal to # of ENMAX and ENMIN for {}".format(self.potcar_path)
        
        enmax_enmin_dict = {}
        for species, enmax, enmin in zip(atomic_species, enmax_list, enmin_list):
            enmax_enmin_dict[species] = {"ENMAX": enmax, "ENMIN": enmin}
        return enmax_enmin_dict
    
    def sort_and_write_potcar(self, new_atomic_species_sequence, filename, cal_loc):
        potcar_block_list = [[]]
        with open(self.potcar_path, "r") as potcar_f:
            for line in potcar_f:
                if "End of Dataset" in line:
                    potcar_block_list[-1].append(line)
                    potcar_block_list.append([])
                else:
                    potcar_block_list[-1].append(line)
        potcar_block_list.pop(-1)
        atomic_species = self.get_atomic_species()
        assert len(atomic_species) == len(potcar_block_list), "The number of atomic species parsed from VRHFIN is not equal to # of POTCAR blocks for {}".format(self.potcar_path)
        for species in new_atomic_species_sequence:
            assert species in atomic_species, "{} cannot be found in {}".format(species, self.potcar_path)
        
        with open(os.path.join(cal_loc, filename), "w") as potcar_f:
            for species in new_atomic_species_sequence:
                species_ind = atomic_species.index(species)
                [potcar_f.write(line) for line in potcar_block_list[species_ind]]
                    


# In[29]:


if __name__ == "__main__":
    potcar = Potcar(filename="POTCAR", cal_loc="test/")
    enmax_enmin_dict = potcar.get_enmax_enmin()
    atomic_species = potcar.get_atomic_species()
    new_atomic_species_sequence = sorted(atomic_species, key=lambda species: float(enmax_enmin_dict[species]["ENMAX"]), reverse=True)
    print(enmax_enmin_dict)
    print(new_atomic_species_sequence)
    potcar.sort_and_write_potcar(new_atomic_species_sequence=new_atomic_species_sequence, filename="new_POSCAR", cal_loc="test/")
    

