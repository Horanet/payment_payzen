{
    'name': 'Payzen Payment Acquirer',
    'version': '11.0.1.0.0',
    'summary': 'Payment Acquirer: Payzen Implementation',
    'author': "Horanet",
    'website': "http://www.horanet.com/",
    'license': "AGPL-3",
    'category': 'Accounting',
    'external_dependencies': {
        'python': []
    },
    'depends': [
        # --- Odoo --- #
        'payment'
        # --- External --- #

        # --- Horanet --- #
    ],
    'css': [],
    'qweb': [],
    'init_xml': [],
    'update_xml': [],
    'data': [
        'views/payment_views.xml',
        'views/payment_payzen_templates.xml',

        'data/payment_acquirer.xml',
    ],
    'demo': [],
    'application': False,
    'auto_install': False,
    'installable': True,
    'post_init_hook': 'post_init_hook',
}
