from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError, ValidationError


class Season(models.Model):
    _name = "season"
    _inherit = ["mail.thread", 'mail.activity.mixin']

    name = fields.Char("Name", tracking=True)
    ref = fields.Char(string="Reference")
    active = fields.Boolean(string="active", default=True, tracking=True)
    company_id = fields.Many2one(
        'res.company', 'Company', index=True,
        default=lambda self: self.env.company)


    # Generic configuration fields
    product_id = fields.One2many('product.product', 'season_id', "Product varient", tracking=True)

    product_template_id = fields.One2many('product.template', 'season_id', "Product", tracking=True)


    @api.model
    def create(self, vals):
        vals['ref'] = self.env['ir.sequence'].next_by_code('season.ref')
        return super(Season, self).create(vals)

class SeasonLine(models.Model):
    _name = "season.line"

    company_id = fields.Many2one(
        related='season_id.company_id', store=True, index=True, readonly=True)

    season_id = fields.Many2one(
        comodel_name='season',
        string="Season Reference",
        required=True, ondelete='cascade', index=True, copy=False)

    # Generic configuration fields
    product_id = fields.Many2one(
        comodel_name='product.product',
        string="Product",
        change_default=True, ondelete='restrict', check_company=True)

    product_template_id = fields.Many2one(
        string="Product Template",
        related='product_id.product_tmpl_id',
        domain=[('sale_ok', '=', True)])