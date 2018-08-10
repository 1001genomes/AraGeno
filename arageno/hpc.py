"""
Utility functions for interacting with HPC backend
"""
import os
from fabric.api import *
from fabric.contrib.files import upload_template, exists
from models import GenotypeSubmission, IdentifyJob, CrossesJob
from models import get_identify_result_path
import tempfile
import json
import datetime, math
from django.conf import settings

#FIXME make it configurable
BASE_DIR = '/lustre/scratch/users/%s/GENOTYPER/' % settings.HPC_USER
SUBMIT_SCRIPT_FOLDER = os.path.join(os.path.dirname(__file__),'submit_script_templates/')


class FabricException(Exception):
    pass


env.use_ssh_config = True
env.abort_on_prompts = True
env.skip_bad_hosts = True
env.abort_exception = FabricException

env.roledefs = {
    'login': ['login.mendel.gmi.oeaw.ac.at'],
    'dmn': ['dmn0.mendel.gmi.oeaw.ac.at'],
}

WALLTIME_MULTIPLIER = 2
MEMORY_MULTIPLIER = 1.5
DEFAULT_MEMORY = (1024*1024* 4)
MIN_MEMORY=1024*100
DEFAULT_WALLTIME = 1200
MIN_WALLTIME=60*10

def sizeof_fmt(num, suffix='b'):
    for unit in ['k','m','g','t','p','e','z']:
        if abs(num) < 1024.0:
            return ("%3.0f%s%s" % (num, unit, suffix)).strip()
        num /= 1024.0
    return "%.0f%s%s" % (num, 'y', suffix)

def _get_memory(memory):
    # convert to bytes
    if not memory:
        memory = DEFAULT_MEMORY
    memory = math.ceil(max(memory * MEMORY_MULTIPLIER,MIN_MEMORY) )
    return sizeof_fmt(memory)

def _get_walltime(walltime):
    if not walltime:
        walltime = DEFAULT_WALLTIME
    return str(datetime.timedelta(seconds=math.ceil(max(walltime * WALLTIME_MULTIPLIER,MIN_WALLTIME) )))



@roles('dmn')
def stagein_identify_job(id, force=False):
    """
    Function to stagein the genotype files
    """
    target_folder = _get_target_folder(id)
    if not force and exists('%s/%s' % (target_folder, id)):
        return
    genotype = _get_genotype(id)
    ext = genotype.get_file_ext()
    run('mkdir -p  %s' % target_folder, pty=False)
    with cd(target_folder):
        put(genotype.genotype_file.path, '%s%s' % (id, ext))


@roles('login')
def submit_parse_job(id, on_hold=True):
    """
    Submit job to parse genotype
    """
    genotype = _get_genotype(id)
    ext = genotype.get_file_ext()
    target_folder = _get_target_folder(id)
    job_script = 'parse_job.sh'
    submit_script = '%s/%s' % (SUBMIT_SCRIPT_FOLDER, job_script)
    ctx = {
        "walltime": _get_walltime(genotype.walltime),
        "memory": _get_memory(genotype.memory),
        "id": id,
        "input_file": '%s%s' % (id, ext),
        "project": settings.HPC_PROJECT
    }
    upload_template(submit_script, target_folder, backup=False, context=ctx)
    with cd(target_folder):
        run('qsub %s %s/%s' % (('-h' if on_hold else ''),
                               target_folder, job_script), pty=False)


@roles('dmn')
def get_parse_job_result(id):
    """
    Stage out the statistics from the parse job
    """
    return json.loads(_read_file(id, '%s.stats.json' % id))


@roles('login')
def submit_identify_jobs(id, job_id = None):
    """
    Submit job to identify job
    """
    # Find out if stagejob exists
    genotype = _get_genotype(id)
    parse_job_id = run('qselect -s H -P %s -N parse_genotype -A %s' % (settings.HPC_PROJECT, id))
    target_folder = _get_target_folder(id)
    job_script = 'identify_job.sh'
    submit_script = '%s/%s' % (SUBMIT_SCRIPT_FOLDER, job_script)
    ctx = {
        "walltime": '01:00:00',
        "memory": '4G',
        "id": id,
        "identify_job_id": None,
        "dataset": None,
        "project": settings.HPC_PROJECT
    }
    depends = ''
    if parse_job_id != '':
        depends = '-W depend=afterok:%s' % parse_job_id
    jobs = genotype.identifyjob_set.filter(pk=job_id) if job_id else genotype.identifyjob_set.all()
    for job in jobs:
        ctx['identify_job_id'] = job.id
        ctx['dataset'] = job.dataset.name.lower()
        ctx['walltime'] = _get_walltime(job.walltime)
        ctx['memory'] = _get_memory(job.memory)
        upload_template(submit_script, target_folder, backup=False, context=ctx)
        with cd(target_folder):
            run('qsub %s %s/%s' % (depends, target_folder, job_script), pty=False)

    if parse_job_id != '':
        run('qrls %s' % parse_job_id)


@roles('login')
def submit_crosses_job(id,job_id):
    """
    Submit job to crosses job
    """
    # Find out if stagejob exists
    job = CrossesJob.objects.get(pk=job_id)
    target_folder = _get_target_folder(id)
    job_script = 'crosses_job.sh'
    submit_script = '%s/%s' % (SUBMIT_SCRIPT_FOLDER, job_script)
    ctx = {
        "walltime": _get_walltime(job.walltime),
        "memory": _get_memory(job.memory),
        "id": id,
        "crosses_job_id": job_id,
        "dataset": job.identifyjob.dataset.name.lower(),
        "project": settings.HPC_PROJECT
    }
    upload_template(submit_script, target_folder, backup=False, context=ctx)
    with cd(target_folder):
        run('qsub %s/%s' % (target_folder, job_script), pty=False)

@roles('dmn')
def get_crosses_job_result(id,job_id):
    """Returns the results from the crosses_check"""
    target_folder = _get_target_folder(id)
    return json.loads(_read_file(id, '%s_crosses.matches.json' % job_id))


@roles('dmn')
def get_identify_job_result(id, identify_job_id):
    """
    Function to stage-out result files and cleanup
    """
    target_folder = _get_target_folder(id)
    output_path = '%s/%s.tsv' % (tempfile.gettempdir(),identify_job_id)
    with cd(target_folder):
        get('%s.scores.txt' % identify_job_id,output_path)
    data = json.loads(_read_file(id, '%s.matches.json' % identify_job_id))
    return data, output_path


@roles('dmn')
def cleanup_files(id):
    """
    Clean up files
    """
    target_folder = _get_target_folder(id)
    run('rm -fr %s' % target_folder)


def identify_pipeline(id):
    execute(stagein_identify_job, id)
    execute(submit_parse_job, id, True)
    execute(submit_identify_jobs, id)


def _read_file(id, filename):
    target_folder = _get_target_folder(id)
    with cd(target_folder):
        return run('cat %s' % filename)


def _get_target_folder(id):
    return '%s/%s' % (BASE_DIR, id)

def _get_genotype(id):
    return GenotypeSubmission.objects.get(pk=id)


