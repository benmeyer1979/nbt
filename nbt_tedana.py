#!/usr/bin/env python3

import gzip
import pickle
import os
import os.path as op
from nipype.interfaces import fsl
from glob import glob
from nipype.interfaces.ants import ApplyTransforms
import argparse
import pdb
import tedana

def nbt_tedana():

    parser = argparse.ArgumentParser(description=
    "nbt_tedana.py performs tedana multi-echo ICA and optimal "
    "combination. ANTs-based normalization and FSL-based masking is performed "
    "on the preprocessed data. fMRIprep preprocessed data with "
    "--me-output-echos option chosen is required.")

    parser.add_argument("base", help=
    "fmriprep directory including derivatives older.")

    parser.add_argument("fmriprepID", help=
    "Unique(!) BIDS-compliant file identifier including task (required), acq "
    "(optional) and run (optional) label, e.g. task-mmid_acq-me4mb3_run-1. "
    "Labels must be part in multi-echo filename.")

    parser.add_argument("-subs", "--subjects", help=
    "list of subject identifiers for processing", nargs='+', required=True)
    parser.add_argument("-sess", "--sessions", help=
    "list of session identifiers for processing", nargs='+',required=True)
    parser.add_argument("-et", "--echotimes", help=
    "list of echo times, e.g. ", nargs='+', 
    default=['12', '28.24', '44.48', '60.72'])
    
    parser.add_argument("-fp", "--fslspath", help=
    "Path to fsl binary", type=str, default='/usr/local/fsl/bin/fsl')
    parser.add_argument("-ap", "--antspath", help=
    "Path to Ants binary", type=str, default='/usr/local/bin/ANTs/bin/ants')
    parser.add_argument("-d", "--derivatives", help=
    "If derivatives folder in the base directory is not named [derivatives]"
    ", provide new folder name here.", type=str)
    
    args = parser.parse_args()

    fmriprepID = args.fmriprepID
   # fmriprepID_underscore = args.fmriprepID.replace('-', '_')

    if args.derivatives is not None:
        der_dirname = args.derivatives
    else:
        der_dirname = "derivatives"    

    deriv_dir = op.join(args.base, der_dirname)
 
    for sub in args.subjects:
        for ses in args.sessions:
        
            substr = 'sub-{0}'.format(sub)
            sesstr = 'ses-{0}'.format(ses)
            echo_suf =  "*" + fmriprepID + '*echo-*_desc-preproc*.nii.gz'

            echo_files = glob(op.join(deriv_dir, substr, sesstr,'func',
            echo_suf))
            
            echo_files.sort()

            sub_ses_func = op.join(deriv_dir, substr, sesstr,'func')

            tedana_arg              = {'echoFiles': echo_files}
            tedana_arg['echoTimes'] = args.echotimes
            tedana_arg['out-dir']   = op.join(sub_ses_func, 'tedana', 
            fmriprepID)

            # Create tedana output directories
            os.makedirs(tedana_arg['out-dir'], exist_ok=True)

            # System call tedana
            sys_str = 'tedana -d ' + ' '.join(tedana_arg['echoFiles']) + ' -e ' \
            + ' '.join(tedana_arg['echoTimes']) + ' --out-dir ' \
            + tedana_arg['out-dir']

            os.system(sys_str)

            boldToMni_suf = '*orig_to-T1w*.txt'
            t1ToMni_suf   = '*T1w_to-MNI*.h5'
            boldref_suf   = '*' + fmriprepID + '*_boldref.nii.gz'
            brainmask_suf = '*' + fmriprepID + '*-brain_mask.nii.gz'


            BOLDtoT1 = glob(op.join(deriv_dir, substr, sesstr,'anat', 
                            boldToMni_suf))[0]
            sub_ses_anat_T1toMNI = glob(op.join(deriv_dir, substr, sesstr, 
                                        'anat',t1ToMni_suf))
            sub_anat_T1toMNI = glob(op.join(deriv_dir, substr,'anat',
                                    t1ToMni_suf))

            if not sub_ses_anat_T1toMNI:
                T1toMNI = sub_anat_T1toMNI[0]
            else:
                T1toMNI = sub_ses_anat_T1toMNI[0]

            ref_file  = glob(op.join(deriv_dir, substr, sesstr,'func',
                             boldref_suf))[0]
            mask_file = glob(op.join(deriv_dir, substr, sesstr,'func',
                             brainmask_suf))[0]

            at = ApplyTransforms()  
          
            at.inputs.transforms = [T1toMNI,BOLDtoT1] 
            at.inputs.reference_image = ref_file
            at.inputs.dimension = 3
            at.inputs.input_image_type = 3
            at.inputs.default_value = 0.0
            at.inputs.interpolation = 'LanczosWindowedSinc'
            at.inputs.float = True
            
            at.inputs.input_image = op.join(tedana_arg['out-dir'], 
                                            'desc-optcom_bold.nii.gz')
            at.inputs.output_image = op.join(tedana_arg['out-dir'],
                                             'desc-optcom_bold_mni.nii.gz')

            # Add ANTs to PATH
            os.environ['PATH'] += os.path.pathsep + '/usr/local/bin/ANTs/bin/'

            at.run()

            # Set arguments for ApplyMask
            applymask_arg = {'mask': mask_file, 'file': at.inputs.output_image,
                             'output': at.inputs.output_image.replace('.nii.gz', 
                             '_masked.nii.gz')}

            # Add fsl to PATH and set output_type to nii.gz
            os.environ['PATH'] += os.path.pathsep + '/usr/local/fsl/bin/'
            fsl.FSLCommand.set_default_output_type('NIFTI_GZ')

            # Run ApplyMask
            mask = fsl.ApplyMask(in_file = applymask_arg['file'], 
                   mask_file = applymask_arg['mask'], 
                   out_file = applymask_arg['output'])
            
            mask.run()

if __name__ == '__main__':
    nbt_tedana()
