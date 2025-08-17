# -*- coding: utf-8 -*-
{
    'name': 'Owl Javascript ',
    'version': '1.0',
    'category': 'OWL',
    'author': 'BaSeM_WaLiD',
    'summary': 'Technical Training - Introduction to OWL by Odoo',
    'website': 'https://www.odoo.com/slides/technical-training-introduction-to-owl-454',
    'sequence': -1,
    'depends': ['sale'],
    'data': [
        'views/sale_order_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # Add OWL JS files here if needed
            'technical_training_owl/static/src/components/example/example.xml',
            'technical_training_owl/static/src/components/example/example.js'

        ],
    },
    'application': True,
    'installable': True,
    'auto_install': False,
}