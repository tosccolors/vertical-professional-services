from odoo import fields, models


class CrmLeadEmployee(models.Model):
    _name = "crm.lead.employee"
    _description = "CRM lead employee"
    _rec_name = "employee_id"

    lead_id = fields.Many2one("crm.lead", required=True)
    employee_id = fields.Many2one("hr.employee", required=True)
    rate = fields.Monetary()
    currency_id = fields.Many2one(related="lead_id.company_currency")
