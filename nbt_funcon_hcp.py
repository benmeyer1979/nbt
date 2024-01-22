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
from multiprocessing import Pool
from concurrent.futures import ProcessPoolExecutor

os.system("taskset -p 0xff %d" % os.getpid())

def read_args_funcon():
    parser = argparse.ArgumentParser(description="nbt_funcon.py calculates "
                                     "functional connectivity matrices and "
                                     "maps for preprocessed HCP data.")
    parser.add_argument("base", help="HCP base directory.", type=str)
    parser.add_argument("-sub", "--subjects", help="list of subjects for FC "
                        "analysis",nargs='+')
    parser.add_argument("-t", "--task", help="Task Label must be defined for "
                        "FC analyses (e.g. REST1). For HCP analyses this must "
                        "not include the phase encoding direction label "
                        "(LR/RL)", type=str)
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

##############################################################################

def get_hcp_epipathlist(basedir, task_label, subs):
    filepat = basedir + "/**/*" + task_label + "_" + "LR" + "*clean.nii.gz"
    epiPathList_LR = sorted(glob.glob(filepat, recursive=True))
    epiPathList_RL = [i.replace("LR","RL") for i in epiPathList_LR]

    return epiPathList_LR, epiPathList_RL

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

##############################################################################

def generate_group_epi_mask(epimasklist):
    brain_mask_ind = []
    [brain_mask_ind.append(nilearn.masking.compute_epi_mask(i)) \
     for i in epimasklist]
    group_mask = nilearn.masking.intersect_masks(brain_mask_ind, 
                                                 threshold=0.8, connected=True)
    return group_mask

##############################################################################

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

###############################################################################

def parallel_fc_hcp(arglist_item):
    try:
        epiPath_LR = arglist_item['epiPath'][0]
        epiPath_RL = arglist_item['epiPath'][1]
        args       = arglist_item['args']
        epimask_LR = epiPath_LR.replace("rfMRI_REST1_LR_hp2000_clean.nii.gz", \
                                        "brainmask_fs.2.nii.gz")
        epimask_RL = epiPath_RL.replace("rfMRI_REST1_RL_hp2000_clean.nii.gz", \
                                        "brainmask_fs.2.nii.gz")
        epimask   = nilearn.masking.intersect_masks([epimask_LR,epimask_RL], \
                                                       threshold=1)
        atlasIDs   = arglist_item['atlasIDs']

        # get seed timeseries
        seeds = []
        [seeds.append(atlasIDs.index(i)) for i in args.seeds]
        outfileFC=[]
        outfileZFC=[]

        # Directory of epi image
        epiDir_LR = os.path.split(epiPath_LR)[-2]
        epiDir_RL = os.path.split(epiPath_RL)[-2]

        if not (os.path.exists(epiPath_RL) | os.path.exists(epiPath_LR) | \
                os.path.exists(epiPath_RL) | os.path.exists(epimask_LR)):
            with open("errorlog.txt","a") as errorlog:
                errorlog.write("Dataset " + epiPath_LR + " / " + epiPath_RL + ": incomplete!!")
            return None

        for j in seeds:
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
       
        confounds_df = None

        # get brain timeseries
        brain_timeseries_LR, masker_LR = \
        extract_brain_timeseries(epiPath_LR, epimask, 
                                args.low_pass, args.high_pass,
                                args.time_rep, confounds_df, args.smooth_fwhm)
        # get atlas timeseries
        atlas_timeseries_LR = \
        extract_atlas_timeseries(epiPath_LR, args.atlas, args.low_pass, 
                                args.high_pass, args.time_rep, confounds_df)
        # get brain timeseries
        brain_timeseries_RL, masker_RL = \
        extract_brain_timeseries(epiPath_RL, epimask, 
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
            fc_map.to_filename(outfileFC[i])
            zfc_map.to_filename(outfileZFC[i])

    except:
        with open("errorlog.txt","a") as errorlog:
             errorlog.write("Unknown problem with " + epiPath_LR + " \ " + \
                            epiPath_RL + "!!")
        print("Unknown problem with " + epiPath_LR + " \ " + epiPath_RL + "!!")
        return None

###############################################################################

def nbt_funcon():

    cpu_divisor = 4

    args = read_args_funcon()
    if args.task is None:
        sys.exit('No task defined!')

    epiPathList = ''

    epiPathList_LR,epiPathList_RL = get_hcp_epipathlist(args.base, args.task, \
                                    args.subjects)
    epiPathList = map(list,zip(epiPathList_LR,epiPathList_RL))

    atlasLabels, atlasIDs = read_atlas(args.atlas)

    args.atlas = nilearn.image.load_img(args.atlas)

    if args.parallel is True:
        cpus = mp.cpu_count()
        pool = mp.Pool()
        arg_list = []

        [arg_list.append({'epiPath':epiPath,'args':args,'atlasIDs':atlasIDs}) \
         for epiPath in epiPathList]

        if __name__=='__main__':
            with ProcessPoolExecutor(5) as p:
                results = p.map(parallel_fc_hcp, arg_list)
    else:
        arg_list = []

        [arg_list.append({'epiPath':epiPath,'args':args,'atlasIDs':atlasIDs}) \
         for epiPath in epiPathList]

        [parallel_fc_hcp(i) for i in arg_list]

if __name__ == "__main__":
    nbt_funcon()
