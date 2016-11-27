"""
Serializers for REST api views
"""

from django.urls import reverse
from rest_framework import serializers
from models import GenotypeSubmission, IdentifyJob, Dataset
import json
from services import retrieve_accession_infos


class JSONSerializerField(serializers.Field):
    """ Serializer for JSONField -- required to make field writable"""

    def to_internal_value(self, data):
        return json.dumps(data)

    def to_representation(self, value):
        return json.loads(value)


class DatasetSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Dataset
        fields = ('id', 'name', 'description', 'num_of_markers',
                  'num_of_samples', 'pubmed_id', 'doi')


class CrossesJobSerializer(serializers.HyperlinkedModelSerializer):
    statistics = JSONSerializerField()
    status_text = serializers.CharField(source='get_status_display')
    plot_url = serializers.SerializerMethodField()

    class Meta:
        model = IdentifyJob
        fields = ('id', 'status', 'status_text',
                  'progress','remaining','updated','created', 'statistics', 'plot_url')

    def get_plot_url(self, obj):
        return reverse('crosses_plot', args=[obj.identifyjob.genotype.id, obj.pk])


class IdentifyJobSerializer(serializers.HyperlinkedModelSerializer):
    dataset = DatasetSerializer()
    statistics = JSONSerializerField()
    status_text = serializers.CharField(source='get_status_display')
    crossesjob = CrossesJobSerializer()

    class Meta:
        model = IdentifyJob
        fields = ('id', 'status', 'status_text','updated','created', 'progress',
                  'remaining','statistics', 'dataset', 'crossesjob')


class GenotypeSubmissionSerializer(serializers.HyperlinkedModelSerializer):
    identifyjob_set = IdentifyJobSerializer(many=True)
    statistics = JSONSerializerField()
    status_text = serializers.CharField(source='get_status_display')
    accessions = serializers.SerializerMethodField()

    class Meta:
        model = GenotypeSubmission
        fields = ('url', 'id', 'created', 'updated', 'fullname', 'statistics', 'email',
                  'progress','remaining', 'status', 'status_text',  'identifyjob_set', 'identify_finished', 'accessions')

    def get_accessions(self, obj):
        return retrieve_accession_infos(obj.accession_ids)
