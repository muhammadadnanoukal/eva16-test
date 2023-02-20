from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError, ValidationError


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    plan_id = fields.Many2one("production.plan", 'Production Plan')

    project_task_id = fields.Many2one('project.task', 'Project Task')