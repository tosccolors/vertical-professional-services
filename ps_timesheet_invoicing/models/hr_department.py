# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrDepartment(models.Model):
    _inherit = "hr.department"

    no_ott_check = fields.Boolean(
        "Disable overtime restrictions", help="No Overtime Check"
    )
    max_overtime_week = fields.Float(
        "Maximum overtime (week)", help="Maximum overtime hours per week", default=8
    )
    max_overtime_day = fields.Float(
        "Maximum overtime (day)", help="Maximum overtime hours per day", default=4
    )
