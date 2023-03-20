#!/bin/bash

POTCAR_loc=/hpctmp/phyv250/NUS_HPC_VASP_seminar_2023_Mar/htc_demo_I/psp

if [ -f POTCAR ]
then
rm POTCAR
fi

for atom_type in `head -n 6 POSCAR | tail -n 1`
do
if [ -e $POTCAR_loc/$atom_type ]
then
    cat $POTCAR_loc/$atom_type >> POTCAR
else
    touch __manual__
    touch __fail_to_create_POTCAR__
fi
done

