#!/bin/bash

POTCAR_loc=

if [ -f POTCAR ]
then
rm POTCAR
fi

for atom_type in `head -n 6 POSCAR | tail -n 1`
do
if [ -e ${POTCAR_loc}/${atom_type} ]
then
    cat ${POTCAR_loc}/${atom_type} >> POTCAR
else
    touch __manual__
    touch __fail_to_create_POTCAR
fi
done

