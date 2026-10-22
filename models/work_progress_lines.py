from odoo import api, fields, models
from odoo.exceptions import  ValidationError
from markupsafe import Markup


class ConstructionLines(models.Model):
    _name = 'construction.work.progress.line'
    _description = 'Construction Work Progress Line'

    work_progress_id = fields.Many2one(
        'construction.work.progress',
        string='Work Progress'
    )
    sequence = fields.Integer(
        default=10
    )
    description = fields.Char(
        string='Description'
    )
    work_item_id = fields.Many2one(
        'construction.work.item',
        string='Work Item'
    )
    quantity = fields.Float(
        string='Quantity',
        default=1,
        compute='_compute_quantity_price_uom_subtotal',
        store=True
    )
    price_unit = fields.Float(
        string='Price Unit',
        compute='_compute_quantity_price_uom_subtotal',
        store=True
    )
    uom = fields.Many2one(
        comodel_name='uom.uom',
        string='UOM',
        compute='_compute_quantity_price_uom_subtotal',
        store=True
    )
    subtotal = fields.Float(
        string='Subtotal',
        compute='_compute_quantity_price_uom_subtotal',
        store=True
    )
    last_works = fields.Float(
        string='Last Works',
        compute='_compute_last_works',
        store=True
    )
    current_works = fields.Float(
        string='Current Works'
    )
    total_works = fields.Float(
        string='Total Works',
        compute='_compute_total_works',
        store=True
    )
    remaining_qty = fields.Float(
        "Remaining Quantity" ,
        compute='_compute_remaining_qty',
        store=True
    )
    current_value = fields.Float(
        string='Current Value',
        compute='_compute_current_value',
        store=True
    )
    progress_per = fields.Float(
        string='Progress',
        compute='_compute_progress_per',
        store=True
    )
    total_value = fields.Float(
        string='Total Value',
        compute='_compute_total_value',
        store=True,
        inverse='_inverse_total_value'
    )

    @api.depends('work_item_id')
    def _compute_quantity_price_uom_subtotal(self):
        for line in self:
            if line.work_item_id:
                item = line.work_item_id
                line.quantity = item.quantity
                line.price_unit = item.price_unit
                line.uom = item.uom
                line.subtotal = item.quantity * item.price_unit

    @api.depends('work_item_id')
    def _compute_last_works(self):
        item_ids = self.mapped('work_item_id.id')
        all_confirmed_lines = self.sudo().search([
            ('work_item_id', 'in', item_ids),
            ('work_progress_id.state', '=', 'confirm')
        ])
        data_dict = {}
        for line in all_confirmed_lines:
            data_dict.setdefault(line.work_item_id.id, []).append(line)
        for line in self:
            if not line.work_item_id:
                line.last_works = 0.0
                continue
            previous_lines = data_dict.get(line.work_item_id.id, [])
            line.last_works = sum(
                prev.current_works for prev in previous_lines
                if prev.work_progress_id.work_progress_no < line.work_progress_id.work_progress_no
            )

    @api.depends('last_works', 'current_works')
    def _compute_total_works(self):
        for line in self:
            line.total_works = line.last_works + line.current_works

    @api.depends('quantity', 'last_works', 'current_works')
    def _compute_remaining_qty(self):
        for line in self:
            line.remaining_qty = line.quantity - line.total_works

    @api.depends('price_unit', 'current_works')
    def _compute_current_value(self):
        for line in self:
            line.current_value = line.price_unit * line.current_works

    @api.depends('quantity', 'last_works', 'current_works')
    def _compute_progress_per(self):
        for line in self:
            total_works = line.last_works + line.current_works
            qty = line.quantity
            line.progress_per = total_works / qty if qty > 0.0 else 0.0

    @api.depends('price_unit', 'last_works', 'current_works')
    def _compute_total_value(self):
        for line in self:
            done_works = line.last_works + line.current_works
            line.total_value = done_works * line.price_unit

    def _inverse_total_value(self):
        for line in self:
            entered_value = line.total_value
            expected = line.subtotal * (
                (line.last_works + line.current_works) / line.work_item_id.quantity if line.work_item_id.quantity > 0 else 0.0
            )
            if abs(entered_value - expected) > 0.01:
                msg = Markup(
                    f'<span style="color: #999999; text-decoration: line-through;">{expected:,.2f}</span> '
                    f'<span style="color: #5f5f5f; margin: 0 5px;">➔</span> '
                    f'<span style="color: #00A09D; font-weight: bold;">{line.total_value:,.2f}</span> '
                    f'<span style="color: #777777; font-style: italic; margin-left: 5px;">({line.work_item_id.name})</span>'
                )
                line.work_progress_id.message_post(body=msg)
        pass

    @api.model_create_multi
    def create(self, vals_list):
        current_request_items = []
        for vals in vals_list:
            wp_id = vals.get('work_progress_id')
            item_id = vals.get('work_item_id')
            if wp_id and item_id:
                check_key = (wp_id, item_id)
                if check_key in current_request_items:
                    raise ValidationError(
                        "Cannot create work progress, there is duplicated work items in work progress lines"
                    )
                current_request_items.append(check_key)
                duplicate = self.sudo().search_count([
                    ('work_progress_id', '=', wp_id),
                    ('work_item_id', '=', item_id)
                ])
                if duplicate > 0:
                    raise ValidationError(
                        "cannot add this work item, it's already existed in this work progress"
                    )
        return super(ConstructionLines, self).create(vals_list)

    # 1) prevent duplicated work items in same work progress while editing
    def write(self, vals):
        if 'work_item_id' in vals:
            new_item_id = vals.get('work_item_id')
            wp_ids = self.mapped('work_progress_id').ids
            duplicate = self.sudo().search_count([
                ('work_progress_id', 'in', wp_ids),
                ('work_item_id', '=', new_item_id),
                ('id', 'not in', self.ids)
            ])
            if duplicate > 0:
                raise ValidationError(
                    "this work item is already existed in this work progress"
                )
        res = super(ConstructionLines, self).write(vals)
        return res