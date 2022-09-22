# nbt

nbt (nic bids tools) comprises a set of tools to facilitate BIDS-conversion and fMRIprep-based data preprocessing.

## nbt_define.py

**Usage: ./nbt_define.py [OPTIONAL ARGUMENTS] template_json  raw_mri study_json**

nbt_define.py assigns BIDS key-value pairs to each DICOM file in directory **raw_mri** according to a json-formatted template file **template_json**. nbt_define.py returns a json file containing BIDS key-value pairs for all DICOMS that match **template_json**. Example templates can be found in this repository. **raw_mri** must be organized in subject and session subdirectories [e.g. raw/sub1/session1, raw/sub1/session2, raw/sub2/...]. nbt_define.py requires Python 3.XX and some additional packages (see imports in nbt_define.py). For more information type ./nbt_define.py -h.

## nbt_convert.py
## nbt_tedana.py
## nbt_prettyjson.py
## nbt_funcon.py
