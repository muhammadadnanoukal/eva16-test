from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError, ValidationError


class BomInherit(models.Model):
    """ Defines bills of material for a product or a product template """
    _inherit = 'mrp.bom'

    parent_id = fields.Many2one('mrp.bom', string='Template BOM', index=True)
    child_ids = fields.One2many('mrp.bom', 'parent_id', string='Variants BOM', domain=[('active', '=', True)])
    template_bom = fields.Boolean("Is template", default=False)

    @api.model
    def create(self, vals):

        res = super().create(vals)
        if not res.template_bom:
            return res
        if res.parent_id:
            return res

        template = res.product_tmpl_id
        for prod in template.product_variant_ids:
            values = {'product_id': prod.id, 'parent_id': res.id, 'template_bom': False}
            copy = res.copy(default=values)


        return res

    def unlink(self):
        for ch in self.child_ids:
            ch.unlink()
        super(BomInherit, self).unlink()

    def write(self, vals):

        write_result = super(BomInherit, self).write(vals)

        for ch in self.child_ids:
            ch.write(vals)

        return write_result

    def action_show_boms(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("altanmia_eva_production.action_variant_bom")
        action['domain'] = [('parent_id','=', self.id)]
        return action

class MrpBomLine(models.Model):
    _name = 'mrp.bom.line'
    _inherit = 'mrp.bom.line'

    product_id = fields.Many2one('product.product', 'Component', required=False, check_company=True)
    product_template_id = fields.Many2one('product.template', 'Product Template', store=True, index=True)

    @api.model_create_multi
    def create(self, vals_list):
        res=None
        print("vals_list ", vals_list)
        for values in vals_list:
            print("values is ", values)
            if not values.get("product_id", False) and values.get('product_template_id', False):
                print("product tem", values['product_template_id'])
                template = self.env['product.template'].browse(values['product_template_id'])
                first = True
                for prod in template.product_variant_ids:
                    if first:
                        print("first line", prod.name)
                        values.update({'product_id': prod.id})
                        res = super(MrpBomLine, self).create(values)
                        first = False
                        continue
                    print("next line", prod.name)
                    values = {'product_id': prod.id}
                    copy = res.copy(default=values)

        print("add line is ", res)
        if not res:
            res = super(MrpBomLine, self).create(vals_list)

        return res

    @api.onchange('product_template_id')
    def onchange_product_template_id(self):
        if self.product_template_id:
            self.product_uom_id = self.product_template_id.uom_id.id