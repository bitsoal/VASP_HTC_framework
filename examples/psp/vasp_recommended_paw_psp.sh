#!/bin/bash

#The recommened VASP paw psp: https://www.vasp.at/wiki/index.php/Available_PAW_potentials

src=/hpctmp/phyv250/NUS_HPC_VASP_seminar_2023_Mar/POTCAR_folder/potpaw_PBE.54
dst=.

for ele in C Si S Mo_sv 
do
	ele_head=`echo $ele | cut -d _ -f 1`
	cat $src/$ele/POTCAR > $dst/$ele_head
done
