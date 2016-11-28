'''
Views for Genotyper
'''
import os
from django.shortcuts import render
from django.conf import settings
from django.http import HttpResponseRedirect
from forms import UploadFileForm
from django.core.urlresolvers import reverse, reverse_lazy
from django.views.generic import DetailView
from django.db import transaction
from django.views.generic.edit import DeleteView, UpdateView
from models import GenotypeSubmission, delete_upload_folder
from serializers import GenotypeSubmissionSerializer
from djangorestframework_camel_case.render import CamelCaseJSONRenderer
from services import start_identify_pipeline
import logging,traceback
from hpc import FabricException


logger = logging.getLogger(__name__)


def index(request):
    '''
    Home View of Genotyper
    '''
    return render(request, 'index.html')


def faq(request):
    '''
    FAQ View
    '''
    return render(request, 'faq.html')

def about(request):
    '''about'''
    return render(request, 'about.html')

@transaction.atomic
def upload_genotype(request):
    '''
    Upload genotype for identify service
    '''
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                submission = form.save()
                start_identify_pipeline(submission)
                return HttpResponseRedirect(submission.get_absolute_url())
            except Exception as err:
                if submission and submission.genotype_file:
                    delete_upload_folder(submission)
                raise err

    else:
        form = UploadFileForm()
    return render(request, 'upload_genotype.html', {'form': form})


class GenotypeSubmissionInfo(DetailView):
    """
    Display genotype submission and identify status
    """
    model = GenotypeSubmission
    template_name = 'submission_status.html'

    def get_context_data(self, **kwargs):
        kwargs['object_json'] = CamelCaseJSONRenderer().render(
            GenotypeSubmissionSerializer(self.object, context={'request': self.request}).data)
        return super(GenotypeSubmissionInfo, self).get_context_data(**kwargs)


class GenotypeSubmissionDeleteView(DeleteView):
    """
    Confirm view for deleting a submission
    """
    model = GenotypeSubmission
    success_url = reverse_lazy('index')
    template_name = 'submission_confirm_delete.html'
