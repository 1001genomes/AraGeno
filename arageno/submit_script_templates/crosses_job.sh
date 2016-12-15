#!/bin/bash
#PBS -l select=1:ncpus=1:mem=%(memory)s
#PBS -P %(project)s
#PBS -N crosses_check
#PBS -A %(crosses_job_id)s
#PBS -v ID=%(id)s,JOB_ID=%(crosses_job_id)s,DATASET=%(dataset)s,TMPDIR=$WORK/GENOTYPER/$ID
#PBS -q workq
#PBS -l walltime=%(walltime)s

set -e

module use /net/gmi.oeaw.ac.at/software/mendel/intel-x86_64-sandybridge-avx/modules/datasets/

module load matrices_for_snpmatch/1.0.0
module load SNPmatch/1.7.2-foss-2016a-Python-2.7.11


cd "$WORK/GENOTYPER/$ID"

DATASET_FOLDER=$DATASET_MATRICES_FOR_SNPMATCH/$DATASET

snpmatch cross -i $ID.npz -d $DATASET_FOLDER/$DATASET.hdf5 -e $DATASET_FOLDER/$DATASET.acc.hdf5 -s ${JOB_ID}_crosses.txt -o ${JOB_ID}_crosses.windows.txt
#sleep 5 && echo 'test' > $JOB_ID.txt && echo '{"matches": [{"2278": [0.9839400114088569, 7884, 0.9412607449856734], "6909": [0.99421713749268104, 7982, 0.9529608404966571]}], "interpretation": {"case": 2, "text": "An ambiguous sample: Accessions in top hits can be really close"}, "overlap": [0.7530342533489166, 8376]}' > $JOB_ID.txt.matches.json