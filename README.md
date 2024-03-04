# nbt

nbt (nic bids tools) contains a collection of python scripts facilitating BIDS-conversion, fMRIprep-based preprocessing and analyses of BIDS-compliant datasets.

# How to convert raw MRI data into a BIDS dataset  

1. All nbt tools and fmriprep can only be started on Linux systems. If you do not have an account on the Linux VM (or the Linux server) please ask the Linux admins to get an account and a project directory on the nicshare drive. Raw DICOM files must be copied to your nicshare project directory and must be organized in subject and session subdirectories [e.g. raw/sub1/session1, raw/sub1/session2, raw/sub2/...]
2. A json-formatted template file defining the data structure of the raw MRI data must be created. The template must contain a subject object with keys "subjectID" (subject ID) and "sessions" (array of objects each defining the session directory ("sessionDir"), session ID ("sessionID") and a "scans" array). Each "scans" object defines a particular MRI sequence by BIDS key-value pairs:

|key|value|
|---|-----|
|acq|BIDS acquisition (NIC descriptors like mb3me4 for multiband-factor 3 and 4 echos can be used here)|
|data_type|BIDS data type|
|dir|IDS phase encoding direction|
|echos|number of echos|
|intendedfor|can be either a single task or "all" (for applying fieldmaps to all fmri scans)|
|mod|BIDS modality|
|run|BIDS run|
|task|BIDS task name|

For example template files see example1_template.json and example2_template.json.

3. Run nbt_define.py to generate the dataset structure for the entire set of raw DICOM files.

**Usage: nbt_define.py [OPTIONAL ARGUMENTS] template_json  raw_dicom data_json**

nbt_define.py assigns BIDS key-value pairs to each DICOM image in **raw_dicom** according to a json-formatted template file (**template_json**). nbt_define.py returns a json file (**data_json**) containing BIDS key-value pairs for all DICOM images with matches in **template_json**. **raw_dicom** must be organized in subject and session subdirectories [e.g. raw/sub1/session1, raw/sub1/session2, raw/sub2/...]. nbt_define.py requires Python 3.XX plus some further packages (see imports in nbt_define.py). For more information type ./nbt_define.py -h.

4. Run nbt_convert.py to convert dicom to niftis and to create a BIDS-compliant dataset  

**Usage: nbt_convert.py [OPTIONAL ARGUMENTS] [-lic LICENSE] [-fm {single,all,none}] data_json BIDS_outdir**

nbt_convert performs BIDS-compliant dicom-to-nifti conversion. Nifti files are named according to the output file of nbt_define.py (**data_json**). Important: It must be defined whether fieldmaps will be used for single scans [single], for all scans [all] or if fieldmaps will not be used [none]. Furthermore a Freesurfer-license file should be passed using the -lic option as it is required by fMRIprep. nbt_convert.py requires Python 3.XX and some additional packages (see imports in nbt_convert.py). For more information type ./nbt_convert.py -h.

5. Run fMRIprep

**Usage: .\local_fmriprep.sh**

Unfortuantely, some of the fmriprep applications have problems with the external nicshare drive. For this reason, data must be first copied to your local home directory. However, as local space is limited to 450 GB and docker containers require large amounts of storage, only single subjects can be copied and preprocessed at a time. **local_fmriprep.sh** can be used to loop over multiple subjects in order to copy each subject's data to your home directory, preprocess it, copy the preprocessed data to nicshare and remove the files from your home directory. 

6. Run ntb_tedana.py (only required for multi echo data)

**Usage: nbt_tedana.py [OPTIONAL ARGUMENTS] BIDSbase fMRIprepID**

nbt_tedana.py performs tedana multi-echo ICA and optimal combination on partially preprocessed fMRIprep output data in **BIDSbase** (path to BIDS root directory containing an fMRIPrep derivatives folder). ANTs normalization and FSL masking is then performed to transform individual fMRI data to MNI-space. fMRIprep must have been performed using the --me-output-echos option. The **fMRIprepID** is a unique(!) BIDS-compliant file identifier including task (required), acq (optional) and run (optional) label, e.g., task-rest_acq-mb3me4_run-1. Labels must be part of the ME-filename. nbt_tedana.py requires Python 3.XX and some additional packages (see imports in nbt_tedana.py). For more information type ./nbt_tedana.py -h.

## Additional python code

**nbt_prettyjson.py**

**Usage: nbt_prettyjson.py ugly_json pretty_json**

nbt_prettyjson.py pretty prints json files (input file: **ugly_json**, output file: **pretty_json**)

**nbt_funcon.py**

Work in progress
