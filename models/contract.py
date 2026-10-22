from odoo import fields, models, api 
from odoo.exceptions import UserError, ValidationError
from dateutil.utils import today


class Contract(models.Model):
    _name = 'construction.contract'
    _inherit =  ['mail.thread','mail.activity.mixin']
    _description = 'Contract'
    _order = 'name desc'
    _display_name = 'display_name'

    name = fields.Char(
        string='Name',
        required=True,
        default='New',
        readonly=True,
        copy=False
    )
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )
    state = fields.Selection(
        [('draft','Draft'),('confirm','Confirmed'),],
        default='draft',
    )
    reference = fields.Char(

    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Partner',
        required=True,
        tracking=True,
    )
    contract_type = fields.Selection(
        [
            ('customer','Customer'),
            ('subcontractor','Subcontractor')
        ],
        required=True,
        default='customer',
        tracking=True,
    )
    sub_contractor_type = fields.Selection(
        [
            ('company','Company'),
            ('labor','Casual Labor'),
        ],
        tracking=True
    )
    project_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Project',
        required=True,
        tracking=True,
    )
    date = fields.Date(
        string='Date',
        default=today(),
        tracking=True,
    )
    from_date = fields.Date(
        string='From Date'
    )
    to_date = fields.Date(
        string='To Date'
    )
    contract_amount = fields.Monetary(
        string='Contract Amount',
        tracking = True,
        currency_field='currency_id',
    )
    tax_ids = fields.Many2many(
        comodel_name='account.tax',
    )
    amount_included_tax = fields.Monetary(
        currency_field='currency_id',
        compute = '_compute_amount_included_tax',
    )
    currency_id = fields.Many2one(
        'res.currency',
        default = lambda self:self.env.company.currency_id,
        tracking = True,
        required=True,
    )
    line_ids = fields.One2many(
        'construction.contract.line',
        'contract_id',
        string='Lines'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    work_progress_ids = fields.One2many(
        'construction.work.progress',
        'contract_id'
    )
    total_work_progresses = fields.Integer(
        compute='_compute_total_work_progresses'
    )
    work_items_ids = fields.One2many(
        'construction.work.item',
        'contract_id'
    )
    total_work_items =  fields.Integer(
        compute='_compute_total_work_items'
    )
    retention_per = fields.Float(

    )
    contract_retention_value = fields.Monetary(
        currency_field='currency_id',
        compute = '_compute_contract_retention_value',
    )
    wps_payments_value = fields.Monetary(
        currency_field='currency_id',
        compute = '_compute_wps_payments_value_accrual_retention_value',
        store = True
    )
    accrual_retention_value = fields.Monetary(
        compute = '_compute_wps_payments_value_accrual_retention_value',
        store = True,
        currency_field='currency_id',
    )
    paid_retention_value = fields.Monetary(
        currency_field='currency_id',
        compute='_compute_paid_retention_value',
        store=True
    )
    remaining_retention_value = fields.Monetary(
        currency_field='currency_id',
        store = True,
        compute = '_compute_remaining_retention_value',
    )
    contract_total_paid = fields.Monetary(
        currency_field= 'currency_id',
        compute='_compute_contract_total_paid',
        store=True
    )
    retention_payments_ids = fields.One2many(
        inverse_name='construction_contract_id',
        comodel_name='account.payment'
    )
    contract_payment_state = fields.Selection(
        selection=[
            ('partial','Partial'),
            ('paid','Paid')
        ],
        compute = '_compute_contract_payment_state',
        store = True
    )
    down_payment_per = fields.Float(

    )
    down_payment_value = fields.Monetary(
        currency_field = 'currency_id',
        compute = '_compute_down_payment_value',
        store = True
    )
    down_payment_invoice_ids = fields.One2many(
        comodel_name='account.move',
        inverse_name='contract_id',
        readonly=True,
    )
    down_payment_invoice_count = fields.Integer(
        store = True,
        compute = '_compute_down_payment_invoice_count'
    )
    already_invoice = fields.Monetary(
        compute = '_compute_already_invoice',
        currency_field='currency_id',
        store = True,

    )
    amount_after_down_payment = fields.Monetary(
        compute='_compute_amount_after_down_payment',
        currency_field='currency_id',

        store = True
    )
    down_payment_value_include_tax = fields.Monetary(
        compute='_compute_down_payment_value_include_tax',
        currency_field='currency_id',

        store = True
    )



    @api.depends('work_progress_ids')
    def _compute_total_work_progresses(self):
        for rec in self:
            rec.total_work_progresses = (len(rec.work_progress_ids.ids))

    @api.depends('work_items_ids')
    def _compute_total_work_items(self):
        for rec in self:
            rec.total_work_items = len(rec.work_items_ids)

    @api.depends('name', 'partner_id.name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.name}/{rec.partner_id.name}"

    @api.depends('work_progress_ids','work_progress_ids.invoice_ids','paid_retention_value','work_progress_ids.invoice_ids.state','work_progress_ids.invoice_ids.amount_total','work_progress_ids.invoice_ids.amount_residual','work_progress_ids.invoice_ids.reconciled_payment_ids.state')
    def _compute_wps_payments_value_accrual_retention_value(self):
        for rec in self:
            rec.wps_payments_value = 0.0
            rec.accrual_retention_value = 0.0
            contract_wps = rec.work_progress_ids
            invoiced_wps = contract_wps.filtered(lambda wp: any(inv.state == 'posted' for inv in wp.invoice_ids ))
            if invoiced_wps:
                rec.accrual_retention_value = sum(wp.retention_value for wp in invoiced_wps) - rec.paid_retention_value
                invoices = invoiced_wps.invoice_ids
                rec.wps_payments_value = sum((inv.amount_total-inv.amount_residual) for inv in invoices)

    @api.depends('contract_amount', 'tax_ids')
    def _compute_amount_included_tax(self):
        for rec in self:
            rec.amount_included_tax = 0.0
            if not rec.tax_ids:
                rec.amount_included_tax = rec.contract_amount
            else:
                tax_per = 1 + sum(rec.tax_ids.mapped('amount')) / 100
                rec.amount_included_tax = rec.contract_amount * tax_per

    @api.depends('contract_amount', 'down_payment_per')
    def _compute_down_payment_value(self):
        for rec in self:
            rec.down_payment_value = 0.0
            rec.down_payment_value = rec.contract_amount * rec.down_payment_per

    @api.depends('amount_included_tax','retention_per')
    def _compute_contract_retention_value(self):
        for rec in self:
            rec.contract_retention_value = 0.0
            rec.contract_retention_value = rec.amount_included_tax * rec.retention_per

    @api.depends('retention_payments_ids','retention_payments_ids.state')
    def _compute_paid_retention_value(self):
        for rec in self:
            rec.paid_retention_value = 0.0
            rec.paid_retention_value = abs(sum(payment.amount_signed for payment in rec.retention_payments_ids if payment.state == 'paid'))

    @api.depends('wps_payments_value','paid_retention_value')
    def _compute_contract_total_paid(self):
        for rec in self:
            rec.contract_total_paid = 0.0
            rec.contract_total_paid = rec.wps_payments_value + rec.paid_retention_value

    @api.depends('contract_retention_value','paid_retention_value')
    def _compute_remaining_retention_value(self):
        for rec in self:
            rec.remaining_retention_value = 0.0
            rec.remaining_retention_value =  rec.contract_retention_value - rec.paid_retention_value

    @api.depends('amount_after_down_payment','contract_total_paid')
    def _compute_contract_payment_state(self):
        for rec in self:
            rec.contract_payment_state = False
            remaining = rec.amount_after_down_payment - rec.contract_total_paid
            if rec.contract_total_paid > 0:
                if remaining <= 0.01:
                    rec.contract_payment_state = 'paid'
                else:
                    rec.contract_payment_state = 'partial'

    @api.depends('down_payment_invoice_ids')
    def _compute_down_payment_invoice_count(self):
        for rec in self:
            rec.down_payment_invoice_count = 0
            rec.down_payment_invoice_count = len(rec.down_payment_invoice_ids) or 0

    @api.depends('down_payment_invoice_ids','down_payment_invoice_ids.state')
    def _compute_already_invoice(self):
        for rec in self:
            rec.already_invoice = 0
            posted_down_payments = rec.down_payment_invoice_ids.filtered(lambda inv:inv.state == 'posted')
            rec.already_invoice = abs(sum(inv.amount_untaxed_in_currency_signed for inv in posted_down_payments) or 0)

    @api.depends('already_invoice', 'amount_included_tax')
    def _compute_amount_after_down_payment(self):
        for rec in self:
            rec.amount_after_down_payment = 0.0
            tax_per = 1 + sum(rec.tax_ids.mapped('amount')) / 100
            if tax_per:
                already_invoice = rec.already_invoice * tax_per
            rec.amount_after_down_payment = rec.amount_included_tax - already_invoice

    @api.depends('already_invoice', 'amount_included_tax')
    def _compute_down_payment_value_include_tax(self):
        for rec in self:
            tax_per = 1 + sum(rec.tax_ids.mapped('amount')) / 100
            rec.down_payment_value_include_tax = rec.already_invoice
            if tax_per:
                rec.down_payment_value_include_tax = rec.already_invoice * tax_per



    # @api.onchange('line_ids')
    # def _calc_contract_amount(self):
    #     for rec in self:
    #         rec.contract_amount = sum(rec.line_ids.mapped('amount'))

    @api.onchange('product_id', 'line_ids')
    def _calculate_description(self):
        for line in self.line_ids:
            line.description = line.product_id.name if line.product_id else ''

    @api.constrains('contract_amount', 'line_ids')
    def check_contract_amount(self):
        for rec in self:
            if rec.contract_amount != sum(line.amount for line in rec.line_ids):
                raise ValidationError(
                    'Contract Amount must be equal to sum of contract lines'
                )

    @api.constrains('from_date', 'to_date')
    def _check_date_range(self):
        for rec in self:
            if rec.from_date and rec.to_date:
                if rec.from_date >= rec.to_date:
                    raise ValidationError(
                        "To date must be greater than from date"
                    )

    @api.constrains('project_id', 'date', 'name', 'partner_id', 'contract_id', 'line_ids', 'from_date', 'to_date','sub_contractor_type','currency_id','tax_ids','down_payment_per','down_payment_value')
    def _prevent_edit_contract(self):
        for rec in self:
            if rec.state == 'confirm':
                raise ValidationError("Cannot edit confirmed contracts.")

    def write(self,vals):
        for rec in self:
            if 'contract_amount' in vals and rec.work_progress_ids:
                raise ValidationError("Cannot edit contract, work progresses are already linked.")
        return   super(Contract, self).write(vals)

    def unlink(self):
        for rec in self:
            if rec.work_progress_ids:
                wp_states = rec.work_progress_ids.mapped('state')
                if all(state =='draft' for state in wp_states):
                    rec.work_progress_ids.sudo().unlink()
                    rec.work_items_ids.sudo().unlink()
                    return super(Contract, self).unlink()
                else:
                    raise ValidationError("Cannot delete contract, work progresses are already linked.")
            else:
                return super(Contract, self).unlink()

    def action_confirm(self):
        for rec in self:
            if rec.state == 'draft':
                if rec.name == 'New':
                    contract_seq = 'construction.subcontractor.contract' if rec.contract_type == 'subcontractor' else 'construction.customer.contract'
                    if contract_seq:
                        rec.name = self.env['ir.sequence'].next_by_code(contract_seq)
                rec.state = 'confirm'
            else:
                pass

    def action_set_to_draft(self):
        for rec in self:
            if rec.work_progress_ids:
                raise ValidationError("Cannot set contract to draft, work progresses are already linked.")
            else:
                rec.state = 'draft'

    def create_work_progress(self):
        action_id = 'construction.subcontractor_work_progress_action' if self.contract_type == 'subcontractor' else 'construction.customer_work_progress_action'
        action = self.env['ir.actions.act_window']._for_xml_id(action_id)
        last_progress = self.env['construction.work.progress'].sudo().search(
            [('contract_id', '=', self.id)],
            order='work_progress_no desc',
            limit=1
        )
        action['context'] = {
            'default_partner_id': self.partner_id.id,
            'default_contract_id': self.id,
            'default_project_id': self.project_id.id,
            'default_work_progress_no': last_progress.work_progress_no + 1 if last_progress else 0,
            'default_retention_per':self.retention_per,
            'default_tax_ids':self.tax_ids.ids,
        }
        form_view_id = self.env.ref('construction.construction_work_progress_view_form').id
        action['views'] = [(form_view_id, 'form')]
        action['target'] = 'current'
        return action

    def pay_retention(self):
        wizard_action_id = 'construction.action_pay_retention'
        action = self.env['ir.actions.act_window']._for_xml_id(wizard_action_id)
        default_journal_id = self.env['account.journal'].search([('type', 'in', ['bank','cash'])], limit=1)
        action['context'] = {
            'default_partner_id': self.partner_id.id,
            'default_journal_id': default_journal_id.id,
            'default_amount':self.accrual_retention_value,
            'default_contract_id': self.id,
            'default_payment_type':'outbound' if self.contract_type == 'subcontractor' else 'inbound',
            'default_currency_id': self.currency_id.id,

        }
        return action
    
    def open_work_progress(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Work Progress',
            'res_model': 'construction.work.progress',
            'view_mode': 'list,form',
            'domain': [('contract_id', '=', self.id)],
            'context': {'create': False}
        }

    def open_work_items(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Work Items',
            'res_model': 'construction.work.item',
            'view_mode': 'list,form',
            'domain': [('contract_id', '=', self.id)],
            'context': {'create': False,'default_contract_id': self.id},
         }

    def open_contract_wps_payments(self):
        contract_wps = self.work_progress_ids
        invoiced_wps = contract_wps.filtered(lambda wp: any(inv.state == 'posted' for inv in wp.invoice_ids))
        invoices = invoiced_wps.invoice_ids
        payments = invoices.reconciled_payment_ids.ids
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payments',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'domain': [('id', 'in', payments)],
            'context': {'create': False, },
        }

    def open_contract_retention_payments(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payments',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.retention_payments_ids.ids)],
            'context': {'create': False, },
        }

    def create_down_payment_invoice(self):
        is_out = self.contract_type == 'customer'
        if is_out:
            main_account = int(self.env['ir.config_parameter'].sudo().get_param('construction.deferred_revenue_account'))
            xml_id = 'account.action_move_out_invoice'
            move_type = 'out_invoice'

        else:
            main_account = int(self.env['ir.config_parameter'].sudo().get_param('construction.deferred_expense_account'))
            xml_id = 'account.action_move_in_invoice'
            move_type = 'in_invoice'
        if not main_account:
            raise ValidationError("Down payment accounts configuration is required. Please set up the down payment accounts in the settings first.")
        invoice_lines = [
            (0,0,{
                'name':f'Down payment of {self.down_payment_per * 100}%',
                'quantity':1,
                'price_unit': self.down_payment_value - self.already_invoice,
                'tax_ids': self.tax_ids.ids,
                'account_id': main_account,
                'analytic_distribution': {str(self.project_id.id): 100.0},
                }
            )
        ]
        action = self.env['ir.actions.act_window']._for_xml_id(xml_id)
        action.update({
            'views': [(self.env.ref('account.view_move_form').id, 'form')],
            'target': 'current',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_contract_id':self.id,
                'default_move_type': move_type,
                'default_currency_id': self.currency_id.id,
                'default_ref': f"{self.name}",
                'default_invoice_line_ids': invoice_lines
            }
        })
        return action

    def open_down_payment_invoice(self):
        return {
            'type': 'ir.actions.act_window',
            'name':'Bills',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('contract_id', '=', self.id)],
        }



class ContractLine(models.Model):
    _name = 'construction.contract.line'

    sequence = fields.Integer(
        default=10
    )
    product_id = fields.Many2one(
        'product.template',
        string='Work Type'
    )
    description = fields.Char(
        string='Description'
    )
    contract_id = fields.Many2one(
        'construction.contract',
         string='Contract'
    )
    uom = fields.Many2one(
        'uom.uom',
    )
    price_unit = fields.Float(
        string='Unit Price',
    )
    amount = fields.Float(
        string='Amount'
    )




