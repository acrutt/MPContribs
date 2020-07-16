# -*- coding: utf-8 -*-
import os
import flask_mongorest
from marshmallow.utils import get_value
from mongoengine.queryset import DoesNotExist
from flask import Blueprint, current_app, url_for
from flask_mongorest.exceptions import UnknownFieldError
from flask_mongorest.resources import Resource
from flask_mongorest import operators as ops
from flask_mongorest.methods import Fetch, Create, Delete, Update, BulkFetch
from werkzeug.exceptions import Unauthorized
from itsdangerous import SignatureExpired
from mpcontribs.api.core import SwaggerView
from mpcontribs.api.projects.document import Projects
from mpcontribs.api.contributions.document import Contributions
from mpcontribs.api.structures.document import Structures

templates = os.path.join(os.path.dirname(flask_mongorest.__file__), "templates")
projects = Blueprint("projects", __name__, template_folder=templates)


class ProjectsResource(Resource):
    document = Projects
    filters = {
        "project": [ops.In, ops.Exact, ops.IContains],
        "is_public": [ops.Boolean],
        "title": [ops.IContains],
        "long_title": [ops.IContains],
        "authors": [ops.IContains],
        "description": [ops.IContains],
        "owner": [ops.Exact, ops.In],
        "is_approved": [ops.Boolean],
        "unique_identifiers": [ops.Boolean],
    }
    fields = [
        "project",
        "is_public",
        "title",
        "owner",
        "is_approved",
        "unique_identifiers",
    ]
    allowed_ordering = ["project", "is_public", "title"]
    paginate = False

    @staticmethod
    def get_optional_fields():
        return ["long_title", "authors", "description", "urls", "other", "columns"]


class ProjectsView(SwaggerView):
    resource = ProjectsResource
    methods = [Fetch, Create, Delete, Update, BulkFetch]

    def has_add_permission(self, request, obj):
        # limit the number of projects a user can own (unless admin)
        groups = self.get_groups(request)
        if "admin" in groups:
            return True

        # is_approved can only be set by an admin
        if obj.is_approved:
            raise Unauthorized(f"Only admins can set `is_approved=True`")

        # project already created at this point -> count-1 and revert
        nr_projects = Projects.objects(owner=obj.owner).count() - 1
        if nr_projects > 2:
            Projects.objects(project=obj.project).delete()
            raise Unauthorized(f"{obj.owner} already owns {nr_projects} projects.")

        return True


@projects.route("/applications/<token>", defaults={"action": None})
@projects.route("/applications/<token>/<action>")
def applications(token, action):
    ts = current_app.config["USTS"]
    max_age = current_app.config["USTS_MAX_AGE"]
    try:
        owner, project = ts.loads(token, max_age=max_age)
    except SignatureExpired:
        return f"signature for {owner} of {project} expired."

    try:
        obj = Projects.objects.get(project=project, owner=owner, is_approved=False)
    except DoesNotExist:
        return f"{project} for {owner} already approved or denied."

    actions = ["approve", "deny"]
    if action not in actions:
        response = f"<h3>{project}</h3><ul>"
        scheme = "http" if current_app.config["DEBUG"] else "https"
        for a in actions:
            u = url_for(
                "projects.applications",
                token=token,
                action=a,
                _scheme=scheme,
                _external=True,
            )
            response += f'<li><a href="{u}">{a}</a></li>'
        return response + "</ul>"

    if action == "approve":
        obj.is_approved = True
        obj.save()  # post_save (created=False) sends notification when `is_approved` set
    else:
        obj.delete()  # post_delete signal sends notification

    return f'{project} {action.replace("y", "ie")}d and {owner} notified.'
