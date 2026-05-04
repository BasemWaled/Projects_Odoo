{
    'name': 'Student Management',
    'version': '18.0.1.0.0',
    'category': 'Education',
    'summary': 'Manage students, teachers, courses, and staff',
    'description': """
Student Management
==================

Manage students, teachers, courses, and staff for an educational institution.

Features
--------
- Student records with date-of-birth-based age validation (18-60)
- Teacher and staff management
- Course assignments with average age tracking
- Chatter notifications on student enrolment
- Unified search across students, teachers, and staff
""",
    'author': 'Basem Walid',
    'license': 'LGPL-3',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/student_views.xml',
        'views/teacher_views.xml',
        'views/course_views.xml',
        'views/staff_views.xml',
        'wizard/search_wizard_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
