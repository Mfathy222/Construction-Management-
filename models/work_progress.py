from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo import _

class WorkProgress(models.Model):
    _name = 'construction.work.progress'
    _inherit =  ['mail.thread','mail.activity.mixin']
    _description = 'Work Progress'
    _display_name = 'display_name'
    _order = 'work_progress_no asc'

    work_progress_no = fields.Integer(
        string='Work Progress Number',
        required=True
    )
    display_name = fields.Char(
        string='Name',
        compute='_compute_display_name',
        required=True
    )
    state = fields.Selection(
        [
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('cancel', 'Cancel')
        ],
        default='draft'
    )
    contract_id = fields.Many2one(
        'construction.contract',
        required=True,
        readonly=True
    )
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.today()
    )
    partner_id = fields.Many2one(
        'res.partner',
        readonly=True,
        required=True
    )
    work_type = fields.Many2one(
        'product.template',
        required=True
    )
    project_id = fields.Many2one(
        'account.analytic.account',
        required=True,
        readonly=True
    )
    line_ids = fields.One2many(
        'construction.work.progress.line',
        'work_progress_id'
    )
    work_type_domain_ids = fields.Many2many(
    'product.template',
    compute='_compute_work_type_domain',
    )
    currency_id = fields.Many2one(
        'res.currency',
        related = 'contract_id.currency_id',
    )
    total_works_value = fields.Monetary(
        currency_id='currency_id',
        store=True,
        compute='_compute_total_works_value'
    )
    total_achieved_value = fields.Monetary(
        currency_id='currency_id',
        store=True,
        compute='_compute_total_achieved_value'
    )
    last_wp_value = fields.Monetary(
        currency_id='currency_id',
        store=True,
        compute='_compute_last_wp_value'
    )
    wp_value = fields.Monetary(
        currency_id='currency_id',
        compute='_compute_wp_value',
        store=True
    )
    tax_ids = fields.Many2many(
        comodel_name='account.tax',
        related='contract_id.tax_ids'
    )
    wp_value_included_tax = fields.Monetary(
        currency_id='currency_id',
        readonly=True
    )
    retention_per = fields.Float(

    )
    retention_value = fields.Monetary(
        currency_id='currency_id',
    )
    wp_due = fields.Monetary(
        currency_id='currency_id',
        compute='_compute_wp_due',
        store=True
    )
    invoice_ids = fields.One2many(
        comodel_name='account.move',
        inverse_name='work_progress_id',
        readonly=True,
    )
    invoice_count = fields.Integer(
        compute='_compute_invoice_count',
        store=True
    )
    invoice_state= fields.Selection(
        [
            ('to_invoice','To Invoice'),
            ('fully_invoice','Fully Invoiced'),
        ],
        compute='_compute_invoice_state',
        store=True
    )
    
    contract_type = fields.Selection(
        [
            ('customer', 'Customer'),
            ('subcontractor', 'Subcontractor')
        ],
        required=True,
        related='contract_id.contract_type',
        tracking=True,
    )
    sub_contractor_type = fields.Selection(
        [
            ('company', 'Company'),
            ('labor', 'Casual Labor'),
        ],
        related='contract_id.sub_contractor_type'
    )

    @api.depends('work_progress_no')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"WP/{rec.work_progress_no:03}"

    # compute contract products to showing it only in wp's work type field
    @api.depends('contract_id', 'contract_id.line_ids')
    def _compute_work_type_domain(self):
        for rec in self:
            if rec.contract_id:
                products = rec.contract_id.line_ids.mapped('product_id')
                rec.work_type_domain_ids = products
            else:
                rec.work_type_domain_ids = False

    @api.depends('line_ids.quantity', 'line_ids.price_unit')
    def _compute_total_works_value(self):
        for rec in self:
            rec.total_works_value = sum(l.quantity * l.price_unit for l in rec.line_ids)

    @api.depends('line_ids.total_value', )
    def _compute_total_achieved_value(self):
        for rec in self:
            rec.total_achieved_value = sum(l.total_value for l in rec.line_ids)

    @api.depends('line_ids.quantity', 'line_ids.price_unit', 'line_ids.total_value','work_type')
    def _compute_last_wp_value(self):
        contract_ids = self.contract_id.ids
        work_type_ids = self.work_type.ids
        wps_data_related_by_contract_work_type = self.sudo().search(
            [
                ('contract_id', 'in', contract_ids),
                ('work_type','in', work_type_ids),
            ],
        )
        for rec in self:
            rec.last_wp_value = 0.0
            other_wps = wps_data_related_by_contract_work_type.filtered(lambda wp:wp.id != rec.id and wp.work_progress_no < rec.work_progress_no)
            other_wps_numbers = other_wps.mapped('work_progress_no')
            if not other_wps_numbers:
                continue
            last_wp_number = max(other_wps_numbers)
            last_wp = other_wps.filtered(lambda wp:wp.work_progress_no == last_wp_number)
            if last_wp:
                rec.last_wp_value = last_wp.total_achieved_value

    @api.depends('line_ids.quantity', 'line_ids.price_unit', 'line_ids.total_value')
    def _compute_wp_value(self):
        for rec in self:
            rec.wp_value = sum(l.current_value for l in rec.line_ids)

    @api.depends('wp_value_included_tax', 'retention_per', 'retention_value')
    def _compute_wp_due(self):
        for rec in self:
            rec.wp_due = rec.wp_value_included_tax - rec.retention_value

    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = len(rec.invoice_ids.mapped('id'))

    @api.depends('invoice_ids','invoice_ids.state')
    def _compute_invoice_state(self):
        for rec in self:
            invoices_states = rec.invoice_ids.mapped('state')
            rec.invoice_state = 'fully_invoice' if  'posted' in invoices_states or 'draft' in invoices_states else 'to_invoice'

    # compute work progress number
    @api.onchange('contract_id')
    def _onchange_wp_no_calculation(self):
        if not self.contract_id:
            return
        last_progress = self.sudo().search(
            [('contract_id', '=', self.contract_id.id)],
            order='work_progress_no desc',
            limit=1
        )
        self.work_progress_no = (last_progress.work_progress_no + 1) if last_progress else 1

    @api.onchange('wp_value_included_tax', 'retention_per')
    def _onchange_retention_calculation(self):
        self.retention_value = (self.retention_per) * self.wp_value_included_tax

    @api.onchange('retention_value')
    def _onchange_retention_percentage_calculation(self):
        if self.wp_value > 0:
            self.retention_per = (self.retention_value / self.wp_value_included_tax)

    @api.onchange('work_type')
    def _onchange_work_type(self):
        self.update_lines()

    @api.onchange('wp_value','tax_ids')
    def _onchange_tax_wp_included_tax_calculation(self):
        if not self.tax_ids:
            self.wp_value_included_tax = self.wp_value
        else:
            tax_per = 1 + sum(self.tax_ids.mapped('amount'))/100
            self.wp_value_included_tax = self.wp_value * tax_per
        if self.sub_contractor_type == 'labor' and self.tax_ids:
            return {
                'warning': {
                    'title': "خطأ في الإدخال",
                    'message': "هذا المقاول يندرج تحت فئة العمالة، لا يجب إضافة ضرائب له.",
                    'type': 'notification',  # اختياري في بعض الإصدارات
                }
            }

    @api.constrains('work_progress_no')
    def _check_work_progress_no(self):
        for rec in self:
            if rec.work_progress_no <= 0:
                raise ValidationError("Work progress number must be greater than zero.")
            other_contract_work_progresses_numbers = self.env['construction.work.progress'].sudo().search(
                [('contract_id', '=', rec.contract_id.id),('id', '!=', rec.id)]
            ).mapped('work_progress_no')
            if rec.work_progress_no in other_contract_work_progresses_numbers:
                raise ValidationError(
                    'Work progress number must be unique per contract!'
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            contract_id = vals.get('contract_id') or self.env.context.get('default_contract_id')
            work_progress_no = vals.get('work_progress_no')
            before_drafted_wps = self.sudo().search([
                ('contract_id', '=', contract_id),
                ('work_progress_no', '<', work_progress_no)
            ]).mapped('state')
            if before_drafted_wps and 'draft' in before_drafted_wps:
                raise ValidationError(
                    'cannot create work progress, there are drafted work progress before it'
                )
        return super(WorkProgress, self).create(vals_list)

    #prevent edit confirmed work progresses
    def write(self, vals):
        for rec in self:
            other_wps_after_current = self.sudo().search([
                ('contract_id', '=', rec.contract_id.id),
                ('id', '!=', rec.id),
                ('work_progress_no', '>', rec.work_progress_no)
            ])
            if other_wps_after_current:
                raise ValidationError(
                    'cannot edit work progress, there are work progresses after it!'
                )
            if rec.state == 'confirm':
                if any(k in vals for k in ['work_type','tax_ids','wp_value_included_tax','retention_per','retention_value','line_ids']):
                    raise ValidationError(
                        'to edit record, it must be in draft state'
                    )
        return super(WorkProgress, self).write(vals)
    #prevent delete confirmed work progresses
    def unlink(self):
        for rec in self:
            if rec.state == 'confirm':
                raise ValidationError(
                    "cannot delete work progress/s you must set it draft first."
                )
        return super(WorkProgress,self).unlink()

    def action_confirm(self):
        """
        Confirms the work progress, validating that the total value does not
        exceed the contracted amount defined in the contract lines.
        """
        # Prepare search domain to fetch contract lines related to the current work type and contract
        domain_search = [
            ('product_id', 'in', self.work_type.ids),
            ('contract_id', 'in', self.contract_id.ids)
        ]
        # Fetch relevant contract lines
        contracts_items = self.env['construction.contract.line'].sudo().search(domain_search)
        for rec in self:
            # Check if we have lines in this progress report
            if not rec.line_ids:
                raise ValidationError(
                    "Cannot confirm work progress: The work progress lines are empty."
                )
            # Filter for the specific work type in the contract
            item_in_contract = contracts_items.filtered(lambda i: i.product_id.id == rec.work_type.id)
            # Validate budget/contract value
            if item_in_contract:
                value_in_contract = item_in_contract.amount
                value_in_wp = rec.total_works_value
                achieved_in_wp = rec.total_achieved_value
                enable_exceed_contract_value = self.env['ir.config_parameter'].sudo().get_param('construction.enable_exceed_contract_value')
                if (value_in_wp > value_in_contract or achieved_in_wp > value_in_wp)  and not enable_exceed_contract_value:
                    raise ValidationError(
                        "This work progress will exceed the contracted amount."
                    )
            rec.state = 'confirm'

    def action_create_bill(self):
        return self._prepare_invoice_action('in_invoice')

    def action_create_invoice(self):
        return self._prepare_invoice_action('out_invoice')


    def action_set_to_draft(self):
        for rec in self:
            other_wps_after_current = self.sudo().search([
                    ('contract_id','=',rec.contract_id.id),
                    ('id','!=',rec.id),
                    ('work_progress_no','>',rec.work_progress_no)
            ])
            if other_wps_after_current:
                raise ValidationError(
                    'cannot set work progress to draft, there are work progresses after it!'
                )
            if rec.invoice_ids:
                bill_states = rec.invoice_ids.mapped('state')
                if 'posted' in bill_states:
                    raise ValidationError(
                        f"Unable to set to draft: {rec.display_name}. You must first cancel their related vendor bills."
                    )
            rec.state = 'draft'

    def action_open_bill(self):
        return {
            'type': 'ir.actions.act_window',
            'name':'Bills',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('work_progress_id', '=', self.id)],
        }

    def update_lines(self):
        for rec in self:
            commands = [(5, 0, 0)]
            if not rec.contract_id or not rec.work_type:
                rec.line_ids = commands
                continue
            domain = [
                ('work_progress_id.contract_id', '=', rec.contract_id.id),
                ('work_progress_id.work_type', '=', rec.work_type)
            ]
            work_type_ids = self.env['construction.work.progress.line'].search(domain).mapped('work_item_id.id')
            unique_item_ids = list(dict.fromkeys(work_type_ids))
            for item_id in unique_item_ids:
                commands.append(
                    (0, 0, {'work_item_id': item_id})
                )
            rec.line_ids = commands

    def _prepare_invoice_action(self,move_type):
        is_out = move_type == 'out_invoice'
        if is_out:
            global_income_account = self.env['account.account'].sudo().search([('account_type','=','income')],limit=1)
            main_account = self.work_type.property_account_income_id.id or global_income_account.id
            ret_account = int(self.env['ir.config_parameter'].sudo().get_param('construction.retention_receivable_account'))
            ret_name = 'ضمان أعمال عملاء'
            xml_id = 'account.action_move_out_invoice'
            down_payment_account = int(self.env['ir.config_parameter'].sudo().get_param('construction.deferred_revenue_account'))
        else:
            global_expense_account = self.env['account.account'].sudo().search([('account_type','=','expense')],limit=1)
            main_account = self.work_type.property_account_expense_id.id or global_expense_account.id
            ret_account = int(self.env['ir.config_parameter'].sudo().get_param('construction.retention_payable_account'))
            ret_name = 'ضمان أعمال موردين - مقاولين'
            xml_id = 'account.action_move_in_invoice'
            down_payment_account = int(self.env['ir.config_parameter'].sudo().get_param('construction.deferred_expense_account'))

        if not ret_account and self.retention_value > 0:
            raise ValidationError("Missing accounts in Configuration [Retentions Accounts]")

        invoice_lines = [(0, 0, {
            'name': self.work_type.name,
            'quantity': 1,
            'price_unit': self.wp_value,
            'tax_ids': self.tax_ids.ids,
            'account_id': main_account,
            'analytic_distribution': {str(self.project_id.id): 100.0},
        })]
        #handle retentions
        if self.retention_value > 0:
            invoice_lines.append((0, 0, {
                'name': ret_name,
                'quantity': -1,
                'price_unit': self.retention_value,
                'account_id': ret_account,
                'analytic_distribution': {str(self.project_id.id): 100.0},
            }))
        #handle down-payments
        down_payments_value = self.contract_id.already_invoice
        if down_payment_account and down_payments_value > 0:
            #down-payments label
            invoice_lines.append((0, 0, {
                'name': 'Down Payments',
                'display_type': 'line_section',
            }))
            #down-payments
            down_payments_invoices = self.contract_id.down_payment_invoice_ids
            posted_down_payments_invoices = down_payments_invoices.filtered(lambda inv:inv.state == 'posted')
            if posted_down_payments_invoices:
                down_payment_discount_value = self.wp_value * self.contract_id.down_payment_per
                each_invoice_discount = down_payment_discount_value / len(posted_down_payments_invoices) or 1
                for invoice in posted_down_payments_invoices:
                    invoice_lines.append((0, 0, {
                        'name': f'Down Payment: {invoice.name}',
                        'account_id':down_payment_account,
                        'quantity':-1,
                        'price_unit':each_invoice_discount,
                        'analytic_distribution': {str(self.project_id.id): 100.0},
                        'tax_ids': self.tax_ids.ids,
                    }))

        action = self.env['ir.actions.act_window']._for_xml_id(xml_id)
        action.update({
            'views': [(self.env.ref('account.view_move_form').id, 'form')],
            'target': 'current',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_move_type': move_type,
                'default_currency_id': self.currency_id.id,
                'default_ref': f"{self.contract_id.name}/{self.display_name}",
                'default_work_progress_id': self.id,
                'default_invoice_line_ids': invoice_lines
            }
        })
        return action


    # ------------------------------------------------------------------------------------------------------------------
    # print contract button
    # ------------------------------------------------------------------------------------------------------------------
    def print_contract(self):
        self.ensure_one()
        return self.env.ref('construction.construction_work_progress_report').report_action(self)

    def format_wp_report_number(self, value):
        if value in (None, False):
            value = 0
        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value)

        if number.is_integer():
            return f"{int(number):,}"
        return f"{number:,.2f}".rstrip("0").rstrip(".")

    def format_wp_report_qty(self, value):
        if value in (None, False):
            value = 0
        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value)

        if number != 0 and abs(number) < 1:
            return self.format_wp_report_percent(number)

        return self.format_wp_report_number(number)

    def format_wp_report_percent(self, value):
        if value in (None, False):
            value = 0
        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value)

        if abs(number) <= 1:
            number *= 100

        if number.is_integer():
            return f"{int(number):,}%"
        return f"{number:,.2f}".rstrip("0").rstrip(".") + "%"

    def amount_to_text_ar(self, amount):
        self.ensure_one()
        currency = self.env.company.currency_id
        try:
            return currency.with_context(lang='ar_001').amount_to_text(amount)
        except Exception:
            try:
                return currency.amount_to_text(amount)
            except Exception:
                return ''

    def previous_work_progress_no(self):
        self.ensure_one()
        return self.work_progress_no - 1 if self.work_progress_no and self.work_progress_no > 1 else 0



