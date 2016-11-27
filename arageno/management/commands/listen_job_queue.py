from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist
from arageno.models import GenotypeSubmission, IdentifyJob, CrossesJob
from django.utils import timezone
from arageno.models import STATUS_CHOICES, get_identify_result_path, FINISHED, PROCESSING
from arageno.hpc import get_parse_job_result, get_identify_job_result, cleanup_files, get_crosses_job_result, submit_crosses_job
from fabric.api import execute
import pika
import json
from collections import OrderedDict
import re
from AraGenoSite.urls import UUID_REGEX


UUID_MATCHER = re.compile(UUID_REGEX)


class Command(BaseCommand):
    help = 'Listen to th ejob queue'

    def add_arguments(self, parser):
        parser.add_argument(
            'amqp_host', default='amqp.openstack.gmi.oeaw.ac.at/HPC')

    def handle(self, *args, **options):
        amqp_host = options['amqp_host']
        self.stdout.write(self.style.SUCCESS(
            'Starting to listen on "%s"' % amqp_host))
        parameters = pika.URLParameters(amqp_host)
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        channel.basic_consume(self._callback, queue='genotyper', no_ack=True)
        self.stdout.write(self.style.SUCCESS(
            ' [*] Waiting for messages. To exit press CTRL+C'))
        channel.start_consuming()

    def _callback(self, ch, method, properties, body):
        try:
            msg = json.loads(body)
            exit_code = 0
            state = msg['pbs_state']
            if state == 'E':
                exit_code = msg['pbs_exit_status']
            job_name = msg['pbs_job_name']
            if job_name not in ('identify_genotype', 'parse_genotype','crosses_check'):
                raise Exception('Job name %s not supported' % job_name)
            account = msg['pbs_account']
            status = self._get_status_from_pbs(state)
            if not status:
                raise Exception('Job status %s ' % state)
            self.stdout.write(self.style.SUCCESS(
                'Job (%s) message for %s with state %s received' % (job_name, account, state)))
            obj = self._get_obj(account, job_name)
            data = None
            if exit_code != 0:
                status = STATUS_CHOICES[0]
                self.stdout.write(self.style.ERROR(
                    'Non zero exit code (%s) received' % exit_code))
            elif state == 'E':
                data = self._get_data(obj)
                if job_name == 'identify_genotype':
                    obj.identify_file.name = get_identify_result_path(obj.genotype.id, obj.id)
                    # CHECK if crosses job is necessary
                    if data['interpretation']['case'] == 3:
                        try:
                            crosses_job = CrossesJob.objects.get(pk=obj.id)
                            crosses_job.status = STATUS_CHOICES[1][0]
                        except ObjectDoesNotExist:
                            crosses_job = CrossesJob(identifyjob=obj)
                        crosses_job.save()
                        execute(submit_crosses_job, obj.genotype.id, crosses_job.pk)
            obj.status = status[0]
            obj.statistics = json.dumps(data)
            if obj.status == FINISHED:
                obj.finished = timezone.now()
                obj.progress = 100
            elif obj.status == PROCESSING:
                obj.started = timezone.now()
            self.stdout.write(self.style.SUCCESS(
                'Updating %s database entry' % obj))
            obj.save()
            if job_name == 'identify_genotype':
                if obj.genotype.identify_finished:
                    self.stdout.write(self.style.SUCCESS('Cleaning up files for %s' % obj.genotype))
                    #execute(cleanup_files, obj.genotype.id)
            # send email
        except Exception as err:
            # SEND email when there is error
            self.stdout.write(self.style.ERROR(repr(err)))

    def _get_obj(self, account, job_name):
        if job_name == 'parse_genotype':
            account_check = UUID_MATCHER.match(account)
            if not account_check:
                raise Exception('Invalid acount string %s' % account)
            obj = GenotypeSubmission.objects.get(pk=account)
        elif job_name == 'identify_genotype':
            obj = IdentifyJob.objects.get(pk=int(account))
        elif job_name == 'crosses_check':
            obj = CrossesJob.objects.get(pk=int(account))
        else:
            raise ValueError('Job %s not supported ' % job_name)
        return obj

    def _get_data(self, obj):
        data = None
        if isinstance(obj, IdentifyJob):
            data = execute(get_identify_job_result, obj.genotype.id, obj.id)
            data = data[data.keys()[0]]
        elif isinstance(obj, GenotypeSubmission):
            data = execute(get_parse_job_result, obj.id)
            data = data[data.keys()[0]]
            data = OrderedDict(
                sorted(data.items(), key=lambda t: t[0], reverse=True))
        elif isinstance(obj,CrossesJob):
            data = execute(get_crosses_job_result,obj.identifyjob.genotype.id, obj.pk)
            data = data[data.keys()[0]]
        else:
            raise ValueError('Object %s not supported' % obj)
        return data

    def _get_status_from_pbs(self, state):
        if state == 'Q' or state == 'H':
            return STATUS_CHOICES[2]
        elif state == 'S':
            return STATUS_CHOICES[3]
        elif state == 'E':
            return STATUS_CHOICES[4]
        else:
            return None    
