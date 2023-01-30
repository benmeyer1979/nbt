#!/usr/bin/env python3

import json
import sys
import os
import argparse
import pdb

def check_subjects(sublist_arg, data):
    # check if subject arguments exist in json input file
    subi_ds = []
    nrsub_json = len(data)
    for i in range(nrsub_json):
        subi_ds.append(data[i]['subjectID'])

    nrsub_arg = len(sublist_arg)

    for j in range(nrsub_arg):
        if not sublist_arg[j] in subi_ds:
            errormsg = "Error: Subject " + sublist_arg[j] + " not found in json file"
            sys.exit(errormsg)
    return sublist_arg


def add_intendedfor(tasksbold, tasksfmap):
    for key in tasksfmap:
        with open(key, "r") as f:
            data = json.load(f)
            data["IntendedFor"] = tasksbold[tasksfmap[key]]

        # permissions change when using open -> reset to full permission
        os.chmod(key, 0o777)

        with open(key, "w") as f:
            json.dump(data, f, indent=4, sort_keys=True)


def add_task_name(infile, taskname):
    with open(infile, "r") as f:
        data = json.load(f)
        data["TaskName"] = taskname

    # permissions change when using open -> reset to full permission
    os.chmod(infile, 0o777)

    with open(infile, "w") as f:
        json.dump(data, f, indent=4, sort_keys=True)


def add_dataset_description(dataset_json):
    json_obj = {}
    json_obj['Acknowledgements'] = 'TODO: whom you want to acknowledge'
    json_obj['Authors'] = ['TODO:', 'First1 Last1', 'First2 Last2', '...']
    json_obj['BIDSVersion'] = '1.4.1'
    json_obj['DatasetDOI'] = 'TODO: eventually a DOI for the dataset'
    json_obj['Funding'] = ['TODO:', 'GRANT #1', 'GRANT #2']
    json_obj[
        'HowToAcknowledge'] = 'TODO: describe how to acknowledge -- either cite a corresponding paper, or just in acknowledgement section'
    json_obj['License'] = 'TODO: choose a license, e.g. PDDL (http://opendatacommons.org/licenses/pddl/)'
    json_obj['Name'] = 'TODO: name of the dataset'
    json_obj['ReferencesAndLinks'] = ['TODO', 'List of papers or websites']

    # Write the object to file.
    with open(dataset_json, 'w') as jsonFile:
        json.dump(json_obj, jsonFile, indent=4, sort_keys=True)


def rename_file(oldFile,newFile):
    sysstr = 'mv ' + oldFile + ' ' + newFile
    print(sysstr)
    os.system(sysstr)


def nbt_convert():
    parser = argparse.ArgumentParser(description="nbt_convert reorganizes and renames your raw DICOM files for BIDS "
                                                 "compliant conversion to the nifti format.")
    parser.add_argument("json", help="json file defining DICOM series selected for BIDS conversion", type=str)
    parser.add_argument("outdir", help="output directory with DICOM and Nifti subdirectory", type=str)
    parser.add_argument("-sub", "--subjects", help="list of subjects to be processed", nargs='+')
    parser.add_argument("-lic", "--license", help="add path to copy FreeSurfer License File to destination directory "
                                                  "(required for fmriprep)", type=str)
    parser.add_argument("-dd", "--dataset_description", help="add path to dataset_description.json file", type=str)
    parser.add_argument("-fm", "--fieldmap", help="define if fieldmaps are intended for single fmri scans [single], "
                                                  "if a single fieldmap is intended for all fmri scans [all] or if fieldmaps "
                                                  "are not part of the dataset [none, default]. If fieldmaps are part of the "
                                                  "dataset either [single] or [all] must be chosen. If [all] is selected, make sure that "
                                                  "there is only a single fieldmap per session in your imported dicom series. "
                                                  "Fieldmaps intended for multiple but not all bold scans cannot be processed.",
                        choices=["single", "all", "none"], default="none", type=str)

    args = parser.parse_args()

    # read json file
    with open(args.json) as f:
        data = json.load(f)
    print('Destination directory: ' + args.outdir + '\n')
    base_dest = args.outdir

    if args.license is not None:
        sysstr = 'cp ' + args.license + ' ' + base_dest + '/license.txt'
        print(sysstr)
        os.system(sysstr)

    # check if argument subjects exist in json file
    if args.subjects is not None:
        argsubs = check_subjects(args.subjects, data)
    else:
        argsubs = []

    if args.dataset_description is not None:
        sysstr = 'cp ' + args.dataset_description + ' ' + base_dest
        print(sysstr)
        os.system(sysstr)
    else:
        path_dest = os.path.join(base_dest,'Nifti')
        sysstr = 'mkdir -p ' + path_dest
        print(sysstr)
        os.system(sysstr)
        dataset_json = path_dest + '/dataset_description.json'
        add_dataset_description(dataset_json)

    # Number of subjects
    nrsub = len(data)
    # selected subjects for BIDS conversion. Contains all subjects when -sub is not used.
    # key=subid, value= subject index in json
    selsub = {}
    # tasksfmap: each fmap key is associated with subject-session-task value
    tasksfmap = {}
    # tasksbold: each subject-session-task key is associated with one or several bold scans (intendedFor field of fmap
    # json)
    tasksbold = {}

    for sub in range(nrsub):
        # Get subject ID
        subid = data[sub]['subjectID']
        subprefix = 'sub-' + subid

        # check if -sub argument is used
        if args.subjects is None:
            selsub[subid] = sub
        else:
            if subid not in argsubs:
                continue
            else:
                selsub[subid] = sub

        # Number of sessions
        nrsess = len(data[sub]['sessions'])

        for ses in range(nrsess):
            # Get session ID
            sessid = data[sub]['sessions'][ses]['sessionID']
            sesprefix = 'ses-' + sessid
            # Original base directory (where DICOM series are located)
            base_ori = data[sub]['sessions'][ses]['sessionDir']
            # Number of scans
            nrscans = len(data[sub]['sessions'][ses]['scan'])
            # path to nifti session directory
            path_ses_nii = base_dest + '/Nifti' + '/' + subprefix + '/' + sesprefix

            # if exists, remove session directory
            if os.path.isdir(path_ses_nii):
                sysstr = 'rm -r -f ' + path_ses_nii
                print(sysstr)
                os.system(sysstr)

            # scans = image series
            for scan in range(nrscans):
                cur_scan = data[sub]['sessions'][ses]['scan'][scan]
                # scan directory
                scandir = cur_scan['scan_dir']
                # path to DICOM
                scan_ori = base_ori + '/' + scandir
                # data type: func, dwi, anat etc.
                data_type = cur_scan['data_type']
                # modality: bold, dwi, eeg, etc
                if "mod" in cur_scan:
                    mod = cur_scan['mod']
                else:
                    mod = ''

                if "task" in cur_scan and not data_type == 'fmap':
                    taskstr = "task-" + cur_scan['task'] + "_"
                else:
                    taskstr = ""

                if "acq" in cur_scan:
                    acqstr = "acq-" + cur_scan['acq'] + "_"
                else:
                    acqstr = ""

                if 'dir' in cur_scan:
                    dirstr = "dir-" + cur_scan['dir'] + "_"
                else:
                    dirstr = ""

                if 'run' in cur_scan:
                    runstr = "run-" + str(cur_scan['run']) + "_"
                else:
                    runstr = ""

                # location to which DICOMs will be copied
                path_dest = base_dest + '/DICOM' + '/' + subid + '/' + sessid + '/' + data_type
                # scan descriptor: new filename
                scan_descr = taskstr + acqstr + dirstr + runstr + mod
                # scan decriptor without modality
                scan_descr_nomod = taskstr + acqstr + dirstr + runstr
                # destination path to renamed DICOM scans
                scan_dest = path_dest + '/' + scan_descr
                # Prefixes
                sesprefix = 'ses-' + sessid
                subsesprefix = subprefix + '_' + sesprefix + '_'
                path_dest_nii = path_ses_nii + '/' + data_type

                ########################################################################################################
                # BOLD processing
                ########################################################################################################

                if mod == 'bold':
                    intendedfor = []

                    if 'echos' in cur_scan:
                        for echo in range(cur_scan['echos']):
                            intendedfor.append(sesprefix + '/' + data_type + '/' + subsesprefix + scan_descr_nomod +
                                               'echo-' + str(echo + 1) + '_' + mod + '.nii.gz')
                    else:
                        intendedfor = [sesprefix + '/' + data_type + '/' + subsesprefix + scan_descr + '.nii.gz']

                    # connect subject-session-task to bold scans
                    if args.fieldmap == 'single':
                        tasksbold_key = ""
                        if "task" in cur_scan:
                            tasksbold_key = subsesprefix + '_' + cur_scan['task']
                      #  if "acq" in cur_scan:
                      #      tasksbold_key = tasksbold_key + '-' + cur_scan['acq']
                      #  if "run" in cur_scan:
                      #      tasksbold_key = tasksbold_key + '-' + cur_scan['run']

                        tasksbold[tasksbold_key] = intendedfor

                    elif args.fieldmap == 'all':
                        tasksbold_key = subsesprefix + 'ALL'

                        if not tasksbold_key in tasksbold:
                            tasksbold[tasksbold_key] = intendedfor
                        else:
                            for s in intendedfor:
                                tasksbold[tasksbold_key].append(s)

                ########################################################################################################
                # fieldmap processing
                ########################################################################################################

                # if fieldmap associate with corresponding subject-session-task value
                if data_type == 'fmap' and args.fieldmap == 'single':

                    if cur_scan['intendedfor'].lower() == 'all':
                        sys.exit("Error: Fieldmap parameter [single] does not match intendedfor value in "
                                 "json file [all]")
                    if cur_scan['acq'] == 'spinecho':
                        fmap_json = path_dest_nii + '/' + subsesprefix + scan_descr + '.json'
                        tasksfmap[fmap_json] = subsesprefix + '_' + cur_scan['intendedfor']
                    if cur_scan['acq'] == 'gremag':
                        fmap_json = path_dest_nii + '/' + subsesprefix + 'acq-gre_magnitude1.json'
                        tasksfmap[fmap_json] = subsesprefix + '_' + cur_scan['intendedfor']
                        fmap_json = path_dest_nii + '/' + subsesprefix + 'acq-gre_magnitude2.json'
                        tasksfmap[fmap_json] = subsesprefix + '_' + cur_scan['intendedfor']
                    if cur_scan['acq'] == 'grephase':
                        fmap_json = path_dest_nii + '/' + subsesprefix + 'acq-gre_phasediff.json'
                        tasksfmap[fmap_json] = subsesprefix + '_' + cur_scan['intendedfor']
                        
                elif data_type == 'fmap' and args.fieldmap == 'all':

                    if cur_scan['intendedfor'].lower() != 'all':
                        sys.exit("Error: Fieldmap parameter [all] does not match intendedfor value in "                                 "json file!")
                    if cur_scan['acq'] == 'spinecho':
                        fmap_json = path_dest_nii + '/' + subsesprefix + scan_descr + '.json'
                        tasksfmap[fmap_json] = subsesprefix + 'ALL'
                    if cur_scan['acq'] == 'gremag':
                        fmap_json = path_dest_nii + '/' + subsesprefix + 'acq-gre_magnitude1.json'
                        tasksfmap[fmap_json] = subsesprefix + 'ALL'
                        fmap_json = path_dest_nii + '/' + subsesprefix + 'acq-gre_magnitude2.json'
                        tasksfmap[fmap_json] = subsesprefix + 'ALL'
                    if cur_scan['acq'] == 'grephase':
                        fmap_json = path_dest_nii + '/' + subsesprefix + 'acq-gre_phasediff.json'
                        tasksfmap[fmap_json] = subsesprefix + 'ALL'

                elif data_type == 'fmap' and args.fieldmap == 'none':

                    sys.exit("Error: Fieldmaps found but fieldmap parameter [-fm] was not set or set to [none]. If "
                          "fieldmaps are part of the dataset, choose either [all] or [single].")
                            

                sysstr = 'mkdir -p ' + path_dest_nii
                print(sysstr)
                os.system(sysstr)

                dcm2niix_cmd = 'dcm2niix'
                dcm2niix_args = '-o ' + path_dest_nii + ' -b y -z y -f '
                sysstr = dcm2niix_cmd + ' ' + dcm2niix_args + subsesprefix + scan_descr + ' ' + scan_ori
                print(sysstr)
                os.system(sysstr)

                ########################################################################################################
                # BIDS compliant renaming of gre fieldmaps
                ########################################################################################################
                        
                if data_type == 'fmap' and cur_scan['acq'] == 'gremag':
                    fmap_json_old = path_dest_nii + '/' + subsesprefix + scan_descr + 'e1.json'
                    if os.path.isfile(fmap_json_old):
                        fmap_json_new = path_dest_nii + '/' + subsesprefix + 'acq-gre_magnitude1.json'
                        rename_file(fmap_json_old,fmap_json_new)
                        fmap_nii_old  = path_dest_nii + '/' + subsesprefix + scan_descr + 'e1.nii.gz'
                        fmap_nii_new = path_dest_nii + '/' + subsesprefix + 'acq-gre_magnitude1.nii.gz'
                        rename_file(fmap_nii_old,fmap_nii_new)
                                    
                    fmap_json_old = path_dest_nii + '/' + subsesprefix + scan_descr + 'e2.json'
                    if os.path.isfile(fmap_json_old):
                        fmap_json_new = path_dest_nii + '/' + subsesprefix + 'acq-gre_magnitude2.json'
                        rename_file(fmap_json_old,fmap_json_new)
                        fmap_nii_old  = path_dest_nii + '/' + subsesprefix + scan_descr + 'e2.nii.gz'
                        fmap_nii_new = path_dest_nii + '/' + subsesprefix + 'acq-gre_magnitude2.nii.gz'
                        rename_file(fmap_nii_old,fmap_nii_new)

                if data_type == 'fmap' and cur_scan['acq'] == 'grephase':
                    fmap_json_old = path_dest_nii + '/' + subsesprefix + scan_descr + 'e2_ph.json'
                    if os.path.isfile(fmap_json_old):
                        fmap_json_new = path_dest_nii + '/' + subsesprefix + 'acq-gre_phasediff.json'
                        rename_file(fmap_json_old,fmap_json_new)
                        fmap_nii_old  = path_dest_nii + '/' + subsesprefix + scan_descr + 'e2_ph.nii.gz'
                        fmap_nii_new = path_dest_nii + '/' + subsesprefix + 'acq-gre_phasediff.nii.gz'
                        rename_file(fmap_nii_old,fmap_nii_new)

                ########################################################################################################
                # BIDS compliant renaming of multi-echo files
                ########################################################################################################

                if (mod == 'bold' or mod == 'sbref') and 'echos' in cur_scan:

                    if cur_scan['echos'] < 2:
                        sys.exit('Number of echos must be > 1 for multi-echo data. Do not use \'echos\' key for '
                                 'single-echo data.')

                    for i in range(cur_scan['echos']):
                        # rename bold nii
                        echo_file_old = path_dest_nii + '/' + subsesprefix + scan_descr + '_e' + str(i + 1) + '.nii.gz'
                        echo_file_new = path_dest_nii + '/' + subsesprefix + scan_descr_nomod + 'echo-' + str(i + 1) + \
                                        '_' + mod + '.nii.gz'
                        sysstr = 'mv ' + echo_file_old + ' ' + echo_file_new
                        print(sysstr)
                        os.system(sysstr)

                        # rename sbref nii
                        echo_file_old = path_dest_nii + '/' + subsesprefix + scan_descr + '_e' + str(i + 1) + '.json'
                        echo_file_new = path_dest_nii + '/' + subsesprefix + scan_descr_nomod + 'echo-' + str(i + 1) + \
                                        '_' + mod + '.json'
                        sysstr = 'mv ' + echo_file_old + ' ' + echo_file_new
                        print(sysstr)
                        os.system(sysstr)

                        # add task to json file
                        add_task_name(echo_file_new, cur_scan['task'])
                elif (mod == 'bold' or mod == 'sbref') and not ('echos' in cur_scan):
                    # add task to json file
                    infile = path_dest_nii + '/' + subsesprefix + scan_descr + '.json'
                    add_task_name(infile, cur_scan['task'])

    ####################################################################################################################
    # add intendedFor field to fmap json files
    ####################################################################################################################

    if not args.fieldmap == 'none':
        add_intendedfor(tasksbold, tasksfmap)


if __name__ == "__main__":
    nbt_convert()
