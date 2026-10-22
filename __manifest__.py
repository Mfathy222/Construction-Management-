{
    'name': 'Construction',
    'author': 'SijilAcc',
    'version': '19.0.0.1.1',
    'license': 'LGPL-3',
    'application': True,
    'installable': True,
    'data': [
        'security/ir.model.access.csv',
        'views/menus.xml',
        'views/contract.xml',
        'views/work_progress.xml',
        'views/work_item.xml',
        'wizards/change_price_view.xml',
        'wizards/pay_retention_view.xml',
        'views/res_config_settings_views.xml',
        'views/product_template.xml',
        'data/sequences.xml',
        'views/account_move.xml',
        'reports/work_progress_report_inline.xml',

    ],
    'depends': ['base', 'mail','accountant', ], #account @ odoo community
}
