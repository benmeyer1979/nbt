#!/usr/bin/env python3

from dicomanonymizer import *
from glob import glob
import pdb
import os
import argparse

def parse_args():
    parser = argparse.ArgumentParser(description= \
        "nbt_anonymizer pseudonymizes DICOM images organized in subject and \
         session folders. Default settings of the python tool dicom-anonymizer \
         are used.")
    parser.add_argument("raw_mri", help="raw MRI data directory subdivided \
                         into subjects and sessions", type=str)
    parser.add_argument("output", help="directory where anonymized data will \
                        stored", type=str)
    return parser.parse_args()


def nbt_anonymize():

    args = parse_args()
    #List of directories in raw. Project/Subject/Session/Sequence structure is 
    #mandatory
    dicomlist = glob(args.raw_mri + "/*/*/*")

    nrdicoms  = len(dicomlist)

    for dicom_i in range(nrdicoms):

        indir  = dicomlist[dicom_i]
        path_comp = indir.split("/")
        subID  = path_comp[-3]
        sesID  = path_comp[-2]
        scanID = path_comp[-1]

        outdir = os.path.join(args.output,subID,sesID,scanID)

        sysstr = "mkdir -p " + outdir
        os.system(sysstr)

        print(indir + "    " + outdir)

        sysstr = "dicom-anonymizer " + indir + " " + outdir
        os.system(sysstr)
      #  pdb.set_trace()

if __name__ == "__main__":
    nbt_anonymize() 
