from itertools import count

from odoo import api, fields, models
from odoo.exceptions import  ValidationError


class WorkItems(models.Model):
    _name = 'construction.work.item'
    _description = 'Work Items'

    name = fields.Char(
        string='Work Item Name',
        required=True
    )
    uom = fields.Many2one(
        comodel_name='uom.uom',
        string='UOM',
        required=True,
        compute='_compute_uom_price',
        store=True,
        inverse='_inverse_uom_price'
    )
    quantity = fields.Float(
        string='Quantity',
        default=1
    )
    price_unit = fields.Float(
        string='Price Unit',
        compute='_compute_uom_price',
        store=True,
        inverse='_inverse_uom_price'
    )
    contract_id = fields.Many2one(
        'construction.contract',
        string='Contract',
        readonly=True
    )
    work_type_id = fields.Many2one(
        comodel_name='product.template',
        required=True,
        readonly=True,
    )
    work_type_domain_ids = fields.Many2many(
        comodel_name='product.template',
        compute='_compute_work_type_domain_ids',
        store=True
    )
    origin_id = fields.Many2one(
        'construction.work.item',
         readonly=True
    )
    child_id = fields.Many2one(
        'construction.work.item',
        readonly=True
    )
    change_price_date = fields.Date(
        readonly=True
    )
    change_reason = fields.Char(
        readonly=True
    )
    old_price = fields.Float(
        string='Old Price',
        readonly=True
    )

    wp_lines = fields.One2many(
        comodel_name='construction.work.progress.line',
        inverse_name='work_item_id'
    )
    has_confirmed_wps = fields.Boolean(
        compute='_compute_work_item_useful_fields',
        store=True
    )
    remaining_qty = fields.Float(
        default=False,
        related='last_confirmed_line.remaining_qty',
        store=True
    )
    last_confirmed_line = fields.Many2one(
        'construction.work.progress.line',
        compute='_compute_work_item_useful_fields',
        store=True
    )
    item_value = fields.Float(
        compute='_compute_item_value',
    )

    @api.depends('wp_lines.work_progress_id.state')
    def _compute_work_item_useful_fields(self):
        for rec in self:
            rec.last_confirmed_line = False
            rec.has_confirmed_wps = False
            confirmed_wps = rec.wp_lines.filtered(lambda l: l.work_progress_id.state == 'confirm')
            if confirmed_wps:
                rec.has_confirmed_wps = True
                last_confirmed_wp_no = max(confirmed_wps.mapped('work_progress_id.work_progress_no'))
                rec.last_confirmed_line = confirmed_wps.filtered(
                    lambda l: l.work_progress_id.work_progress_no == last_confirmed_wp_no
                ).id or False

    @api.depends('contract_id','contract_id.line_ids')
    def _compute_work_type_domain_ids(self):
        for rec in self:
            if rec.contract_id:
                products = rec.contract_id.line_ids.mapped('product_id')
                rec.work_type_domain_ids = products if products else self.env['product.template']

    @api.depends('contract_id','work_type_id')
    def _compute_uom_price(self):
        for rec in self:
            contract_target_lines = rec.contract_id.line_ids.filtered(lambda l:l.product_id.id == rec.work_type_id.id)
            if contract_target_lines:
                rec.uom = contract_target_lines[0].uom
                rec.price_unit = contract_target_lines[0].price_unit

    def _inverse_uom_price(self):
        for rec in self:
            pass

    @api.depends('price_unit','quantity')
    def _compute_item_value(self):
        for rec in self:
            rec.item_value = rec.price_unit * rec.quantity

    @api.constrains('quantity')
    def _check_quantity(self):
        #Fetching wps_lines
        for rec in self:
            if not rec.wp_lines:
                continue
            done_qty = rec.last_confirmed_line.total_works
            if rec.quantity < done_qty:
                raise ValidationError(
                    f"Invalid quantity: The entered value is less than the already executed work ({done_qty}) for this item."
                )

    @api.constrains('price_unit')
    def _check_price_unit(self):
        for rec in self:
            if rec.has_confirmed_wps:
                raise ValidationError(
                    "Price cannot be updated: This item is already linked to finalized work progress. Please use the 'Change Price' button to create a child item instead."
                )

    @api.constrains('uom')
    def _check_uom(self):
        for rec in self:
            if rec.has_confirmed_wps:
                raise ValidationError(
                    f'Cannot edit work item as it is used in confirmed work progresses'
                )

    def unlink(self):
        for rec in self:
            if rec.wp_lines:
                confirmed_lines = rec.wp_lines.filtered(
                    lambda l:l.work_progress_id.state == 'confirm'
                )
                if confirmed_lines:
                    raise ValidationError(
                        'Cannot delete work items as it is in used'
                    )
        return super(WorkItems, self).unlink()

    def change_price(self):
        action = self.env['ir.actions.act_window']._for_xml_id('construction.action_change_price')
        if self.last_confirmed_line:
            remaining_qty = self.last_confirmed_line.remaining_qty
            action['context'] = {
                'default_name':self.name,
                'default_original_name':self.name,
                'default_uom':self.uom.id,
                'default_contract_id':self.contract_id.id,
                'default_origin_id':self.id,
                'default_quantity':remaining_qty,
                'default_remaining_qty':remaining_qty,
                'default_old_price':self.price_unit,
            }
        return action

    def open_parent_work_item(self):
        parent =  self.env['construction.work.item'].search(
            [('child_id', '=', self.id)],
            limit=1
        )
        if parent:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Work Progress',
                'res_model': 'construction.work.item',
                'view_mode': 'form',
                'res_id': parent.id,
                'target':'current'
            }

    def open_child_work_item(self):
        child = self.env['construction.work.item'].search(
            [('origin_id', '=', self.id)],
             limit=1
        )
        if child:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Work Progress',
                'res_model': 'construction.work.item',
                'view_mode': 'form',
                'res_id': child.id,
                'target':'current'
            }






