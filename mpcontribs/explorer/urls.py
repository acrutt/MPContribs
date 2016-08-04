from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.index, name='mpcontribs_explorer_index'),
    url(r'^(?P<collection>[\w]+)$', views.index, name='mpcontribs_explorer_collection'),
    url(r'^(?P<collection>[\w]+)/(?P<cid>[\w\d]+)$',
        views.contribution, name='mpcontribs_explorer_contribution'),
]
