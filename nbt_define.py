#!/usr/bin/env python3

import json
import subprocess
import fnmatch
import pdb
import os
import copy
from glob import glob
import re
import argparse
from pandas import *

def remove_missing_scans(data_json):

    nrsubs  = len(data_json)
    rmlist_sub = []

    for sub in range(nrsubs):

        nrsess  = len(data_json[sub]['sessions'])
        rmlist_ses = []

        for ses in range(nrsess):

            nrscans  = len(data_json[sub]['sessions'][ses]['scan'])
            rmlist_sc = []
            scanlist = data_json[sub]['sessions'][ses]['scan']

            for sc in range(nrscans):
                if not 'Series0' in scanlist[sc]['scan_dir']:
                    rmlist_sc.append(sc)
            scanlist = [i for j, i in enumerate(scanlist) if j not in rmlist_sc]            
            data_json[sub]['sessions'][ses]['scan'] = scanlist            

            if not scanlist:
                rmlist_ses.append(ses)

        seslist = data_json[sub]['sessions']
        seslist = [i for j, i in enumerate(seslist) if j not in rmlist_ses]            
        data_json[sub]['sessions'] = seslist            
        
        if not seslist:
            rmlist_sub.append(sub)
    
    sublist = data_json
    sublist = [i for j, i in enumerate(sublist) if j not in rmlist_sub]            
    data_json = sublist

    return data_json


def add_scan_to_json(scan,scanID,nr_dicoms,ser_nr):
    if not 'ser_nr' in scan and not 'nr_dicoms' in scan:
        scan['scan_dir'] = scanID
        scan['ser_nr'] = ser_nr
        scan['nr_dicoms'] = nr_dicoms
    else: 
        if scan['ser_nr'] < ser_nr and scan['nr_dicoms'] < nr_dicoms:
            scan['scan_dir'] = scanID
            scan['ser_nr'] = ser_nr
            scan['nr_dicoms'] = nr_dicoms
    return scan


def create_data_matrix(data_temp, data_out):
    data_mat = []
    header   = ["ID"]
    nrsess   = len(data_temp["sessions"])

    for ses in range(nrsess):
            nrscans = len(data_temp['sessions'][ses]['scan'])
            for sc in range(nrscans):
                header_field = data_temp['sessions'][ses]['sessionID'] + "_" + \
                               data_temp['sessions'][ses]['scan'][sc]['scan_dir'] \
         
                header.append(header_field)
    nrsubs = len(data_out)
    data_mat.append(header)

    for sub in range(nrsubs):
        index=0
        new_sub = [float("nan")]*len(header)
        new_sub[0] = data_out[sub]['subjectID']
        nrsess = len(data_temp["sessions"])

        for sesi in range(nrsess):
            tempses  = data_temp['sessions'][sesi]['sessionID']
            nrscans = len(data_temp['sessions'][sesi]['scan'])
            for sci in range(nrscans):
                tempscan = data_temp['sessions'][sesi]['scan'][sci]['scan_dir']

                if 'acq' in data_temp['sessions'][sesi]['scan'][sci]:
                    tempacq = data_temp['sessions'][sesi]['scan'][sci]['acq']
                else:
                    tempacq = ""

                index += 1

                nrses_do = len(data_out[sub]['sessions'])
                for sesj in range(nrses_do):
                    nrscan_do = len(data_out[sub]['sessions'][sesj]['scan'])
                    for scj in range(nrscan_do):
                        curscan \
                        = data_out[sub]['sessions'][sesj]['scan'][scj]['scan_dir']         
                        curses  \
                        = data_out[sub]['sessions'][sesj]['sessionID']
                        curnrim \
                        = data_out[sub]['sessions'][sesj]['scan'][scj]['nr_dicoms']

                        if (tempscan in curscan) and (tempses == curses):
                                if (tempacq == "gremag") \
                                   and not (curnrim == nr_gremag):
                                    continue
                                elif (tempacq == "grephase") \
                                     and not (curnrim == nr_grephase):
                                    continue
                                else:
                                    new_sub[index] = curnrim
        data_mat.append(new_sub)
    return data_mat

def parse_args():
    parser = argparse.ArgumentParser(description= \
        "nbt_define reads your raw data directory and a corresponding json \
         formatted MRI protocol. As output a json including all scans \
         that match the template structure is built.")
    parser.add_argument("template_json", help= "MRI protocol json template", \
                        type=str)
    parser.add_argument("raw_mri", help="raw MRI data directory subdivided \
                         into subjects and sessions", type=str)
    parser.add_argument("study_json", help="Json output file containing all \
                         scans that match the template", type=str)
    parser.add_argument("-subs", "--subjects", help="list of subjects to be \
                         processed", nargs='+')
 
    return parser.parse_args()

#Number of phase images when gre_field_mapping is performed
nr_grephase = 50
#Number of magnitude images when gre_field_mapping is performed
nr_gremag   = 100
#Negative of series number digits
ser_dig = -4


############################ MAIN FUNCTION ####################################

def nbt_define():

    #Wild card to catch scan directories
    sub_ses_scan_wc = "/*/*/*"
    #Read arguments    
    args = parse_args()
    #List of directories in raw
    dicomlist = glob(args.raw_mri + "/*/*/*")
    
    if not dicomlist:
        sys.exit("No dicom series found! make sure your dataset is organized in "
                 "subject, session and scan directories!")

    #Number of dicom series
    nrdicoms  = len(dicomlist)

    #read json study template
    with open(args.template_json) as f:
        data_temp = json.load(f)

    #Create subject dictionary of subIDs and corresponding running numbers
    subs = {}
    #output json file structured like data 
    data_out = []
    #number of sessions
    nrsess = len(data_temp['sessions'])

    #Iterate over each raw dicom series
    for dicom_i in range(nrdicoms):
        dicom_raw = dicomlist[dicom_i]
        #decompose raw dicom path
        path_comp = dicom_raw.split("/")
        #subject ID
        subID = path_comp[-3]

         # check if -sub argument is used
        if args.subjects is None:
            pass 
        elif subID not in args.subjects:
            continue

        #session ID
        sesID = path_comp[-2]
        #sequence name    scanID    = path_comp[-1]
        scanID = path_comp[-1]
        #number of dicoms
        nr_dicoms = len(os.listdir(dicom_raw))
        #name of session directory
        ses_dir = path_comp[0:-1]

        #Check if series is relevant 
        if not re.match(".+Series[0-9]+$",scanID): 
            continue
        else:
            ser_nr = int(scanID[ser_dig:])
        if "localizer" in scanID: 
            continue
        if "Phoenix" in scanID: 
            continue

        ses_path = '/' + os.path.join(*ses_dir)

        if not subID in subs:
            data_out.append(copy.deepcopy(data_temp))
            subs[subID] = len(data_out)-1

        #Iterate over MRI study  template
        for ses in range(nrsess):
            nrscans = len(data_temp['sessions'][ses]['scan'])
            
            for sc in range(nrscans):

                #dicom template pattern
                dicom_pat = data_temp['sessions'][ses]['sessionDir'] + '/' + \
                            data_temp['sessions'][ses]['scan'][sc]['scan_dir'] \
                            + '*'
                
                if fnmatch.fnmatch(dicom_raw,dicom_pat):
                    
                    #Assign subject ID
                    data_out[subs[subID]]['subjectID'] = subID                
                    #Assign session path
                    data_out[subs[subID]]['sessions'][ses]['sessionDir'] \
                    = ses_path
                    #Assign session ID
                    data_out[subs[subID]]['sessions'][ses]['sessionID']  \
                    = sesID
                    
                    temp_scan = data_temp['sessions'][ses]['scan'][sc]
               
                    #gre feild maping magnitude and phase directories have the
                    #same name. Distinction is made based on number of dicoms 
                    #in directory
                    if 'gre_field_mapping' in scanID \
                        and temp_scan["acq"] == "grephase" \
                        and nr_dicoms == nr_grephase:
                    
                        scan = data_out[subs[subID]]['sessions'][ses]['scan'][sc]
                        data_out[subs[subID]]['sessions'][ses]['scan'][sc] \
                        = add_scan_to_json(scan,scanID,nr_dicoms,ser_nr)

                    elif 'gre_field_mapping' in scanID \
                          and temp_scan["acq"] == "gremag" \
                          and nr_dicoms == nr_gremag:
                   
                        scan = data_out[subs[subID]]['sessions'][ses]['scan'][sc]

                        data_out[subs[subID]]['sessions'][ses]['scan'][sc] \
                        = add_scan_to_json(scan,scanID,nr_dicoms,ser_nr)

                    elif not 'gre_field_mapping' in scanID: 
                        scan = data_out[subs[subID]]['sessions'][ses]['scan'][sc]
                        data_out[subs[subID]]['sessions'][ses]['scan'][sc] \
                        = add_scan_to_json(scan,scanID,nr_dicoms,ser_nr)

    #Remove missing scans from output json
    data_out = remove_missing_scans(data_out)

    #json data file
    outjson = args.study_json + ".json"
    with open(outjson,'w') as jsonFile:
        json.dump(data_out, jsonFile, indent=4, sort_keys=True)

    #html data table
    outhtml = args.study_json + ".html"
    csv = create_data_matrix(data_temp, data_out)
    df  = DataFrame(csv)
    html = df.to_html()

    textfile = open(outhtml,"w")
    textfile.write(html)
    textfile.close()
###############################################################################

if __name__ == "__main__":
    nbt_define() 
