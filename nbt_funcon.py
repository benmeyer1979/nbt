#!/usr/bin/env python3

import argparse
import csv
import glob
import sys
import nilearn
from nilearn.input_data import NiftiMasker
from nilearn.input_data import NiftiLabelsMasker
import numpy as np
import os
import copy
import pandas as pd
import pdb
import re
import multiprocessing as mp

def read_args_funcon():
    parser = argparse.ArgumentParser(description="nbt_funcon.py calculates "
                                     "functional connectivity matrices and "
                                     "maps for BIDS formatted data.")
    parser.add_argument("base", help="BIDS or HCP base directory.", type=str)
    parser.add_argument("-ds", "--dataset", help="Choose if BIDS or HCP dataset "
                        "[bids|hcp]",default='hcp', type=str)
    parser.add_argument("-sub", "--subjects", help="list of subjects for FC "
                        "analysis",nargs='+')
    parser.add_argument("-t", "--task", help="Task Label must be defined for "
                        "FC analyses (e.g. REST1). For HCP analyses this must "
                        "not include the phase encoding direction label "
                        "(LR/RL)", type=str)
    parser.add_argument("-rm", "--remove_motion", help="regress out motion "
                        "parameters (y|n, default=n)", default='n', type=str)
    parser.add_argument("-rwm", "--remove_white_matter", help="regress out "
                        "white matter time course (y|n, default=n)",
                        default='n', type=str)
    parser.add_argument("-rcsf", "--remove_csf", help="regress out CSF time "
                        "course (y|n, default=n)", default='n', type=str)
    parser.add_argument("-tr", "--time_rep", help="repetition time TR "
                        "(default = 1, choose 0.72 for HCP data)", default=1, 
                        type=float)
    parser.add_argument("-lp", "--low_pass", help="low-pass filter setting",
                        default=0.1, type=float)
    parser.add_argument("-hp", "--high_pass", help="high-pass filter setting",
                        default=0.008, type=float)
    parser.add_argument("-sp", "--smooth_fwhm", help="FWHM smoothing parameter",
                        default=4, type=float)
    parser.add_argument("-sds", "--seeds", help="List of seeds for seed-based FC",
                        nargs='+')
    parser.add_argument("-at", "--atlas", help="atlas file used for FC analyses",
                        default="/Users/benjaminmeyer/Data/atlases/repdopa/"
                        "repdopa_atlas.nii")
    parser.add_argument("--parallel", help="Use parallel processing",
                        action='store_true')
    args = parser.parse_args()
    return args

def check_hcp_epipathlist(basedir, task_label, subs, ped):
    filepat = basedir + "/**/*" + task_label + "_" + ped + "*clean.nii.gz"
    epiPathList = sorted(glob.glob(filepat, recursive=True))
    if not subs:
        return epiPathList
    else:
        epiPathList_red = []
        for sub in subs:
            [epiPathList_red.append(s) for s in epiPathList if sub in s]
        return epiPathList_red

def read_hcp_epi_masks(rootdir, task_label, subs, ped):
    filepat = rootdir + "/**/rfMRI_" + task_label + '_' + ped + "/" + \
              "brainmask_fs.2.nii.gz"
    epiPathList = sorted(glob.glob(filepat, recursive=True))
    if not subs:
        return epiPathList
    else:
        epiPathList_red = []
        for sub in subs:
            [epiPathList_red.append(s) for s in epiPathList if sub in s]
        return epiPathList_red

##############################################################################

def check_bids_epipathlist(basedir, task_label, subs):
    filepat = basedir + "/**/*" + task_label + \
              "*MNI152NLin2009cAsym_desc-preproc_bold.nii.gz"
    epiPathList = sorted(glob.glob(filepat, recursive=True))
    if not subs:
        return epiPathList
    else:
        epiPathList_red = []
        for sub in subs:
            [epiPathList_red.append(s) for s in epiPathList if sub in s]
        return epiPathList_red


def read_bids_epi_masks(rootdir, task_label, subs):
    filepat = rootdir + "/**/*" + task_label + "*brain_mask.nii.gz"
    epiPathList = sorted(glob.glob(filepat, recursive=True))
    if not subs:
        return epiPathList
    else:
        epiPathList_red = []
        for sub in subs:
            [epiPathList_red.append(s) for s in epiPathList if sub in s]
        return epiPathList_red

##############################################################################

def check_epi_masks(rootdir, task_label, filepat, subs):
    filepat = rootdir + "/**/*" + task_label + filepat
    masklist = sorted(glob.glob(filepat, recursive=True))
    if not subs:
        return masklist
    else:
        masklist_red = []
        for sub in subs:
            [masklist_red.append(s) for s in masklist if sub in s]
        return masklist_red

def generate_group_epi_mask(epimasklist):
    brain_mask_ind = []
    [brain_mask_ind.append(nilearn.masking.compute_epi_mask(i)) \
     for i in epimasklist]
    group_mask = nilearn.masking.intersect_masks(brain_mask_ind, 
                                                 threshold=0.8, connected=True)
    return group_mask


def generate_epi_masks(epipathlist):
    for epiPath in epipathlist:
        pathComp = os.path.split(epiPath)
        epiFile = pathComp[-1]
        epiDir = pathComp[-2]
        maskpattern = os.path.join(epiDir, '*mask*.nii.gz')
        if not glob.glob(maskpattern):
            epiMask = nilearn.masking.compute_epi_mask(epiPath)
            epiMaskFile = epiFile.replace('.nii.gz', '_mask.nii.gz')
            print('No epi-mask in ' + epiDir + ' ! New mask is generated.')
            epiMask.to_filename(os.path.join(epiDir, epiMaskFile))
        else:
            print('Epi-mask in ' + epiDir + ' already exists! No new mask '
                                            'generated.')


def read_atlas(atlasfile):
    atlasLabels = []
    atlasIDs = []
    atlasLabelsFile = atlasfile.replace('.nii', '_labels.txt')
    with open(atlasLabelsFile) as csv_file:
        csv_reader = csv.reader(csv_file)
        for row in csv_reader:
            atlasLabels.append(row[1])
            atlasIDs.append(row[0])
    return atlasLabels, atlasIDs


def extract_atlas_timeseries(epifile, atlasfile, low_pass, high_pass, 
                             t_r, confounds_df):
    masker = NiftiLabelsMasker(labels_img=atlasfile, standardize=True, 
                               detrend=True,low_pass=low_pass, 
                               high_pass=high_pass,t_r=t_r, 
                               memory='nilearn_cache', memory_level=1,
                               verbose=0)
    atlas_timeseries = masker.fit_transform(epifile, confounds=confounds_df)
    return atlas_timeseries


def extract_brain_timeseries(epifile, epi_group_mask, low_pass, high_pass, 
                             t_r, confounds_df, smooth_fwhm):
    masker = NiftiMasker(mask_img=epi_group_mask, smoothing_fwhm=smooth_fwhm, 
                         detrend=True,standardize=True, low_pass=low_pass, 
                         high_pass=high_pass, t_r=t_r, memory='nilearn_cache', 
                         memory_level=1, verbose=0)

    brain_timeseries = masker.fit_transform(epifile, confounds=confounds_df)
    return brain_timeseries, masker


#def read_hcp_confounds(epidir, args):
#    motion = glob.glob(os.path.join(epidir, 'Movement_Regressors.txt'))
#    csf = glob.glob(os.path.join(epidir, '*CSF.txt'))
#    wm = glob.glob(os.path.join(epidir, '*WM.txt'))
#    conf_df = []
#    if args.remove_motion == 'y':
#        conf_df.append(pd.read_csv(motion[0], delim_whitespace=True, header=None))
#    if args.remove_white_matter == 'y':
#        conf_df.append(pd.read_csv(wm[0], header=None))
#    if args.remove_csf == 'y':
#        conf_df.append(pd.read_csv(csf[0], header=None))
#    confounds_df = pd.concat(conf_df, axis=1)
#    return confounds_df


def read_fmriprep_confounds(epidir,args):
    filepat = epidir + "/*" + args.task + "*confounds_timeseries.tsv"
    confound_file = glob.glob(os.path.join(epidir, filepat))

    confound_vars = []

    if  args.remove_motion == 'y':
        confound_vars.extend(['rot_x','rot_y','rot_z','rot_x_derivative1',
                               'rot_y_derivative1','rot_z_derivative1',
                               'trans_x','trans_y','trans_z','trans_x_derivative1',
                               'trans_y_derivative1','trans_z_derivative1'])
    if args.remove_csf == 'y':
        confound_vars.extend(['csf'])    
    if args.remove_white_matter == 'y':
        confound_vars.extend(['white_matter']) 

    confounds_df = pd.read_csv(confound_file[0], delimiter='\t')
    confounds_df = confounds_df[confound_vars]
    confounds_df = confounds_df.fillna(0)
   
    return confounds_df

def check_bids_epipathlist(basedir, task_label, subs):
    filepat = basedir + "/**/*" + task_label + \
              "*MNI152NLin2009cAsym_desc-preproc_bold.nii.gz"
    epiPathList = glob.glob(filepat, recursive=True)
    if not subs:
        return epiPathList
    else:
        epiPathList_red = []
        for sub in subs:
            [epiPathList_red.append(s) for s in epiPathList if sub in s]
        return epiPathList_red



def parallel_fc_bids(arglist_item):

    epiPath         = arglist_item['epiPath']
    args            = arglist_item['args']
    epi_group_mask  = arglist_item['epi_group_mask']
    atlasIDs        = arglist_item['atlasIDs']

    # Directory of epi image
    epiDir = os.path.split(epiPath)[-2]
    # get confounds dataframe
    if args.dataset == 'hcp':
        confounds_df = None
        # get confounds dataframe
    elif args.dataset == 'bids':
        confounds_df = read_fmriprep_confounds(epiDir,args)

    # get brain timeseries
    brain_timeseries, masker = extract_brain_timeseries(epiPath, epi_group_mask, args.low_pass, args.high_pass,
                                                        args.time_rep, confounds_df, args.smooth_fwhm)
    # get atlas timeseries
    atlas_timeseries = extract_atlas_timeseries(epiPath, args.atlas, args.low_pass, args.high_pass,
                                                args.time_rep, confounds_df)
    # get seed timeseries
    seeds = []
    [seeds.append(atlasIDs.index(i)) for i in args.seeds]
    seed_timeseries = np.take(atlas_timeseries, indices=seeds, axis=1)

    for j in seeds:
        print("\tCalculating FC for seed " + str(j) + ' in ' + epiPath)
        # Calculate FC (Pearson's R)
        fc_data = (np.dot(brain_timeseries.T, atlas_timeseries[:, j-1]) / atlas_timeseries.shape[0])
        # Convert FC data to image
        fc_map = masker.inverse_transform(fc_data.T)
        # Calculate Fisher's z-transform
        zfc_data = np.arctanh(fc_data)
        # Convert z-FC data to image
        zfc_map = masker.inverse_transform(zfc_data.T)

        # Save z-FC map

        if args.dataset == 'hcp':
            #make directory
            outPath = copy.copy(epiPath)
            outPath = outPath.replace("HCP_1200","FC")
            outPath = outPath.replace("MNINonLinear/Results/","")
            outFile = copy.copy(outPath)
            outPath = re.sub('[a-zA-Z0-9_-]*.nii.gz','',outPath)
            sysstr = "mkdir -p " + outPath
            os.system(sysstr)
            #save fc map to file
            suffix_fc_outfile = '_fc_seed_' + str(atlasIDs[j]) + '.nii.gz'
            outfileFC = outFile.replace('.nii.gz', suffix_fc_outfile)
            fc_map.to_filename(outfileFC)
            #save z-fc map to file
            suffix_zfc_outfile = '_zfc_seed_' + str(atlasID[j]) + '.nii.gz'
            outfileZFC = outFile.replace('.nii.gz', suffix_zfc_outfile)
            zfc_map.to_filename(outfileZFC)
        elif args.dataset == 'bids':
            sys.exit('FC output calculated from bids data still under development.')


def parallel_fc_hcp(arglist_item):
    try:
        epiPath_LR         = arglist_item['epiPath'][0]
        epiPath_RL         = arglist_item['epiPath'][1]
        args               = arglist_item['args']
        epi_group_mask     = arglist_item['epi_group_mask']
        atlasIDs           = arglist_item['atlasIDs']

        # get seed timeseries
        seeds = []
        [seeds.append(atlasIDs.index(i)) for i in args.seeds]
        outfileFC=[]
        outfileZFC=[]

        # Directory of epi image
        epiDir_LR = os.path.split(epiPath_LR)[-2]
        epiDir_RL = os.path.split(epiPath_RL)[-2]

        pdb.set_trace()

        #check wether participants are the same for LR/RL
        epiDir_RL = epiDir_RL.replace('_RL','_LR')
        if not epiDir_LR == epiDir_RL:
            with open("errorlog.txt","a") as errorlog:
                errorlog.write('LR and RL are not from the same subject ' + epiPath_LR + '!')
                print('LR and RL are not from the same subject: ' + epiPath_LR + '!!')
            return None
        else:
            print('LR/RL check passed!')            

        for j in seeds:
            if args.dataset == 'hcp':
                #prepare output filenames
                outPath = copy.copy(epiPath_LR)
                outPath = outPath.replace("_LR","_LR_RL")
                outPath = outPath.replace("HCP_1200","FC")
                outPath = outPath.replace("MNINonLinear/Results/","")
                outFile = copy.copy(outPath)
                outPath = re.sub('[a-zA-Z0-9_-]*.nii.gz','',outPath)
                sysstr = "mkdir -p " + outPath
                os.system(sysstr)
                suffix_fc_outfile = '_fc_seed_' + str(atlasIDs[j]) + '.nii.gz'
                outfileFC.append(outFile.replace('.nii.gz', suffix_fc_outfile))
                suffix_zfc_outfile = '_zfc_seed_' + str(atlasIDs[j]) + '.nii.gz'
                outfileZFC.append(outFile.replace('.nii.gz', suffix_zfc_outfile))

                if os.path.exists(outfileZFC[-1]):
                    print("File " + outfileZFC[-1] + " already exists!")
                    return None

        # get confounds dataframe
        if args.dataset == 'hcp':
            confounds_df = None
            # get confounds dataframe
        elif args.dataset == 'bids':
            confounds_df = read_fmriprep_confounds(epiDir,args)

        # get brain timeseries
        brain_timeseries_LR, masker_LR = \
        extract_brain_timeseries(epiPath_LR, epi_group_mask, 
                                args.low_pass, args.high_pass,
                                args.time_rep, confounds_df, args.smooth_fwhm)
        # get atlas timeseries
        atlas_timeseries_LR = \
        extract_atlas_timeseries(epiPath_LR, args.atlas, args.low_pass, 
                                args.high_pass, args.time_rep, confounds_df)
        # get brain timeseries
        brain_timeseries_RL, masker_RL = \
        extract_brain_timeseries(epiPath_RL, epi_group_mask, 
                                args.low_pass, args.high_pass,
                                args.time_rep, confounds_df, args.smooth_fwhm)
        # get atlas timeseries
        atlas_timeseries_RL = \
        extract_atlas_timeseries(epiPath_RL, args.atlas, args.low_pass, 
                                args.high_pass,args.time_rep, confounds_df)
   
        brain_timeseries = np.concatenate((brain_timeseries_LR, brain_timeseries_RL),axis=0)
    
        atlas_timeseries = np.concatenate((atlas_timeseries_LR, atlas_timeseries_RL),axis=0)
        
        seed_timeseries = np.take(atlas_timeseries, indices=seeds, axis=1)
            
        for i in range(len(seeds)):
            print("\tCalculating FC for seed " + str(atlasIDs[seeds[i]])  + ' in ' + epiPath_LR + epiPath_RL)
            # Calculate FC (Pearson's R)
            fc_data = (np.dot(brain_timeseries.T, atlas_timeseries[:, seeds[i]]) / atlas_timeseries.shape[0])
            # Convert FC data to image
            fc_map = masker_LR.inverse_transform(fc_data.T)
            # Calculate Fisher's z-transform
            zfc_data = np.arctanh(fc_data)
            # Convert z-FC data to image
            zfc_map = masker_LR.inverse_transform(zfc_data.T)

            #save files
            if args.dataset == 'hcp':
                fc_map.to_filename(outfileFC[i])
                zfc_map.to_filename(outfileZFC[i])
            elif args.dataset == 'bids':
                sys.exit('FC output calculated from bids data still under development.')

    except:
        with open("errorlog.txt","a") as errorlog:
             errorlog.write('Problem with ' + epiPath_LR + '!')

        print('Problem with ' + epiPath_LR + '!!')
        return None


def nbt_funcon():
    #divisor to determine the number of CPUs for parallel processing (e.g. 32(CPUs)/4(cpu_divisor)=8)
    cpu_divisor = 4

    args = read_args_funcon()
    if args.task is None:
        sys.exit('No task defined!')

    epiPathList = ''
    epiPathList_mask = ''
    # List of epi images of chosen task
    if args.dataset == 'hcp':
        epiPathList_LR = check_hcp_epipathlist(args.base, args.task, args.subjects,'LR')
        epiPathList_RL = check_hcp_epipathlist(args.base, args.task, args.subjects,'RL')
        epiPathList = map(list,zip(epiPathList_LR,epiPathList_RL))
        epiPathList_mask_RL = read_hcp_epi_masks(args.base, args.task, args.subjects,'RL')
        epiPathList_mask_LR = read_hcp_epi_masks(args.base, args.task, args.subjects,'LR')

    elif args.dataset == 'bids':
        epiPathList = check_bids_epipathlist(args.base, args.task, args.subjects)
        epiPathList_mask = read_bids_epi_masks(args.base, args.task, args.subjects)
 
    print("\tCalculating group mask...   ",end='')
    epi_group_mask_LR = generate_group_epi_mask(epiPathList_mask_LR)
    epi_group_mask_RL = generate_group_epi_mask(epiPathList_mask_RL)
    epi_group_mask    = nilearn.masking.intersect_masks([epi_group_mask_LR,
                                                        epi_group_mask_RL],
                                                        threshold=1)

    atlasLabels, atlasIDs = read_atlas(args.atlas)
    print("\t...done")

    #Filename must be changed to image object to avoid Bad File Descriptor error during
    #parallel procesing
    args.atlas = nilearn.image.load_img(args.atlas)

    if args.parallel is True:
        cpus = mp.cpu_count()
        pool = mp.Pool()
        arg_list = []
        if args.dataset == 'hcp':
            [arg_list.append({'epiPath':epiPath,
                              'args':args,'epi_group_mask':epi_group_mask,
                              'atlasIDs':atlasIDs}) for epiPath in epiPathList]
            pool.map(parallel_fc_hcp, arg_list)
        else:
            [arg_list.append({'epiPath':epiPath,'args':args,'epi_group_mask':epi_group_mask,'atlasIDs':atlasIDs})  for epiPath in epiPathList]
            pool.map(parallel_fc_bids, arg_list)
        pool.close()
    else:
        arg_list = []
        if args.dataset == 'hcp':
            [arg_list.append({'epiPath':epiPath,'args':args,
                              'epi_group_mask':epi_group_mask,
                              'atlasIDs':atlasIDs})  
                               for epiPath in epiPathList]
            [parallel_fc_hcp(i) for i in arg_list]
        else:
            [arg_list.append({'epiPath':epiPath,'args':args,'epi_group_mask':epi_group_mask,'atlasIDs':atlasIDs})  for epiPath in epiPathList]
            [parallel_fc_bids(i) for i in arg_list]

if __name__ == "__main__":
    nbt_funcon()
