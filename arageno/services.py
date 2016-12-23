"""
Business logic/Service layer
"""

from models import IdentifyJob, Dataset
from django.core.mail import EmailMessage
from django.db import transaction
from hpc import identify_pipeline
from django.conf import settings
from apps import AraGenoConfig
import requests
import logging
import plotting
import re
import subprocess
import shutil
import tempfile
from serializers import IdentifyJobSerializer
from rest_framework.renderers import JSONRenderer
import zipfile


# Get an instance of a logger
logger = logging.getLogger(__name__)


WC_REGEX = re.compile(r"^(\d)+")

@transaction.atomic
def create_identifyjobs(genotype, datasets=None):
    """Create identifyjobs for a submission"""
    if datasets is None:
        datasets = Dataset.objects.all()
    if len(datasets) == 0:
        raise ValueError('No datasets found.')
    for dataset in datasets:
        identifyjob = IdentifyJob(genotype=genotype, dataset=dataset)
        identifyjob.save()


def start_identify_pipeline(genotype, send_email=True):
    """Start the identify pipeline"""
    identify_pipeline(genotype.id)
    if send_email:
        email = EmailMessage(
            'Identification job stated on AraGeno',
            genotype.get_email_text(),
            bcc=[settings.DEFAULT_FROM_EMAIL],
            to=[genotype.email],
        )
        email.send(True)



def count_lines(filename):
    """Return number of lines in file"""
    lines = None
    try:
        lines = subprocess.check_output(["wc", "-l", filename])
        m = WC_REGEX.search(lines)
        lines = int(m.group(0))
    except subprocess.CalledProcessError, err:
        logger.error(err)
    return lines

def create_download_zip(fp,job):

    with zipfile.ZipFile(fp, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        dir_name = tempfile.mkdtemp()
        json = JSONRenderer().render(IdentifyJobSerializer(job).data)
        stats_file = '%s/stats.json' % dir_name
        with open(stats_file,'w') as fp:
            fp.write(json)
        zip_file.write(stats_file,'stats.json')
        # put files there
        shutil.copyfile(job.identify_file.path,'%s/result.tsv' % dir_name)
        zip_file.write('%s/result.tsv' % dir_name,'result.tsv')
        if(hasattr(job, 'crossesjob')):
            plt = plotting.plot_crosses_data(job.crossesjob)
            plt.savefig('%s/crosses_plot.pdf' % dir_name)
            zip_file.write('%s/crosses_plot.pdf' % dir_name,'crosses_plot.pdf')
        shutil.rmtree(dir_name,ignore_errors=True)



