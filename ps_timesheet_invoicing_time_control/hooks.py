from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    cr.execute(
        """
        select
        account_id, company_id, date,
        product_uom_id, product_id, project_id,
        task_id, ticket_id,
        unit_amount, user_id
        from account_analytic_line
        where
        user_id is not null and
        (task_id is not null or ticket_id is not null)
        """
    )
    vals_list = cr.dictfetchall()
    env["ps.time.line"].create(vals_list)
