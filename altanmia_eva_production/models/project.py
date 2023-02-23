from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError, ValidationError


class Project(models.Model):
    _inherit = "project.project"

class Task(models.Model):
    _inherit = "project.task"

    mrp_order_ids = fields.One2many('mrp.production', 'project_task_id', "Manufacturing Orders")

    mrp_order_id = fields.Many2one('mrp.production', 'Manufacturing Order', compute='_compute_mrp_order')

    move_raw_ids = fields.One2many('stock.move', related="mrp_order_id.move_raw_ids", store=False)

    production_plan_id = fields.Many2one('production.plan', 'Production Plan')

    porder_state = fields.Selection(related="mrp_order_id.state", string="Production Order State", store=False)

    @api.depends('mrp_order_ids')
    def _compute_mrp_order(self):
        for p in self:
            p.mrp_order_id = p.mrp_order_ids[:1].id