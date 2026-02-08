from odoo import api, models


class PsTimeLine(models.Model):
    _inherit = "ps.time.line"

    @api.model_create_multi
    def create(self, vals_list):
        result = super().create(vals_list)
        result._ensure_task()
        return result

    def _ensure_task(self):
        for this in self:
            standard_task = this.ticket_id.project_id.standard_task_id
            if not this.task_id and standard_task:
                this.task_id = standard_task
                this.ticket_id.task_id = standard_task
