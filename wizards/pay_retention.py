from odoo import models , fields , api
from odoo.exceptions import ValidationError


class PayRetention(models.TransientModel):
    _name = 'construction.contract.pay.retention'

    contract_id = fields.Many2one(
        'construction.contract'
    )
    amount = fields.Monetary(
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency',
    )
    payment_type = fields.Selection(
        selection=[
            ('outbound','Send'),
            ('inbound','Receive'),
           ]
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
    )
    date = fields.Date(
        default=fields.Date.today()
   )
    memo = fields.Char(

    )
    journal_id = fields.Many2one(
        'account.journal',
    )


    @api.constrains('amount')
    def _check_amount(self):
        if self.amount < 1:
            raise ValidationError('Amount must be greater than 0')

    def action_confirm(self):
        destination_account = self.env['ir.config_parameter'].sudo().get_param('construction.retention_receivable_account') if self.payment_type == 'inbound' \
        else self.env['ir.config_parameter'].sudo().get_param('construction.retention_payable_account')
        if not destination_account:
            raise ValidationError('Missing accounts in Configuration [Retentions Accounts]')
        created_payment = self.env['account.payment'].create(
                            {
                                'journal_id': self.journal_id.id,
                                'payment_type':self.payment_type,
                                'partner_id':self.partner_id.id,
                                'amount':self.amount,
                                'currency_id':self.currency_id.id,
                                'memo':self.memo,
                                'destination_account_id':int(destination_account),
                                'construction_contract_id':self.contract_id.id
                            }
                        )
        if created_payment:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Retention Payment',
                'res_model': 'account.payment',
                'res_id': created_payment.id,
                'target': 'current',
                'view_mode': 'form',
            }