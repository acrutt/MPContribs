import re
import os
from collections import defaultdict
import flask_mongorest
from flask import Blueprint
from flask_mongorest.resources import Resource
from flask_mongorest import operators as ops
from flask_mongorest.methods import *
from flask_mongorest.exceptions import UnknownFieldError
from mpcontribs.api.core import SwaggerView
from mpcontribs.api.contributions.document import Contributions
from mpcontribs.api.structures.document import Structures
from mpcontribs.api.tables.document import Tables

templates = os.path.join(
    os.path.dirname(flask_mongorest.__file__), 'templates'
)
contributions = Blueprint("contributions", __name__, template_folder=templates)
exclude = r'[^$.\s_~`^&(){}[\]\\;\'"/]'


# TODO data__ regex doesn't work through bravado/swagger client
class ContributionsResource(Resource):
    document = Contributions
    filters = {
        'id': [ops.In, ops.Exact],
        'project': [ops.In, ops.Exact],
        'identifier': [ops.In, ops.Contains, ops.Exact],
        'formula': [ops.In, ops.Contains, ops.Exact],
        'is_public': [ops.Boolean],
        re.compile(r'^data__((?!__).)*$'): [ops.Contains, ops.Gte, ops.Lte]
    }
    fields = ['id', 'project', 'identifier', 'formula', 'is_public']
    allowed_ordering = [
        'id', 'project', 'identifier', 'formula', 'is_public',
        re.compile(r'^data(__(' + exclude + ')+){1,3}$')
    ]
    paginate = True
    default_limit = 20
    max_limit = 250
    download_formats = ['json', 'csv']

    @staticmethod
    def get_optional_fields():
        return ['data', 'structures', 'tables']

    def value_for_field(self, obj, field):
        # add structures and tables info to response if requested
        if field.startswith('structures'):
            from mpcontribs.api.structures.views import StructuresResource
            sr = StructuresResource(view_method=self.view_method)
            field_split = field.split('.')
            field_len = len(field_split)
            # return full structures only if download requested
            full = bool(self.view_method == Download and
                        self.params.get('_fields') == '_all')
            if field_len > 2:
                raise UnknownFieldError
            elif field_len == 2:
                if field_split[1] in Structures._fields:
                    # TODO return structure subfields if nested fields requested
                    # TODO find a way to not re-query structures for every subfield?
                    return f'TODO requested {field_split[1]}'
                else:
                    # requested structure(s) for label
                    mask = ['id', 'name']
                    objects = Structures.objects.only(*mask)
                    objects = objects.filter(contribution=obj.id, label=field_split[1]).order_by('-id')
                    if not objects:
                        raise UnknownFieldError
                    return [sr.serialize(o, fields=mask) for o in objects]
            elif field_len == 1:
                mask = ['id', 'label', 'name']
                fmt = self.params.get('format')
                if full and fmt == 'json':
                    mask += ['lattice', 'sites', 'charge', 'klass', 'module']
                objects = Structures.objects.only(*mask).filter(contribution=obj.id).order_by('-id')
                value = defaultdict(list)
                for o in objects:
                    s = sr.serialize(o, fields=mask)
                    value[s.pop('label')].append(sr.value_for_field(o, 'cif') if fmt == 'csv' else s)
                return value

        elif field == 'tables':
            tables = Tables.objects.only('id', 'name').filter(contribution=obj.id)
            return [{'id': t.id, 'name': t.name} for t in tables]
        else:
            raise UnknownFieldError


class ContributionsView(SwaggerView):
    resource = ContributionsResource
    methods = [Fetch, Delete, Update, BulkFetch, BulkCreate, BulkUpdate, BulkDelete, Download]
