from __future__ import unicode_literals
import requests
import logging
from django.conf import settings
from django.apps import AppConfig
logger = logging.getLogger(__name__)


class AraGenoConfig(AppConfig):
    name = 'arageno'
    accessions_map = {}

    def ready(self):
        super(AraGenoConfig, self).ready()
        self._get_accession_map()
        logger.info('Accession map initialized')

    @classmethod
    def _get_accession_map(cls):
        ret = requests.get(settings.ACCESSION_REST_MAP_URL)
        ret.raise_for_status()
        accessions = ret.json()
        for acc in accessions:
            acc_id = acc['pk']
            acc['url'] = 'https://arapheno.1001genomes.org/accession/{0}'.format(acc_id)
            acc['picture_url'] = 'http://gwapp.gmi.oeaw.ac.at/public/plants/{0}.png'.format(acc_id)
            cls.accessions_map[acc_id] = acc

