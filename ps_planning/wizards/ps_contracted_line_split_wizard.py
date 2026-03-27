import json
from datetime import timedelta

from odoo import api, fields, models


class PsContractedLineSplitWizard(models.TransientModel):
    _name = "ps.contracted.line.split.wizard"
    _description = "Split contracted lines"

    contracted_line_ids = fields.Many2many("ps.contracted.line")
    split_on_range_id = fields.Many2one(
        "date.range", string="Starting period", required=True
    )
    split_on_range_id_domain = fields.Char(compute="_compute_split_on_range_id_domain")

    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        if "contracted_line_ids" in fields_list and "contracted_line_ids" not in result:
            lines = self.env["ps.contracted.line"].browse(
                self.env.context.get("active_ids") or []
            )
            result["contracted_line_ids"] = [(6, 0, lines.ids)]
        return result

    @api.depends("contracted_line_ids")
    def _compute_split_on_range_id_domain(self):
        for this in self:
            this.split_on_range_id_domain = json.dumps(
                [
                    (
                        "type_id",
                        "=",
                        self.env.ref("account_fiscal_month.date_range_fiscal_month").id,
                    ),
                    (
                        "date_start",
                        "<=",
                        fields.Date.to_string(
                            min(this.contracted_line_ids.mapped("date_to"))
                        ),
                    ),
                    (
                        "date_end",
                        ">=",
                        fields.Date.to_string(
                            max(this.contracted_line_ids.mapped("date_from"))
                        ),
                    ),
                    (
                        "date_start",
                        ">",
                        fields.Date.to_string(
                            min(this.contracted_line_ids.mapped("date_from"))
                        ),
                    ),
                ]
            )

    def action_split_contracted_lines(self):
        for contracted_line in self.contracted_line_ids:
            new_line = contracted_line.copy(
                {"date_from": self.split_on_range_id.date_start}
            )
            contracted_line.planning_line_ids.filtered(
                lambda x: x.range_id.date_start >= self.split_on_range_id.date_start
            ).contracted_line_id = new_line
            original_data = contracted_line.read(["date_to", "days"])[0]
            contracted_line.write(
                {
                    "date_to": self.split_on_range_id.date_start - timedelta(days=1),
                    "days": original_data["days"]
                    * (
                        self.split_on_range_id.date_start
                        - timedelta(days=1)
                        - contracted_line.date_from
                    )
                    / (contracted_line.date_to - contracted_line.date_from),
                }
            )
            contracted_line._onchange_days()
            new_line.write(
                {
                    "date_to": original_data["date_to"],
                    "days": original_data["days"] - contracted_line.days,
                }
            )
            new_line._onchange_days()
