# Copyright 2018 - 2023 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.tools.misc import format_date


class CrmMonthlyRevenue(models.Model):
    _inherit = "ps.crm.department.mixin"
    _name = "crm.monthly.revenue"
    _description = "Monthly revenue"
    _rec_name = "month"
    _order = "date asc"

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        ctx = self.env.context.copy()
        if "default_lead_id" in ctx:
            crm_obj = self.env["crm.lead"].browse(ctx["default_lead_id"])
            latest_revenue_date = (
                crm_obj.latest_revenue_date
                or crm_obj.start_date
                or datetime.now().strftime("%Y-%m-%d")
            )
            if latest_revenue_date:
                upcoming_month_end_date = (
                    latest_revenue_date + relativedelta(months=2)
                ).replace(day=1) - timedelta(days=1)
                res["date"] = upcoming_month_end_date
                res["latest_revenue_date"] = latest_revenue_date
        return res

    date = fields.Date("Date", required=True)
    year = fields.Many2one(
        "date.range", string="Year", compute="_compute_date_fields", store=True
    )
    month = fields.Many2one(
        "date.range", string="Month", compute="_compute_date_fields", store=True
    )
    no_of_days = fields.Char(
        string="Work days", compute="_compute_date_fields", store=True
    )
    latest_revenue_date = fields.Date("Latest Revenue Date")
    weighted_revenue = fields.Monetary(
        "Weighted Revenue", compute="_compute_weighted_revenue", store=True
    )
    expected_revenue = fields.Monetary("Expected Revenue", required=True)
    percentage = fields.Float(string="Probability")
    lead_id = fields.Many2one(
        "crm.lead", string="Opportunity", ondelete="cascade", required=True
    )
    currency_id = fields.Many2one(
        related="lead_id.company_currency",
    )
    user_id = fields.Many2one(
        related="lead_id.user_id",
    )
    computed_line = fields.Boolean(string="Computed line")
    project_id = fields.Many2one(
        "project.project", related="lead_id.project_id", string="Project", store=True
    )
    partner_id = fields.Many2one(
        "res.partner", related="lead_id.partner_id", string="Customer", store=True
    )
    industry_id = fields.Many2one(
        "res.partner.industry",
        related="lead_id.industry_id",
        string="Main Sector",
        store=True,
    )
    department_id = fields.Many2one(
        "hr.department", related="lead_id.department_id", string="Practice", store=True
    )
    operating_unit_id = fields.Many2one(
        "operating.unit",
        related="lead_id.operating_unit_id",
        store=True,
    )

    @api.depends("expected_revenue", "percentage", "lead_id.probability")
    def _compute_weighted_revenue(self):
        for this in self:
            this.weighted_revenue = this.expected_revenue * this.percentage / 100

    @api.onchange("lead_id")
    def onchange_lead_id(self):
        self.percentage = self.lead_id.probability

    @api.onchange("date", "expected_revenue")
    def onchange_editable_fields(self):
        self.computed_line = False

    @api.depends("date")
    def _compute_date_fields(self):
        date_range = self.env["date.range"]
        for this in self:
            company_id = this.lead_id.company_id.id or this.env.user.company_id.id
            common_domain = [
                ("date_start", "<=", this.date),
                ("date_end", ">=", this.date),
                "|",
                ("company_id", "=", company_id),
                ("company_id", "=", False),
            ]
            month = date_range.search(
                common_domain + [("type_id.fiscal_month", "=", True)],
                order="company_id asc",
                limit=1,
            )
            this.month = month.id
            year = date_range.search(
                common_domain + [("type_id.fiscal_year", "=", True)],
                order="company_id asc",
                limit=1,
            )
            this.year = year.id

            days = self.env["crm.lead"]._date_diff_days(
                this.date.replace(day=1), this.date
            )
            this.no_of_days = _("%d days (1 - %s %s)") % (
                days,
                this.date.day,
                format_date(self.env, this.date, date_format="MMMM"),
            )
