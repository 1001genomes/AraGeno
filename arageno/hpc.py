"""
Utility functions for interacting with HPC backend
"""
import os
from fabric import Connection
from .models import GenotypeSubmission, IdentifyJob, CrossesJob
from .models import get_identify_result_path, STATUS_CHOICES, CREATED, FINISHED, PROCESSING, FINISHED, QUEUED, ERROR
from patchwork.files import exists
from django.utils import timezone
from django.core.files import File
import tempfile
from datetime import datetime
import json
import re
import datetime, math
from django.conf import settings
import logging
from collections import OrderedDict

logger = logging.getLogger(__name__)

SBATCH_PATTERN = re.compile(r"Submitted batch job ([0-9]*)")

SLURM_STATUS_DICT = {'COMPLETED': FINISHED, 'RUNNING': PROCESSING, 'COMPLETING': PROCESSING, '': FINISHED, 'PENDING': QUEUED }
#FIXME make it configurable
BASE_DIR = '/scratch-cbe/users/%s/AraGeno/' % settings.HPC_USER
SUBMIT_SCRIPT_FOLDER = os.path.join(os.path.dirname(__file__),'submit_script_templates/CBE/')

c = Connection(settings.HPC_HOST, user=settings.HPC_USER)


WALLTIME_MULTIPLIER = 2
MEMORY_MULTIPLIER = 5
DEFAULT_MEMORY = (1024*1024* 4)
MIN_MEMORY=1024*1024*4
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

def _read_file(id, filename):
    target_folder = _get_target_folder(id)
    return c.run(f"cd {target_folder} && cat {filename}" ,pty=True, hide=True)



def _get_target_folder(id):
    return os.path.join(BASE_DIR, str(id))

def _get_genotype(id):
    return GenotypeSubmission.objects.get(pk=id)

def _get_rendered_submit_script(submit_script, ctx):
    with open(os.path.join(SUBMIT_SCRIPT_FOLDER, submit_script)) as fh:
        content = fh.read()
        return content % ctx



def stagein_identify_job(id, force=False):
    """
    Function to stagein the genotype files
    """
    target_folder = _get_target_folder(id)
    if not force and exists(c, path=os.path.join(target_folder, str(id))):
        return
    genotype = _get_genotype(id)
    ext = genotype.get_file_ext()
    c.run(f'mkdir -p  {target_folder}')
    c.put(genotype.genotype_file.path, f"{target_folder}/{id}{ext}")


def upload_submit_script(script, target_folder, filename):
    with tempfile.NamedTemporaryFile(delete=False) as fp:
        fp.write(script.encode())
    c.put(fp.name, os.path.join(target_folder,filename))
    os.unlink(fp.name)



def submit_parse_job(id, on_hold=True):
    """
    Submit job to parse genotype
    """
    genotype = _get_genotype(id)
    ext = genotype.get_file_ext()
    target_folder = _get_target_folder(id)
    job_script = 'parse_job.sh'
    ctx = {
        "walltime": _get_walltime(genotype.walltime),
        "memory": _get_memory(genotype.memory),
        "id": id,
        "input_file": '%s%s' % (id, ext),
        "workdir": target_folder
    }
    rendered_script = _get_rendered_submit_script(job_script, ctx)
    upload_submit_script(rendered_script, target_folder, job_script)
    on_hold_flag = "-H" if on_hold else ""
    sbatch_cmd = f"sbatch {on_hold_flag} {target_folder}/{job_script}"
    logger.info("SBATCH call: %s" % sbatch_cmd)
    sbatch_output = c.run(sbatch_cmd)
    if sbatch_output.failed:
      raise Exception("Failed to submit Job: %s" % sbatch_output.stderr)
    match = SBATCH_PATTERN.match(sbatch_output.stdout)
    if not match:
        raise Exception('Failed to get jobid' % sbatch_output.stdout )
    job_id = match.group(1)
    genotype.jobid = job_id
    genotype.save()
    logger.info('Parse job sucessfully submitted (%s)' % job_id)
    return job_id

def get_parse_job_result(job):
    """
    Stage out the statistics from the parse job
    """
    output_result = _read_file(job.id, f"{job.id}.stats.json")
    return json.loads(output_result.stdout)

def get_crosses_job_result(job):
    """Returns the results from the crosses_check"""
    output_result = _read_file(job.identifyjob.genotype.id, f'{job.pk}_crosses.matches.json')
    return json.loads(output_result.stdout)


def get_identify_job_result(job):
    """
    Function to stage-out result files and cleanup
    """
    target_folder = _get_target_folder(job.genotype.id)
    output_path = os.path.join(tempfile.gettempdir(),f"{job.id}.tsv")
    c.get(os.path.join(target_folder,f'{job.id}.scores.txt'), output_path)
    output_result = _read_file(job.genotype.id, f'{job.id}.matches.json')
    data = json.loads(output_result.stdout)
    return data, output_path

def cleanup_files(id):
    """
    Clean up files
    """
    target_folder = _get_target_folder(id)
    c.run('rm -fr %s' % target_folder)

def submit_identify_jobs(id, job_id=None):
    """
    Submit job to identify job
    """
    # Find out if stagejob exists
    genotype = _get_genotype(id)
    target_folder = _get_target_folder(id)
    job_script = 'identify_job.sh'
    ctx = {
        "walltime": '01:00:00',
        "memory": '4G',
        "id": id,
        "identify_job_id": None,
        "dataset": None,
        "workdir": target_folder
    }
    depends = ''
    parse_job_id = genotype.jobid
    if parse_job_id is not None:
        depends = '-d afterok:%s' % parse_job_id
    jobs = genotype.identifyjob_set.filter(pk=job_id) if job_id else genotype.identifyjob_set.all()
    jobids = []
    for job in jobs:
        ctx['identify_job_id'] = job.id
        ctx['dataset'] = job.dataset.name.lower()
        ctx['walltime'] = _get_walltime(job.walltime)
        ctx['memory'] = _get_memory(job.memory)
        rendered_script = _get_rendered_submit_script(job_script, ctx)
        job_script_final = f"{ctx['dataset']}-{job_script}"
        upload_submit_script(rendered_script, target_folder, job_script_final)
        sbatch_cmd = f"sbatch {depends} {target_folder}/{job_script_final}"
        logger.info("SBATCH call: %s" % sbatch_cmd)
        sbatch_output = c.run(sbatch_cmd)
        if sbatch_output.failed:
            raise Exception("Failed to submit Job: %s" % sbatch_output.stderr)
        match = SBATCH_PATTERN.match(sbatch_output.stdout)
        if not match:
            raise Exception('Failed to get jobid' % sbatch_output.stdout )
        job_id = match.group(1)
        job.jobid = job_id
        job.save()
        jobids.append(job_id)
        logger.info('Identify job sucessfully submitted (%s)' % job_id)
    if parse_job_id is not None:
        c.run('scontrol release %s' % parse_job_id)
    return jobids


def submit_crosses_job(job):
    """
    Submit job to crosses job
    """
    # Find out if stagejob exists
    id = job.identifyjob.genotype.id
    target_folder = _get_target_folder(id)
    job_script = 'crosses_job.sh'
    submit_script = '%s/%s' % (SUBMIT_SCRIPT_FOLDER, job_script)
    ctx = {
        "walltime": _get_walltime(job.walltime),
        "memory": _get_memory(job.memory),
        "id": id,
        "crosses_job_id": job.pk,
        "dataset": job.identifyjob.dataset.name.lower(),
        "workdir": target_folder
    }
    rendered_script = _get_rendered_submit_script(job_script, ctx)
    upload_submit_script(rendered_script, target_folder, job_script)
    sbatch_cmd = f"sbatch {target_folder}/{job_script}"
    logger.info("SBATCH call: %s" % sbatch_cmd)
    sbatch_output = c.run(sbatch_cmd)
    if sbatch_output.failed:
        raise Exception("Failed to submit Job: %s" % sbatch_output.stderr)
    match = SBATCH_PATTERN.match(sbatch_output.stdout)
    if not match:
        raise Exception('Failed to get jobid' % sbatch_output.stdout )
    job_id = match.group(1)
    job.jobid = job_id
    job.save()
    logger.info('Crosses job sucessfully submitted (%s)' % job_id)


def get_job_status(job_id):
    # TODO check for pending state
    check_cmd = f"squeue -j {job_id} -o %T -h"
    check_output = c.run(check_cmd, warn=True)
    if check_output.failed or check_output.stdout == "":
        check_cmd = "sacct -j %s.batch -o state -pn" % job_id
        check_output = c.run(check_cmd)
        status = check_output.stdout[:-1]
    slurm_status = check_output.stdout.strip().replace("|","")
    status = SLURM_STATUS_DICT.get(slurm_status, ERROR)
    logger.info('Job state is %s' % status)
    return status

def update_job_results(job):
    if isinstance(job, IdentifyJob):
        data, output_path = get_identify_job_result(job)
        django_file = File(open(output_path,'rb'))
        job.identify_file.save(f'{job.id}.tsv', django_file)
        os.unlink(output_path)
    elif isinstance(job, GenotypeSubmission):
        data = get_parse_job_result(job)
        data = OrderedDict(
            sorted(data.items(), key=lambda t: t[0], reverse=True))
    elif isinstance(job,CrossesJob):
        data = get_crosses_job_result(job)
    else:
        raise ValueError(f'Object {job} not supported')
    return data


def update_job_status(job):
    data = json.loads(job.statistics) if job.statistics else None
    if job.status in (CREATED, QUEUED, PROCESSING):
        new_status = get_job_status(job.jobid)
        job.status = new_status
        if new_status == FINISHED:
            if not job.statistics:
                data = update_job_results(job)
                job.statistics = json.dumps(data)
            # retrieve result
            job.finished = timezone.now()
            job.progress = 100
        elif new_status == PROCESSING:
            if not job.started:
                job.started = timezone.now()
        job.save()
    return data


def update_genotype_status(genotype):
    """Check if job is finished"""
    update_job_status(genotype)
    if genotype.status == FINISHED:
        for identify_job in genotype.identifyjob_set.all():
            data = update_job_status(identify_job)
            if data is not None and data['interpretation']['case'] == 3:
                crosses_job, created = CrossesJob.objects.get_or_create(identifyjob=identify_job, defaults={'status': CREATED})
                if created or not crosses_job.jobid:
                    submit_crosses_job(crosses_job)
            if hasattr(identify_job, 'crossesjob'):
                update_job_status(identify_job.crossesjob)

    if genotype.identify_finished:
        cleanup_files(genotype.id)


def identify_pipeline(id):
    stagein_identify_job(id)
    submit_parse_job(id, True)
    submit_identify_jobs(id)