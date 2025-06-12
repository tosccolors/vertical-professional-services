from odoo import fields, models


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    timesheet_ids = fields.One2many(comodel_name="ps.time.line")

    def button_create_task(self):
        for this in self:
            if this.task_id:
                continue
            this.task_id = self.env["project.task"].create(
                {
                    "name": this.name,
                    "project_id": this.project_id.id,
                    "user_ids": [fields.Command.set(this.user_id.ids)],
                    "partner_id": this.partner_id.id,
                    "planned_hours": this.planned_hours,
                }
            )
            this.timesheet_ids.task_id = this.task_id
