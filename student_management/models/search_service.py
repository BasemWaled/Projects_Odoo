from odoo import models, api


class StudentSearchService(models.AbstractModel):
    _name = 'student.search.service'
    _description = 'Public Search Service'

    @api.model
    def search_persons(self, name, is_student, is_teacher, is_staff):
        """Search across student, teacher, and staff models.

        Returns a list of dicts with keys: name, record_type, res_id.
        Uses ORM domain search so Postgres index on each name field is hit.
        Falls back to searching all three models when every flag is False.
        """
        domain = [('name', 'ilike', name or '')]
        search_all = not (is_student or is_teacher or is_staff)

        rows = []
        if is_student or search_all:
            rows += [
                {'name': r.name, 'record_type': 'student', 'res_id': r.id}
                for r in self.env['student.student'].search(domain)
            ]
        if is_teacher or search_all:
            rows += [
                {'name': r.name, 'record_type': 'teacher', 'res_id': r.id}
                for r in self.env['teacher.teacher'].search(domain)
            ]
        if is_staff or search_all:
            rows += [
                {'name': r.name, 'record_type': 'staff', 'res_id': r.id}
                for r in self.env['staff.staff'].search(domain)
            ]
        return rows
