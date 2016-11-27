"""
Form and ModelForm definitions
"""

import os
from django import forms
from models import GenotypeSubmission, IdentifyJob
from django.db import transaction
from services import create_identifyjobs , count_lines


SUPPORTED_EXTENSION = ('.vcf', '.bed')

TEXT_WIDGET = forms.TextInput(attrs={'class':'mdl-textfield__input'})

def _validate_file(value):
    extension = os.path.splitext(value.name)[1]
    if extension not in SUPPORTED_EXTENSION:
        raise forms.ValidationError(
            "Wrong file extension. Only %s supported" % ','.join(SUPPORTED_EXTENSION),
            params={'value':value})
    return value


class UploadFileForm(forms.ModelForm):
    """
    Form for uploading a genotype
    """
    genotype_file = forms.FileField(validators=[_validate_file])

    class Meta:
        model = GenotypeSubmission
        fields = ['firstname', 'lastname', 'email', 'genotype_file']
        widgets = {
            'email': forms.EmailInput(attrs={'class':'mdl-textfield__input', 'required':True}),
            'firstname': TEXT_WIDGET,
            'lastname': TEXT_WIDGET
        }
    @transaction.atomic
    def save(self, commit=True):
        genotype = super(UploadFileForm, self).save()
        create_identifyjobs(genotype)
        genotype.num_of_markers = count_lines(genotype.genotype_file.path)
        genotype.save()
        return genotype

