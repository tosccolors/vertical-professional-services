from odoo.tests.common import Form, TransactionCase


class TestPsCrm(TransactionCase):
    def setUp(self):
        super().setUp()
        self.lead = self.env.ref("crm.crm_case_10")

    def test_crm_lead_form(self):
        """Run onchanges on crm lead form"""
        partner = self.env.ref("ps_crm.lead_main_partner")
        partner_contact = self.env.ref("ps_crm.lead_main_partner_contact")
        operating_unit = self.env.ref("operating_unit.main_operating_unit")
        with Form(self.lead) as lead_form:
            lead_form.partner_id = partner
            self.assertEqual(lead_form.partner_contact_id, partner_contact)
            self.assertEqual(lead_form.contact_name, partner_contact.name)
            lead_form.partner_id = partner_contact
            self.assertFalse(lead_form.partner_contact_id)
            self.assertFalse(lead_form.contact_name)
            lead_form.operating_unit_id = operating_unit
            lead_form.expected_revenue = 42000
            lead_form.probability = 50
            lead_form.start_date = "2024-01-01"
            lead_form.end_date = "2024-06-30"
            with lead_form.monthly_revenue_ids.edit(1) as revenue_form:
                revenue_form.expected_revenue = 1000
            lead_form.probability = 100
        self.assertTrue(self.lead.monthly_revenue_split_ids)
        february = self.lead.monthly_revenue_ids.filtered(lambda x: x.date.month == 2)
        self.assertFalse(february.computed_line)
        self.assertEqual(february.expected_revenue, 1000)
        self.assertEqual(
            self.lead.expected_revenue,
            self.lead.company_currency.round(
                sum(self.lead.monthly_revenue_ids.mapped("expected_revenue"))
            ),
        )
        self.assertFalse(self.lead.show_recalculate_total_button)
        february.expected_revenue = 999
        self.assertTrue(self.lead.show_recalculate_total_button)
        self.lead.recalculate_total()
        self.assertFalse(self.lead.show_recalculate_total_button)
        self.assertEqual(self.lead.expected_revenue, 41999)
