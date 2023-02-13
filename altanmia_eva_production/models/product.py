from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError, ValidationError


class Product(models.Model):
    _inherit ="product.product"

    season_id = fields.Many2one('season', 'Season')


class ProductTemplate(models.Model):
    _inherit = "product.template"

    season_id = fields.Many2one('season', 'Season')