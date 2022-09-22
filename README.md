# nbt

nbt (nic bids tools) is a set of tools facilitating BIDS-conversion, fMRIprep-based preprocessing and analyses of BIDS-compliant datasets.

TODO (Author's note): 
- change study_json to data_json in nbt_define.py
- rename nbt_define.py to nbt_assign.py
- nbt_convert.py: -help says that DICOMs are returned and stored in out. Not true.
- nbt_convert.py: adjust arg names in -help to match README.md
- nbt_convert.py: check fieldmap handling [single, all, none]. What is fmriprep doing with multiple fieldmaps in a single and multiple sessions?
- nbt_tedana.py: adjust arg names in -help to match README.md
- tedana.py: finish README

## nbt_define.py

**Usage: ./nbt_define.py [OPTIONAL ARGUMENTS] template_json  raw_mri data_json**

nbt_define.py assigns BIDS key-value pairs to each DICOM image in **raw_mri** according to a json-formatted template file (**template_json**). nbt_define.py returns a json file (**data_json**) containing BIDS key-value pairs for all DICOM images with matches in **template_json**. Example template files can be found here. **raw_mri** must be organized in subject and session subdirectories [e.g. raw/sub1/session1, raw/sub1/session2, raw/sub2/...]. nbt_define.py requires Python 3.XX plus some further packages (see imports in nbt_define.py). For more information type ./nbt_define.py -h.

## nbt_convert.py

**Usage: nbt_convert.py [OPTIONAL ARGUMENTS] [-lic LICENSE] [-fm {single,all,none}] data_json BIDS_outdir**

nbt_convert performs BIDS-compliant dicom-to-nifti conversion. Nifti files are named according to a json-formatted study template listing all scans and corresponding BIDS key-value pairs (**data_json**). Imortant: It must be defined whether fieldmaps will be used for single scans [single], for all scans [all] or if fieldmaps will not be used/are not applicable [none]. Furthermore a Freesurfer-license file should be passed using the -lic option as it is required by fMRIprep. nbt_convert.py requires Python 3.XX and some additional packages (see imports in nbt_convert.py). For more information type ./nbt_convert.py -h.

## nbt_tedana.py

**Usage: nbt_tedana.py [OPTIONAL ARGUMENTS] BIDSbase fMRIprepID**

nbt_tedana.py performs tedana multi-echo ICA and optimal combination on partially preprocessed fMRIprep ouput data in **BIDSbase** (path to BIDS root directory). ANTs-based normalization and FSL-based masking is performed using nipype to prepare minimally preprocessed MNI-space fMRI data for further analyses. fMRIprep must be performed using the --me-output-echos option. nbt_tedana.py requires Python 3.XX and some additional packages (see imports in nbt_tedana.py). For more information type ./nbt_tedana.py -h.

## nbt_prettyjson.py

**Usage: nbt_prettyjson.py ugly_json pretty_json**

nbt_prettyjson.py pretty prints json files (input file: **ugly_json**, output file: **pretty_json**)

## nbt_funcon.py

Work in progress
