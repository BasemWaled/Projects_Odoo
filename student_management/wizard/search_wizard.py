from odoo import models, fields, _


class StudentSearchWizard(models.TransientModel):
    _name = 'student.search.wizard'
    _description = 'Public Person Search'

    name = fields.Char(string='Name')
    is_student = fields.Boolean(string='Students', default=True)
    is_teacher = fields.Boolean(string='Teachers', default=True)
    is_staff = fields.Boolean(string='Staff', default=True)
    result_ids = fields.One2many('student.search.result', 'wizard_id', string='Results')

    def action_search(self):
        self.result_ids.unlink()

        rows = self.env['student.search.service'].search_persons(
            self.name, self.is_student, self.is_teacher, self.is_staff,
        )

        if rows:
            self.env['student.search.result'].create([
                dict(wizard_id=self.id, **row) for row in rows
            ])

        return {
            'type': 'ir.actions.act_window',
            'name': _('Public Search'),
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }


class StudentSearchResult(models.TransientModel):
    _name = 'student.search.result'
    _description = 'Public Search Result'
    _order = 'record_type, name'

    wizard_id = fields.Many2one(
        'student.search.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    name = fields.Char(string='Name', readonly=True)
    record_type = fields.Selection([
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('staff', 'Staff'),
    ], string='Type', readonly=True)
    res_id = fields.Integer(string='Record ID', readonly=True)
