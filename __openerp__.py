# -*- coding: utf-8 -*-
{
    'name': "Payzen Payment Acquirer",
    'version': '8.0.16.15.12',
    'summary': 'Interface de gestion des factures',
    'author': "Horanet",
    'website': "http://www.horanet.com/",
    'license': "AGPL-3",
    'contributors': [
        'Alexandre Papin',
        'Adrien Didenot'
    ],
    'depends': [
        # --- Odoo --- #
        'account',
        'payment',
        'account_voucher',

        # --- External --- #

        # --- Horanet --- #
    ],
    'data': [
        'views/inherited_res_config_view.xml',
        'views/payzen.xml',
        'views/payment_acquirer.xml',
        'data/payzen.xml',
    ],
    'installable': True,
}
