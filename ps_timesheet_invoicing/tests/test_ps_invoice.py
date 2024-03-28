from odoo.tests.common import Form, TransactionCase


class TestPsInvoiceBase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.project = self.env.ref("project.project_project_2")
        self.ps_line = self.env.ref(
            "ps_timesheet_invoicing.time_line_demo_user_2023_12_18"
        )
        self.ps_invoice = self._create_ps_invoice()

    def _create_ps_invoice(self, generate=True):
        wizard = (
            self.env["time.line.status"]
            .with_context(
                active_id=self.ps_line[:1].id,
                active_ids=self.ps_line.ids,
                active_model=self.ps_line._name,
            )
            .create({"name": "invoiceable"})
        )
        wizard.ps_invoice_lines()
        ps_invoice = self.env["ps.invoice"].search(
            [("user_total_ids.detail_ids", "in", self.ps_line.ids)]
        )
        if generate:
            ps_invoice.generate_invoice()
        return ps_invoice


class TestPsInvoice(TestPsInvoiceBase):
    def _create_ps_invoice(self, generate=True):
        self.ps_line += self.env.ref(
            "ps_timesheet_invoicing.time_line_demo_user_2023_12_18_mileage"
        )
        return super()._create_ps_invoice(generate=generate)

    def test_01_invoicing(self):
        """Test invocing time lines"""
        ps_invoice = self.ps_invoice
        self.assertTrue(ps_invoice)
        ps_invoice.generate_invoice()
        self.assertTrue(ps_invoice.expense_line_ids)
        self.assertTrue(
            ps_invoice.invoice_id.invoice_line_ids.filtered("ps_analytic_line_ids")
        )
        self.assertEqual(set(self.ps_line.mapped("state")), {"invoice_created"})
        self.assertEqual(ps_invoice.state, "open")
        ps_invoice.invoice_id.target_invoice_amount = 40
        ps_invoice.invoice_id.compute_target_invoice_amount()
        self.assertTrue(
            all(line.discount for line in ps_invoice.invoice_id.invoice_line_ids)
        )
        ps_invoice.invoice_id.action_post()
        self.assertEqual(ps_invoice.state, "invoiced")
        self.assertEqual(set(self.ps_line.mapped("state")), {"invoiced"})
        return ps_invoice

    def test_02_delete_invoice(self):
        ps_invoice = self.test_01_invoicing()
        ps_invoice.delete_invoice()
        self.assertEqual(set(self.ps_line.mapped("state")), {"progress"})
        with Form(ps_invoice) as ps_invoice_form:
            ps_invoice_form.project_id = self.env["project.project"].search(
                [("id", "!=", ps_invoice_form.project_id.id)],
                limit=1,
            )
        self.assertEqual(
            ps_invoice.user_total_ids.detail_ids + ps_invoice.mileage_line_ids,
            self.ps_line,
        )
        ps_invoice.unlink()
        self.assertEqual(set(self.ps_line.mapped("state")), {"invoiceable"})

    def test_03_amend_invoice(self):
        ps_line1, mileage_line = self.ps_line
        ps_line2 = ps_line1.copy({"state": "open"})
        self.ps_line = ps_line2
        ps_invoice = self._create_ps_invoice()
        self.assertEqual(ps_invoice, self.ps_invoice)
        self.assertEqual(ps_invoice.user_total_ids.detail_ids, ps_line1 + ps_line2)
        self.assertEqual(ps_line1.state, "invoice_created")
        self.assertEqual(ps_line2.state, "invoice_created")
        self.assertEqual(mileage_line.state, "invoice_created")
        ps_invoice.invoice_id.action_post()
        self.assertEqual(ps_line1.state, "invoiced")
        self.assertEqual(ps_line2.state, "invoiced")
        self.assertEqual(mileage_line.state, "invoiced")


class TestPsInvoiceGrouped(TestPsInvoiceBase):
    def _create_ps_invoice(self, generate=True):
        self.project.invoice_properties = self.env.ref(
            "project.project_project_1"
        ).invoice_properties
        self.project = self.env.ref("project.project_project_1")
        self.ps_line += self.env.ref(
            "ps_timesheet_invoicing.time_line_demo_user_2023_12_19"
        )
        return super()._create_ps_invoice(generate=generate)

    def test_invoicing(self):
        ps_invoice = self.ps_invoice
        self.assertEqual(len(ps_invoice), 1)
        self.assertEqual(len(ps_invoice.user_total_ids), 2)
        self.assertEqual(
            ps_invoice.period_id.type_id,
            self.env.ref("ps_timesheet_invoicing.date_range_quarter"),
        )


class TestPsInvoiceFixed(TestPsInvoiceBase):
    def _create_ps_invoice(self, generate=True):
        self.project.invoice_properties = self.env.ref(
            "ps_timesheet_invoicing." "project_invoicing_property_fixed_amount"
        )
        self.env["account.analytic.account"].search(
            [
                ("id", "!=", self.project.analytic_account_id.id),
                ("partner_id", "=", self.project.partner_id.id),
            ]
        ).active = False
        self.project.ps_fixed_amount = 4242
        self.project.ps_fixed_hours = 42
        return super()._create_ps_invoice(generate=generate)

    def test_invoicing(self):
        ps_invoice = self.ps_invoice
        invoice = ps_invoice.invoice_id
        self.assertEqual(self.ps_line.state, "invoice_created")
        self.assertEqual(invoice.amount_untaxed, self.project.ps_fixed_amount)
        invoice.action_post()
        invoice.flush()
        self.assertEqual(self.ps_line.state, "invoiced-by-fixed")
        value_tag = self.env.ref(
            "ps_timesheet_invoicing.analytic_tag_fixed_amount_value_difference"
        )
        value_line = invoice.invoice_line_ids.analytic_line_ids.filtered(
            lambda x: x.tag_ids == value_tag
        )
        self.assertTrue(value_line)
        self.env.ref(
            "ps_timesheet_invoicing.analytic_tag_fixed_amount_hours_difference"
        )
        hours_line = invoice.invoice_line_ids.analytic_line_ids.filtered(
            lambda x: x.tag_ids == value_tag
        )
        self.assertEqual(hours_line.unit_amount, 1)
        self.assertEqual(
            invoice.invoice_line_ids.analytic_account_id,
            ps_invoice.account_analytic_ids,
        )
        ps_invoice.delete_invoice()
        self.assertFalse((value_line + hours_line).exists())

    def test_03_amend_invoice(self):
        ps_line1 = self.ps_line
        ps_line2 = ps_line1.copy({"state": "open"})
        self.ps_line = ps_line2
        ps_invoice = self._create_ps_invoice()
        self.assertEqual(ps_invoice, self.ps_invoice)
        self.assertEqual(ps_invoice.user_total_ids.detail_ids, ps_line1 + ps_line2)
        self.assertEqual(ps_line1.state, "invoice_created")
        self.assertEqual(ps_line2.state, "invoice_created")
        ps_invoice.invoice_id.action_post()
        self.assertEqual(ps_line1.state, "invoiced-by-fixed")
        self.assertEqual(ps_line2.state, "invoiced-by-fixed")
