from odoo import models, fields


class Teacher(models.Model):
    _name = 'teacher.teacher'
    _description = 'Teacher'
    _inherit = ['base.person', 'mail.thread', 'mail.activity.mixin']
    _order = 'name'

    subject = fields.Char(string='Subject')
    user_id = fields.Many2one(
        'res.users',
        string='Linked User', required=True,
        help='System user that receives enrolment notifications for this teacher.',
    )
