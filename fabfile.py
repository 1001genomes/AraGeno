from fabric.api import *
from fabric.contrib.console import confirm
from fabric.contrib import django
django.settings_module('AraGenoSite.settings')
import django
django.setup()
from arageno.hpc import *
from arageno.models import *

@task
def stagein(id):
    execute(stagein_identify_job, id)


@task
def parseJob(id, on_hold=False):
    execute(submit_parse_job, id, on_hold)

@task
def identifyJobs(id,job_id=None):
    execute(submit_identify_jobs, id, job_id)


@task
def crossesJob(id,job_id):
    execute(submit_crosses_job,id,job_id)

@task
def identify(id):
    execute(identify_pipeline, id)

@task
def genotypeStats(id):
    ret = execute(get_parse_job_result, id)
    print ret


@task
def identifyResult(id, job_id,save_to_db=False):
    data = execute(get_identify_job_result, id, job_id)
    if save_to_db:
        job = IdentifyJob.objects.get(pk=int(job_id))
        # TODO move to services.py
        data = data[data.keys()[0]]

        from operator import itemgetter
        matches = data['matches']
        data['matches'] = [[key, matches[key][0], matches[key][1], matches[key][2]]
                            for key in matches.keys()]
        data['matches'] = sorted(
            data['matches'], key=itemgetter(1), reverse=True)
        job.statistics = json.dumps(data)

        job.status = STATUS_CHOICES[4][0]
        job.progress = 100
        job.save()
    print data
