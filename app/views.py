from flask import render_template
from flask_appbuilder.models.sqla.interface import SQLAInterface
from flask_appbuilder import ModelView, ModelRestApi
from wtforms import SelectField
from wtforms.validators import InputRequired, ValidationError
import os
import re

from . import appbuilder, db

from .models import Source, Country

 
class CountryView(ModelView):
    datamodel = SQLAInterface(Country)
 
class SourceView(ModelView):
    datamodel = SQLAInterface(Source)
    edit_template = "source_edit.html"
    add_template = "source_add.html"

    IDENTIFIER_MAP_TYPES = (
        (0, "0 - Standard normalization"),
        (1, "1 - Regex replace"),
        (2, "2 - Mapping from file"),
    )
    IDENTIFIER_MAP_TYPE_LABELS = {
        key: value.split(" - ", 1)[1] for key, value in IDENTIFIER_MAP_TYPES
    }

    # labels
    label_columns = {
        "source_id": "Source",
        "name": "Name",
        "type": "Type",
        "site_id": "Site ID",
        "country_iso": "Country",
        "updated_at": "Updated",
        "identifier_prefix": "Identifier Prefix",
        "identifier_map_type": "Identifier Mapping Mode",
        "identifier_map_regex": "Regex Pattern",
        "identifier_map_replace": "Regex Replacement",
        "identifier_map_filename": "Mapping File Path",
    }

    description_columns = {
        "identifier_prefix": "Base OAI prefix expected after normalization. Example: oai:sedici.unlp.edu.ar",
        "identifier_map_type": "How identifiers are normalized before indexing.",
        "identifier_map_regex": "Used only for mode 1 (Regex replace). Example: ^oai:([^:]+):(.+)$",
        "identifier_map_replace": "Replacement for mode 1. Example: oai:\\1:\\2",
        "identifier_map_filename": "Used only for mode 2 (Mapping from file). Absolute path inside container.",
    }

    list_columns = ["source_id", "name", "type", "site_id", "country_iso", "identifier_map_type", "updated_at"]

    formatters_columns = {
        "identifier_map_type": lambda value: SourceView.IDENTIFIER_MAP_TYPE_LABELS.get(
            value, f"Unknown ({value})"
        )
    }

    edit_columns = [
        "source_id",
        "name",
        "url",
        "institution",
        "type",
        "site_id",
        "national_site_id",
        "regional_site_id",
        "auth_token",
        "country_iso",
        "identifier_prefix",
        "identifier_map_type",
        "identifier_map_regex",
        "identifier_map_replace",
        "identifier_map_filename",
    ]
    add_columns = edit_columns

    @staticmethod
    def _trim_or_none(value):
        if value is None:
            return None
        value = value.strip()
        return value or None

    @staticmethod
    def _coerce_mode(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return value

    @staticmethod
    def _validate_identifier_mapping_by_mode(mode, regex_value, replace_value, filename_value):
        mode = SourceView._coerce_mode(mode)
        if mode == 0:
            return
        if mode == 1:
            if not regex_value:
                raise ValidationError("Regex Pattern is required for mode 'Regex replace'.")
            if not replace_value:
                raise ValidationError("Regex Replacement is required for mode 'Regex replace'.")
            return
        if mode == 2:
            if not filename_value:
                raise ValidationError("Mapping File Path is required for mode 'Mapping from file'.")
            return
        raise ValidationError("Invalid Identifier Mapping Mode. Allowed values: 0, 1, 2.")

    def _validate_mapping_mode_field(form, field):
        mode = SourceView._coerce_mode(field.data)
        if mode not in SourceView.IDENTIFIER_MAP_TYPE_LABELS:
            raise ValidationError("Invalid Identifier Mapping Mode. Allowed values: 0, 1, 2.")

        regex_value = SourceView._trim_or_none(form.identifier_map_regex.data)
        replace_value = SourceView._trim_or_none(form.identifier_map_replace.data)
        filename_value = SourceView._trim_or_none(form.identifier_map_filename.data)

        if mode == 1:
            if not regex_value:
                raise ValidationError("Regex Pattern is required when mode is 'Regex replace'.")
            if not replace_value:
                raise ValidationError("Regex Replacement is required when mode is 'Regex replace'.")
            try:
                re.compile(regex_value)
            except re.error as exc:
                raise ValidationError("Invalid regex pattern: %s" % exc)
            try:
                re.compile(regex_value).sub(replace_value, "oai:test:123/456")
            except re.error as exc:
                raise ValidationError("Invalid replacement expression: %s" % exc)

        if mode == 2:
            if not filename_value:
                raise ValidationError("Mapping File Path is required when mode is 'Mapping from file'.")
            if not os.path.isfile(filename_value):
                raise ValidationError(
                    "Mapping file does not exist in the container path: %s" % filename_value
                )

    def _validate_regex_field(form, field):
        mode = SourceView._coerce_mode(form.identifier_map_type.data)
        regex_value = SourceView._trim_or_none(field.data)
        if mode == 1 and not regex_value:
            raise ValidationError("Regex Pattern is required when mode is 'Regex replace'.")
        if mode == 1 and regex_value:
            try:
                re.compile(regex_value)
            except re.error as exc:
                raise ValidationError("Invalid regex pattern: %s" % exc)

    def _validate_replace_field(form, field):
        mode = SourceView._coerce_mode(form.identifier_map_type.data)
        replace_value = SourceView._trim_or_none(field.data)
        if mode == 1 and not replace_value:
            raise ValidationError("Regex Replacement is required when mode is 'Regex replace'.")
        if mode == 1 and replace_value:
            regex_value = SourceView._trim_or_none(form.identifier_map_regex.data)
            if not regex_value:
                return
            try:
                regex = re.compile(regex_value)
            except re.error:
                # Regex field validator will report the syntax issue.
                return
            try:
                regex.sub(replace_value, "oai:test:123/456")
            except re.error as exc:
                raise ValidationError("Invalid replacement expression: %s" % exc)

    def _validate_filename_field(form, field):
        mode = SourceView._coerce_mode(form.identifier_map_type.data)
        filename_value = SourceView._trim_or_none(field.data)
        if mode != 2:
            return
        if not filename_value:
            raise ValidationError("Mapping File Path is required when mode is 'Mapping from file'.")
        if not os.path.isfile(filename_value):
            raise ValidationError(
                "Mapping file does not exist in the container path: %s" % filename_value
            )

    validators_columns = {
        "identifier_map_regex": [_validate_regex_field],
        "identifier_map_replace": [_validate_replace_field],
        "identifier_map_filename": [_validate_filename_field],
    }

    add_form_extra_fields = {
        "identifier_map_type": SelectField(
            "Identifier Mapping Mode",
            choices=IDENTIFIER_MAP_TYPES,
            coerce=int,
            validators=[InputRequired(), _validate_mapping_mode_field],
        )
    }
    edit_form_extra_fields = add_form_extra_fields

    def _normalize_identifier_mapping_fields(self, item):
        item.identifier_map_type = self._coerce_mode(item.identifier_map_type)
        item.identifier_prefix = self._trim_or_none(item.identifier_prefix)
        item.identifier_map_regex = self._trim_or_none(item.identifier_map_regex)
        item.identifier_map_replace = self._trim_or_none(item.identifier_map_replace)
        item.identifier_map_filename = self._trim_or_none(item.identifier_map_filename)

        if item.identifier_map_type == 0:
            item.identifier_map_regex = None
            item.identifier_map_replace = None
            item.identifier_map_filename = None
        elif item.identifier_map_type == 1:
            item.identifier_map_filename = None
        elif item.identifier_map_type == 2:
            item.identifier_map_regex = None
            item.identifier_map_replace = None

    def pre_add(self, item):
        self._normalize_identifier_mapping_fields(item)

    def pre_update(self, item):
        self._normalize_identifier_mapping_fields(item)

"""
    Create your Model based REST API::

    class MyModelApi(ModelRestApi):
        datamodel = SQLAInterface(MyModel)

    appbuilder.add_api(MyModelApi)


    Create your Views::


    class MyModelView(ModelView):
        datamodel = SQLAInterface(MyModel)


    Next, register your Views::


    appbuilder.add_view(
        MyModelView,
        "My View",
        icon="fa-folder-open-o",
        category="My Category",
        category_icon='fa-envelope'
    )
"""

"""
    Application wide 404 error handler
"""


@appbuilder.app.errorhandler(404)
def page_not_found(e):
    return (
        render_template(
            "404.html", base_template=appbuilder.base_template, appbuilder=appbuilder
        ),
        404,
    )


db.create_all()
appbuilder.add_view(CountryView, "List Country", icon="fa-folder-open-o", category="", category_icon="fa-envelope")
appbuilder.add_view(SourceView, "List Source", icon="fa-folder-open-o", category="", category_icon="fa-envelope")
appbuilder.add_api(CountryView)
appbuilder.add_api(SourceView)
