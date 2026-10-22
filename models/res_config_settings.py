from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_exceed_contract_value = fields.Boolean(
        string="Enable Exceed Contract Value",
        config_parameter='construction.enable_exceed_contract_value'
    )
    retention_receivable_account = fields.Many2one(
        'account.account',
        config_parameter='construction.retention_receivable_account'
    )
    retention_payable_account = fields.Many2one(
        'account.account',
        config_parameter='construction.retention_payable_account'
    )
    deferred_expense_account = fields.Many2one(
        'account.account',
        config_parameter='construction.deferred_expense_account'
    )
    deferred_revenue_account = fields.Many2one(
        'account.account',
        config_parameter='construction.deferred_revenue_account'
    )