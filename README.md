# VASP_HTC_framework
### This is a simple framework designed for high-throughput calculation based on VASP.

### version: python2.7

### Package requirements: pymatgen

### How to run:
    I: fill HTC_lib_path, cif_file_folder, cal_folder, HTC_calculation_setup_file in htc_main.py
    II: write a file named, say HTC_calculation_setup according to Manual.md.
    III: python htc_main.py OR nohup python htc_main.py > log.txt 2>&1 &
	You may look through the htc example about WSe2 supercell under folder examples