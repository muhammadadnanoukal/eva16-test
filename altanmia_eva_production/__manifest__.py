# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Eva Production',
    'version' : '1.0.0',
    'summary': 'Eva Clothes Shop ',
    'sequence': -50,
    'description': """
            Eva Production
            ====================
            Description
                """,
    'category': 'Manufacturing/Manufacturing',
    'website': 'https://www.odoo.com/app/invoicing',
    'images' : [],
    'depends' : ['mail','stock','mrp'],
    'data': [
        'views/bom_view.xml',
        'views/season_view.xml',
        'views/product_view.xml',
        'views/dist_plan_view.xml',
        'views/main_menu.xml',
        'data/sequence_data.xml',
        'security/eva_security.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'assets': {},
    'license': 'LGPL-3',
}
