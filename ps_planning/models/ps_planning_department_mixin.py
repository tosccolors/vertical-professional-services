# Copyright 2024 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

import json

from lxml import etree

from odoo import api, models


class PsPlanningDepartmentMixin(models.AbstractModel):
    _name = "ps.planning.department.mixin"
    _description = "Mixin to inject department filters in the search view"

    @api.model
    def _fields_view_get(
        self, view_id=None, view_type="form", toolbar=False, submenu=False
    ):
        result = super()._fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu
        )
        if view_type == "search":
            arch = etree.fromstring(result["arch"])
            for node in arch.xpath("//search"):
                departments = (
                    self.env["hr.department"]
                    .search([])
                    .filtered(
                        lambda x: self.env["project.project"].search_count(
                            [
                                ("department_id", "=", x.id),
                            ]
                        )
                    )
                )
                field_names = [
                    field_name
                    for field_name in ("project_id", "employee_id")
                    if field_name in self._fields
                ]
                for field_name in field_names:
                    field = self.env["ir.model.fields"]._get(self._name, field_name)
                    etree.SubElement(
                        node,
                        "separator",
                    )
                    prefix = ""
                    if field_name != "project_id":
                        prefix = "%s: " % field.field_description
                    for department in departments:
                        etree.SubElement(
                            node,
                            "filter",
                            attrib={
                                "string": prefix
                                + (
                                    department.name
                                    if not (
                                        departments.filtered(
                                            lambda x: x.id != department.id
                                            and x.name == department.name
                                        )
                                    )
                                    else "%s (%s)"
                                    % (
                                        department.name,
                                        department.parent_id.name
                                        or department.company_id.name,
                                    )
                                ),
                                "domain": json.dumps(
                                    [
                                        (
                                            "%s.department_id" % field_name,
                                            "=",
                                            department.id,
                                        ),
                                    ]
                                ),
                            },
                        )

            result["arch"] = etree.tostring(arch)
        return result
