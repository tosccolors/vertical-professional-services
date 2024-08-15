from odoo import fields, models


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    timesheet_ids = fields.One2many(comodel_name="ps.time.line")
