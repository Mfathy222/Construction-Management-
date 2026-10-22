from odoo import api, fields, models, tools

class ChangePrice(models.TransientModel):
    _name = 'work.item.change.price'

    name = fields.Char(string='Work Item Name', required=True)
    uom = fields.Many2one(comodel_name='uom.uom', string='UOM', required=True)
    quantity = fields.Float(string='Quantity', default=1)
    price_unit = fields.Float(string='Price Unit')
    contract_id = fields.Many2one('construction.contract', string='Contract', readonly=True)
    origin_id = fields.Many2one('construction.work.item', readonly=True)
    change_price_date = fields.Date()
    change_reason = fields.Char()
    old_price = fields.Float(string='Old Price')
    original_name = fields.Char(string='Original Name')
    remaining_qty = fields.Float(string='Remaining Quantity')


    @api.onchange('change_price_date')
    def _calc_item_name(self):
        if not self.change_price_date:
            self.name = self.original_name
        else:
            self.name = False
            formatted_date = self.change_price_date.strftime("%y/%m/%d")
            self.name = f"{self.original_name}  [{formatted_date}]"


    def action_confirm(self):
        work_items_table = self.env['construction.work.item'].sudo()
        parent = work_items_table.browse(self.origin_id.id)
        vals = {'name':self.name,
                'quantity':self.quantity,
                'uom':self.uom.id,
                'contract_id':self.contract_id.id,
                'price_unit':self.price_unit,
                'origin_id':self.origin_id.id,
                'change_price_date':self.change_price_date,
                'change_reason':self.change_reason,
                'old_price':parent.price_unit,
                }
        child = work_items_table.create(vals)
        if child:
            qty = parent.quantity - self.remaining_qty
            parent.write({'quantity':qty,'child_id':child.id})
            return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'message': f'work item has been created successfully!.',
                                'sticky': False,
                                'type': 'success',
                                'next': {'type': 'ir.actions.act_window_close'},
                            }
                        }

