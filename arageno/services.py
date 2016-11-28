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
import re
import subprocess

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


def start_identify_pipeline(genotype):
    """Start the identify pipeline"""
    identify_pipeline(genotype.id)
    admin_name, admin_email = settings.ADMINS[0]
    email = EmailMessage(
        'Genotype submitted to AraGeno',
        genotype.get_email_text(),
        '%s <%s>' % (admin_name, admin_email),
        [genotype.email],
        [admin_email],
        reply_to=[admin_email]
    )
    email.send(True)



def retrieve_accession_infos(accession_ids):
    """Retrieves accession infos from REST endpoint"""
    accession_infos = {}
    if accession_ids:
        #TODO make it more efficient
        for acc_id in accession_ids:
            try:
                accession_infos[acc_id] = AraGenoConfig.accessions_map[int(acc_id)]
            except Exception as err:
                logger.warn('Could not retrieve infos for acc %s. Error: %s ', acc_id, repr(err))
    return accession_infos


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
