# Copyright 2018 The Open Source Company ((www.tosc.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError
import calendar
from contextlib import contextmanager


class TimeLine(models.Model):
    _name = 'ps.time.line'
    _inherit = 'account.analytic.line'
    _description = 'Professional Services Time Line'
    _order = 'date desc'
    _check_company_auto = True

    @api.depends('project_id.chargeable',
                 'project_id.correction_charge',
                 'project_id.user_id',
                 'project_id.invoice_properties.expenses',
                 'project_id.standard_task_id.task_user_ids',
                 'account_id',
                 'unit_amount',
                 'planned',
                 'date',
                 'task_id',
                 'user_id',
                 'task_id.task_user_ids',
                 'task_user_id.from_date',
                 'task_user_id.product_id',
                 'task_user_id.fee_rate',
                 )
    def _compute_time_line(self):
        uom_hrs = self.env.ref("uom.product_uom_hour").id
        for line in self.filtered(lambda line: line.task_id and line.product_uom_id.id == uom_hrs):
            # all ps_time lines need a project_operating_unit_id and
            # for all ps_time lines day_name, week_id and month_id are computed
            date = line.date
            line.project_operating_unit_id = line.account_id.operating_unit_ids[:1]
            line.day_name = '%s (%s)' % (
                date.strftime("%m/%d/%Y"),
                date.strftime('%a'),
            )
            line.week_id = line.find_daterange_week(date)
            line.month_id = var_month_id = line.find_daterange_month(date)
            # only when project_id these fields are computed
            if line.project_id:
                line.chargeable = line.project_id.chargeable
                line.correction_charge = line.project_id.correction_charge
                line.project_mgr = line.project_id.user_id or False
                if line.project_id.invoice_properties:
                    line.expenses = line.project_id.invoice_properties.expenses
            else:
                line.project_mgr = line.account_id.project_ids.user_id or False
            task = line.task_id
            user = line.user_id
            date = line.date
            # only if task_id the remaining fields are computed
            if task and user:
                uou = user._get_operating_unit_id()
                if uou:
                    line.operating_unit_id = uou
                    if line.planned:
                        line.planned_qty = line.unit_amount
                        line.actual_qty = 0.0
                    else:
                        if line.month_of_last_wip:
                            line.wip_month_id = line.month_of_last_wip
                        else:
                            line.wip_month_id = var_month_id
                        if line.product_uom_id.id == uom_hrs:
                            if date and line.state in ['new',
                                                       'draft',
                                                       'open',
                                                       'delayed',
                                                       'invoiceable',
                                                       'progress',
                                                       're_confirmed', ]:
                                task_user = self.env['task.user'].get_task_user_obj(task.id, user.id, date)[:1]
                                if task_user:
                                    line.task_user_id = task_user
                                # check standard task for fee earners
                                else:
                                    # project_id = self.env['project.task'].browse(task.id).project_id
                                    if line.project_id:
                                        standard_task = line.project_id.standard_task_id
                                    if len(standard_task) == 1:
                                        line.task_user_id = self.env['task.user'].get_task_user_obj(standard_task.id,
                                                                                                    user.id,
                                                                                                    date) or False
                                line.line_fee_rate = line.get_fee_rate()[0]
                                line.amount = line.get_fee_rate_amount()
                                line.product_id = line.get_task_user_product()
                        line.actual_qty = line.unit_amount
                        line.planned_qty = 0.0

    @api.model
    def _default_user(self):
        return self.env.context.get('user_id', self.env.user.id)

    def find_daterange_week(self, date):
        """
        try to find a date range with type 'week'
        with @param:date contained in its date_start/date_end interval
        """
        date_range_type_cw_id = self.env.ref(
            'ps_date_range_week.date_range_calender_week').id
        s_args = [
            ('type_id', '=', date_range_type_cw_id),
            ('date_start', '<=', date),
            ('date_end', '>=', date),
            '|',
            ('company_id', '=', self.company_id.id),
            ('company_id', '=', False),
        ]
        date_range = self.env['date.range'].search(s_args,
                                                   limit=1,
                                                   order='company_id asc')
        return date_range

    def find_daterange_month(self, date):
        """
        try to find a date range with type 'month'
        with @param:date contained in its date_start/date_end interval
        """
        date_range_type_fm_id = self.env.ref(
            'account_fiscal_month.date_range_fiscal_month').id

        s_args = [
            ('type_id', '=', date_range_type_fm_id),
            ('date_start', '<=', date),
            ('date_end', '>=', date),
            '|',
            ('company_id', '=', self.company_id.id),
            ('company_id', '=', False),
        ]
        date_range = self.env['date.range'].search(
            s_args,
            limit=1,
            order='company_id asc'
        )
        return date_range

    @api.model
    def default_get(self, fields):
        context = self._context
        res = super().default_get(fields)
        if 'planning_lines' in context:
            project = self.env['project.project']
            project_id = context.get('default_project_id', project)
            task_id = context.get('default_task_id', False)
            project = project.browse(project_id)
            account_id = project.analytic_account_id
            operating_unit_id = account_id.operating_unit_ids and account_id.operating_unit_ids[0] or False
            res.update({'operating_unit_id':operating_unit_id, 'name': '/', 'task_id': task_id})
        if 'timesheet_date_start' in context:
            date = context.get('timesheet_date_start')
            res.update({'date': date})
        return res

    kilometers = fields.Integer(
        'Kilometers'
    )
    non_invoiceable_mileage = fields.Boolean(
        string='Invoice Mileage',
        store=True
    )
    ref_id = fields.Many2one(
        'ps.time.line',
        string='Reference'
    )
    week_id = fields.Many2one(
        'date.range',
        compute=_compute_time_line,
        string='Week',
        store=True,
    )
    month_id = fields.Many2one(
        'date.range',
        compute=_compute_time_line,
        string='Month',
        store=True,
    )
    wip_month_id = fields.Many2one(
        'date.range',
        compute=_compute_time_line,
        store=True,
        string="Month of PS Time Line or last Wip Posting"
    )
    month_of_last_wip = fields.Many2one(
        "date.range",
        "Month Of Next Reconfirmation"
    )
    operating_unit_id = fields.Many2one(
        'operating.unit',
        compute=_compute_time_line,
        string='Operating Unit',
        store=True
    )
    project_operating_unit_id = fields.Many2one(
        'operating.unit',
        compute=_compute_time_line,
        string='Project Operating Unit',
        store=True
    )
    task_id = fields.Many2one(
        'project.task', 'Task',
        ondelete='restrict'
    )
    planned = fields.Boolean(
        string='Planned'
    )
    actual_qty = fields.Float(
        string='Actual Qty',
        compute=_compute_time_line,
        store=True
    )
    planned_qty = fields.Float(
        string='Planned Qty',
        compute=_compute_time_line,
        store=True
    )
    day_name = fields.Char(
        string="Day",
        compute=_compute_time_line,
        store=True,
    )
    ts_line = fields.Boolean(
        compute=_compute_time_line,
        string='Timesheet line',
        store=True,
    )
    correction_charge = fields.Boolean(
        compute=_compute_time_line,
        string='Correction Chargeability',
        store=True,
    )
    chargeable = fields.Boolean(
        compute=_compute_time_line,
        string='Chargeable',
        store=True,
    )
    expenses = fields.Boolean(
        compute=_compute_time_line,
        string='Expenses',
        store=True,
    )
    project_mgr = fields.Many2one(
        comodel_name='res.users',
        compute=_compute_time_line,
        store=True
    )
    ot = fields.Boolean(
        string='Overtime',
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee'
    )
    line_fee_rate = fields.Float(
        compute=_compute_time_line,
        string='Fee Rate',
        store=True,
    )
    project_rate = fields.Float(
        compute=_compute_time_line,
        string='Project Rate',
        store=True,
    )
    project_amount = fields.Float(
        compute=_compute_time_line,
        string='Project Amount',
        store=True,
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Confirmed'),
        ('delayed', 'Delayed'),
        ('invoiceable', 'To be Invoiced'),
        ('progress', 'In Progress'),
        ('invoice_created', 'Invoice Created'),
        ('invoiced', 'Invoiced'),
        ('write-off', 'Write-Off'),
        ('change-chargecode', 'Change-Chargecode'),
        ('re_confirmed', 'Re-Confirmed'),
        ('invoiced-by-fixed', 'Invoiced by Fixed'),
        ('expense-invoiced', 'Expense Invoiced')
    ],
        string='Status',
        readonly=True,
        copy=False,
        index=True,
        track_visibility='onchange',
        default='draft'
    )
    user_total_id = fields.Many2one(
        'ps.time.line.user.total',
        string='Summary Reference',
    )
    date_of_last_wip = fields.Date(
        "Date Of Last WIP"
    )
    date_of_next_reconfirmation = fields.Date(
        "Date Of Next Reconfirmation"
    )
    tag_ids = fields.Boolean(
        'field not used'
    )
    task_user_id = fields.Many2one(
        'task.user',
        string='Task User Fee Rate',
        compute=_compute_time_line,
        store=True
    )

    def get_task_user_product(self, task_id=None, user_id=None):
        taskUserObj = self.env['task.user']
        product_id = False
        task_id = task_id or self.task_id.id
        user_id = user_id or self.user_id.id
        if task_id and user_id:
            date_now = fields.Date.today()
            #task-358
            taskUser = taskUserObj.search([('task_id', '=', task_id), ('from_date', '<=', date_now), ('user_id', '=', user_id)],
                                          limit=1, order='from_date Desc')
            if taskUser and taskUser.product_id:
                product_id = taskUser.product_id.id
            else:
                #check standard task for fee earners
                project_id = self.env['project.task'].browse(task_id).project_id
                standard_task = project_id.task_ids.filtered('standard')
                if standard_task:
                    taskUser = taskUserObj.search([('task_id', '=', standard_task.id), ('user_id', '=', user_id)],
                                                  limit=1)
                    product_id = taskUser.product_id.id if taskUser and taskUser.product_id else False

        if user_id and not product_id:
            user = self.env['res.users'].browse(user_id)
            employee = user._get_related_employees()
            product_id = employee.product_id and employee.product_id.id or False
        return product_id

    def get_fee_rate(self, task_id=None, user_id=None, date=None, project_rate=False):
        uid = user_id or self.user_id.id or False
        tid = task_id or self.task_id.id or False
        date = date or self.date or False
        fr = 0.0
        ic_fr = 0.0
        # fr = None
        if uid and tid and date:
            task_user = self.env['task.user'].get_task_user_obj(tid, uid, date)[:1]
            if task_user and task_user.fee_rate:
                fr = task_user.fee_rate
                ic_fr = task_user.ic_fee_rate
            if project_rate:
                return fr or 0.0
            # check standard task for fee earners
            else:
                project_id = self.env['project.task'].browse(tid).project_id
                standard_task = project_id.task_ids.filtered('standard')
                if standard_task:
                    # task-358
                    task_user = self.env['task.user'].get_task_user_obj(standard_task.id, uid, date)
                    if task_user:
                        fr = task_user[:1].fee_rate
                        ic_fr = task_user[:1].ic_fee_rate
        return [fr, ic_fr]
        # if fr == None:
        #     employee = self.env['hr.employee'].search([('user_id', '=', uid)])
        #     fr = employee.fee_rate or employee.product_id and employee.product_id.lst_price or 0.0
        #     if self.product_id and self.product_id != employee.product_id:
        #         fr = self.product_id.lst_price
        # return fr
    def merge_timelines(self):
        unit_amount = sum(
            [t.unit_amount for t in self])
        amount = sum([t.amount for t in self])
        self[0].write({
            'unit_amount': unit_amount,
            'amount': amount,
        })
        self[1:].unlink()
        return self[0]

    @api.model
    def get_fee_rate_amount(self, task_id=None, user_id=None, unit_amount=False):
        fr = self.get_fee_rate(task_id=task_id, user_id=user_id)[0]
        unit_amount = unit_amount if unit_amount else self.unit_amount
        amount = - unit_amount * fr
        return amount

    @api.onchange('date')
    def _onchange_dates(self):
        if self.planned or self.env.context.get('default_planned',False) :
            dt = datetime.strptime(str(self.date), "%Y-%m-%d") if self.date else datetime.now().date()
            self.date = dt-timedelta(days=dt.weekday())
            self.company_id = self.env.user.company_id
            date = self.find_daterange_week(self.date)
            self.week_id = date.id
        elif self.sheet_id and not self.sheet_id.date_start <= self.date <= self.sheet_id.date_end:
            self.date = self.sheet_id.date_start
            return {
                'warning': {'title': _('Error'), 'message': _('Please fill in date within timesheet dates.'), },
            }
        elif self.env.context.get('timesheet_date_start',False) and  self.env.context.get('timesheet_date_end',False):
            start_date = datetime.strptime(self.env.context.get('timesheet_date_start'), "%Y-%m-%d").date()
            end_date = datetime.strptime(self.env.context.get('timesheet_date_end'), "%Y-%m-%d").date()
            if not start_date <= self.date <= end_date:
                self.date = start_date
            # return {
            #     'warning': {'title': _('Error'), 'message': _('Please fill in date within timesheet dates.'), },
            # }


    @api.onchange('product_id', 'product_uom_id', 'unit_amount', 'currency_id')
    def on_change_unit_amount(self):
        if self.product_uom_id == self.env.ref("uom.product_uom_hour").id:
            return {}
        return super().on_change_unit_amount()

    def write(self, vals):
        uom_hour = self.env.ref("uom.product_uom_hour")
        # don't call super if only state has to be updated
        if self and 'state' in vals and len(vals) == 1:
            state = vals['state']
            cond, rec = ("IN", tuple(self.ids)) if len(self) > 1 else ("=",
                                                                       self.id)
            self.env.cr.execute("""
                               UPDATE %s SET state = '%s' WHERE id %s %s
                               """ % (self._table, state, cond, rec))
            self.env.cache.invalidate()
            vals.pop('state')
            return True

        if len(self) == 1:
            task_id = vals.get('task_id', self.task_id and self.task_id.id)
            user_id = vals.get('user_id', self.user_id and self.user_id.id)
            # for planning skip fee rate check
            planned = vals.get('planned', self.planned)
            # some cases product id is missing
            if not vals.get('product_id', self.product_id) and user_id:
                product_id = self.get_task_user_product(task_id, user_id) or False
                if not product_id and not planned:
                    user = self.env.user.browse(user_id)
                    raise ValidationError(_(
                        'Please fill in Fee Rate Product in employee %s.\n '
                    ) % user.name)
                vals['product_id'] = product_id
            ts_line = vals.get('ts_line', self.product_uom_id == uom_hour and task_id and not planned)
            if ts_line:
                unit_amount = vals.get('unit_amount', self.unit_amount)
                vals['amount'] = self.get_fee_rate_amount(task_id, user_id, unit_amount)

        if self.filtered('ts_line') and not (
                'unit_amount' in vals or
                'product_uom_id' in vals or
                'sheet_id' in vals or
                'date' in vals or
                'project_id' in vals or
                'task_id' in vals or
                'user_id' in vals or
                'name' in vals or
                'ref' in vals) and any(this.product_uom_id == uom_hour for this in self):
            # always copy context to keep other context reference
            context = self.env.context.copy()
            context.update({'ps_check_state': True})
            return super().with_context(context).write(vals)
        return super().write(vals)

    def _get_timesheet_cost(self, values):
        ## turn off updating amount and account
        values = values if values is not None else {}
        if values.get('project_id') or self.project_id:
            if values.get('amount'):
                return {}
            # unit_amount = values.get('unit_amount', 0.0) or self.unit_amount
            user_id = values.get('user_id') or self.user_id.id or self._default_user()
            user = self.env['res.users'].browse([user_id])
            emp = self.env['hr.employee'].search([('user_id', '=', user_id)], limit=1)
            # cost = emp and emp.timesheet_cost or 0.0
            uom = (emp or user).company_id.project_time_mode_id
            # Nominal employee cost = 1 * company project UoM (project_time_mode_id)
            return {
                # 'amount': -unit_amount * cost,
                'product_uom_id': uom.id,
                # 'account_id': values.get('account_id') or self.account_id.id or emp.account_id.id,
            }
        return {}

    def _check_state(self):
        """
        to check if any lines computes method calls allow to modify
        :return: True or super
        """
        context = self.env.context.copy()
        if 'ps_check_state' in context \
                or 'active_invoice_id' in context:
            return True
        return super()._check_state()

    @api.model
    def run_reconfirmation_process(self):
        current_date = datetime.now().date()
        # pre_month_start_date = current_date.replace(day=1, month=current_date.month - 1)
        month_days = calendar.monthrange(current_date.year, current_date.month)[1]
        month_end_date = current_date.replace(day=month_days)

        domain = [('date_of_next_reconfirmation', '!=', False), ('date_of_next_reconfirmation', '<=', month_end_date),
                  ('state', '=', 'delayed')]
        query_line = self._where_calc(domain)
        self_tables, where_clause, where_clause_params = query_line.get_sql()

        list_query = ("""                    
                UPDATE {0}
                SET state = 're_confirmed', date_of_next_reconfirmation = null
                WHERE {1}                          
                     """.format(
            self_tables,
            where_clause
        ))
        self.env.cr.execute(list_query, where_clause_params)
        return True

    @contextmanager
    def _as_analytic_line(self, recordset):
        """Return a context manager that returns the ps.time.line model when saying recordset.env['account.analytic.line']"""

        class EnvWithAnalyticLineAsPsTimeLine(api.Environment):
            def __new__(cls, wrapped_env):
                self = object.__new__(cls)
                args = (wrapped_env.cr, wrapped_env.uid, wrapped_env.context, wrapped_env.su)
                self.cr, self.uid, self.context, self.su = self.args = args
                self.registry = wrapped_env.registry
                self.cache = wrapped_env.cache
                self._cache_key = wrapped_env._cache_key
                self._protected = wrapped_env._protected
                self.all = wrapped_env.all
                return self

            def __getitem__(self, model_name):
                return super().__getitem__(
                    model_name if model_name != 'account.analytic.line' else 'ps.time.line'
                )

        original_env = recordset.env
        if type(original_env) != EnvWithAnalyticLineAsPsTimeLine:
            recordset.env = EnvWithAnalyticLineAsPsTimeLine(recordset.env)
        yield recordset
        if type(original_env) != EnvWithAnalyticLineAsPsTimeLine:
            recordset.env = original_env
