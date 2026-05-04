import logging

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class Course(models.Model):
    _name = 'course.course'
    _description = 'Course'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Name', required=True, index=True, tracking=True)
    description = fields.Text(string='Description')
    teacher_id = fields.Many2one(
        'teacher.teacher',
        string='Teacher',
        required=True,
        ondelete='restrict',
        tracking=True,
        index=True,
    )
    student_ids = fields.Many2many(
        'student.student',
        'course_student_rel',
        'course_id',
        'student_id',
        string='Students',
    )
    # If another module adds a staff_id with a different relation on this model,
    # the last one loaded wins and the other breaks silently. Safe options: rename
    # (e.g. sm_staff_id) or declare an explicit dependency on the conflicting module.
    staff_id = fields.Many2one(
        'staff.staff',
        string='Staff',
        ondelete='set null',
        index=True,
    )
    average_age = fields.Float(
        string='Average Student Age',
        compute='_compute_average_age',
        store=True,
        readonly=True,
        digits=(5, 1),
    )

    @api.depends('student_ids.age')
    def _compute_average_age(self):
        for course in self:
            students = course.student_ids
            course.average_age = sum(students.mapped('age')) / len(students) if students else 0.0

    def _notify_teacher_on_enrolment(self, added_student_ids):
        """Post a chatter note when students are added to this course.

        Safe to override in other modules — always call super() first so that
        every module in the chain fires, not just the last one loaded.
        Notification runs in the current user's context; company and record-level
        access is enforced by ir.rule, so no hardcoded company filtering is needed.
        To debug: run with --log-level=debug and check the _logger output below;
        if it never appears, added_student_ids was empty before this was called.
        """
        self.ensure_one()
        added_students = self.env['student.student'].browse(list(added_student_ids))
        student_names = ', '.join(added_students.mapped('name'))
        body = _("New student enrolled in %s: %s") % (self.name, student_names)
        _logger.debug(
            "Course '%s': notifying teacher '%s' about new students: %s",
            self.name, self.teacher_id.name, student_names,
        )

        # Existing internal note visible to all course followers.
        self.message_post(
            body=body,
            subtype_xmlid='mail.mt_note',
        )

        # If the teacher has a linked user, send a direct message and schedule an activity.
        if self.teacher_id.user_id:
            partner = self.teacher_id.user_id.partner_id
            self.message_post(
                body=body,
                partner_ids=[partner.id],
                subtype_xmlid='mail.mt_comment',
            )
            activity_type = self.env.ref(
                'mail.mail_activity_data_todo', raise_if_not_found=False
            )
            if activity_type:
                self.env['mail.activity'].create({
                    'res_model_id': self.env['ir.model']._get(self._name).id,
                    'res_id': self.id,
                    'user_id': self.teacher_id.user_id.id,
                    'summary': _('New student enrolled'),
                    'note': body,
                    'activity_type_id': activity_type.id,
                })

    @api.model_create_multi
    def create(self, vals_list):
        # In Odoo 18, super().create() writes Many2many rows directly to the DB
        # without populating the ORM cache. Extract student IDs from vals before
        # calling super() so the notification has them regardless.
        pending_students = []
        for vals in vals_list:
            ids = set()
            for cmd in vals.get('student_ids', []):
                if cmd[0] == 6:
                    ids.update(cmd[2])
                elif cmd[0] == 4:
                    ids.add(cmd[1])
            pending_students.append(ids)

        courses = super().create(vals_list)

        for course, student_ids in zip(courses, pending_students):
            if student_ids and course.teacher_id:
                course._notify_teacher_on_enrolment(student_ids)

        return courses

    def write(self, vals):
        old_student_sets = {}
        if 'student_ids' in vals:
            old_student_sets = {course.id: set(course.student_ids.ids) for course in self}

        result = super().write(vals)

        if old_student_sets:
            for course in self:
                added_ids = set(course.student_ids.ids) - old_student_sets.get(course.id, set())
                if added_ids and course.teacher_id:
                    course._notify_teacher_on_enrolment(added_ids)

        return result
