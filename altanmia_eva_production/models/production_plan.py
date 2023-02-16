import math

from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError, ValidationError


class ProductionPlan(models.Model):
    _name = "production.plan"
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

    production_type = fields.Selection([
        ('tmp', 'Products'),
        ('var', 'Variant'),
    ], string="Production Level", default='tmp')

    @api.model
    def create(self, vals):
        vals['ref'] = self.env['ir.sequence'].next_by_code('prod.plan.ref')
        return super(ProductionPlan, self).create(vals)

    def _default_production_line(self):
        if not self.season_id:
            return []

        if self.production_type == 'tmp':
            return [Command.create(
                {
                    'product_id': prod.product_variant_id.id,
                    'product_template_id': prod.id,
                }) for prod in self.season_id.product_template_id]
        else:
            return [Command.create(
                {
                    'product_id': prod.id,
                    'product_template_id': prod.product_tmpl_id.id,
                }) for prod in self.season_id.product_id]

    @api.onchange('production_type')
    def _onchange_production_type(self):
        if self.production_type == 'tmp':
            self.production_line = [(5, 0, 0)] + [Command.create(
                {
                    'product_id': prod.product_variant_id.id,
                    'product_template_id': prod.id,
                }) for prod in self.season_id.product_template_id]
        else:
            self.production_line = [(5, 0, 0)] + [Command.create(
                {
                    'product_id': prod.id,
                    'product_template_id': prod.product_tmpl_id.id,
                }) for prod in self.season_id.product_id]

    @api.onchange('season_id')
    def _onchange_season_id(self):
        if self.season_id:
            self.production_line = [(5,0,0)]+[Command.create({'product_id': prod.id}) for prod in self.season_id.product_id]

    season_id = fields.Many2one('season', 'Season')

    distribution_plan = fields.Many2one('distribution.plan', 'Distribution Plan')

    production_line = fields.One2many('production.plan.line', 'plan_id', "Production Line",
                                    tracking=True, domain=[('product_id','!=', False)], default=_default_production_line)

    mrp_orders_count = fields.Integer('# MRP Orders', compute='_compute_orders_count')

    state = fields.Selection([
        ('draft', "Draft"),
        ('confirm', "Confirm"),
        ('mrp', "Manufacturing"),
        ('stored', "Stored"),
    ], default='draft', string="Status")

    def _compute_orders_count(self):
        self.mrp_orders_count = self.env['mrp.production'].search_count([('plan_id', '=', self.id)])

    def action_confirm(self):
        for rec in self:

            for line in rec.production_line:
                rec.create_mrp_orders(line)

            rec.write({'state': 'confirm'})

    def create_mrp_orders(self, line):
        if line.production_amount == 0:
            return

        dist_total = 0
        locations = self.distribution_plan.location_line.filtered(lambda l: l.percentage > 0)
        for loc in locations:

            loc_qty = math.floor(line.production_amount * loc.percentage / 100)
            dist_total += loc_qty
            if loc == locations[-1]:
                loc_qty += line.production_amount - dist_total

            if loc_qty == 0:
                continue

            products = [line.product_id] if line.product_id else line.product_template_id.product_variant_ids

            for prod in products:

                self.env['mrp.production'].create({
                    'product_id': prod.id,
                    'plan_id': self.id,
                    'product_qty': loc_qty,
                    'location_dest_id': loc.location_id.id,
                    'location_src_id': loc.cmp_source_location_id.id
                })

    def action_mrp_production_show(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("mrp.mrp_production_action")
        action['domain'] = [('plan_id', '=', self.id)]
        return action

    def action_manufacture(self):
        for rec in self:
            orders = self.env['mrp.production'].search([('plan_id', '=', self.id)])
            for order in orders:
                order.action_confirm()
            rec.write({'state': 'mrp'})

    @api.onchange('distribution_plan')
    def _onchange_distribution_plan(self):
        for rec in self:
            if not rec.distribution_plan:
                return

            for line in rec.production_line:
                line.production_amount = rec.distribution_plan.default_production_amount
                line._compute_dest_location()

class ProductionPlanLine(models.Model):
    _name = "production.plan.line"
    _inherit = ["mail.thread", 'mail.activity.mixin']

    plan_id = fields.Many2one(
        comodel_name='production.plan',
        string="Production Plan Reference",
        required=True, ondelete='cascade', index=True, copy=False)

    company_id = fields.Many2one(
        related='plan_id.company_id', store=True, index=True, readonly=True)

    # Generic configuration fields
    product_id = fields.Many2one(
        comodel_name='product.product',
        string="Product",
        change_default=True, ondelete='restrict', check_company=True)

    product_template_id = fields.Many2one(
        comodel_name='product.template',
        string="Product Template",
        domain=[('sale_ok', '=', True)])

    production_amount = fields.Integer("Production Amount", default=0)

    loc_dist = fields.Html("Distribution Locations", compute="_compute_dest_location")

    def _compute_dest_location(self):
        for rec in self:
            if not rec.plan_id.distribution_plan:
                rec.loc_dist = ""

            loc = ""
            for line in rec.plan_id.distribution_plan.location_line:
                if line.percentage == 0:
                    continue
                loc += "<span class='loc-name'>%s</span> <span " \
                       "class='loc-percent'>%s&#37</span>" % (line.location_id.complete_name
                                                          if rec.plan_id.distribution_plan.distribution_type == 'location'
                                                          else line.warehouse_id.name, line.percentage)
            rec.loc_dist = loc
