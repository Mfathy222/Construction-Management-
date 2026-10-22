from odoo import fields,models
class AccountMove(models.Model):
    _inherit = 'account.move'

    contract_id = fields.Many2one(
        comodel_name='construction.contract',
        readonly=True
    )
    work_progress_id = fields.Many2one(
        comodel_name='construction.work.progress',
        readonly = True
    )

    def open_contract(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Contract',
            'res_model': 'construction.contract',
            'res_id':self.contract_id.id,
            'target': 'current',
            'view_mode': 'form',
        }
    def open_work_progress(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Work Progress',
            'res_model': 'construction.work.progress',
            'res_id':self.work_progress_id.id,
            'target': 'current',
            'view_mode': 'form',
        }
