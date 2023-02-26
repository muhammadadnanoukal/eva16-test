from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class PurchaseOrderLineInherit(models.Model):
    _inherit = "purchase.order.line"

    project_id = fields.Many2one("project.project", "Project")
    task_id = fields.Many2one("project.task", "Task", domain="[('project_id', '=', project_id)]")
    stage_id = fields.Many2one('project.task.type', string='Stage', store=False, related="task_id.stage_id")

    @api.onchange('project_id')
    def onchange_project_id(self):
        self.task_id = False