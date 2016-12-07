# -*- coding: utf-8 -*-

from openerp import models, fields


class AccountPaymentConfig(models.TransientModel):
    _inherit = 'account.config.settings'

    module_payment_payzen = fields.Boolean(
        string='Manage Payments Using Payzen',
        help='It installs the module payment_payzen'
    )
