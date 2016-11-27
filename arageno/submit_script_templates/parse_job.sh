#!/bin/bash
#PBS -l select=1:ncpus=1:mem=%(memory)s
#PBS -P nordborg_common
#PBS -N parse_genotype
#PBS -A %(id)s
#PBS -v INPUT_FILE=%(input_file)s,ID=%(id)s,TMPDIR=$WORK/GENOTYPER/$ID
#PBS -q new_nodes
#PBS -l walltime=%(walltime)s

set -e

module use /net/gmi.oeaw.ac.at/software/shared/nordborg_common/modulefiles/
module load snpmatch/1.5.1-foss-2016a-Python-2.7.11

cd "$WORK/GENOTYPER/$ID"

snpmatch parser -i ${INPUT_FILE} -o ${ID}

#sleep 5 && echo '{"snps": {"Chr5": 2536, "Chr4": 1846, "Chr3": 2253, "Chr2": 2070, "Chr1": 2418}, "num_of_snps": 11123, "interpretation": {"case": 0, "text": "Sufficient number of SNPs"}}' > $ID.stats.json   