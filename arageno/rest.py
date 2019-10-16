"""
Views for the rest API
"""
from rest_framework import routers, serializers, viewsets, mixins, generics
from rest_framework.decorators import action, permission_classes
import rest_framework.permissions as permissions
from .models import GenotypeSubmission, IdentifyJob, CrossesJob
from .serializers import GenotypeSubmissionSerializer, IdentifyJobSerializer, CrossesJobSerializer
from rest_framework.decorators import api_view, permission_classes, renderer_classes, parser_classes
from rest_framework.parsers import FormParser,MultiPartParser
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, AllowAny
from django.http import HttpResponseBadRequest, HttpResponse, Http404
from django.db import transaction
from .models import GenotypeSubmission, IdentifyJob
from .plotting import plot_crosses_data
from .services import create_download_zip, start_identify_pipeline, create_identifyjobs, count_lines, update_submission
from wsgiref.util import FileWrapper
import tempfile
import zipfile
from io import BytesIO


class IsCreationOrIsAuthenticated(permissions.BasePermission):

    def has_permission(self, request, view):
        if not request.user.is_authenticated():
            if view.action == 'create' or view.action == 'destroy':
                return True
            else:
                return False
        else:
            return True


class GenotypeSubmissionViewSet(mixins.CreateModelMixin,mixins.DestroyModelMixin, viewsets.ReadOnlyModelViewSet):
    queryset = GenotypeSubmission.objects.all()
    serializer_class = GenotypeSubmissionSerializer
    authentication_classes = []
    parser_classes = (MultiPartParser,FormParser,)

    def get_object(self):
        obj = super(GenotypeSubmissionViewSet, self).get_object()
        obj = update_submission(obj)
        return obj


    def get_permissions(self):
        if self.action == 'list':
            self.permission_classes = [permissions.IsAdminUser,]
        elif self.action == 'create' or self.action == 'destroy':
            self.permission_classes = [IsCreationOrIsAuthenticated, ]
        return super(GenotypeSubmissionViewSet, self).get_permissions()

    @transaction.atomic
    def perform_create(self, serializer):
        if self.request.data.get('genotype') is None:
            raise serializers.ValidationError("Genotype file must be passed via 'genotype'")
        genotype_file = self.request.data.get('genotype')
        num_of_markers = count_lines(genotype_file.temporary_file_path())
        genotype = serializer.save(genotype_file=genotype_file,num_of_markers=num_of_markers)
        create_identifyjobs(genotype)
        start_identify_pipeline(genotype,send_email=False)



class IdentifyJobViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = IdentifyJob.objects.all()
    serializer_class = IdentifyJobSerializer


    def get_permissions(self):
        if self.action == 'list':
            self.permission_classes = [permissions.IsAdminUser,]
        return super(IdentifyJobViewSet, self).get_permissions()


class CrossesJobViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CrossesJob.objects.all()
    serializer_class = CrossesJobSerializer


    def get_permissions(self):
        if self.action == 'list':
            self.permission_classes = [permissions.IsAdminUser,]
        return super(CrossesJobViewSet, self).get_permissions()


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
        buf = BytesIO()
        plot.savefig(buf,format=format)
        response = HttpResponse(buf.getvalue(),content_type=content_type)
        return response

@api_view(['GET'])
@permission_classes((IsAuthenticatedOrReadOnly,))
def download(request, pk, job_id):
    """
    Download identify result
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
        - application/zip
    """

    if request.method == "GET":
        job = IdentifyJob.objects.get(pk=job_id)
        fp = tempfile.NamedTemporaryFile(suffix='zip')
        create_download_zip(fp,job)
        fp.seek(0)
        response = HttpResponse(FileWrapper(fp), content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="%s_%s.zip"' % (job.genotype.id, job.dataset.name)
        return response
