# Copyright 2018 - 2023 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class Lead(models.Model):
    _inherit = ["ps.crm.department.mixin", "crm.lead"]
    _name = "crm.lead"

    start_date = fields.Date("Start Date")
    end_date = fields.Date("End Date")
    project_id = fields.Many2one("project.project", string="Project")
    subject = fields.Char("Subject")
    operating_unit_id = fields.Many2one(
        "operating.unit", string="Operating Unit", required=True
    )
    contract_signed = fields.Boolean(string="Contract Signed")
    department_id = fields.Many2one("hr.department", string="Business line")
    expected_duration = fields.Integer(string="Expected Duration")
    monthly_revenue_ids = fields.One2many(
        "crm.monthly.revenue", "lead_id", string="Monthly Revenue"
    )
    sum_monthly_revenue = fields.Float(compute="_compute_sum_monthly_revenue")
    show_recalculate_total_button = fields.Boolean(
        compute="_compute_show_recalculate_total_button"
    )
    latest_revenue_date = fields.Date(
        "Latest Revenue Date", compute="_compute_latest_revenue_date", store=True
    )
    partner_contact_id = fields.Many2one("res.partner", string="Contact Person")
    monthly_revenue_split_ids = fields.One2many(
        "crm.monthly.revenue.split",
        "lead_id",
        string="Revenue split",
    )
    user_id = fields.Many2one(string="Owner")
    user_name = fields.Char(related="user_id.name")
    lead_employee_ids = fields.One2many(
        "crm.lead.employee", "lead_id", string="Employees"
    )
    first_employee_name = fields.Char(compute="_compute_first_employee_name")
    docs_link = fields.Char("Link to documentation")

    @api.depends("monthly_revenue_ids.date")
    def _compute_latest_revenue_date(self):
        for this in self:
            this.latest_revenue_date = this.monthly_revenue_ids[-1:].date

    @api.depends(
        "monthly_revenue_ids.expected_revenue", "monthly_revenue_ids.percentage"
    )
    def _compute_sum_monthly_revenue(self):
        for this in self:
            this.sum_monthly_revenue = this.company_currency.round(
                sum(self.monthly_revenue_ids.mapped("expected_revenue"))
            )

    @api.depends("expected_revenue", "sum_monthly_revenue")
    def _compute_show_recalculate_total_button(self):
        for this in self:
            this.show_recalculate_total_button = (
                this.expected_revenue != this.sum_monthly_revenue
            )

    @api.depends("lead_employee_ids")
    def _compute_first_employee_name(self):
        for this in self:
            this.first_employee_name = this.lead_employee_ids[:1].employee_id.name

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        user = self.env.user
        res.update({"operating_unit_id": user.default_operating_unit_id.id})
        return res

    @api.model_create_multi
    def create(self, vals_list):
        result = super().create(vals_list)
        for this in result:
            this.update_monthly_revenue()
        return result

    def write(self, vals):
        result = super().write(vals)
        for this in self:
            this.stage_id_changed()
        return result

    def _get_split_operating_units(self):
        return self.env["operating.unit"].search(
            [
                ("company_id", "=", self.operating_unit_id.company_id.id),
            ]
        )

    def _date_diff_days(self, date_start, date_end):
        """
        Allow other modules to ie use work days instead of calendar days
        """
        return (date_end - date_start).days + 1

    def update_monthly_revenue(self):
        self.ensure_one()
        manual_lines = []
        sd = self.start_date
        ed = self.end_date
        if not sd or not ed:
            return

        total_expected_revenue = self.expected_revenue
        manual_days = 0

        for line in self.monthly_revenue_ids.filtered(lambda x: not x.computed_line):
            manual_lines.append(
                (
                    0,
                    0,
                    {
                        "date": line.date,
                        "expected_revenue": line.expected_revenue,
                        "percentage": line.percentage,
                    },
                )
            )
            total_expected_revenue -= line.expected_revenue
            manual_days += self._date_diff_days(
                line.month.date_start, line.month.date_end
            )

        month_end_date = (sd + relativedelta(months=1)).replace(day=1) - timedelta(
            days=1
        )
        if month_end_date > ed:
            month_end_date = ed
        monthly_revenues = []
        total_days = self._date_diff_days(sd, ed) - manual_days

        while True:
            if not any(
                vals["date"].month == month_end_date.month
                for _dummy, _dummy, vals in manual_lines
            ):
                days_per_month = self._date_diff_days(sd, month_end_date)
                expected_revenue_per_month = self.company_currency.round(
                    total_expected_revenue * days_per_month / total_days
                )
                monthly_revenues_vals = {
                    "date": month_end_date,
                    "latest_revenue_date": month_end_date.replace(day=1)
                    - timedelta(days=1),
                    "expected_revenue": expected_revenue_per_month,
                    "computed_line": True,
                    "percentage": self.probability,
                }
                self.env["crm.monthly.revenue"].new(monthly_revenues_vals)
                monthly_revenues.append(
                    (
                        0,
                        0,
                        monthly_revenues_vals,
                    )
                )

            sd = month_end_date + timedelta(days=1)
            month_end_date = (sd + relativedelta(months=1)).replace(day=1) - timedelta(
                days=1
            )
            if sd > ed:
                break
            if month_end_date > ed:
                month_end_date = ed

        difference_amount = self.expected_revenue - (
            sum(
                vals["expected_revenue"]
                for _dummy, _dummy, vals in (monthly_revenues + manual_lines)
            )
        )
        if difference_amount and monthly_revenues:
            monthly_revenues[0][2]["expected_revenue"] += difference_amount

        self.monthly_revenue_ids = [(5, 0, [])] + monthly_revenues + manual_lines
        self.monthly_revenue_split_ids = [(5, 0, [])] + [
            (
                0,
                0,
                {
                    "month_id": monthly_revenue.month.id,
                    "operating_unit_id": ou.id,
                    "percentage": 100 if ou == self.operating_unit_id else 0,
                    "expected_revenue": monthly_revenue.expected_revenue,
                },
            )
            for monthly_revenue in self.monthly_revenue_ids
            for ou in self._get_split_operating_units()
        ]

    def stage_id_changed(self):
        for this in self:
            this.monthly_revenue_ids.percentage = this.probability

            if this.stage_id.popup_requirements and this.stage_id.requirements:
                text = this.stage_id.requirements
                self.env.user.notify_info(
                    message=text.replace("\n", "<br/>"), sticky=True
                )

    def recalculate_total(self):
        for this in self:
            this.expected_revenue = this.sum_monthly_revenue

    @api.onchange("start_date", "end_date", "expected_revenue", "probability")
    def onchange_date(self):
        if (
            self.start_date
            and self.end_date
            and not self._origin.end_date
            and self.start_date > self.end_date
        ):
            self.end_date = self.start_date
        self.update_monthly_revenue()

    @api.onchange("operating_unit_id")
    def onchange_operating_unit_id(self):
        for record in self.monthly_revenue_split_ids:
            record.percentage = (
                100 if record.operating_unit_id == self.operating_unit_id else 0
            )

    @api.onchange("partner_id")
    def onchange_partner(self):
        values = {}
        if not self.partner_id:
            return values

        part = self.partner_id
        addr = self.partner_id.address_get(["contact"])

        if part.type == "contact":
            contact = self.env["res.partner"].search(
                [
                    ("is_company", "=", False),
                    ("type", "=", "contact"),
                    ("parent_id", "=", part.id),
                ]
            )
            if len(contact) >= 1:
                contact_id = contact[0]
            else:
                contact_id = False
        elif addr["contact"] == part.id:
            contact_id = False
        else:
            contact_id = addr["contact"]

        values.update({"partner_contact_id": contact_id, "partner_name": part.name})

        if part.industry_id:
            values.update(
                {
                    "industry_id": part.industry_id,
                    "secondary_industry_ids": [(6, 0, part.secondary_industry_ids.ids)],
                }
            )
        else:
            values.update(
                {
                    "industry_id": False,
                    "secondary_industry_ids": False,
                }
            )
        return {"value": values}

    @api.onchange("partner_contact_id")
    def onchange_contact(self):
        if self.partner_contact_id:
            partner = self.partner_contact_id
            values = {
                "contact_name": partner.name,
                "title": partner.title.id,
                "email_from": partner.email,
                "phone": partner.phone,
                "mobile": partner.mobile,
                "function": partner.function,
            }
        else:
            values = {
                "contact_name": False,
                "title": False,
                "email_from": False,
                "phone": False,
                "mobile": False,
                "function": False,
            }
        return {"value": values}

    @api.onchange("monthly_revenue_split_ids")
    def _onchange_monthly_revenue_split_ids(self):
        try:
            self._check_monthly_revenue_split_ids()
        except ValidationError as exception:
            return {
                "warning": {
                    "message": exception.args[0],
                }
            }

    @api.constrains("start_date", "end_date")
    def _check_dates(self):
        start_date = self.start_date
        end_date = self.end_date
        if (start_date and end_date) and (start_date > end_date):
            raise ValidationError(_("End date should be greater than start date."))

    @api.constrains("monthly_revenue_split_ids")
    def _check_monthly_revenue_split_ids(self):
        for this in self:
            by_month = {
                revenue_split.month_id: sum(
                    rs.percentage
                    for rs in this.monthly_revenue_split_ids.filtered(
                        lambda x: x.month_id == revenue_split.month_id
                    )
                )
                for revenue_split in this.monthly_revenue_split_ids
            }
            if any(percentage > 100 for percentage in by_month.values()):
                raise ValidationError(_("Total percentage should be equal to 100"))
