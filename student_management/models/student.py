from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Student(models.Model):
    _name = 'student.student'
    _description = 'Student'
    _inherit = ['base.person', 'mail.thread', 'mail.activity.mixin']
    _order = 'name'

    age = fields.Integer(
        string='Age',
        compute='_compute_age',
        store=True,
        readonly=True,
        tracking=True,
    )
    date_of_birth = fields.Date(string='Date of Birth', tracking=True, required=True)
    document = fields.Binary(string='Document', attachment=True)
    document_name = fields.Char(string='Document Filename')

    @api.depends('date_of_birth')
    def _compute_age(self):
        today = fields.Date.today()
        for student in self:
            if student.date_of_birth:
                student.age = relativedelta(today, student.date_of_birth).years
            else:
                student.age = 0

    # @api.depends triggers recomputation whenever a listed field changes.
    # @api.constrains runs after every write that touches the listed fields and
    # should raise ValidationError to reject the change — it never returns a value.

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            dob = vals.get('date_of_birth')
            if dob:
                if isinstance(dob, str):
                    dob = fields.Date.from_string(dob)
                age = relativedelta(fields.Date.today(), dob).years
                if not (18 <= age <= 60):
                    raise ValidationError(
                        _("Student age must be between 18 and 60. "
                          "The provided date of birth gives an age of %d.") % age
                    )
        # super() runs the full ORM pipeline (SQL write, computed fields,
        # mail.thread init) and every other create() in the inheritance chain.
        return super().create(vals_list)

    @api.constrains('date_of_birth')
    def _check_age_range(self):
        for student in self:
            if student.date_of_birth:
                age = relativedelta(fields.Date.today(), student.date_of_birth).years
                if not (18 <= age <= 60):
                    raise ValidationError(_("Student age must be between 18 and 60."))
