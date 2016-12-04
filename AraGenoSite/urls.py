"""AraGenoSite URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.contrib import admin
from rest_framework import routers, serializers, viewsets
from rest_framework.urlpatterns import format_suffix_patterns
import arageno.views as views
from arageno.rest import GenotypeSubmissionViewSet, plot_crosses_windows, download

admin.autodiscover()

UUID_REGEX = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"

# Routers provide an easy way of automatically determining the URL conf.
router = routers.DefaultRouter()
router.register(r'identify', GenotypeSubmissionViewSet)

urlpatterns = [
    url(r'^$', views.index, name="index"),
    url(r'^faq/', views.faq, name="faq"),
    url(r'^about/', views.about, name="about"),
    url(r'^identify/$', views.upload_genotype, name="upload_genotype"),
    url(r'^identify/(?P<pk>%s)/$' % UUID_REGEX, views.GenotypeSubmissionInfo.as_view(), name="genotype_submission_result"),
    url(r'^identify/(?P<pk>%s)/delete/$' % UUID_REGEX, views.GenotypeSubmissionDeleteView.as_view(), name="delete_submission"),
    url(r'^api-auth/', include('rest_framework.urls')),
    url(r'^api/', include(router.urls))
]

restpatterns = [
    url(r'^api/identify/(?P<pk>%s)/jobs/(?P<job_id>(\d+))/plot/$' % UUID_REGEX, plot_crosses_windows, name="crosses_plot"),
    url(r'^api/identify/(?P<pk>%s)/jobs/(?P<job_id>(\d+))/download/$' % UUID_REGEX, download, name="download"),
]


restpatterns = format_suffix_patterns(restpatterns, allowed=['json','zip','png','pdf'])
urlpatterns += restpatterns
