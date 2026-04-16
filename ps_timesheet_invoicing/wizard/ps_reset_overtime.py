from datetime import timedelta

from odoo import _, fields, models

from ..models.ps_time_line import OVERTIME_SENTINEL


class PsResetOvertime(models.TransientModel):
    _name = "ps.reset.overtime"
    _description = "Reset overtime for employee"

    date = fields.Date(
        "Reset date",
        default=fields.Date.today().replace(month=1, day=1) - timedelta(days=1),
        required=True,
    )

    def action_reset_overtime(self):
        PsTimeLine = self.env["ps.time.line"]
        OvertimeBalanceReport = self.env["overtime.balance.report"]
        employees = self.env["hr.employee"].browse(
            self.env.context.get("active_ids", [])
        )
        uom_hour = self.env.ref("uom.product_uom_hour")
        created_lines = PsTimeLine.browse([])
        for overtime_data in OvertimeBalanceReport.read_group(
            [
                ("date", "<=", self.date),
                ("user_id.employee_ids", "in", employees.ids),
            ],
            ["user_id"],
            ["user_id", "overtime_balanced"],
            orderby="date",
            lazy=False,
        ):
            if not overtime_data["overtime_balanced"]:
                continue
            user_id = overtime_data["user_id"][0]
            ps_time_line = PsTimeLine.search(
                [
                    (
                        "id",
                        "in",
                        OvertimeBalanceReport.search(overtime_data["__domain"]).ids,
                    ),
                    ("project_id.overtime_hrs", "=", True),
                ],
                limit=1,
            ) or PsTimeLine.search(
                [("user_id", "=", user_id), ("project_id.overtime_hrs", "=", True)],
                limit=1,
            )
            overtime_project = ps_time_line.project_id or self.env[
                "project.project"
            ].search([("project_id.overtime_hrs", "=", True)], limit=1)
            overtime_project_task = ps_time_line.task_id
            created_lines += PsTimeLine.with_context(
                ps_timesheet_invoicing_overtime=OVERTIME_SENTINEL
            ).create(
                {
                    "name": _("Reset Overtime"),
                    "account_id": overtime_project.analytic_account_id.id,
                    "project_id": overtime_project.id,
                    "task_id": overtime_project_task.id,
                    "date": self.date,
                    "unit_amount": -overtime_data["overtime_balanced"],
                    "product_uom_id": uom_hour.id,
                    "ot": True,
                    "user_id": user_id,
                }
            )

        return {
            "type": "ir.actions.act_window",
            "name": _("Created lines"),
            "res_model": PsTimeLine._name,
            "views": [(False, "tree")],
            "domain": [("id", "in", created_lines.ids)],
        }
