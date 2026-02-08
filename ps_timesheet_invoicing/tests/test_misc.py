from odoo.exceptions import ValidationError
from odoo.tests.common import Form, TransactionCase


class TestMisc(TransactionCase):
    def setUp(self):
        super().setUp()
        self.project = self.env.ref("project.project_project_2")
        self.ps_line = self.env.ref(
            "ps_timesheet_invoicing.time_line_demo_user_2023_12_18"
        )
        self.ps_line_mileage = self.env.ref(
            "ps_timesheet_invoicing.time_line_demo_user_2023_12_18_mileage"
        )

    def test_change_chargecode(self):
        wizard = (
            self.env["change.chargecode"]
            .with_context(
                active_id=self.ps_line.id,
                active_ids=self.ps_line.ids,
                active_model=self.ps_line._name,
            )
            .create({})
        )
        with Form(wizard) as wizard_form:
            project = self.env["project.project"].search(
                [("id", "!=", self.ps_line.project_id.id)],
                limit=1,
            )
            wizard_form.project_id = project
            wizard_form.task_id = project.task_ids[:1]

        line_max = self.env["ps.time.line"].search([], limit=1, order="id desc")
        wizard.post()

        reverse_line, new_line = self.env["ps.time.line"].search(
            [("id", ">", line_max.id)], order="id asc"
        )
        self.assertEqual(self.ps_line.unit_amount, -reverse_line.unit_amount)

    def test_invoicing_properties(self):
        """Test invoicing properties form"""
        km_line = self.ps_line.copy(
            {
                "product_uom_id": self.env.ref("uom.product_uom_km").id,
                "non_invoiceable_mileage": True,
            }
        )
        with Form(self.project.invoice_properties) as properties_form:
            properties_form.invoice_mileage = True
        self.assertFalse(km_line.non_invoiceable_mileage)

    def test_task_user(self):
        """Test creating task.user objects"""
        task_user = self.env.ref("ps_timesheet_invoicing.task_user_task_11")
        hour_amount = self.ps_line.amount
        mileage_amount = self.ps_line_mileage.amount
        with self.assertRaises(ValidationError):
            task_user.copy({"fee_rate": 420})
        task_user += task_user[:1].copy({"from_date": "2023-01-02", "fee_rate": 420})
        task_user += task_user[:1].copy({"from_date": "2023-01-03", "fee_rate": 4200})
        task_user._compute_last_valid_fee_rate()
        self.assertEqual(task_user.filtered("last_valid_fee_rate"), task_user[-1:])
        self.env.clear()
        self.assertEqual(hour_amount * 100, self.ps_line.amount)
        self.assertEqual(mileage_amount, self.ps_line_mileage.amount)

    def test_odometer(self):
        """Test odometer recomputation works"""
        vehicle = self.env.ref("fleet.vehicle_1")
        self.env["fleet.vehicle.odometer"].search([]).unlink()
        odometer20230601 = self.env["fleet.vehicle.odometer"].create(
            {
                "vehicle_id": vehicle.id,
                "value_update": 42,
                "date": "2023-06-01",
            }
        )
        self.assertEqual(odometer20230601.value_period, 42)
        odometer20230101 = odometer20230601.copy(
            {"date": "2023-01-01", "value_period_update": 10}
        )
        self.assertEqual(odometer20230601.value, 52)
        odometer20230701 = odometer20230601.copy(
            {"date": "2023-07-01", "value_period_update": 20}
        )
        self.assertEqual(odometer20230701.value, 72)
        odometer20230101.value = 8
        self.assertEqual(odometer20230701.value, 70)
        odometer20230101.unlink()
        self.assertEqual(odometer20230701.value, 62)

    def test_status_time_report(self):
        """Test that the status report works"""
        self.env["hr.employee"].search([]).write(
            {"official_date_of_employment": "2022-12-31"}
        )
        self.env["hr.employee"].flush_model()
        self.env["status.time.report"].with_user(
            self.env.ref("base.user_admin")
        ).search([]).read([])

    def test_vehicle_driver(self):
        """Test the constraints of vehicle driver records"""
        vehicle1 = self.env.ref("fleet.vehicle_1")
        vehicle1.fleet_vehicle_driver_ids.unlink()
        vehicle2 = vehicle1.copy()
        driver1 = self.env["res.partner"].create({"name": "driver 1"})

        vehicle1.write(
            {
                "fleet_vehicle_driver_ids": [
                    (
                        0,
                        0,
                        {
                            "driver_id": driver1.id,
                            "date_start": "2024-07-29",
                        },
                    )
                ],
            }
        )
        with self.assertRaisesRegex(
            ValidationError, "open-ended"
        ), self.env.cr.savepoint():
            vehicle1.write(
                {
                    "fleet_vehicle_driver_ids": [
                        (
                            0,
                            0,
                            {
                                "driver_id": driver1.id,
                                "date_start": "2024-08-05",
                            },
                        )
                    ],
                }
            )
        with self.assertRaisesRegex(
            ValidationError, "overlapping"
        ), self.env.cr.savepoint():
            vehicle1.write(
                {
                    "fleet_vehicle_driver_ids": [
                        (
                            0,
                            0,
                            {
                                "driver_id": driver1.id,
                                "date_start": "2024-08-05",
                                "date_end": "2024-08-12",
                            },
                        )
                    ],
                }
            )
        with self.assertRaisesRegex(
            ValidationError, "multiple"
        ), self.env.cr.savepoint():
            vehicle2.write(
                {
                    "fleet_vehicle_driver_ids": [
                        (
                            0,
                            0,
                            {
                                "driver_id": driver1.id,
                                "date_start": "2024-07-22",
                                "date_end": "2024-08-05",
                            },
                        )
                    ],
                }
            )
        vehicle2.write(
            {
                "fleet_vehicle_driver_ids": [
                    (
                        0,
                        0,
                        {
                            "driver_id": driver1.id,
                            "date_start": "2024-07-22",
                            "date_end": "2024-07-29",
                        },
                    )
                ],
            }
        )
        with self.assertRaisesRegex(ValidationError, "Monday"):
            vehicle2.fleet_vehicle_driver_ids.date_start = "2024-07-21"
        self.assertEqual(
            self.env["fleet.vehicle"].search([("driver_id", "=", driver1.id)]),
            vehicle1,
        )
        vehicle1.write({"driver_id": False})
        self.assertEqual(len(vehicle1.fleet_vehicle_driver_ids), 1)
        self.assertFalse(vehicle1.driver_id)

    def test_recompute_time_line(self):
        """Test recomputation of time lines"""
        task = self.env.ref("project.project_1_task_1")
        time_line = self.env.ref(
            "ps_timesheet_invoicing.time_line_demo_user_2023_12_18"
        )
        line_fee_rate = time_line.line_fee_rate
        task_user_data = task.task_user_ids.copy_data()[0]

        task.task_user_ids.fee_rate *= 2
        self.assertEqual(time_line.line_fee_rate, 2 * line_fee_rate)

        standard_task = self.env["project.task"].create(
            {
                "name": "standard task",
                "project_id": task.project_id.id,
                "standard": True,
                "task_user_ids": [(0, 0, task_user_data)],
            }
        )
        task.task_user_ids.unlink()
        self.assertEqual(time_line.line_fee_rate, line_fee_rate)

        time_line.user_id.employee_id.active = False
        new_product = standard_task.task_user_ids.product_id.copy()
        task.write(
            {
                "task_user_ids": [
                    (
                        0,
                        0,
                        dict(
                            task_user_data,
                            fee_rate=2 * line_fee_rate,
                            product_id=new_product.id,
                        ),
                    )
                ],
            }
        )
        task.flush()
        self.assertEqual(time_line.line_fee_rate, 2 * line_fee_rate)
        self.assertEqual(time_line.product_id, new_product)
