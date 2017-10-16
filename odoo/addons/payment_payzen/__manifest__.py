# coding: utf8
{
    # Module name in English
    'name': 'Payzen Payment Acquirer',
    # Version, "odoo.min.yy.m.d"
    'version': '10.0.1.0.0',
    # Short description (with keywords)
    'summary': 'Payment Acquirer: Payzen Implementation',
    # Description with metadata (in french)
    'description': """Payzen Payment Acquirer""",
    'author': "Horanet",
    'website': "http://www.horanet.com/",
    # distribution license for the module (defaults: AGPL-3)
    'license': "AGPL-3",
    # Categories can be used to filter modules in modules listing. For the full list :
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    'category': 'Accounting',
    #
    'external_dependencies': {
        'python': []
    },
    # any module necessary for this one to work correctly. Either because this module uses features
    # they create or because it alters resources they define.
    'depends': [
        # --- Odoo --- #
        'payment'
        # --- External --- #

        # --- Horanet --- #
    ],
    # always loaded
    'css': [],
    'qweb': [],
    # list of XML files with data that will load to DB at moment when you install module
    'init_xml': [],
    # list of XML files with data that will load to DB at moment when you install or update module.
    'update_xml': [],
    # List of data files which must always be installed or updated with the module. A list of paths from the module root directory
    'data': [
        'views/payment_views.xml',
        'views/payment_payzen_templates.xml',

        'data/payment_acquirer.xml',
    ],
    # only loaded in demonstration mode
    'demo': [],
    'application': False,
    'auto_install': False,
    # permet d'installer automatiquement le module si toutes ses dépendances sont installés
    # -default value set is False
    # -If false, the dependent modules are not installed if not installed prior to the dependent module.
    # -If True, all corresponding dependent modules are installed at the time of installing this module.
    'installable': True,
    # -True, module can be installed.
    # -False, module is listed in application, but cannot install them.

    'post_init_hook': 'set_currencies_codes'
}
