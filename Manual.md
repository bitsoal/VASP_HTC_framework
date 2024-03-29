## `VASP_HTC_Framework`: a Python Framework for First-Principles Hight-throughput Calculations Using the Vienna Ab Initio Simulation Packages (VASP)

### Authors:

* Yang Tong  
    bitsoal@gmail.com; yangtong@u.nus.edu  
    Department of Applied Physics, The Hong Kong Polytechnic University  
* Asst/Prof. [Yang Ming](https://www.polyu.edu.hk/en/ap/people/academic-staff/dr-yang-ming/) (co-supervisor)  
    kevin.m.yang@polyu.edu.hk  
    Department of Applied Physics, The Hong Kong Polytechnic University
* Prof. [Feng Yuanping](https://www.physics.nus.edu.sg/faculty/feng-yuan-ping/) (supervisor))  
    phyfyp@nus.edu.sg  
    Department of Physics, National University of Singapore  

-----------------

### python version:

* python_2 for the [`Master` Branch](https://github.com/bitsoal/VASP_HTC_framework/tree/master)
* python_3 for the `upgrade_to_python_3` Branch (**current branch**)    

---------------------------

### Potential Users:

#### A few calculations are cheap, but hundreds of thousands of calculations are definitely not! So this package might be useful only to experienced VASP users who know what they are doing.

---------------------------

### Package Setup and Execution:

1. This package currently relies on [pymatgen](http://pymatgen.org/index.html). Make sure it has been installed. pymatgen.2022.11.7 or earlier versions will do.
2. enter `HTC_lib` and you will find a file named `setup.py`. run `python setup.py` to set up this package. 
3. The main program script: ~~`htc_main.py` &~~ `htc_main_mpi.py` & `htc_main_ProcessPoolExecutor.py`
   - ~~`htc_main.py` is under `HTC_lib/VASP`.~~  
   - `htc_main_mpi.py` is under `HTC_lib/VASP`. `htc_main_mpi.py` is built on the [`mpi4py`](https://mpi4py.readthedocs.io/en/stable/) package. It prepares vasp input files and update calculation status (e.g. error checking and handling) in parallel. But the job submission is still performed by the master process.
   - `htc_main_ProcessPoolExecutor.py` is another version and also under `HTC_lib/VASP`. `htc_main_ProcessPoolExecutor.py` is built on python class [`ProcessPoolExecutor`](https://docs.python.org/3/library/concurrent.futures.html). It prepares vasp input files and update calculation status (e.g. error checking and handling) in parallel. But the job submission is still performed by the master process.
4. Just **COPY (DO NOT MOVE)** either ~~`htc_main.py` or~~ `htc_main_mpi.py` or `htc_main_ProcessPoolExecutor.py` to the folder where the high-throughput calculations are going to be run. Let's denote the folder as `${HTC_CWD}`.
5. Write up a setup file named `HTC_calculation_setup_file` under `${HTC_CWD}` or a collection of setup files under `${HTC_CWD}/HTC_calculation_setup_folder`. See below for the details of `HTC_calculation_setup_file` and `${HTC_CWD}/HTC_calculation_setup_folder`.
6. Under `${HTC_CWD}`
   - ~~`htc_main.py`: execute `python htc_main.py >htc_out 2>&1&` OR `nohup python htc_main.py >htc_out 2>&1 &` to start this HTC program. OR you can put `python htc_main.py >htc_out 2>&1` in a batch script and submit it to the batch scheduler.~~
   - `htc_main_mpi.py`: The execution command looks like `mpirun -n x python htc_main_mpi.py > htc_out 2>&1`, where `x` is the number of requested cores/cpus. You are not suggested to run the command on the login node of a supercomputing cluster, which may make the login node sluggish. Instead, just put `mpirun -n x python htc_main_mpi.py > htc_out 2>&1` in a batch script and submit it to the batch scheduler which will dispatch the command to computing nodes.
   - `htc_main_ProcessPoolExecutor.py`: execute `python htc_main_ProcessPoolExecutor.py >htc_out 2>&1&` OR `nohup python htc_main_ProcessPoolExecutor.py >htc_out 2>&1 &` to start this HTC program. OR you can put `python htc_main_ProcessPoolExecutor.py >htc_out 2>&1` in a batch script and submit it to the batch scheduler.   

**Note that whenever this package is moved/copied to a new place, you NEED TO DO step 2. This is to ensure that ~~`VASP/htc_main.py` and~~ `VASP/htc_main_mpi.py` and `htc_main_ProcessPoolExecutor.py` are updated and thus the moved/copied package can be found properly. Otherwise, ~~`VASP/htc_main.py` and~~ `VASP/htc_main_mpi.py` and `htc_main_ProcessPoolExecutor.py` would still call the package in the old place.** 

</br>

------------------------------------------

## The calculations listed below are already available:

* **Structural relaxations**
* **Self-consistent calculations**
* **Density of states**
* **LDA+U calculations**
* **Band structure (KPOINTS can be automatically created for either PBE and HSE06)**
* **Partial charge around CBM and VBM**
* **Bader charge calculation**
* **Other calculations that can be setup by simply changing INCAR (e.g. phonon dispersions)**
* **Sub-folder calculations**
  * **Convergence test of essential paramters (ENCUT, SIGMA and KPOINTS) (Debug is underway)**
  * **lattice constant optimization**

------------------------------------------

</br>

## Terminologies we used

We adopt the terminologies below from pymatgen and atomate:

* firetask - A Firetask is an atomic job. For example:
  * copy, move, remove files  
  * prepare VASP input files based on pymatgen
  * modify INCAR
  * modify KPOINTS
  * modify POSCAR
  * submit VASP jobs
  * submit or kill VASP jobs
  * fix some common errors, i.e. ionic divergence, electronic divergence, positive energy.
* firework - A firework is a series of firetaks OR what needs to be done for a single VASP calculation. Normally, it is composed of three types of firetasks. 
  * pre-process: setup VASP input files.
    * They can be copied or moved from previous step calucations.
    * They can be generated by pymatgen from scratch.
    * Once VASP input files are prepared via either ways above, they need to be modified so that they are finally appropriate for the target VASP calculation.
  * post-process: actions made after the VASP calculations. *(On the to-do list)*
  * job-management: related to job submissions, queries or terminations. **Note that in fact, job submissions, job status queries, or jobs terminations will be realized via signal files (see below).**
* workflow - A workflow is a set of fireworks with dependencies between them. For example: 
  * CHGCAR from scf will be required for DOS or band structure calculations.
  * It is common that including dipole corrections likely leads to the electronic divergence. So CHGCAR may be required from a previous calculation without dipole corrections.
  * For [HSE06 calculations](https://cms.mpi.univie.ac.at/vasp/vasp/Typical_hybrid_functional_Hartree_Fock_calculations.html), a preconverged PBE WAVECAR is a good starting point.

You may refer to [atomate](https://hackingmaterials.github.io/atomate/creating_workflows.html#creating-workflows) for more detailed definitions.

-----------------------------------------------

## How to write up HTC\_calculation\_setup\_file

**We assume the HTC workflow setup is saved into a file named **`HTC_calculation_setup_file`**. In addition to structure files, this is the only file that you need to prepare to automate the HTC calculations. What follows is how to define a workflow in `HTC_calculation_setup_file`**

* `HTC_calculation_setup_file` consists of a set of blocks. Each block defines a firework or a VASP caculation.
* Every firework starts from the line which is simply `**start`, and ends up with the line which is `**end`
* In a firework
  * pre-processes and post-processes are defined in a key-value manner with the equal sign `=` linking them. **There is an exception that inside a firework, there is a sub-block related to INCAR modifications. This sub-block starts from the line which is `*begin(add_new_incar_tags)` and it ends with the line which is `*end(add_new_incar_tags)`. In this sub-block, you can overwrite INCAR tags or add new INCAR tags as you are writing INCAR, which are also `=`-linked key-value pairs**
  * In addition, job submissions, job status queries or job terminations will also need to be specified in a key-value manner.
  * Note that **in the first firework**, some job management tags must be set and these setting will be used for the whole workflow:
    * the command to query a job status from a queue system.
    * the command to kill a running job
    * the file which hosts the queue id, say job_id
    * the regular expression to parse the queue id from file job_id using python `re.findall()`
    * tag **vasp.out**.
      * if the job submission cmd in the submission script looks like `mpirun -n 16 vasp_std > out`, then `vasp.out=out`
      * if the job submission cmd in the submission script looks like `mpirun -n 16 vasp_std`, then file vasp.out isn't renamed. So `vasp.out=vasp.out`
    * the prefix and suffix of the stdout file generated by the queue system after the calculation.
    * the prefix and suffix of the stderr file generated by the queue system after the calculation.
    * tag **forece_gamma**: if the kpoints are forced to be gamma-centered.
    * tag **2d_system**: for 2D systems, KPOINTS will be modified so that K\_z is zero for all kpoints.*(obsolete in the near future.)*
    * tag **sort_structure**: Whether sort structure or not beforing write POSCAR by the electronegativity of the species 
    * tag **max\_running\_job** and **job\_name**: they decide the maximum number of running/pending jobs.
    * tag **max\_no\_of_ready\_jobs**: The maximum number of jobs that are prepared and ready to run. (See below for more information about this tag)  

## `HTC_calculation_setup_folder` - an alternative to `HTC_calculation_setup_file`

In principle, you can define the whole HTC workflow in `HTC_calculation_setup_file`. **But defining everything in a single file would sometimes make the file too long, which may cause inconvenience.** For example, you may refer to the 3rd firework/calculation setup while defining the 10th firework/calculation. 6 fireworks/calculations in between the 3rd and 10th firework/calculation are long enough to prevent the 3rd and 10th firework/calculation from being simultaneously shown on the screen.  
**So here we provide an alternative to  `HTC_calculation_setup_file`. Instead of `HTC_calculation_setup_file`, a collection of files named as `step_n_xxx` under `HTC_calculation_setup_folder` can be used to define the whole calculation workflow: `HTC_calculation_setup_folder/step_n_xxx` defines the n-th firework/calculation.** The format of `HTC_calculation_setup_folder/step_n_xxx` is the same as that in `HTC_calculation_setup_file`. **We have a specific requirement on the filename of `step_n_xxx`. Please see `cal_name` below**  

### Below is a template of the 1st firework/calculation

> `**start` 
> 
> `step_no = 1`  
> `cal_name = structural optimization`  
> 
> `extra_copy = ${HTC_CWD}/vasp_input_files/INCAR #What follows # is a comment`    
> `user_defined_cmd = bash ${HTC_LIB_LOC}/HTC_lib/VASP/POTCAR/write_potcar.sh`  
> `final_user_defined_cmd = python ${HTC_LIB_LOC}/HTC_lib/VASP/KPOINTS/VASP_Automatic_K_Mesh.py -write --NL:30 --max_vacuum_thickness:5_5_5`  
> `kpoints_type = MPRelaxSet #Just set this here. Will be obsolete`  
> 
> `job_submission_script = ${HTC_CWD}/vasp_input_files/vasp.pbs`  
> `job_submission_command = qsub < vasp.pbs > job_id`    
> 
> `incar_template = ${HTC_CWD}/vasp_input_files/incar_template`  
> `valid_incar_tags = ${HTC_CWD}/vasp_input_files/valid_incar_tags`  
> 
> `job_query_command = qstat`    
> `job_killing_command = qdel`  
> `where_to_parse_queue_id = job_id`  
> `re_to_parse_queue_id = [0-9a-zA-Z]+    #based on re.findall`    
> `queue_stdout_file_prefix = #At least one of queue_stdxxx should be specified`  
> `queue_stdout_file_suffix = .o`  
> `queue_stderr_file_prefix = `  
> `queue_stderr_file_suffix = .e` 
> 
> `vasp.out = out`  
> 
> `max_running_job = 10`  
> `max_no_of_ready_jobs = 50`  
> `job_name=vasp_htc`  
> 
> `structure_folder = ${HTC_CWD}/Structures`  
> `cal_folder = ${HTC_CWD}/cal_folder`  
> 
> `htc_input_backup = structures`  
> `htc_input_backup_loc = htc_backup` 
> 
> `**end`

### Below is a template of the n-th firework/calculation (n=2, 3, 4, ...)

> `**start`  
> `step_no = 3`  
> `cal_name = scf`  
> 
> `copy_which_step = 2 #Assume step 2 is the fine structural optimization`  
> `copy_from_prev_cal = INCAR, POTCAR, CONTCAR, KPOINTS`  
> `contcar_to_poscar = Yes` 
> 
> `final_user_defined_cmd = python ${HTC_LIB_LOC}/HTC_lib/VASP/KPOINTS/VASP_Automatic_K_Mesh.py -write --NL:50 --max_vacuum_thickness:5_5_5`  
> `kpoints_type = MPRelaxSet #Just set this here. Will be obsolete`  
> 
> `*begin(add_new_incar_tags)`   
> `ENCUT = 500`  
> `EDIFF = 1.0E-5`  
> `LCHARG = .TRUE.`  
> `LWAVE = .TRUE.`  
> `*end(add_new_incar_tags)`  
> `remove_incar_tags = IBRION, EDIFFG, NSW, ISIF`
> 
> `job_submission_script = ${HTC_CWD}/vasp_input_files/vasp.pbs`  
> `job_submission_command = qsub < vasp.pbs > job_id`  
> `**end`  

**Please refer to the tag list below for all available HTC tags and their detailed descriptions**
<br>

--------------------------------------------------------------------------------------

## The HTC directory structure

The directory structure of a HTC is illustrated in the figure below.

* HTC root directory  
  * file `htc_main.py`: the main python file to invoke this HTC program  
  * file `HTC_calculation_setup_file`: a file in which the calculation workflow is defined  
  * folder `Structure folder`: the folder containing those to-be-calculated structures in the cif or POSCAR format. Because this HTC program will apply the pre-defined workflow only to the structures in the folder specified by the HTC tag `structure_folder`, this folder could be anywhere. Putting it into the HTC root directory might be a good choice.  
  * folder `Calculation folder`: The HTC program will read the to-be-calculated structures in `Structure folder` and create a sub-folders for every materials. The sub-folder names would be the same as the associated structure filenames but without extensions. e.g. structure file `Mater_A.cif` will have a corresponding sub-folder named `Mater_A` under `Structure folder`. Similar to `Structure folder`, this folder could be anywhere with the associated HTC tag `cal_folder`, but again putting it into the HTC root directory is a choice.      
    * folder `Mater_A`: The folder corresponding to structure `Mater_A.cif` in `Structure folder`. In this folder, a series of sub-folders will be created for the DFT calculations according to the pre-defined workflow. **Whether the DFT calculations are performed in this folder or in its sub-folders is determined by the HTC tag `sub_dir_cal`**
      * folder `step_1_xxx`: 
        * if `sub_dir_cal=Yes`: a series of sub-folders will be created under this folder. It is in those sub-folders that DFT calculations are carried out. The sub-folder calculations somewhat are fully determined by the command pre-difined by the HTC tag `sub_dir_cal_cmd`
        * if `sub_dir_cal=No`: the DFT calculation pre-defined in the workflow is going to be carried out directly in this folder.
      * folder `step_2_xxx`: 
        * if `sub_dir_cal=Yes`: a series of sub-folders will be created under this folder. It is in those sub-folders that DFT calculations are carried out. The sub-folder calculations somewhat are fully determined by the command pre-defined by the HTC tag `sub_dir_cal_cmd`
        * if `sub_dir_cal=No`: the second DFT calculation pre-defined in the workflow is going to be carried out directly in this folder.
      * ...
    * folder `Mater_B`
      * folder `step_1_xxx`
      * folder `step_2_xxx`
    * ...  

![](https://github.com/bitsoal/VASP_HTC_framework/blob/upgrade_to_python_3/figs/HTC_directory_structure.png)
</br>

--------------------------------------------------------------------------------------

## Built-in Tag list - below are built-in tags that can be directly used in HTC\_calculation\_setup\_file

- **`${HTC_CWD}`**: The absolute path to the folder under which `htc_main.py` is  
  Any file in `HTC_calculation_setup_file` can be specified by its absolute path or the relative path to `${HTC_CWD}`  
  e.g. Suppose the absolute path of `htc_main.py` is `/home/user0/htc_cal/htc_main.py` and we need to refer to a file named `file_1` under `/home/user0/htc_cal/folder1/`.  
  In this case, `${HTC_CWD}=/home/user0/htc_cal`. `file_1` can be specified using either `/home/user0/htc_cal/folder1/file_1` or `${HTC_CWD}/folder1/file_1`   
  ***We strongly suggest you to use `${HTC_CWD}` to refer to any files that are needed in the calculations. This will make it easy to move the calculations from one place to another with little trouble in modifying the paths to those files.***    

-------------------------------------

- **`${HTC_LIB_LOC}`**: the absolute path to the HTC package.   
  Any file in `HTC_calculation_setup_file` can be specified by its absolute path or the relative path to `${HTC_LIB_LOC}`  
  e.g. Suppose the absolute path to `VASP_Automatic_K_Mesh.py` is `/home/user0/HTC_lib/VASP/KPOINTS/VASP_Automatic_K_Mesh.py`. `VASP_Automatic_K_Mesh.py` can be specified using either `/home/user0/HTC_lib/VASP/KPOINTS/VASP_Automatic_K_Mesh.py` or `${HTC_LIB_LOC}/HTC_lib/VASP/KPOINTS/VASP_Automatic_K_Mesh.py`.  
  If the HTC package is under the same folder as `htc_main.py`, `${HTC_LIB_LOC} = ${HTC_CWD}`.   

---------------------------------------

- **`${MAT_FOLDER_NAME}`**: the material folder name, i.e. `Mater_A`, `Mater_B` in Fig. 1.   
  In our HTC directory structure (Fig. 1), a material, say `Mater_A.cif`, has a associated folder named as `Mater_A` under `Calculation folder`. This folder (`Mater_A` in Fig. 1) is what we call the material folder associated with `Mater_A.cif` here, under which there are a series of calculations on `Mater_A.cif`.  
  We introduce this variable to represent the material folder name. **All `${MAT_FOLDER_NAME}` appearing in HTC tag `user_defined_cmd`, `final_user_defined_cmd`, `sub_dir_cal_cmd`, `incar_cmd, poscar_cmd`, `kpoints_cmd`, `potcar_cmd` and `cmd_to_process_finished_jobs` will be replaced with the corresponding material folder name.** For example, `${MAT_FOLDER_NAME}` will be replaced by `Mater_A` and `Mater_B` for `Mater_A.cif` and `Mater_B.cif`, respectively.   
  *If you still have no idea about what `${MAT_FOLDER_NAME}` is, try to set `user_defined_cmd= echo ${MAT_FOLDER_NAME} > mat_folder_name` in your HTC and check `mat_folder_name` under each material folder*

## Tag list - below are tags that can be set in HTC\_calculation\_setup\_file

### (Note that for boolean data type, we use 'Yes' and 'No')

----------------------

![Alt Text](https://github.com/bitsoal/VASP_HTC_framework/blob/upgrade_to_python_3/figs/VASP_input_file_preparations.png)
</br>
![](https://github.com/bitsoal/VASP_HTC_framework/blob/upgrade_to_python_3/figs/VASP_input_file_preparations_2.png)

- **structure\_folder** (str), **required for the first firework**  
  *The absolute path* of the directory containing to-be-calculated structures. Those to-be-calculated structures could be in the cif format, the VASP POSCAR format or other formats that are supported by `pymatgen.Structure.from_file`.

----------------------

- **cal\_folder** (str), optional for the first firework  
  *The absolute path* of the calculation folder. Under this folder, a sub-folder will be created for every to-be-calculated structure. A series of sub-sub-folder will subsequently created for a sequence of VASP calculations.  
  Default: `cal_folder= where the htc_main.py is called + \cal_folder`

-------------------

- **max\_no\_of\_ready\_jobs** (a positive integer), optional for the first firework.  
  We don't prepare the VASP input files for **all** available calculatoins **at once**. Instead, the available calculations are prepared in such a way that there are up to *around* `max_no_of_ready_jobs` calculations tagged by `__ready__` or `__prior_ready__`. Nevertheless, set `max_no_of_ready_jobs` to a huge number if you want to prepare all available calculations at once.  
  Note that in some cases, the number of calculations tagged by `__ready__` or `__prior_ready__` may exceed `max_no_of_ready_jobs`, because all subsequent independent calculations are prepared simultaneously when the preceeding calculation is finished.   
  Default: `max_no_of_ready_jobs=50` 

-------------------

- **step\_no** (integer), **required for every firework**.  
  start from 1.  
  for the n-th firework, step\_no must be n.

------------------------------------------

- **cal\_name** (str), **required for every firework**.  
  numbers, alphabets and underscores are valid symbols. *Note that each white space between words will be replaced with an underscore.*  
  Together with step\_no, a **sub-folder** named `step_ + step_no + _ + cal_name` will be created. Under this folder, the VASP calculation will be carried out. e.g. if `step_no=4`, `cal_name=band str`, then the folder name is `step_4_band_str`  
  **A specific requirement on file `HTC_calculation_setup_folder/step_n_xxx`: If the whole workflow is defined by a collection of files named as `step_n_xxx` under `HTC_calculation_setup_folder`, we require `step_n_xxx` to be exactly the same as ***the sub-folder name***. In the above example, the 4-th firework/calculation should be defined in file `HTC_calculation_setup_folder/step_4_band_str`.**

-----------------------------

- **copy\_from\_prev\_cal**, optional.  
  **This is one way to set up VASP input files.**  
  One or more than one files that will be copied from the previous calculation.
  *If more than one files are specified, separate them with commas*    
  If copy\_which\_step is not set, "the previous calculation" means the *nearest* previous calculation.    
  **Note that there is no "the previous calculation" for the first calculation**  
  Default: empty

------------------------------

- **move\_from\_prev\_cal**, optional.  
  same as copy\_from\_prev\_cal, but those specified files will be moved instead of being copied from the previous firework specified by copy\_which\_step.  
  If copy\_which\_step is not set, "the previous firework" is the *nearest* previous firework.   
  **Note that there is no "the previous firework" for the first firework**   
  Default: empty

----------------------

- **contcar\_to\_poscar** (bool), optional.  
  Whether to copy the POSCAR from the previous firework specified by copy\_which\_step and rename it as POSCAR.  
  If this tag is `Yes`, the CONTCAR from the previous calculation will be *implicitly* copied and renamed as POSCAR, even though CONTCAR is not in the file list specified by tags copy\_from\_prev\_cal or move\_from\_prev\_cal  
  **Note that there is no "the previous firework" for the first firework**  
  Default: `No`

--------------------------------

- **copy\_which\_step**, required except for the first step.  
  This will specify the parent calculation step from which the files listed in copy\_from\_prev\_cal are copied or the files listed in move\_from\_prev\_cal are moved into the current calculation step.  
  *Note that this tag is meaningless for the first firework*  
  *In a workflow, if there are more than one fireworks that depend on the output of the same calculation and are independent of one another, the calculations defined by them will be carried out simultaneously.*    
  *For any calculation step/firework with `copy_which_step=-1`, POSCAR will be written according to `sort_structure` prescribed in the first calculation/firework.*     
  
  **In old versions, `copy_which_step` was an optional tag, to which the step no of the parent calculation step was passed (e.g. `copy_which_step=2`). Now, however, this tag is mandatory and must be set to the full name of the parent calculation step (format: `step_i_xyz`). This change aims to ensure that you always copy (move) files from the correct parent calculation step according to `copy_from_prev_cal` (`move_from_prev_cal`), especially when you make big changes to `HTC_calculation_setup_file` or `HTC_calculation_setup_folder`, i.e. inserting more steps between existing calculation steps or renaming existing calculation steps.**    

-------------------------------

- **additional\_cal\_dependence**, optional.  
  By default, the calculation of the current firework may only rely on the output of its parent firework (specified by `copy_which_step`). However, chances are that the current firework may depend on the outputs of additional previous fireworks. In this case, the current firework shouldn't start unless all dependent previous fireworks are complete.  
  ~~`additional_cal_dependence` should be a `step_no` or a array of `step_no`s of the additional dependent fireworks. If an array is given, `step_no` in the array should be separated by commas `,`.~~  
  `additional_cal_dependence` should be a full name of an additional dependent calculation step or a array of full names if more than one. In the latter case, separate them using commas `,`.   

Example 1: `step_3_scf` and `step_5_band_str` are the self-consistent calculation (provide WAVECAR) and the band structure calculation (provide CBM, VBM, Efermi). In step 6, we want to calculate the associated partial charge density around CBM. In this case, the INCAR setting of step 6 rely on both step 3 and step 5. The corresponding setting should be  

> `copy_which_step=step_3_scf`  
> `additional_cal_dependence=step_5_band_str`   

Example 2: If the raw VASP input setup of step 6 is copied/moved from `step_2_xxx`, and the modification of the input setup of this step also is based on the output of `step_3_yyy`, `step_4_zzz` and `step_5_xyz`. Then the corresponding setting should be  

> `copy_which_step=step_2_xxx`  
> `additional_cal_dependence=step_3_yyy, step_4_zzz, step_5_xyz`

Default: `empty` 

---------------------------------

- **remove\_after\_cal**, optional.  
  *This tag currently is not available*  
  One or more than one files that will be removed after the calculation defined in this firework is complete. If more than one files are specified, separate them via commas.    
  ***While using this tag, make sure that those specified files will not be needed for later calculations.***    
  Default: empty

----------------------------------------

- **extra\_copy**, optional.  
  **This tag allows you to prepare VASP input files.**  
  This tag allows you to copy files which are not in any previous firework folders.  
  *If more than one files are specified, separate them with commas.*  
  **The copy action defined by this tag is carried out earlier than the copy/move actions defined by copy\_from\_prev\_cal, move\_from\_prev\_cal. So it is before the modifications on vasp input files.**  
  **Note that the absolute path should be provided.**

------------------------------------

- **final\_extra\_copy**, optional.  
  This tag allows you to copy files which are not in any previous firework folders.  
  *If more than one files are specified, separate them with commas.*  
  **The copy action defined by this tag is carried out AFTER the modifications on VASP input files.**   
  **Note that the absolute path should be provided.**    

-------------------------------

- **comment\_incar\_tags**, optional.  ***This tag is already obsolete***  
  comment VASP INCAR tags  
  *If multiple tags need to be commented, separate them with commas.*  
  **It doesn't make sense that you comment an INCAR tag using `comment_incar_tags` while resetting it in `add_new_incar_tags` sub-block simultaneously. If such a contradiction takes place, an error will be incurred.**    
  Default: empty

--------------------------

- **remove\_incar\_tags**, optional.  
  remove VASP INCAR tags.  
  If multiple INCAR tags need to be removed, separate them with commas.  
  **It doesn't make sense that you remove an INCAR tag using `remove_incar_tags` while resetting it in `add_new_incar_tags` sub-block simultaneously. If such a contradiction takes place, an error will be incurred.**  
  Default: empty

-------------------------------

- **is\_fixed\_incar\_tags\_on**, optional. (**Debug is underway**)   
  In most cases, the energy or force convergence of a given calculation step (`EDIFF` and `EDIFFG`) is set to a certain value. However, these values may be automatically changed when the package tries to handle errors. This HTC tag together with `fixed_incar_tags` below are used to overcome this involuntary automatic update of specified INCAR tags. When these two HTC tags are, what these HTC tags do is that  
	
	1. Right after the **FIRST** creation of INCAR for a given step, the package will will retrieve the values of the INCAR tags specified by `fixed_incar_tags` from the very initial INCAR and save them into a file named `fixed_incar_tags.json` under the same calculation folder.   
	2. Let the package change the values of the specified INCAR tags during the process of handling errors.
	3. After the calculation successfully converges, check if the specified INCAR tags changed comapred to those stored in `fixed_incar_tags.json`. If any tag changes, reset them to those stored in `fixed_incar_tags.json` and repeat the last two steps until the calculation completes with the values of the specified INCAR tags being the same as those in `fixed_incar_tags.json`.   
  
  *Note 1: These two HTC tags also apply to other INCAR tags. Please refer to the examples in the `fixed_incar_tags` section*   
  *Note 2: for sub-dir calculations, `fixed_incar_tags.json` will be copied to the newly created sub-folder(s)*  
 
  Default: `is_fixed_incar_tags_on = Yes`      

-------------------------------

- **fixed\_incar\_tags**, optional. (**Debug is underway**)  
  This tag is active only at `is_fixed_incar_tags_on = Yes`. For more detail, please refer to tag `is_fixed_incar_tags_on`. If multiple incar tags need to be specified, separate them using commas.   
  
	1. example 1: `fixed_incar_tags = EDIFF`   
	2. example 2: `fixed_incar_tags = EDIFF, EDIFFG`   
	3. example 3: `fixed_incar_tags = EDIFF, EDIFFG, PREC`   

  Default: `fixed_incar_tags = EDIFF`  
  *Note that whenever `is_fixed_incar_tags_on` is on, tag `EDIFF` is implicitly added to the comma-separated INCAR tag lists that you explicitly set.*

-------------------------------

- **partial\_charge\_cal**, optional.  
  This tag enables the partial charge calculation. If this tag is set to `Yes`, the following tags will be automatically added into INCAR of this firework  
  
  > LPARD = .TRUE.  
  > NBMOD = -3  
  > EINT  = determined by tag `EINT_wrt_CBM` or `EINT_wrt_VBM` and `which_step_to_read_cbm_vbm`

Default: `No`  
**It should be noted that once this tag is set to `Yes`, either `EINT_wrt_CBM` or `EINT_wrt_VBM` should be set in order to determine `EINT`. `which_step_to_read_cbm_vbm` should also be set to read CBM, VBM and Efermi**

--------------------------------------------

- **which\_step\_to\_read\_cbm\_vbm**, optional  
  This tag tells us from which previous step CBM, VBM and Efermi can be read in order to determine `EINT` in INCAR if the partial charge calculation is activated.  
  Default: `Must be specified in the case where partial charge_cal is set to Yes. No need to set in other cases`  
  **It should be noted that `EINT` cannot be determined unless `which_step_to_read_vbm` and one of (`EINT_wrt_CBM`, `EINT_wrt_VBM`) are provided at the same time**  
  **CBM, VBM and Efermi are read from the vasprun.xml of the specified previous step. So that vasprun.xml must exist.**

--------------------------------------------

- **EINT\_wrt\_CBM** & **EINT\_wrt\_VBM**, optional    
  **either one should be given if `partial_charge_cal=Yes`**  
  Default: `Must be specified in the case where partial charge_cal is set to Yes. No need to set in other cases`  
  **It should be noted that `EINT` cannot be determined unless `which_step_to_read_vbm` and one of (`EINT_wrt_CBM`, `EINT_wrt_VBM`) are provided at the same time**

-----------------------------------

- **add\_new\_incar\_tags** sub-block, optional
  - start from the line which starts with `*begin(add_new_incar_tags)`; It ends up with the line which starts with `*end(add_new_incar_tags)`
  - In between the starting line and ending line, just specify INCAR tags as if you are writing INCAR:
    - If an INCAR tag is already in the old INCAR, this tag will be overwritten.
    - If an INCAR tag is not in the old INCAR, this tag will be added.  

**Note that in this sub-block, the multiple pairs of tag-values separated by `;` in a line is not supported. In this case, only the first pair of tag-value will be parsed as a new INCAR tag, and the value is what is in between the first `=` and the second `=`. This may incur unpredictable errors**   
**Setting multiple pairs of tag-values separated by `;` in a line in INCAR is not supported, either. In this case, an error will be incurred.**

**It doesn't make sense that you reset an INCAR tag in `add_new_incar_tags` sub-block while simultaneously trying to remove this INCAR tag using `remove_incar_tags`. If such a contradiction takes place, an error will be incurred.**  
Default: `empty`  
  ![](https://github.com/bitsoal/VASP_HTC_framework/blob/upgrade_to_python_3/figs/VASP_specific_calculation.png)  

-------------------------------------

- **EMAX** and **EMIN** setup in **add\_new\_incar\_tags** sub-block, optional  
	- For DOS calculations, the focus is usually on the states around the Fermi level. VASP INCAR tags **EMAX** and **EMIN** are used to set the upper and lower energy boundary for DOS evaluations. Since the values assigned to **EMAX** and **EMIN** are not relative to the Fermi level, a set of fixed **EMAX** and **EMIN** values may not work well for all materials of which the Fermi level varies greatly. Here, we introduction symbol `Efermi@step_x_yz` to enable us to set **EMAX** and **EMIN** relative to the Fermi level of each material of interest.  
	- Format:
		- `EMAX = Efermi@step_3_scf + 5` (Retrieve the Fermi level from the previous calculation `step_3_scf` and set **EMAX** to the sum of the retrieved Fermi level and 5)
		- `EMIN = Efermi@step_3_scf - 5` (Retrieve the Fermi level from the previous calculation `step_3_scf` and set **EMIN** to the subtraction of 5 from the retrieved Fermi level)
	- Of couse, fixed numbered can also be assigned to **EMAX** and **EMIN**
	- default: `No default`

----------------  

- **NBANDS** in the **add\_new\_incar\_tags** sub-block, optional  
  In addition to its default VASP format, an additional assignment method is enabled as below.
  - *additional assigment method*: `number X prev_cal_step_name`  
    - `number`: a float number larger than or equal to 1  
    - `prev_cal_step_name`: a previous calculation step name.  
    - There must be at least a whitespace between `number` and `X`, and between `X` and `prev_cal_step_name`  
  - *function*: Retrive NBANDS from OUTCAR of `prev_cal_step_name`, which is denoted as NBANDS_prev --> set NBANDS of the current step to the closest integer to `number * NBANDS_prev`

----------------

- **set\_ispin\_based\_on\_prev\_cal**, optional (**debug is underway**)  
  Set ISPIN in INCAR of the current step based on the calculated total magnetic moment in a previous calculation step.   
  - *Format*: `mag + unit + @ + prev_cal_step_name`  
    - `mag`: the magnetic moment threshold. It is a float number;    
    - `unit`: the unit of `mag`. It could be either `/atom` or `tot`; *It must be >=0 since we only compare the magnitude.*        
    - `prev_cal_step_name`: a previous calculation step name. There should not be any whitespace in `prev_cal_step_name`.        
  - *Function*: Read the calculated total magnetic moment (`tot_mag_prev`) from OSZICAR of `prev_cal_step_name` --> Compare `tot_mag_prev` with `mag`:
    - If `tot_mag_prev <= mag`, set `ISPIN = 1` in INCAR of the current step;  
    - If `tot_mag_prev > mag`, set `ISPIN = 2 ` in INCAR of the current step.  
  - *Examples*:
    - `0.02/atom@step_1_str_opt`;  
    - `0.05tot@step_1_str_opt`;
  - default: `empty`
  - During the INCAR preparation, INCAR is modified first according to the setup in the **add\_new\_incar\_tags** sub-block. Afterwards, set ISPIN if the current tag is provided. Therefore, if provided, the current tag will overwrite the ISPIN provided in the **add\_new\_incar\_tags** sub-block.    

----------------

- **bader\_charge**, optional.
  This bool tag decides whether to calculate the [Bader Charge](http://theory.cm.utexas.edu/henkelman/code/bader/). 
  - `Yes`: Calculate the Bader Charge. In this case, those tags will be automatically added into INCAR:  
    - `LCHARG = .TRUE.  
    - LAECHG=.TRUE.  
    - NGXF = 2 * default value  
    - NGYF = 2 * default value  
    - NGZF = 2 * default value`
  - `No`: Don't calculate the Bader Charge.  
    Default: `bader_charge=No`  

**Where to find default (NGXF, NGYF, NGZF):**  
    - if the current firework is the first step (no parent firework), a calculation without these tags will be carried out and then be terminated once the default values of (NGXF, NGYF, NFZF) are found in the OUTCAR. Afterwards, add all of the associated tags into INCAR for the Bader Charge calculation  
    - if the current firework is not the first step, (NGXF, NGYF, NGZF) will be retrieved from the OUTCAR of the previous calculation which is indicated by `copy_which_step` 

---------------------------------------------------  

- **set\_lmaxmix**, optional.    
  If this tag is set to `Yes`, read elements types from `HTC_lib/VASP/INCAR/element_type_table.json` and accordingly set `LMAXMIX` in INCAR to:     
  - 6 if there is (are) f-element(s);   
  - 4 if there is no f-element but there is (are) d-element(s);  
  - 2 if there are only sp-elements;   

*Note that there is no a universal categorization. So we do not provide `element_type_table.json`.* To build up your element type table, please follow the procedure as below:    
step 1: go to `HTC_lib/VASP/INCAR/` and run `python parse_element_type_table.py`. A file named as `element_type_table` will be created. Now, it is almost an empty element table with only H, He and Li provided for your reference to the file format. (Note that we have categorized some elements in `HTC_lib/VASP/INCAR/element_type_table_embedded`. You may also consider building up your own version based on this file by copying `element_type_table_embedded` to `element_type_table` and editting the later).     
step 2: add the elements **of interest to you** into `element_type_table`. *You do not add the whole periodic table.*   
step 3: run `python parse_element_type_table.py` to parse `element_type_table`. If no error occurs, `element_type_table.json` will be created.  

Note that if the type of an element in a structure is not provided in `element_type_table.json`, signal file `__manual__` will be created and the relevant error information will be written into `log.txt`. In this case, please go to provide the type of that element in `element_type_table`, and run `python parse_element_type_table.py` under `HTC_lib/VASP/INCAR/` to re-generate `element_type_table.json`. You are suggested to remove this calculation folder and let this package prepare input files from scratch.  

`LMAXMIX` can be set via `set_lmaxmix`, `ldau_u_j_table` and `add_new_incar_tags` sub-block. This program responds to first `add_new_incar_tags` sub-block, then `set_lmaxmix`, and finally `ldau_u_j_table`. That is, `LMAXMIX` in `add_new_incar_tags` sub-block (`set_lmaxmix`) will be overwritten by that in `set_lmaxmix` (`ldau_u_j_table`).   

Default: `set_lmaxmix = no`     

---------------------------------------------------

- **ldau\_cal**, optional.  
  Invoke a LDA+U calculation. Note that you need to provide a file containing the Hubbard U and J for the atomic species to which the on-site interaction need to be added. Such file is specified by tag `ldau_u_j_table`.  
  Default: `ldau_cal=No`

--------------------------------------------------

- **ldau\_u\_j\_table**, required if `ldau_cal=Yes`  
  A file containing the Hubbard U and J for the atomic species to which the on-site interaction need to be added.  
  The format of the file:  
  `LDAUTYPE=1 | 2 | 4` should be specified in the first line to indicate which type of LDA+U is used. For the following lines, there are four columns, namely, `atomic species`, `orbital type`, `U`, `J`. Bellow is an example of the file:  
  
  > LDAUTYPE = 2  
  > \#element   orbital_type     U     J  
  > Sc            d                2.11    0  
  > Ti            d                2.58    0  
  > V            d                2.72    0  
  > Cr            d                2.79    0  
  > Mn            d                3.06    0  

**Note that U, J and LDAUTYPE may vary, depending on the systems of your interest. So we don't provide default values.** 

---------------------------------------------------

- **incar\_template** (`str`), optional for the first firework  
  This tag comes into play if you want to order INCAR tags when writing INCAR. `incar_template` refers to a file of which each line is either an INCAR tag or empty. Comments (starting with `#`) will be skipped.  
  If this tag is set, INCAR tags will be written into INCAR in the same order/sequence as that in the referred file. The INCAR tags that don't appear in the referred file will be appended to INCAR alphabetically. 
  Suppose we have the referred file like below:
  
  > SYSTEM
  > 
  > ENCUT  
  > ISMEAR  
  > SIGMA  
  > EDIFF       
  > 
  > ISPIN  
  > 
  > IBRION  
  > ISIF  
  > EDIFFG  

If We need to write the above tags into an INCAR except `ISPIN` and there are two more tags (e.g. `NPAR` and `ICHARG`), the output INCAR will be similar to what is shown below:  

> SYSTEM
> 
> ENCUT  
> ISMEAR  
> SIGMA  
> EDIFF       
> 
> IBRION  
> ISIF  
> EDIFFG  
> 
> ICHARG  
> NPAR

-----------------------------------------------------------------------

- **valid\_incar\_tags** (`str`), optional for the first firework  
  This tag refers to a file of which each line is a incar tag. Comments (starting with `#`) will be skipped. We call these incar tags appearing in the referred file **valid incar tags**. *Everytime when INCAR is written, the program will check if all incar tags are **valid**. If any incar tag is found invalid， the program will stop and raise an error prompt*  
  *This is usefull to avoid unpredictable incar tags due to automatic error corrections or any spelling mistake due to manual modifications*  
  *If this tag isn't set or the referred file is empty, nothing will be done*  

----------------------------

![](https://github.com/bitsoal/VASP_HTC_framework/blob/upgrade_to_python_3/figs/VASP_kpoints_type_1.png)
![](https://github.com/bitsoal/VASP_HTC_framework/blob/upgrade_to_python_3/figs/VASP_kpoints_type_II.png)
![](https://github.com/bitsoal/VASP_HTC_framework/blob/upgrade_to_python_3/figs/VASP_kpoints_type_III.png)

--------------------------------------

- **kpoints\_type**, **case sensitive**, **required for every firework**  
  options - MPRelaxSet, MPStaticSet, MPNonSCFSet\_line, MPNonSCFSet\_uniform, Line-mode:
  - MPRelaxSet: The KPOINTS generated by pymatgen.io.vasp.sets.MPRelaxSet
  - MPStaticSet: The KPOINTS generated by pymatgen.io.vasp.sets.MPStaticSet
  - MPNonSCFSet\_line: The KPOINTS generated by pymatgen.io.vasp.sets.MPNonSCFSet in the line mode --> In pymatgen, this type of KPOINTS is for band structure calculations
  - MPNonSCFSet\_uniform: The KPOINTS generated by pymatgen.io.vasp.sets.MPNonSCFSet in the uniform mode --> In pymatgen, this type of KPOINTS is for DOS calculations.
  - Line-mode： The KPOINTS in the line mode is written in the reciprocal coordinates for the band structure calculations. The high-symmetry kpoints is decided by [pymatgen.symmetry.bandstructure.HighSymmKpath](http://pymatgen.org/_modules/pymatgen/symmetry/bandstructure.html)

This tag has three functions:

1. After extra\_copy, copy\_from\_prev\_cal or move\_from\_prev\_cal, if there is still no file KPOINTS under the current firework folder, KPOINTS will be created according to kpoints\_type.   
2. If tag `2d_system` is `Yes`, the KPOINTS will be modified so that K\_z is zero for all kpoints. *Note that this function will be only invoked if KPOINTS under the current firework folder is created. If KPOINTS is copied or moved here from any previous calculations, KPOINTS is then assumed to have zero K\_z for all kpoints.*  
3. Tag `denser_kpoints` is only valid for the KPOINTS generated at kpoints\_type = MPRelaxSet, MPStaticSet.    

--------------------------------------

- **denser\_kpoints** (three float numbers), optional.  
  This tag is only valid for the KPOINTS generated at kpoints\_type = MPRelaxSet, MPStaticSet.  
  Suppose the divisions in the reciprocal space are nk_x, nk_y, nk_z and `denser_kpoints` is set to `mx, my, mz`, then the new divsions are `int(nk_x*mx), int(nk_y*my), int(nk_z*mz)`  
  *Separate the three numbers with commas.*  
  Default: `1, 1, 1`

---------------------------------------------------------

- **reciprocal\_density** (integer), optional.  
  This tag is only valid at kpoints\_type=MPNonSCFSet\_uniform  
  Default: `1000` <--- the value adopted by atomate's firework NonSCFFW

-----------------------------------------------------------------------

- **kpoints\_line\_density** (integer), optional.  
  This tag is only valid at kpoints_type=MPNonSCFSet\_line  
  Default: `40` <-- the default value for atomate's firework NonSCFFW is 20

---------------------------------

- **intersections** (integer), optional.  
  This tag is only valid at kpoints_type=Line-mode.  
  **intersections** is the number of equally spaced kpoints between the starting and ending kpoints of every segment of the overall kpath, inclusive of the starting and ending kpoints.  
  Default: `20`

-----------------------------

- **force\_gamma**, optional.  
  This tag can be set only in the first firework and *this setting will be applied to the whole workflow.*
  - `Yes`: force the kpoints to be gamma-cented.
  - `No`: no such kind of constraint.  
  - Default: `No`

-----------------

- **2d\_system**, optional (obsolete in the future)  
  **This tag can be set only in the first firework and this setting will be applied to the whole workflow.**
  - `Yes`: modify kpoints such that K_z is zero for all kpoints.
  - `No`: no such modification on kpoints.
  - Default: `No`  

----------------------------------

- **sort\_structure**, **optional for the first firework**.  
  **This tag is activated once POSCAR is written for any firework.**
  - `Yes`: Sort sites by the electronegativity of the atomic species using [`pymatgen.Structure.get_sorted_structure`](http://pymatgen.org/_modules/pymatgen/core/structure.html).
  - `No`: If the given structure is POSCAR-formated, just copy the structure and rename it as POSCAR; If not, write POSCAR using `pymatgen.Structure` without re-ordering atom sites.
  - Default: `Yes`  

***Why do we need this tag?***

* In some cases, the atomic sites may be ordered carefully for some specific purposes. So you may not want to change the order of atoms by pymatgen
* The `Yes` state of this tag aims to deal with the given structures whose atoms are not grouped by atomic species. For example, the atoms of the given MoS2 may be arranged like `S  Mo  S` instead of `S S  Mo` or `Mo S S`. Such non-grouped atom arrangements may happen if the to-be-calculated structures are outputs of pymatgen and while exporting from pymatgen, `get_sorted_structure` has not been called to group atoms.  
* The `No` state of this tag can facilitate [split-mode CALYPSO](http://www.calypso.cn/) for structure predictions. By applying the particle swarm optimization method, CALYPSO generates certain number of to-be-relaxed structures. *If CALYPSO works in the split mode, users should **manually** relax these structures.* These structures are POSCAR-formated. Taking into account the backward compatibility of VASP, the line listing atomic species in POSCAR is missing, but `pymatgen.Structure` cannot correctly parse such kind of POSCAR, let alone create correct POSCARs and POTCARs. So we provide this tag `sort_structure` whose `No` mode allows POSCAR to be created by just copying and renaming. With this `No` mode, this VASP HTC framework can be utilized to automatically relax structures predicted by CALYPSO. *Note that since `pymatgen` cannot write correct POTCAR due to the absence of atomic species line in CALYPSO-generated POSCARs, `POTCAR` should be copied from somewhere. This can be realized via tag `extra_copy` or `final_extra_copy`.*   

***The creation of POSCAR:***  
*For the second or later fireworks, POSCAR can be inherited from previous calculations, while this is not the case for the first firework. By default, for the first firework, the program will retrieve the structure under the folder which is specified by tag `structure_folder` where all to-be-calculated structures are stored in the form of cif, POSCAR or others that are supported by `pymatgen.Structure`. Once POSCAR is created according to tag `sort_structure` for the first firework, other VASP input files can be created accordingly and calculations therefore proceed. Of course, you may use tag `user_defined_cmd` to overwrite POSCAR, say cleave surfaces, which is why we let the firetasks defined by `user_defined_cmd` run before the creation of other VASP input files.*

---------------------------------------------

**max\_ionic\_step** (positive integer), optional,  
This tag provides us with another degree of freedom to ensure an accurate structural relaxation.  
**Chances are that a structural relaxation calculation may converge w.r.t `EDIFFG` after N steps, but it will still take tens or hundreds of steps to converge if we change CONTCAR to POSCAR and do one more structural relaxation with the same VASP input setting. In principle, the structural relaxation based on the optimized structure should converge within few steps.**   
If `max_ionic_step` is set, the program will compare the number of step to achieve the ionic convergence, denoted as N, with `max_ionic_step`. If `N>max_ionic_step`, the program will treat the structural relaxation calculation as if the structural relaxation does not converge. The following operations made by the program are to backup the calculation, change CONTCAR to POSCAR, reset `IBRION=1` and re-submit the job. Of course, these automatic operations will be executed only if the number of errors that already happened for the calculation does not reach the specified error maximum above which the error should be handled manually.  
Default `max_ionic_step=-1 (inactive)`  

-------------------------------------------

**skip\_this\_step**, optional. (Debug is underway)  
While designing a workflow, you may leave some steps empty/skipped for later use. An empty/skipped step can be realized by seting `skip_this_step = Yes`.  
When this tag is on, other tags will be ignored. Nevertheless, some compulsory tags need to be set. The following template should work well.  
>`step_no = 3`  
>`cal_name = empty_step`      
>`kpoints_type = MPRelaxSet` 
> 
>`copy_which_step = step_2_xyz`
>  
>`skip_this_step = Yes`
>
>`job_submission_script = a valid path to a whatever file`  
>`job_submission_command = whatever bash command`  

*Note that the first step cannot be skipped.*  
Default: `skip_this_step = No`

-------------------------------------------

**user\_defined\_cmd**, optional,  
This tag allows users to execute a series of commands to perform user-defined firetasks, say cleave a surface from a bulk structure optimized in the previous firework, introduce dopants/defects *et. al.*  
*If there are multiple commands, separate them with commas.*  
e.g. `user_defined_cmd = date >>__test_file__, echo 'test user_defined_cmd tag' >>__test_file__`    
**By default, the commands will be executed in the current firework folder. You can put your commands in a bash script so that before executing them, you can switch to other folders. If your firetasks involve modifications of VASP input files, we suggest you to make a sub-folder under the current firework folder. Just copy required files into this sub-folder, carry out your firetasks and copy results back, e.g. new POSCAR**  
Default: empty

------------------------

**final\_user\_defined\_cmd**, optional,  
This tag allows users to execute a series of commands to perform user-defined firetasks.  
*If there are multiple commands, separate them with commas.*  
e.g. `final_user_defined_cmd = date >>__test_file__, echo 'test final_user_defined_cmd tag' >>__test_file__`    
**By default, the commands will be executed in the current firework folder. You can put your commands in a bash script so that before executing them, you can switch to other folders. If your firetasks involve modifications of VASP input files, we suggest you to make a sub-folder under the current firework folder. Just copy required files into this sub-folder, carry out your firetasks and copy results back**  
Default: empty

------------------------------------

**incar\_cmd, poscar\_cmd, kpoints\_cmd** and **potcar\_cmd**, optional,   
These tags work in the same way as `user_defined_cmd` and `final_user_defined_cmd`. They are provided to avoid heavily using `user_defined_cmd` and `final_user_defined_cmd`. The commands specified by these tags are **first** executed to **create** or **modify** INCAR, POSCAR, KPOINTS and POTCAR. The execution of these commands may have impacts on other HTC tags:   

- `poscar_cmd`: If the commands specified by this tag creates POSCAR, tag `sort_structure` is deactivated.   
- `potcar_cmd`: If this tag creates POTCAR, pymatgen won't be called to create POTCAR  
- `kpoints_cmd`: all other HTC tags related to KPOINTS should work.  
- `incar_cmd`: If the commands specified by this tag creates INCAR, `pymatgen.io.vasp.sets.MPRelaxSet` won't be called to create the initial INCAR. But the subsequent modification defined by other HTC tags should work.  

------------------------------------

**cmd\_to\_process\_finished\_jobs**, optional,   
This tag defines the command(s) to clean or analyze the successfully finished calculation labelled by `__done__`. It has the same format as `user_defined_cmd, final_user_defined_cmd, ...`   
If the commands are successfully called, change `__done__` to `__done_cleaned_analyzed__`; Otherwise, change `__done__` to `__done_failed_to_clean_analyze__`.   
*Of course, if this tag is not set, the calculation status will remain at `__done__`.*      
*Note that if you are going to delete output files using this tag, ensure that the command(s) is(are) capable of ignoring non-existent files.* **You should be cautious about file/folder removal because this action is not reversible.**    
Default: empty

--------------------------------------------

**user\_defined\_postprocess\_cmd**, optional,  
This tag allows users to execute a series of commands to perform user-defined firetasks for post-process. *This tag is currently not available*  
*If there are multiple commands, separate them with commas.*  
e.g. `user_defined_postprocess_cmd = date >>__test_file__, echo 'test user_defined_postprocess_cmd tag' >>__test_file__`    
**By default, the commands will be executed in the current firework folder. You can put your commands in a bash script so that before executing them, you can switch to other folders. If your firetasks involve modifications of VASP output files, we suggest you to make a sub-folder under the current firework folder in order to avoid damaging VASP output files. Just copy required files into this sub-folder, carry out your firetasks (and copy results back to the current firework folder)**  
Default: empty

-------------------------------------

**sub\_dir\_cal**, optional,  
This tag together with `sub_dir_cal_cmd` defines the sub-folder calculations, as shown in the first figure (the HTC directory structure). See `sub_dir_cal_cmd` for more details about the sub-folder calculations.  
Default: `No`  

------------------------------------

**sub\_dir\_cal\_cmd**, required if `sub_dir_cal=Yes`; optional otherwise,  
This is the main HTC tag to realize sub-folder calculations.  
**Why is there this tag:**  

* Might be useful for the lattice constant optimization for 1D/2D materials if you don't want to use `ISIF=3` to relax everything. Suppose we are gonna relax lattice constant a, we may relax the structure with `ISIF=2` first and then do a single-point calculation with different a. To get the optimal a, we may fit the a v.s. Energy to an equation of state or just make an interpolation.  

**How to realize the sub-folder calculations**  
As shown in the second figure (`The procedure of preparing VASP input files and relevant tags`), actions related to `sub_dir_cal` and `sub_dir_cal_cmd` are taken at the end. So INCAR, POSCAR, KPOINTS and POTCAR have already been prepared according to the preceding HTC tags. **Commands defined by `sub_dir_cal_cmd` should:** 

* use these VASP input files as parent input files, change them as you want, create sub-folders and save them into the sub-folders for sub-folder DFT calculations.
* create a signal file after the input file preparations in sub-folders such that the HTC program can respond.
  * `__ready__` or `__prior_ready__`: The calculation will be submitted and the signal file will be changed to `__running__`
* change `__sub_dir_cal__` to `__manual__` if any error takes place during the sub-folder input file preparations or in other specified conditions.
* change `__sub_dir_cal__` to `__done__` when all the sub-folder calculations and post-process of the outcome are complete.
* copy some files from sub-folders back to the parent folder such that the subsequent calculations relying on this step can copy required files. **Note that such action may not needed. Those required files can be copied or moved by setting `user_defined_cmd` in the subsequent dependent calculations using relative paths.**  

**commands defined by `sub_dir_cal_cmd` is going to be called repeatedly by the program to detect and change the status of the sub-folder calculation. We suggest you to write all commands into a script and copy that script to the specific calculation folder using HTC tag `extra_copy` or `final_extra_copy`. Then just execute that script.**  

**A bunch of scripts are ready under `HTC_lib/VASP/Sub_Directory_Calculation_Scripts`. The aim and the execution of each script have been detailed at the beginning of each script. We are testing those scripts. Any feedbacks are also appreciated!**  

Default: **No default command. Any command that can be executed in the linux terminal. If there are more than one commands, separate them using `,`. Anyway, we suggest you to put all commands into a script and simply run that script.**  

-------------------------------------------------

**preview\_vasp\_inputs**, **optional for the first firework**  
**This tag has been obsolete. Not matter what the user sets to `preview_vasp_inputs`, it will eventually be set to `No`. The best way to check whether your `HTC_calculation_setup` works or not should be to feed one small/test structure to it and let the pre-defined calculations run for the test structure.**  
~~This tag enables you to preview the vasp inputs of each firework defined in `HTC_calculation_setup`. **This tag is designed to check whether the input setting defined in `HTC_calculation_setup` is correct before the real HTC calculation is carried out.**~~   

- ~~`Yes`: When `python htc_main.py` is executed, a folder named `preview_HTC` will be created under the same directory where `python htc_main.py` is executed. Under `preview_HTC`, the vasp inputs of each firework will be written. ***In this case, the real HTC calculation won't be carried out.***~~  
- ~~`No`: ***The real HTC calculation will be carried out***~~  
  ~~default: `No`~~

-----------------------------------

- **error\_backup\_files**, optional.  
  When an error occurs to a calculation and the program is able to handle it, the VASP input|output files specified by `error_backup_files` will be copied/saved under `error_folder/error_#`. In the meanwhile, the files specified by `vasp.out`, `queue_stdout_file_prefix`, `queue_stdout_file_suffix`, `queue_stderr_file_prefix`, `queue_stderr_file_suffix` will also be copied/saved under the same folder.  
  *When an error cannot be automatically fixed by the program, you have to manually get rid of it. In this case, these backup files might be helpful.*

default:   
`for step 1: error_backup_files = INCAR, POSCAR, CONTCAR, KPOINTS, XDATCAR, OUTCAR, OSZICAR`  
`for other steps: error_backup_files = the same as step 1`  

---------------------------------- 

- **htc\_input\_backup** && **htc\_input\_backup\_loc**, optional for the first firework  
  `htc_input_backup` can specifiy a series of comma-separated ***files*** or ***folders***, which the program will back up under the folder specified by `htc_input_backup_loc`.  
  *Note that the specified files or folders should be relative to `${HTC_CWD}` (see above for this built-in tag). Don't refer to them using the absolute paths.*  
  `htc_main.py`, `HTC_calculation_setup_file` (if existent) and `HTC_calculation_setup_folder` (if existent) will be ***implicitly*** backed up.  
  `htc_input_backup` comes into play only if you have additional important htc input to be backed up.  

default:  
`htc_input_backup: empty`  
`htc_input_backup_loc: ${HTC_CWD}/htc_input_backup_folder`

-----------------------------------------

#### Below are tags related to job managements

-----------------------

- **job\_submission\_script**, **required for every firework**.  
  **Note that the absolute path should be used.**

-------------------------------------------------

- **job\_submission\_command**, **required for every firework**.  
  e.g. On LSF queue system, suppose the job submission script refered by job\_submission\_script tag is called `vasp.lsf` and this tag can be `bsub < vasp.lsf > job_id`, where `job_id` will store the queue id and will be the value of tag where\_to\_parse\_queue\_id

--------------------------------

- **job\_name**, optional for the first firework.  
  The job name shown in the job status query output.  
  In PBS queue system, `job_name` is the one specified by the field `#PBS -N "xxx"`  
  In LSF queue system, `job_name` is the one specified by the field `#BSUB -J "xxx"`  
  where `xxx` in the double quotation marks are `job_name`  
  Note that if provided, we will append a white space to the specified `job_name`. This would allow us to distinguish `xxx` from `xxxy`.  
  Default: `empty` 

- **max\_running\_job** (integer), optional for the first firework    
  The maximum number of running/pending jobs in queue for your htc project. For example, if `max_running_job=10`, the program can automatically submit jobs such that there are maximally 10 running/pending jobs in queue.   
  Default: `max_running_job=30`  
  **how to count running jobs**  
  In general, when you use the cmd specified by `job_query_command` to query the overall status for all submitted jobs, the queue will return a multiple-line summary. Each line of the summary displays the status of a submitted job except the header (the first several lines). The program will count the running/pending jobs of your htc project by counting the string specified by `job_name` in this multiple-line summary. *Note that if the string specified by `job_name` appears more than once in a line, it will be counted as 1.* 

**Tips**  
    - If you want `max_running_job` to refer to the total number of running/pending jobs, including those of this htc project and those of other projects, do not set `job_name`. This might be useful if the job submission per user is limited, say every user can submit 20 jobs maximally.  
    - If you want `max_running_job` to refer to the total number of running/pending jobs **only** for this htc project, do set `job_name` and make sure it is unique. This might be useful if there are more than one htc projects, e.g. 20 running/pending jobs for project 1; 30 running/pending jobs for project 2; 5 running/pending jobs for project 3.  
    - If the job submission per user is limited, it is recommended not to set `max_running_job` to that maximal value in case you want to submit some urgent jobs manually. Say each user can submit 30 jobs maximally, `max_running_job=25 or 26 or 27 or 28` might be a good choice.

--------------------

- **where\_to\_parse\_queue\_id**, **required only for the first firework**.  
  a file from which the queue id will be parsed.  
  e.g. If the job submission cmd is `bsub < vasp.lsf > job_id`, then `where_to_parse_queue_id=job_id`

---------------------

- **re\_to\_parse\_queue\_id**, **required only for the first firework**.  
  The regular expression pattern passed to python `re.findall` to parse queue id from the file specified by where\_to\_parse\_queue\_id.  
  Just make sure this regular expression is well designed such that no other string in the file where\_to\_parse\_queue\_id can be matched.

----------------------------------

- **job\_query\_command**, **required only for the first firework**.      
  For LSF batch system, it is `bjobs -w`   
  For PBS system, it is `qstat`

---------------------------------------------------------

- **job\_killing\_command**, **required only for the first firework**.  
  For LSF batch system, it is `bkill`.    
  For PBS system, it is `qdel`

--------------------------

- **queue\_stdout\_file\_prefix**, **queue\_stdout\_file\_suffix**, **queue\_stderr\_file\_prefix**, **queue\_stderr\_file\_suffix**, **Required for the first firework**.  
  Normally, when the calculation is done, the queue system will generate two files reporting errors and summarizing this work, respectively. Let's denote them as stdout, stderr.  
  The two files are useful for their presence indicates that the job is done. If no error is detected for this step, the post-process will proceed and afterwards, the next firework will be carried out. 
  
     **These four tags are set to search for stdout and stderr files.**  
     **Note that you need to specify at least one of the four tags:**  
  
       - Sometimes the queue stdout and stderr files will join together, giving a single file. In this case, this single file is the target file. You can set its prefix or suffix using either (queue\_stdout\_file\_prefix, queue\_stdout\_file\_suffix) or (queue\_stderr\_file\_prefix, queue\_stderr\_file\_suffix) pair.
       - For either queue stdout or stderr files, it may only have a fixed prefix or a fixed suffix. In this case, you just need to specify the fixed one for the queue file.
         - e.g. for lsf.o1234, just set queue_stdout_file_prefix = lsf.o
         - e.g. for 1234pbs.e, just set queue_stderr_file_suffix = pbs.e
      - **Just make sure the provided suffix or prefix can find the target file(s) stdout or stderr.** 

--------------------------

- **vasp.out**, **required only for the first firework**.  
  e.g. If the vasp submission cmd is `mpirun -n 16 vasp_std > out`, then **vasp.out** is `out`  
  e.g. If the vasp submission cmd is `mpirun -n 16 vasp_std`, then **vasp.out** is `vasp.out`

-------------

- **`jobs_treated_like_running_jobs`, optional for the first firework.** (Debug is underway)  
The running jobs which are automatically submitted by the HTC package are tagged with `__running__`. But chances are that you do not want the HTC package to do the automatic submission. Instead, you have an additional script responsible for the job submission. This would be the case if you are allowed to request a certain amount of CPUs and memories with a very very long walltime (e.g. a few weeks/months). In this case, the allocated CPUs and memories can be used to run multiple (small) jobs one after another until the walltime is reached. We call these (small) jobs **packed**.  Depending on the calcualtion status, these packed jobs can be tagged with different non-magic signal files. For example, the to-be-calculated packed jobs are tagged with `__packed_1__`; the running packed job with `__packed_running__`; the packed jobs which finished unsuccessfully are tagged with `__packed_error__`. For the **running** packed job, `jobs_treated_like_running_jobs` provides a way to check whether an error occurs for the calculation **on the fly** just like those jobs tagged with `__running__`. Hence, we can somewhat improve the utilization of the limited allocated computational resources.     
If the running packed jobs have been assigned different signal files, say `__packed_running_1__` for one running packed job and `__packed_running_2__` for another running packed job, separate them using commas, i.e., `jobs_treated_like_running_jobs = __packed_running_1__, __packed_running_2__`.  
Default: Empty 

-------

- **`max_workers`**, **required for the parallel computing based on the python class ProcessPoolExecutor**  
In addition to mpi4py, the parallel implementation of this htc program has also been achieved using python class [ProcessPoolExecutor](https://docs.python.org/3/library/concurrent.futures.html). `max_workers` is needed in the **first** step setup to specify the maximum number of proccesses which can be utlized for ProcessPoolExecutor-based parallelization. The associated htc main script is tentatively named as `htc_main_ProcessPoolExecutor.py`, whereas `htc_main_mpi.py` corresponds to the parallelization based on mpi4py. In the latter mpi4py case, this tag MUST NOT be set in the first step setup.  
Default: no default. A positive integer must be set to `max_workers` while running htc_main_ProcessPoolExecutor.py


### Tag list ends here. You can find a template of `HTC_calculation_setup_file` under folder `Template`

-------------------------

<br>
<br>
<br>

## How to control job status

### We use ***built-in*** signal files to control job submission, job termination, error detection and error correction

![Alt Text](https://github.com/bitsoal/VASP_HTC_framework/blob/upgrade_to_python_3/figs/signal_file_response.PNG)

When the workflow is running, some **built-in** signal file will be present in every firework folder. The program will respond to these signal files as listed below:  

- **Format requirement of any signal file**: It must start and end with double underscores (`__`) 
- **In `${HTC_CWD}/
- .json`, the calculation tagged by signal file `__xyz__` is categorized into `xyz_folder_list`**  
- `__vis__`: The program will prepare the vasp input files according to the workflow. Once it is done, `__vis__` --> `__ready__`
- `__ready__`: The program will submit the job by using the command defined in the workflow. Once submitted, `__ready__` --> `__running__`
- `__prior_ready__`: The program will first submit the jobs with this signal file compared to those labeled by `__ready__`
- `__sub_dir_cal__`: This signal file tells the program that a series of calculations are carried out under this folder. HTC tag `sub_dir_cal=Yes` switch `__vis__` to this signal file instead of `__ready__`. This signal file can be changed to `__manual__` or `__done__`, fully depending on the HTC tag `sub_dir_cal_cmd`. Please refer to HTC tags `sub_dir_cal` & `sub_dir_cal_cmd` above for more detail. 
- `__running__`: The program will check the errors on the fly, e.g. check the electronic divergence. If the errors are detected, `__running__` --> `__error__` and write the error type into `__error__`
- `__error__`: The program will kill the job. Once it is done, `__error__` --> `__killed__`
- `__killed__`: The program will try to fix the error. If successful, `__killed__` --> `__ready__`; otherwise `__killed__` --> `__manual__`
- queue system's `stdout` and `stderr`: The program will think the job is done and all error checkers will be called to check errors. If any errors are found, `__running__` --> `__error__`; Otherwise, `__running__` --> `__done__`
- `__manual__`: The program cannot fix the error and the error should be fixed manually.
- `__bad_termination_`: When the job fails due to the error `=   BAD TERMINATION OF ONE OF YOUR APPLICATION PROCESSES` in file vasp.out **for the first time**, the program will **resubmit** the job automatically and create this signal file. When such error happens again, the presence of this signal file tells the program that this is the second time to encounter such error. In this case, the program cannot automatically handle this error anymore, `__killed__` --> `__manual__`.
- `__skipped__`: The jobs labeled by this signal file will be skipped. Users can simply judge if a job is necessary via tag `user_defined_cmd`/`final_user_defined_cmd`. If the calculation is unnecessary, users can generate this signal file to skip unnecessary calculations.  
- `__done_cleaned_analyzed__`: When the command(s) defined by `cmd_to_process_finished_jobs` is successfully run on a job labelled by `__done__`, `__done__` --> `__done_cleaned_analyzed__`.   
- `__done_failed_to_clean_analyze__`: When the command(s) defined by `cmd_to_process_finished_jobs` fails to run on a job labelled by `__done__`, `__done__` --> `__done_failed_to_clean_analyze__`.   

***Signal file priority:*** `__done__` > `__done_cleaned_analyzed__` > `__done_failed_to_clean_analyze__` >`__manual__` > `__vis__` > `__skipped__` > `__ready__` > `prior_ready__` > `__sub_dir_cal__` > `__error__` > `__running__` >  `__killed__`  

*Note that signal file `__complete__` is introduced to the material folder. This signal file indicates that all of the pre-defined calculations for a given material are complete. It make no sense to still check these finished calculations repeatedly. As such, the program shoud stop checking the status of these calculations and just look for those to-be-updated calculations. This would save much time because as htc goes on, more and more jobs are in the complete status. If you insist checking the calculations of a material repeatedly, delete `__complete__` and create `__incomplete__`.* 

**Note that when you manually fix a calculation labelled by `__manual__`, DO not remove this signal tag until all changes have been made. After modifications, you have two ways to bring it back to the program scope (_The second way is recommended_):**

- If you want to manually submit the job:
  - step I: remove OUTCAR, OSZICAR, vasp.out, queue stdout & stderr files.
  - step II: submit the job
  - step III: change `__manual__` to `__running__`.
- If you want the program to do the job submission:
  - All you need to do is to change `__manual__` to `__ready__`. In this case, the program will automatically remove OUTCAR, OSZICAR, vasp.out, queue stdout & stderr files before submitting this job.    

**Note that the program only responds to the above built-in signal files. Users can define new signal files to tag some calculations. But the program will do nothing to those calculations.**  

**If you take a look at `${HTC_CWD}/htc_job_status.json`, you will find some calculations may be categorized into a non-built-in type, say `xyz_folder_list`. This is because for a given calculation, the program will first search for any of the above built-in signal files. If none of them is found, the program will then check whether there is any file starting and ending with double underscores (`__`). If found, such a file will be treated as an *unknown* signal file and the calculation will be categorized into such a type. Otherwise, put it into `other_folder_list`. Note that if there are more than one unknown signal files detected for one calculation, say `__xyz__` and `__abc__`, this calculation will be put into both `xyz_folder_list` and `abc_folder_list`. But for any calculation tagged by a built-in signal file, it is unique in `${HTC_CWD}/htc_job_status.json`.**

### Update the calculation status and go to job submission

- **`__update_now__` under `${HTC_CWD}`**, *one-time signal file*:   
    By default, the program scans/updates the calculations every 10 mins. Meanwhile, scanning the status of certain calculations may involve very slow external commands (e.g. `sub_dir_cmd`, `incar_cmd`, `poscar_cmd`, ...). It may already take much time (few minutes) to run such external commands on a calculation; Running these slow commands to all of such kind of calculations may take serveral hours. If you want to skip update of the rest of such kind of calculations and write the latest status into `htc_job_status.json` and `htc_job_status_folder` as soon as possible, just create a file named `__update_now__` under `${HTC_CWD}`.   
    ~~*Note that `__update_now__` could be created anywhere under `${HTC_CWD}`. It could be exactly under `${HTC_CWD}` or under any `sub-...-sub-folder` of `${HTC_CWD}`. The program is able to find and respond to it.*~~ We abandon this function because it may be a great burden and take much time to go to every `sub-...-sub-folder` of `${HTC_CWD}` to look for `__update_now__`, especially when there are hundreds of thousands of files/sub-directories under `${HTC_CWD}`. This is in fact contradicting the idea of this signal file, i.e. *scan/update calculations as soon as possible*.  

- **`__scan_all__` under `${HTC_CWD}`**, *one-time signal file*      
    As the high-throughput calculations go on, more and more calculations are carried out. One problem is that the time spent in checking the status of all calculations would increase significantly. To overcome this issue, four actions below are taken:    
  
    1. When the program starts, it will scan ALL calculations and save these statuses into a python variable `total_cal_status(_dict)`. *Later on, the program will JUST scan these calculations which were found by the very first scan-all operation and update `total_cal_status(_dict)` with the new calculation statuses.* For example, when the program is checking calculation A under `cal_loc_A`, which is tagged with `__running__`, it will change `__running__` to `__done__` if calculation A finished successfully, or to `__error__` if calculation A is dead because of an error, or remain `__running__` if calculation A has not finished. Having checked/updated calculation A, the program will try to figure out the new status of calculation A and update `total_cal_status(_dict)`.        
    2. Sometimes, you need to manually handle some calculations tagged by `__manual__`. In this case, DO NOT remove `__manual__` until all changes have been made. The program is able to find the new status of these manually fixed calculations.   
    3. You can always create `__scan_all__` under `${HTC_CWD}` to ask the program to scan ALL calculations.    
    4. Normally, a series of calculations are carried out for a material and they are put into the same folder, which is called **material folder**. The program will tag a material folder with `__complete__` if all calculations under this folder are complete. This would speed up the process of scanning all calculations because the status of completed calculations will remain unchanged and the existence of `__complete__` under a material folder tells the program to safely skip this material folder. Of course, you need to remove `__complete__` if you want to add more calculations to a material.    

- **`__go_to_submission__` under `${HTC_CWD}`**, *one-time signal file*     
    As explained by its name, this signal file asks the program to directly go to job submission.   

***It may take some time to wait for the program to handle `__udpate_now__`, `__scan_all__` and `__go_to_submission__`. When these one-time signal files are removed by this program, it means that they have been handled***

### How to change a certain number of calculations from their original status to a target status

Under `${HTC_CWD}`, you can create a signal file named `__change_signal_file__` to change a certain number of calculations from their original status (signal file) to a target status (signal file). In `__change_signal_file__`, three parameters should be defined in the following format, e.g.

> `original_signal_file = __ready__`  
> `target_signal_file = __null__`   
> `calculation_name = step_n_xyz #Optional`   
> `no_of_changes = 20`  

The above setup means to randomly pick at most 20 calculations originally tagged by `__ready__` (`ready_folder_list` in `htc_job_status.json`) and change them to `__null__`. An optional tag `calculation_name` is provided if the to-be-changed target calculations are only those at the *n*-th step.  

* Note that `original_signal_file` must be one of the existent signal files (See above for all valid|built-in signal files), whereas `target_signal_file` could be anything.  
* We also ask you to define `original_signal_file` and `target_signal_file` in such a way that they start and end with double underscores (`__`)
* If `target_signal_file` is not in the builit-in signal file list, this program will do nothing to the calculations tagged by `target_signal_file`  
* `__change_signal_file__` is a **one-time** signal file. After the program responds to this signal file, it will be removed and the response to it will be written into `${HTC_CWD}/__change_signal_file__.log`   

### Read the updated pre-defined calculation workflow on the fly

- **`__update_input__` under `${HTC_CWD}`**, one-time signal file   
    During the high-throughput calculations, you may want to make changes to the pre-defined calculation workflow in either `HTC_calculation_setup_folder` or `HTC_calculation_setup_file`. The presence of one-time signal file `__update_input__` under `${HTC_CWD}` tells the program to read the updated calculation workflow. No need to kill and re-execute the program any more :). *Again, it may take some time to wait for the program to handle this signal file.*   
    If you update `structure_folder` or `cal_folder` in the setup of the first step, file `__forced_sleep__` will be automatically created under `${HTC_CWD}` to ask you to verify this update. If this is what you want, just remove  `__forced_sleep__`, and the program will proceed with the updated `structure_folder` or `cal_folder`. If this is not the case, (step i) correct `structure_folder` or `cal_folder` in the first calculation steup; (step ii) create `__update_input__` under `${HTC_CWD}`; and (step iii) remove `__forced_sleep__`. In this case, the program will re-read the updated calculation setup and repeat the above checkup about `structure_folder` or `cal_folder`.   

~### Pack many small calculation jobs into one. (alpha phase)~  
~`Normally, one job, one submission. On the other hand, you can also pack a bunch of small jobs into one, and just submit once. Let's call those to-be-packed small jobs `sub-jobs`. `HTC_lib/VASP/Pack_jobs/prepare_packed_job_PBS_script.py` may help you to create a job submision script to pack `sub-jobs` for PBS batch scheduler. **The idea is to request a certain number of CPUs and memory at once, and then re-allocate them to a bunch of sub-jobs.** You need to change the parameters needed at the beginning of `HTC_lib/VASP/Pack_jobs/prepare_packed_job_PBS_script.py`, which are well self-explained. Let's call the created submission script `packed_jobs_script.pbs`  
`packed_jobs_script.pbs` assumes that the status of each to-be-packed sub-job is `__packed__`. Prior to run VASP, it directs `${PBS_JOBID}` to a file named `job_id` under each sub-job and changes the status of each sub-job from `__packed__` to `__packed_running__`. If the VASP calculation associated with a sub-job finishes before running out of time, `__packed_running__` will be changed to `__runing__`. So, those finished sub-jobs can be handled directly by the program.  
We suggest you to use `__change_signal_file__` to change a certain number of calculation jobs from `__ready__` to `__packed__`. For exmaple, you want to pack 20 calculation jobs:~  
~>`__change_signal_file__`~
~>>`original_signal_file = __ready__`~  
~>>`target_signal_file = __packed__`~ 
~>>`no_of_changes = 20`~  

~Then you can find the absolute path to those calculations tagged by `__packed__` in `${HTC_CWD}/htc_job_status.json` as well as in file `${HTC_CWD}/htc_job_status_folder/packed_folder_list`. Copy the latter to somewhere, and feed this copied file to `HTC_lib/VASP/Pack_jobs/prepare_packed_job_PBS_script.py` by setting parameter `filename` at the beginning.~ 

### How to stop the program.

You can stop this program by creating a file named `__stop__` under `${HTC_CWD}` where `python htc_main.py` or `nohup python htc_main.py 2>1&` was executed to start this program.
