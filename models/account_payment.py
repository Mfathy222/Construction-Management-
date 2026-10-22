from odoo import fields, models, api
class AccountPayment(models.Model):
    _inherit = 'account.payment'

    construction_contract_id = fields.Many2one(
        comodel_name='construction.contract',
        readonly = True,
    )