from odoo import models


class HrTimesheetSheet(models.Model):
    _inherit = "hr_timesheet.sheet"

    def action_timesheet_confirm(self):
        self.timesheet_ids.date_time = False
        return super().action_timesheet_confirm()
