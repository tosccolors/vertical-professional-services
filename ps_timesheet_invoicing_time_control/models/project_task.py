from odoo import fields, models


class ProjectTask(models.Model):
    _inherit = "project.task"

    timesheet_ids = fields.One2many(comodel_name="ps.time.line")

    def _compute_effective_hours(self):
        with self.env["ps.time.line"]._as_analytic_line(self):
            return super()._compute_effective_hours()
