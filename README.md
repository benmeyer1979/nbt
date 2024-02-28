# nbt

nbt (nic bids tools) contains a collection of python scripts facilitating BIDS-conversion, fMRIprep-based preprocessing and analyses of BIDS-compliant datasets.

# How to convert raw MRI data into a BIDS dataset  

1. All DICOM files must be organized in subject and session subdirectories [e.g. raw/sub1/session1, raw/sub1/session2, raw/sub2/...]
2. A json-formatted template file defining the data structure of the raw MRI data must be created. Examples can be found in GLC_template.json

The template must contain a subject object with keys "subjectID" (subject ID) and "sessions" (array of objects each defining the session directory ("sessionDir"), session ID ("sessionID") and a "scans" array). Each "scans" object defines a particular MRI sequence by BIDS key-value pairs:

|key|value|
|---|-----|
|acq|BIDS acquisition (NIC descriptors like mb3me4 for multiband-factor 3 and 4 echos can be used here)|
|data_type|BIDS data type|
|dir|IDS phase encoding direction|
|echos|number of echos|
|intendedfor|can be either a single task name or "all"|
|mod|BIDS modality|
|run|BIDS run|
|task|BIDS task name|

Example files can be found in XXX and XXX. 

3. Run nbt_define.py to generate the dataset structure for the entire set of raw DICOM files.

**Usage: nbt_define.py [OPTIONAL ARGUMENTS] template_json  raw_mri data_json**

nbt_define.py assigns BIDS key-value pairs to each DICOM image in **raw_mri** according to a json-formatted template file (**template_json**). nbt_define.py returns a json file (**data_json**) containing BIDS key-value pairs for all DICOM images with matches in **template_json**. Example template files can be found here. **raw_mri** must be organized in subject and session subdirectories [e.g. raw/sub1/session1, raw/sub1/session2, raw/sub2/...]. nbt_define.py requires Python 3.XX plus some further packages (see imports in nbt_define.py). For more information type ./nbt_define.py -h.

4. Run nbt_convert.py to convert dicom to niftis and to create a BIDS-compliant dataset  

**Usage: nbt_convert.py [OPTIONAL ARGUMENTS] [-lic LICENSE] [-fm {single,all,none}] data_json BIDS_outdir**

nbt_convert performs BIDS-compliant dicom-to-nifti conversion. Nifti files are named according to the output file of nbt_define.py (**data_json**). Important: It must be defined whether fieldmaps will be used for single scans [single], for all scans [all] or if fieldmaps will not be used [none]. Furthermore a Freesurfer-license file should be passed using the -lic option as it is required by fMRIprep. nbt_convert.py requires Python 3.XX and some additional packages (see imports in nbt_convert.py). For more information type ./nbt_convert.py -h.

5. Run fMRIprep

**Usage: nbt_tedana.py [OPTIONAL ARGUMENTS] BIDSbase fMRIprepID**

nbt_tedana.py performs tedana multi-echo ICA and optimal combination on partially preprocessed fMRIprep ouput data in **BIDSbase** (path to BIDS root directory). ANTs-based normalization and FSL-based masking is performed using nipype to prepare minimally preprocessed MNI-space fMRI data for further analyses. fMRIprep must be performed using the --me-output-echos option. nbt_tedana.py requires Python 3.XX and some additional packages (see imports in nbt_tedana.py). For more information type ./nbt_tedana.py -h.

## nbt_prettyjson.py

**Usage: nbt_prettyjson.py ugly_json pretty_json**

nbt_prettyjson.py pretty prints json files (input file: **ugly_json**, output file: **pretty_json**)

## nbt_funcon.py

Work in progress
