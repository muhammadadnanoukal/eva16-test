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

    season_id = fields.Many2one('season', 'Season')

    distribution_plan = fields.Many2one('distribution.plan', 'Distribution Plan')

    production_line = fields.One2many('production.plan.line', 'plan_id', "Production Line",
                                    tracking=True, domain=[('product_id','!=', False)], default=_default_production_line)

    mrp_orders_count = fields.Integer('# MRP Orders', compute='_compute_orders_count')

    project_task_count = fields.Integer('# MRP Orders', compute='_compute_task')

    dist_type =  fields.Selection(related='distribution_plan.distribution_type')

    state = fields.Selection([
        ('draft', "Draft"),
        ('confirm', "Confirm"),
        ('mrp', "Manufacturing"),
        ('stored', "Stored"),
    ], default='draft', string="Status")

    def _compute_orders_count(self):
        self.mrp_orders_count = self.env['mrp.production'].search_count([('plan_id', '=', self.id)])

    def _compute_task(self):
        self.project_task_count = self.env['project.task'].search_count([('production_plan_id', '=', self.id)])


    def action_confirm(self):
        for rec in self:

            for line in rec.production_line:
                rec.create_mrp_orders(line)

            rec.write({'state': 'confirm'})

    @api.onchange('production_type','season_id','distribution_plan')
    def _build_prod_lines(self):
        if not self.season_id:
            return

        amount = self.distribution_plan.default_production_amount if self.distribution_plan else 0
        if self.production_type == 'tmp':
            if self.distribution_plan:
                dist_total = 0
                locations = self.distribution_plan.location_line.filtered(lambda l: l.percentage > 0)
                lines = []
                for loc in locations:
                    loc_qty = math.floor(amount* loc.percentage / 100)
                    dist_total += loc_qty
                    if loc == locations[-1]:
                        loc_qty += amount - dist_total

                    if loc_qty <1:
                        continue
                    lines += [Command.create(
                    {
                        'product_id': prod.product_variant_id.id,
                        'product_template_id': prod.id,
                        'production_amount': loc_qty,
                        'dist_location_id': loc.location_id,
                        'dist_warehouse_id': loc.warehouse_id,
                        'dist_cmp_source_location_id': loc.cmp_source_location_id,
                        'dist_cmp_source_warehouse_id':loc.cmp_source_warehouse_id

                    }) for prod in self.season_id.product_template_id]
                
                self.production_line = [(5, 0, 0)] + lines
                    
            else:
                self.production_line = [(5, 0, 0)] + [Command.create(
                    {
                        'product_id': prod.product_variant_id.id,
                        'product_template_id': prod.id,
                        'production_amount': amount,
                    }) for prod in self.season_id.product_template_id]
        else:
            if self.distribution_plan:
                dist_total = 0
                locations = self.distribution_plan.location_line.filtered(lambda l: l.percentage > 0)
                lines = []
                for loc in locations:
                    loc_qty = math.floor(amount* loc.percentage / 100)
                    dist_total += loc_qty
                    if loc == locations[-1]:
                        loc_qty += amount - dist_total

                    if loc_qty <1:
                        continue
                    lines += [Command.create(
                    {
                        'product_id': prod.id,
                        'product_template_id': prod.product_tmpl_id.id,
                        'production_amount': loc_qty,
                        'dist_location_id': loc.location_id,
                        'dist_warehouse_id': loc.warehouse_id,
                        'dist_cmp_source_location_id': loc.cmp_source_location_id,
                        'dist_cmp_source_warehouse_id':loc.cmp_source_warehouse_id

                    }) for prod in self.season_id.product_id]
                
                self.production_line = [(5, 0, 0)] + lines
            else:
                self.production_line = [(5, 0, 0)] + [Command.create(
                {
                    'product_id': prod.id,
                    'product_template_id': prod.product_tmpl_id.id,
                    'production_amount': amount,
                }) for prod in self.season_id.product_id]

   
    def create_mrp_orders(self, line):
        if line.production_amount == 0:
            return

        products = [line.product_id] if self.production_type=='var' else line.product_template_id.product_variant_ids

        for prod in products:

            prod_order =  self.env['mrp.production'].create({
                    'product_id': prod.id,
                    'plan_id': self.id,
                    'analytic_account_id': self.season_id.project_id.analytic_account_id.id,
                    'product_qty': line.production_amount,
                    'location_dest_id': line.dist_location_id.id,
                    'location_src_id': line.dist_cmp_source_location_id.id
                })
            if self.season_id.project_id:
                variant = prod.product_template_attribute_value_ids._get_combination_name()
                name = variant and "%s (%s)" % (prod.name, variant) or prod.name
                task = self.env['project.task'].create({'project_id': self.season_id.project_id.id,
                                                    'production_plan_id': self.id,
                                                    'name': "%s - Produce [%s] %s" % (prod_order.name,line.production_amount, name)}) \

                prod_order.write({'project_task_id': task.id,})

    def action_mrp_production_show(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("mrp.mrp_production_action")
        action['domain'] = [('plan_id', '=', self.id)]
        return action

    def action_project_task_show(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("project.act_project_project_2_project_task_all")
        action['domain'] = [('production_plan_id', '=', self.id)]
        action['context'] = {
            'default_project_id': self.season_id.project_id.id,
            'show_project_update': True,
            'active_id':self.season_id.project_id.id
        }

        return action

    def action_manufacture(self):
        for rec in self:
            orders = self.env['mrp.production'].search([('plan_id', '=', self.id)])
            for order in orders:
                order.action_confirm()
            rec.write({'state': 'mrp'})


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

    dist_location_id = fields.Many2one(
        'stock.location', 'Location',
        domain=[('usage', 'in', ['internal', 'transit'])],
        auto_join=True, ondelete='restrict',  index=True, check_company=True)

    dist_warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse", check_company=True)

    dist_cmp_source_location_id = fields.Many2one(
        'stock.location', 'Component source Location',
        domain=[('usage', 'in', ['internal', 'transit'])],
        auto_join=True, ondelete='restrict',  index=True, check_company=True)

    dist_cmp_source_warehouse_id = fields.Many2one('stock.warehouse', string="Component source Warehouse", check_company=True)

    @api.onchange('dist_warehouse_id')
    def _onchange_dist_warehouse_id(self):
        self.dist_location_id = self.dist_warehouse_id.lot_stock_id

    @api.onchange('dist_cmp_source_warehouse_id')
    def _onchange_dist_cmp_source_warehouse_id(self):
        self.dist_cmp_source_location_id = self.dist_cmp_source_warehouse_id.lot_stock_id


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
