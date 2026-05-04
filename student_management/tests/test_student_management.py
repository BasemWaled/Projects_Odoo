from datetime import date

from dateutil.relativedelta import relativedelta

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestStudentManagement(TransactionCase):
    """
    setUpClass records are shared across all test methods — never mutate them
    inside a test or state leaks to later methods.
    For stale stored computed fields, call invalidate_recordset() before asserting.
    M2M command (6, 0, [ids]) replaces the full set; (4, id) appends one record —
    mixing both in the same write produces unexpected set sizes.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Teacher = cls.env['teacher.teacher']
        cls.Student = cls.env['student.student']
        cls.Course = cls.env['course.course']
        cls.Staff = cls.env['staff.staff']

        cls.teacher = cls.Teacher.create({
            'name': 'Alice Smith',
            'subject': 'Mathematics',
            'age': 35,
        })
        cls.student1 = cls.Student.create({
            'name': 'Bob Jones',
            'date_of_birth': '2000-01-15',
        })
        cls.student2 = cls.Student.create({
            'name': 'Carol White',
            'date_of_birth': '1998-06-20',
        })

    # --- Age computation ---

    def test_age_computed_from_dob(self):
        expected = relativedelta(date.today(), date(2000, 1, 15)).years
        self.assertEqual(self.student1.age, expected)

    def test_age_zero_without_dob(self):
        student = self.Student.create({'name': 'No DOB', 'date_of_birth': False})
        self.assertEqual(student.age, 0)

    # --- Age validation ---

    def test_underage_student_rejected(self):
        with self.assertRaises(ValidationError):
            self.Student.create({'name': 'Too Young', 'date_of_birth': '2015-01-01'})

    def test_over_60_student_rejected(self):
        with self.assertRaises(ValidationError):
            self.Student.create({'name': 'Too Old', 'date_of_birth': '1950-01-01'})

    def test_boundary_age_18_accepted(self):
        dob_18 = date.today() - relativedelta(years=18)
        student = self.Student.create({
            'name': 'Boundary 18',
            'date_of_birth': dob_18.strftime('%Y-%m-%d'),
        })
        self.assertEqual(student.age, 18)

    def test_boundary_age_60_accepted(self):
        dob_60 = date.today() - relativedelta(years=60)
        student = self.Student.create({
            'name': 'Boundary 60',
            'date_of_birth': dob_60.strftime('%Y-%m-%d'),
        })
        self.assertEqual(student.age, 60)

    def test_age_recomputes_on_dob_write(self):
        student = self.Student.create({
            'name': 'DOB Update Test',
            'date_of_birth': '2000-06-01',
        })
        age_before = student.age
        new_dob = date.today() - relativedelta(years=30)
        student.write({'date_of_birth': new_dob.strftime('%Y-%m-%d')})
        student.invalidate_recordset()
        self.assertNotEqual(student.age, age_before)
        self.assertEqual(student.age, 30)

    # --- Course teacher constraint ---

    def test_course_without_teacher_rejected(self):
        with self.assertRaises(Exception):
            self.Course.create({'name': 'No Teacher Course'})

    def test_course_with_teacher_created(self):
        course = self.Course.create({
            'name': 'Valid Course',
            'teacher_id': self.teacher.id,
        })
        self.assertEqual(course.teacher_id, self.teacher)

    # --- Average age ---

    def test_average_age_no_students(self):
        course = self.Course.create({
            'name': 'Empty Course',
            'teacher_id': self.teacher.id,
        })
        self.assertEqual(course.average_age, 0.0)

    def test_average_age_single_student(self):
        course = self.Course.create({
            'name': 'Solo Course',
            'teacher_id': self.teacher.id,
            'student_ids': [(6, 0, [self.student1.id])],
        })
        self.assertAlmostEqual(course.average_age, float(self.student1.age), places=1)

    def test_average_age_multiple_students(self):
        course = self.Course.create({
            'name': 'Multi Student Course',
            'teacher_id': self.teacher.id,
            'student_ids': [(6, 0, [self.student1.id, self.student2.id])],
        })
        expected = (self.student1.age + self.student2.age) / 2.0
        self.assertAlmostEqual(course.average_age, expected, places=1)

    def test_average_age_updates_on_enrolment(self):
        course = self.Course.create({
            'name': 'Growing Course',
            'teacher_id': self.teacher.id,
            'student_ids': [(6, 0, [self.student1.id])],
        })
        self.assertAlmostEqual(course.average_age, float(self.student1.age), places=1)
        course.write({'student_ids': [(4, self.student2.id)]})
        expected = (self.student1.age + self.student2.age) / 2.0
        self.assertAlmostEqual(course.average_age, expected, places=1)

    # --- Enrolment notifications ---

    def test_enrolment_notifies_on_create(self):
        course = self.Course.create({
            'name': 'Notify On Create Course',
            'teacher_id': self.teacher.id,
            'student_ids': [(6, 0, [self.student1.id])],
        })
        course.invalidate_recordset(['message_ids'])
        enrolment_msgs = course.message_ids.filtered(
            lambda m: 'enrolled' in (m.body or '').lower()
        )
        self.assertTrue(enrolment_msgs, "Expected enrolment chatter message after create()")

    def test_enrolment_notifies_on_write(self):
        course = self.Course.create({
            'name': 'Notify On Write Course',
            'teacher_id': self.teacher.id,
        })
        msg_count_before = len(course.message_ids)
        course.write({'student_ids': [(4, self.student1.id)]})
        course.invalidate_recordset()
        self.assertGreater(len(course.message_ids), msg_count_before)

    def test_no_notification_when_no_students_added(self):
        course = self.Course.create({
            'name': 'Silent Write Course',
            'teacher_id': self.teacher.id,
        })
        msg_count_before = len(course.message_ids)
        course.write({'description': 'Updated description'})
        course.invalidate_recordset()
        self.assertEqual(len(course.message_ids), msg_count_before)

    # --- Name search ---

    def test_name_search_returns_match(self):
        result = self.Student.name_search('Bob')
        matched_names = [r[1] for r in result]
        self.assertTrue(any('Bob' in n for n in matched_names))

    def test_name_search_case_insensitive(self):
        result = self.Student.name_search('bob')
        matched_names = [r[1] for r in result]
        self.assertTrue(any('Bob' in n for n in matched_names))

    def test_teacher_name_search(self):
        result = self.Teacher.name_search('Alice')
        self.assertTrue(len(result) >= 1)

    def test_staff_name_search(self):
        staff = self.Staff.create({'name': 'Dave Admin', 'position': 'Admin'})
        result = self.Staff.name_search('Dave')
        matched_ids = [r[0] for r in result]
        self.assertIn(staff.id, matched_ids)


class TestUnifiedSearch(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Wizard = cls.env['student.search.wizard']
        cls.student = cls.env['student.student'].create({
            'name': 'Search Student Alpha',
            'date_of_birth': '2000-03-10',
        })
        cls.teacher = cls.env['teacher.teacher'].create({
            'name': 'Search Teacher Beta',
            'subject': 'Physics',
            'age': 40,
        })
        cls.staff = cls.env['staff.staff'].create({
            'name': 'Search Staff Gamma',
            'position': 'Admin',
        })

    def _run_search(self, name='', is_student=True, is_teacher=True, is_staff=True):
        wizard = self.Wizard.create({
            'name': name,
            'is_student': is_student,
            'is_teacher': is_teacher,
            'is_staff': is_staff,
        })
        wizard.action_search()
        return wizard

    def test_search_all_models_by_name(self):
        wizard = self._run_search(name='Search')
        result_names = wizard.result_ids.mapped('name')
        self.assertIn(self.student.name, result_names)
        self.assertIn(self.teacher.name, result_names)
        self.assertIn(self.staff.name, result_names)

    def test_search_returns_student_record(self):
        wizard = self._run_search(name='Alpha')
        self.assertEqual(len(wizard.result_ids), 1)
        self.assertEqual(wizard.result_ids[0].name, self.student.name)
        self.assertEqual(wizard.result_ids[0].record_type, 'student')

    def test_search_returns_teacher_record(self):
        wizard = self._run_search(name='Beta')
        self.assertEqual(len(wizard.result_ids), 1)
        self.assertEqual(wizard.result_ids[0].name, self.teacher.name)
        self.assertEqual(wizard.result_ids[0].record_type, 'teacher')

    def test_search_returns_staff_record(self):
        wizard = self._run_search(name='Gamma')
        self.assertEqual(len(wizard.result_ids), 1)
        self.assertEqual(wizard.result_ids[0].name, self.staff.name)
        self.assertEqual(wizard.result_ids[0].record_type, 'staff')

    def test_filter_students_only(self):
        wizard = self._run_search(name='Search', is_student=True, is_teacher=False, is_staff=False)
        types = set(wizard.result_ids.mapped('record_type'))
        self.assertIn('student', types)
        self.assertNotIn('teacher', types)
        self.assertNotIn('staff', types)

    def test_filter_teachers_only(self):
        wizard = self._run_search(name='Search', is_student=False, is_teacher=True, is_staff=False)
        types = set(wizard.result_ids.mapped('record_type'))
        self.assertNotIn('student', types)
        self.assertIn('teacher', types)
        self.assertNotIn('staff', types)

    def test_filter_staff_only(self):
        wizard = self._run_search(name='Search', is_student=False, is_teacher=False, is_staff=True)
        types = set(wizard.result_ids.mapped('record_type'))
        self.assertNotIn('student', types)
        self.assertNotIn('teacher', types)
        self.assertIn('staff', types)

    def test_all_unchecked_searches_all_three(self):
        # All unchecked falls back to searching all three models.
        wizard = self._run_search(name='Search', is_student=False, is_teacher=False, is_staff=False)
        types = set(wizard.result_ids.mapped('record_type'))
        self.assertIn('student', types)
        self.assertIn('teacher', types)
        self.assertIn('staff', types)

    def test_empty_results_for_nonexistent_name(self):
        wizard = self._run_search(name='ZZZ_NoSuchRecord_XYZ')
        self.assertEqual(len(wizard.result_ids), 0)

    def test_blank_name_returns_records(self):
        wizard = self._run_search(name='')
        result_names = wizard.result_ids.mapped('name')
        self.assertIn(self.student.name, result_names)
        self.assertIn(self.teacher.name, result_names)
        self.assertIn(self.staff.name, result_names)

    def test_result_stores_res_id(self):
        wizard = self._run_search(name='Alpha')
        self.assertEqual(wizard.result_ids[0].res_id, self.student.id)

    def test_action_search_returns_act_window(self):
        wizard = self.Wizard.create({
            'name': 'Search',
            'is_student': True,
            'is_teacher': False,
            'is_staff': False,
        })
        action = wizard.action_search()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_id'], wizard.id)
        self.assertEqual(action['target'], 'new')
