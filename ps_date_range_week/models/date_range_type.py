# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class DateRangeType(models.Model):

    _inherit = "date.range.type"

    calender_week = fields.Boolean(string="Is calender week?", readonly=True)
    fiscal_year = fields.Boolean(string="Is Fiscal Year?", readonly=True)

    def unlink(self):
        date_range_type_cw = self.env.ref("ps_date_range_week.date_range_calender_week")
        if date_range_type_cw.id in self.ids:
            raise UserError(_("You can't delete date range type: " "Calender week"))
        return super().unlink()
