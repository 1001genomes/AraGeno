#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --mem=%(memory)s
#SBATCH -J AraGeno-parse-%(id)s
#SBATCH --export=INPUT_FILE=%(input_file)s,ID=%(id)s
#SBATCH --time=%(walltime)s
#SBATCH -D %(workdir)s
set -e

module load snpmatch/3.0.1-foss-2018b-python-2.7.15

export NUMEXPR_MAX_THREADS=272
snpmatch parser -i ${INPUT_FILE} -o ${ID}

#sleep 5 && echo '{"snps": {"Chr5": 2536, "Chr4": 1846, "Chr3": 2253, "Chr2": 2070, "Chr1": 2418}, "num_of_snps": 11123, "interpretation": {"case": 0,

