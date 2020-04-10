# `VASP_HTC_framework`： a Python Package for First-Principles Hight-throughput Calculations Using the Vienna Ab Initio Simulation Packages (VASP)

### `Master` Branch: stable and work well on python2.7
### `upgrading_to_python_3` Branch: The branch we are working on to upgrade to python3

### Package requirements: pymatgen

### Please refer to Manual for how to use and run this package.

  
## A series of things to be added
1. add a new tags in HTC_set_up which allow users to specify what VASP files are backed up in error_folders

2. add new tags INCAR_cmd, KPOINTS_cmd, POTCAR_cmd, POSCAR_cmd, allowing users to deal with them, respectively. These tags can
	*avoid heavily using user_defined_cmd & final_user_defined_cmd.
	*aleviate the reliance on pymatgen. Users can call pymatgen to create vasp input files using these new tags. More user freedom
		**provide a bunch of template scripts calling pymatgen for vasp input file creation.
		
3. upgrade to python3

4. add a new calculation status file named by __done_cleaned__. The program is going to the calculation folder labelled by __done__
	and delete the irrelevant files specified by a new tag del_irrelevant_output_files
	
5. add a new tag enabling users to provide an INCAR template. The program will read this template and re-order the INCAR tags
	and add empty lines accordingly.   
	****Apr 10, 2020: Coded. Debug is underway.****
	
6. re-think about sub folder calculations to automize the convergence testing of ENCUT, SIGMA, KPOINTS as well as lattice optimizatoin
	one by one. Provide corresponding scripts.
	
7. set DIPOL

8. read e_fermi and set EMIN & EMAX for DOS calculations.

9. backup the content of HTC_calculation_setup_file in Parsed_HTC_setup.JSON

10. allow users to use ${HTC_CWD} to denote the absolute path to the main directory where htc_main.py is called. therefore, users can refer to a file by using its absolute
	path or ${HTC_CWD}+the relative path   
	*****Apr 10, 2020: Coded. Debug is underway.*****