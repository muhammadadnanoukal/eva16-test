from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError, ValidationError


class DistributionPlan(models.Model):
    _name = "distribution.plan"
    _inherit = ["mail.thread", 'mail.activity.mixin']

    def _compute_name(self):
        for rec in self:
            rec.name = "Plan %s"%rec.ref

    name = fields.Char("name", compute="_compute_name")

    ref = fields.Char(string="Reference")
    active = fields.Boolean(string="active", default=True, tracking=True)
    company_id = fields.Many2one(
        'res.company', 'Company', index=True,
        default=lambda self: self.env.company)

    distribution_type = fields.Selection([
        ('warehouse', 'Warehouse'),
        ('location', 'Location'),
    ], string="Distribution Level", default='location')

    default_production_amount = fields.Integer("Default Production Amount")

    def _default_location(self):
        if self.distribution_type == 'warehouse':
            return [Command.create(
                {
                    'warehouse_id': wh.id,
                    'location_id': wh.lot_stock_id.id,
                    'cmp_source_warehouse_id': wh.id,
                    'cmp_source_location_id': wh.lot_stock_id.id
                }) for wh in self.env['stock.warehouse'].search([])]
        else:
            return [Command.create(
                {
                    'location_id': loc.id,
                    'warehouse_id': loc.warehouse_id.id,
                    'cmp_source_location_id': loc.id,
                    'cmp_source_warehouse_id': loc.warehouse_id.id
                }) for loc in self.env['stock.location'].search([('usage', 'in', ['internal', 'transit'])])]


    location_line = fields.One2many('distribution.loc', 'plane_id', "Location percentage",
                                    tracking=True, default=_default_location)


    @api.model
    def create(self, vals):
        vals['ref'] = self.env['ir.sequence'].next_by_code('dist.plan.ref')
        return super(DistributionPlan, self).create(vals)

    @api.onchange('distribution_type')
    def _onchange_distribution_type(self):
        if self.distribution_type == 'warehouse':
            self.location_line = [(5,0,0)] + [Command.create(
                {
                    'warehouse_id': wh.id,
                    'location_id': wh.lot_stock_id.id,
                    'cmp_source_warehouse_id': wh.id,
                    'cmp_source_location_id': wh.lot_stock_id.id
                }) for wh in self.env['stock.warehouse'].search([])]
        else:
            self.location_line = [(5,0,0)] + [Command.create(
                {
                    'location_id': loc.id,
                    'warehouse_id': loc.warehouse_id.id,
                    'cmp_source_location_id': loc.id,
                    'cmp_source_warehouse_id': loc.warehouse_id.id
                }) for loc in self.env['stock.location'].search([('usage', 'in', ['internal', 'transit'])])]

    @api.constrains('location_line')
    def validate_location_line(self):
        total = 0
        for record in self:
            for loc in record.location_line:
                total += loc.percentage
        if total != 100:
            raise ValidationError(_("Products should distributed as percentage 100 overall locations"))

class DistributionLocation(models.Model):
    _name = "distribution.loc"

    plane_id = fields.Many2one(
        comodel_name='distribution.plan',
        string="Distribution Plan Reference",
        required=True, ondelete='cascade', index=True, copy=False)

    company_id = fields.Many2one(
        related='plane_id.company_id', store=True, index=True, readonly=True)

    location_id = fields.Many2one(
        'stock.location', 'Location',
        domain=[('usage', 'in', ['internal', 'transit'])],
        auto_join=True, ondelete='restrict',  index=True, check_company=True)

    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse", check_company=True)

    cmp_source_location_id = fields.Many2one(
        'stock.location', 'Component source Location',
        domain=[('usage', 'in', ['internal', 'transit'])],
        auto_join=True, ondelete='restrict',  index=True, check_company=True)

    cmp_source_warehouse_id = fields.Many2one('stock.warehouse', string="Component source Warehouse", check_company=True)

    percentage = fields.Integer(string="Percentage", default=0)

    @api.constrains('percentage')
    def validate_percentage(self):
        for record in self:
            if record.percentage > 100 or record.percentage < 0:
                raise ValidationError(_("Percentage should be between 0 and 100"))
    
    @api.onchange('cmp_source_warehouse_id')
    def _onchange_cmp_source_warehouse_id(self):
        self.cmp_source_location_id = self.cmp_source_warehouse_id.lot_stock_id

    @api.onchange('cmp_source_location_id')
    def _onchange_cmp_source_location_id(self):
        self.cmp_source_warehouse_id = self.cmp_source_location_id.warehouse_id
