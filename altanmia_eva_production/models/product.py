from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError, ValidationError


class ProductInherit(models.Model):
    _inherit ="product.product"

    season_id = fields.Many2one('season', 'Season')

    color = fields.Integer(compute="_compute_color")

    def _compute_color(self):
        for rec in self:
            rec.color = rec.product_tmpl_id.id % 10


class ProductTemplateInherit(models.Model):
    _inherit = "product.template"

    season_id = fields.Many2one('season', 'Season')