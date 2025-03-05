from odoo import api, fields, models


class CrmMonthlyRevenueSplit(models.Model):
    _name = "crm.monthly.revenue.split"
    _description = "Revenue split"

    lead_id = fields.Many2one(
        "crm.lead", string="Opportunity", required=True, ondelete="cascade"
    )
    department_id = fields.Many2one(related="lead_id.department_id", store=True)
    partner_id = fields.Many2one(related="lead_id.partner_id", store=True)
    project_id = fields.Many2one(related="lead_id.project_id", store=True)
    user_id = fields.Many2one(related="lead_id.user_id", store=True)
    name = fields.Char(related="lead_id.name", store=True)
    lead_operating_unit_id = fields.Many2one("lead_id.operating_unit_id", store=True)
    currency_id = fields.Many2one("lead_id.company_currency", store=True)
    month_id = fields.Many2one("date.range", string="Month", required=True)
    operating_unit_id = fields.Many2one("operating.unit")
    percentage = fields.Float()
    revenue = fields.Monetary(compute="_compute_revenue", store=True)
    expected_revenue = fields.Monetary(compute="_compute_revenue", store=True)

    @api.depends("percentage", "month_id")
    def _compute_revenue(self):
        CrmMonthlyRevenue = self.env["crm.monthly.revenue"]
        for this in self:
            this.expected_revenue = sum(
                CrmMonthlyRevenue.search(
                    [
                        ("lead_id", "=", this.lead_id.id),
                        ("month", "=", this.month_id.id),
                    ]
                ).mapped("expected_revenue")
            )
            this.revenue = this.expected_revenue * this.percentage / 100
