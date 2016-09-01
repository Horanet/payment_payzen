# -*- coding: utf-8 -*-
{
    'name': "Payzen Payment Acquirer",
    'version': '8.0.16.8.30',
    'summary': 'Interface de gestion des factures',
    'author': "Horanet",
    'website': "http://www.horanet.com/",
    'license': "AGPL-3",
    'contributors': [
        'Alexandre Papin',
        'Adrien Didenot'
    ],
    'depends': [
        'horanet_collectivity',
        'horanet_payment',
    ],
    'data': [
        'views/payzen.xml',
        'views/payment_acquirer.xml',
        'data/payzen.xml',
    ],
    'installable': True,
}
