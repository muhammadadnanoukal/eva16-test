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
    product_id = fields.One2many('product.product', 'season_id', "Variants", tracking=True)

    product_template_id = fields.One2many('product.template', 'season_id', "Products", store=True, tracking=True)

    project_id = fields.Many2one('project.project', 'Project',
                                 help="Project link to season help you to deal with all manufacturing orders as tasks "
                                      "in project.\n "
                                      "If you let it empty, a new project will be created automatically")

    @api.onchange('product_template_id','product_id')
    def _onchange_product_template_id(self):
        for rec in self:
            prods = []
            for tmp in rec.product_template_id:
                prods += [prod.id for prod in tmp.product_variant_ids]
            rec.product_id = [(5,0,0)] + [(6,0,prods)]


    @api.model
    def create(self, vals):
        vals['ref'] = self.env['ir.sequence'].next_by_code('season.ref')

        if not vals['project_id']:
            vals['project_id'] = self.env['project.project'].create({'name':vals['name'] + " Project"}).id
        return super(Season, self).create(vals)