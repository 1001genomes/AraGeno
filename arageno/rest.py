"""
Views for the rest API
"""
from rest_framework import routers, serializers, viewsets
from rest_framework.decorators import detail_route, list_route, permission_classes
from rest_framework.permissions import IsAdminUser
from models import GenotypeSubmission, IdentifyJob, CrossesJob
from serializers import GenotypeSubmissionSerializer, IdentifyJobSerializer, CrossesJobSerializer
from rest_framework.decorators import api_view, permission_classes, renderer_classes, parser_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, AllowAny
from django.http import HttpResponseBadRequest, HttpResponse, Http404
from models import GenotypeSubmission, IdentifyJob
from plotting import plot_crosses_data


class GenotypeSubmissionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GenotypeSubmission.objects.all()
    serializer_class = GenotypeSubmissionSerializer


    def get_permissions(self):
        if self.action == 'list':
            self.permission_classes = [IsAdminUser,]
        return super(self.__class__, self).get_permissions()


class IdentifyJobViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = IdentifyJob.objects.all()
    serializer_class = IdentifyJobSerializer


    def get_permissions(self):
        if self.action == 'list':
            self.permission_classes = [IsAdminUser,]
        return super(self.__class__, self).get_permissions()


class CrossesJobViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CrossesJob.objects.all()
    serializer_class = CrossesJobSerializer


    def get_permissions(self):
        if self.action == 'list':
            self.permission_classes = [IsAdminUser,]
        return super(self.__class__, self).get_permissions()


@api_view(['GET'])
@permission_classes((IsAuthenticatedOrReadOnly,))
def plot_crosses_windows(request,pk,job_id,format=None):
    """
    Plot the crosses window plot
    ---
    parameters:
        - name: pk
          description: id of the submission
          required: true
          type: number
          paramType: path
        - name: job_id
          description: id of the job_id
          required: True
          type: number
          paramType: path
    
    omit_serializer: true
    produces:
        - image/png
        - image/pdf
    """

    if request.method == "GET":
        content_type=None
        if not format:
            format = 'png'
        if format == 'png':
            content_type = 'image/png'
        elif format == 'pdf':
            content_type = 'application/pdf'
        job = IdentifyJob.objects.get(pk=job_id)

        if str(job.genotype.id) != str(pk):
            raise Http404()
        plot = plot_crosses_data(job.crossesjob)
        response = HttpResponse(content_type=content_type)
        plot.savefig(response)
        return response