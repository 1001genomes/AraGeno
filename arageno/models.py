"""
Database models
"""
import uuid
import json
import os
from abc import ABCMeta, abstractmethod, abstractproperty
from datetime import datetime,timedelta
from django.utils import timezone
from django.urls import reverse
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.db.models.signals import post_delete
from django.dispatch.dispatcher import receiver
import shutil
import logging
import numpy as np


# Get an instance of a logger
logger = logging.getLogger(__name__)

UPLOAD_FOLDER = 'uploaded_genotypes'

# Create your models here.

ERROR = -1
CREATED = 0
QUEUED = 1
PROCESSING = 2
FINISHED = 3

STATUS_CHOICES = (
    (
        (ERROR, 'Error'),
        (CREATED, 'Created'),
        (QUEUED, 'Queued'),
        (PROCESSING, 'Processing'),
        (FINISHED, 'Finished')
    )
)


def delete_upload_folder(instance):
    if not instance or not instance.genotype_file:
        return
    folder = os.path.dirname(instance.genotype_file.path)
    instance.genotype_file.delete(False)
    shutil.rmtree(folder, ignore_errors=True)


def _calculate_polynominal(num_of_markers,polynominal):
    """Calculates the walltime"""
    if not num_of_markers or not polynominal:
        return None
    poly = np.poly1d(polynominal)
    return abs(poly(num_of_markers))

def calculate_finish_date(num_of_markers, start_date, polynominal):
    """Calculates the finish date"""
    duration = _calculate_polynominal(num_of_markers,polynominal)
    if duration is None:
        return None
    return start_date + timedelta(0,duration)


def calculate_progress(start_date, end_date):
    """Calculats the progress"""
    if not end_date:
        return None
    duration = (end_date - start_date).seconds
    elapsed = (timezone.now() - start_date ).seconds
    if elapsed > duration:
        return 99
    return round((float(elapsed)/duration) * 100)



def get_upload_folder(id):
    """Returns the folder path for genotpye uploads"""
    return '%s/%s' % (UPLOAD_FOLDER, id)

def get_identify_result_path(id, job_id):
    """Returns the path to the result file"""
    return '%s/%s.txt' % (get_upload_folder(id), job_id)


def identify_result_file(instance,filename):
    return '{0}/{1}'.format(get_upload_folder(instance.genotype.id),filename)

def genotype_file_directory(instance, filename):
    uid = instance.id
    if not uid:
        uid = uuid.uuid4()
        instance.id = uid
    return '{0}/{1}'.format(get_upload_folder(uid), filename)


@python_2_unicode_compatible
class Setting(models.Model):
    """
    Some settings
    """
    key = models.CharField(max_length=50, primary_key=True)
    value = models.TextField()

    def __str__(self):
        return 'Setting [%s: %s ]' % (self.key, self.value)


@python_2_unicode_compatible
class Dataset(models.Model):
    """
    Datasets for checking identity against
    """
    name = models.CharField(max_length=200)
    description = models.TextField()
    num_of_samples = models.PositiveIntegerField()
    num_of_markers = models.PositiveIntegerField()
    pubmed_id = models.CharField(
        max_length=255, db_index=True, blank=True, null=True)
    doi = models.CharField(
        max_length=255, db_index=True, blank=True, null=True)
    runtime_identify = models.CharField(max_length=100)
    memory_identify = models.CharField(max_length=100)
    runtime_crosses = models.CharField(max_length=100)
    memory_crosses = models.CharField(max_length=100)

    def __str__(self):
        return '%s (%s samples, %s markers)' % (self.name, self.num_of_samples, self.num_of_markers)


class Job(models.Model):
    """
    Common abstract base class for job related information
    """
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    started = models.DateTimeField(blank=True, null = True)
    finished = models.DateTimeField(blank=True,null=True)
    status = models.SmallIntegerField(
        choices=STATUS_CHOICES, default=CREATED, db_index=True)
    statistics = models.TextField(blank=True, null=True, db_column='data')
    _progress = models.PositiveSmallIntegerField(default=0,db_column='progress')
    jobid = models.PositiveIntegerField(blank=True, null=True, db_index=True)

    class Meta:
        abstract = True

    @abstractproperty
    def num_of_markers(self):
        pass

    @abstractproperty
    def poly_runtime(self):
        pass

    @abstractproperty
    def poly_memory(self):
        pass

    @property
    def walltime(self):
        """Calculates the walltime for the HPC jobs"""
        return _calculate_polynominal(self.num_of_markers,self.poly_runtime)

    @property
    def memory(self):
        """Return the required memory usage"""
        return _calculate_polynominal(self.num_of_markers,self.poly_memory)

    @property
    def finish_date(self):
        """Return the date when the job is finished"""
        if self.status in [CREATED,QUEUED, ERROR]:
            return None
        elif self.status == FINISHED:
            return self.started
        else:
            return calculate_finish_date(self.num_of_markers,self.started,self.poly_runtime)

    @property
    def remaining(self):
        if self.status in [CREATED,QUEUED,ERROR]:
            return None
        elif self.status == FINISHED:
            return 0
        else:
            return abs(self.finish_date - timezone.now()).seconds


    @property
    def progress(self):
        """Return the current progress"""
        if self.status in [CREATED,QUEUED,ERROR,FINISHED]:
            return self._progress
        else:
            progress = calculate_progress(self.started,self.finish_date)
            logger.info("Started: %s, FInished: %s. Progress: %s" % (self.started, self.finish_date,progress))
            if not progress:
                return self._progress
            return progress

    @progress.setter
    def progress(self, value):
        """Updates progress"""
        self._progress = value



@python_2_unicode_compatible
class GenotypeSubmission(Job):
    """
    Submission model
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission_date = models.DateTimeField(auto_now_add=True)
    firstname = models.CharField(max_length=100)
    lastname = models.CharField(max_length=200)
    email = models.CharField(max_length=200)
    genotype_file = models.FileField(upload_to=genotype_file_directory)
    _num_of_markers = models.PositiveIntegerField(blank=True, null=True,db_column='num_of_markers')


    @property
    def accession_ids(self):
        """Retrieves the ids of all identifyjobs"""
        accession_ids = []
        for job in self.identifyjob_set.all():
            accession_ids.extend(job.accession_ids)
        return set(accession_ids)

    @property
    def fullname(self):
        """Returns name of the userProcessing"""
        return '%s %s' % (self.firstname, self.lastname)

    def get_absolute_url(self):
        """returns the submission page page"""
        return reverse('genotype_submission_result', args=[str(self.id)])

    @property
    def identify_finished(self):
        """Returns if all identifyjobs are finished"""
        return self.identifyjob_set.unfinished().count() == 0

    @property
    def num_of_markers(self):
        """Returns the number of markers"""
        if self.statistics:
            data = json.loads(self.statistics)
            if data:
                return data['num_of_snps']
        return self._num_of_markers

    @num_of_markers.setter
    def num_of_markers(self, value):
        self._num_of_markers = value

    @property
    def poly_runtime(self):
        ext = 'bed' if self.is_bed else 'vcf'
        polynominal = Setting.objects.filter(pk="runtime_parsing_%s" % ext).first()
        if polynominal:
            return json.loads(polynominal.value)
        return polynominal

    @property
    def poly_memory(self):
        ext = 'bed' if self.is_bed else 'vcf'
        polynominal = Setting.objects.filter(pk="memory_parsing_%s" % ext).first()
        if polynominal:
            return json.loads(polynominal.value)
        return polynominal


    @property
    def is_bed(self):
        if self.genotype_file.name.endswith('.bed'):
            return True
        return False

    def get_file_ext(self):
        """Returns the file extension"""
        if self.genotype_file:
            return os.path.splitext(self.genotype_file.name)[1]
        return None

    def get_email_text(self):
        """returns the email body that will be sent upon submission"""
        return '''Dear %(firstname)s %(lastname)s,
you submitted your genotype for identification.
You can check the status of the submission using folowing URL:
http://arageno.gmi.oeaw.ac.at%(submission_url)s
Thank you for your patience
Best
AraGeno Team
''' % {'firstname': self.firstname, 'lastname': self.lastname,
               'genotype_file': self.genotype_file.name,
               'submission_url': self.get_absolute_url(),
               'submission_id': self.id}

    def __str__(self):
        return 'GenotypeSubmission(%s, %s)' % (self.id, os.path.basename(self.genotype_file.name))


@receiver(post_delete, sender=GenotypeSubmission)
def genotypesubmission_delete(sender, instance, **kwargs):
    # Pass false so FileField doesn't save the model.
    delete_upload_folder(instance)



class CrossesJobQuerySet(models.QuerySet):
    """
    Custom QuerySet for CrossesJob
    """

    def unfinished(self):
        """
        Returns the unfinished jobs
        """
        return self.exclude(status=ERROR).exclude(status = FINISHED)

class CrossesJob(Job):
    """
    Job for checking crosses
    """
    identifyjob = models.OneToOneField('IdentifyJob', on_delete=models.CASCADE, primary_key=True)
    objects = CrossesJobQuerySet.as_manager()

    @property
    def matches(self):
        """Retrieve match statistics"""
        if self.status == 3:
            return json.loads(self.statistics)['matches']
        return None

    @property
    def poly_runtime(self):
        return json.loads(self.identifyjob.dataset.runtime_crosses)

    @property
    def poly_memory(self):
        return json.loads(self.identifyjob.dataset.memory_crosses)

    @property
    def num_of_markers(self):
        return self.identifyjob.genotype.num_of_markers

    @property
    def accession_ids(self):
        """Retrieves the ids of the matched accessions"""
        accession_ids = []
        matches = self.matches
        if matches:
            accession_ids = set([acc[0] for acc in matches])

        return accession_ids

    def __str__(self):
        return 'CrossesJob (%s, %s: %s (%s))' % (self.identifyjob.genotype.id, self.identifyjob.dataset.name, self.get_status_display(), self.progress)



class IdentifyJobQuerySet(models.QuerySet):
    """
    Custom QuerySet for IdentifyJob
    """

    def unfinished(self):
        """
        Returns the unfinished jobs
        """
        RUNNING = [CREATED,QUEUED,PROCESSING,ERROR]
        return self.filter(status__in=RUNNING) | self.filter(status=FINISHED,crossesjob__status__in=RUNNING)

@python_2_unicode_compatible
class IdentifyJob(Job):
    """
    Identify Job for matching a line
    """
    genotype = models.ForeignKey(
        GenotypeSubmission, on_delete=models.CASCADE)
    dataset = models.ForeignKey('Dataset', on_delete=models.CASCADE)
    identify_file = models.FileField(upload_to=identify_result_file)

    objects = IdentifyJobQuerySet.as_manager()



    @property
    def poly_runtime(self):
        return json.loads(self.dataset.runtime_identify)

    @property
    def poly_memory(self):
        return json.loads(self.dataset.memory_identify)

    @property
    def num_of_markers(self):
        return self.genotype.num_of_markers

    @property
    def overlap(self):
        """Retrieve the overlap from the statistics"""
        if self.status == 3:
            return json.loads(self.statistics)['overlap'] * 100
        return None

    @property
    def matches(self):
        """Retrieve match statistics"""
        if self.status == 3:
            return json.loads(self.statistics)['matches']
        return None

    @property

    def accession_ids(self):
        """Retrieves the ids of the matched accessions"""
        try:
            accession_ids = list(self.crossesjob.accession_ids)
        except CrossesJob.DoesNotExist:
            accession_ids = None
        accession_ids = []
        matches = self.matches
        if matches:
            accession_ids.extend([acc[0] for acc in matches])
        return set(accession_ids)

    def __str__(self):
        return 'IdentifyJob (%s, %s: %s (%s))' % (self.genotype.id, self.dataset.name, self.get_status_display(), self.progress)


@receiver(post_delete, sender=IdentifyJob)
def identifyjob_delete(sender, instance, **kwargs):
    # Pass false so FileField doesn't save the model.
    instance.identify_file.delete(False)
