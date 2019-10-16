#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --mem=%(memory)s
#SBATCH -J AraGeno-crosses-%(id)s
#SBATCH --export=ID=%(id)s,JOB_ID=%(crosses_job_id)s,DATASET=%(dataset)s
#SBATCH --time=%(walltime)s
#SBATCH -D %(workdir)s

set -e

module load snpmatch/3.0.1-foss-2018b-python-2.7.15
export NUMEXPR_MAX_THREADS=272

DATASET_FOLDER=$SCRATCHDIR/matrices_for_snpmatch/$DATASET
snpmatch cross -i $ID.npz -d $DATASET_FOLDER/$DATASET.hdf5 -e $DATASET_FOLDER/$DATASET.acc.hdf5 -o ${JOB_ID}_crosses
#sleep 5 && echo 'test' > $JOB_ID.txt && echo '{"matches": [{"2278": [0.9839400114088569, 7884, 0.9412607449856734], "6909": [0.99421713749268104, 7982, 0.9529608404966571]}], "interpretation": {"case": 2, "text": "An ambiguous sample: Accessions in top hits can be really close"}, "overlap": [0.7530342533489166, 8376]}' > $JOB_ID.txt.matches.json
