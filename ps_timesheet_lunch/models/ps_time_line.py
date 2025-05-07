from odoo import fields, models


class PsTimeLine(models.Model):
    _inherit = "ps.time.line"

    had_lunch = fields.Integer()
    had_lunch_boolean = fields.Boolean(
        string="Lunch",
        compute="_compute_had_lunch_boolean",
        inverse="_inverse_had_lunch_boolean",
    )

    def _compute_had_lunch_boolean(self):
        for this in self:
            this.had_lunch_boolean = bool(this.had_lunch)

    def _inverse_had_lunch_boolean(self):
        for this in self:
            this.had_lunch = 1 if this.had_lunch_boolean else 0
