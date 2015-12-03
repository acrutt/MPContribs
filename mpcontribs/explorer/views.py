"""This module provides the views for the explorer interface."""

from django.shortcuts import render_to_response
from django.template import RequestContext
from mpcontribs.rest.rester import MPContribsRester

def get_endpoint():
    from django.core.urlresolvers import reverse
    return reverse('mpcontribs_rest_index')[:-1]

def index(request, collection=None):
    ctx = RequestContext(request)
    if request.user.is_authenticated():
        if collection is not None:
            API_KEY = request.user.api_key
            ENDPOINT = request.build_absolute_uri(get_endpoint())
            with MPContribsRester(API_KEY, endpoint=ENDPOINT) as mpr:
                identifiers, projects, cids = set(), set(), set()
                docs = mpr.query_contributions(collection=collection)
                if docs:
                    for doc in docs:
                        for project, contribs in doc.iteritems():
                            if project == '_id':
                                # contribs = mp-id or composition
                                identifiers.add(contribs)
                            else:
                                projects.add(project)
                                # contribs = contributions for specific project
                                for cid in contribs:
                                    cids.add(cid)
                else:
                    ctx.update({'alert': 'No {} available!'.format(collection)})
    else:
        ctx.update({'alert': 'Please log in!'})
    return render_to_response("mpcontribs_explorer_index.html", locals(), ctx)

def composition(request, composition):
    ctx = RequestContext(request)
    if request.user.is_authenticated():
        API_KEY = request.user.api_key
        ENDPOINT = request.build_absolute_uri(get_endpoint())
        with MPContribsRester(API_KEY, endpoint=ENDPOINT) as mpr:
            urls = [
                '/'.join([request.path, project, cid])
                for project, contribs in mpr.query_contributions(
                    criteria={'_id': composition}, collection='compositions'
                )[0].iteritems() if project != '_id'
                for cid in contribs
            ]
    else:
        ctx.update({'alert': 'Please log in!'})
    return render_to_response("mpcontribs_explorer_index.html", locals(), ctx)

def contribution(request, composition, project, cid):
    if request.user.is_authenticated():
        material = {}
        API_KEY = request.user.api_key
        ENDPOINT = request.build_absolute_uri(get_endpoint())
        with MPContribsRester(API_KEY, endpoint=ENDPOINT) as mpr:
            material['contributed_data'] = mpr.query_contributions(
                criteria={'_id': composition}, collection='compositions',
                projection={'_id': 0, '.'.join([project, cid]): 1}
            )[0][project][cid]
        material['pretty_formula'] = composition
    else:
        material = {k: composition for k in ['pretty_formula']}
    ctx = RequestContext(request, {'material': jsanitize(material)})
    return render_to_response("mpcontribs_explorer_composition.html", locals(), ctx)

# Instead of
# from monty.json import jsanitize
# use the following to fix UnicodeEncodeError
# and play nice with utf-8 encoding
from bson import SON
def jsanitize(obj):
    if isinstance(obj, (list, tuple)):
        return [jsanitize(i) for i in obj]
    elif isinstance(obj, dict):
        return SON([
            (unicode(k).encode('utf-8'), jsanitize(v))
            for k, v in obj.items()
        ])
    elif isinstance(obj, (int, float)):
        return obj
    elif obj is None:
        return None
    else:
        return unicode(obj).encode('utf-8')
