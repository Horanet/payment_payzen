# -*- coding: utf-8 -*-

from openerp import fields, models


class AccountPaymentConfig(models.TransientModel):
    """
    This allow users to install this module by ticking the corresponding
    checkbox in the accounting settings view
    """
    _inherit = 'account.config.settings'

    module_payment_payzen = fields.Boolean(
        string='Manage Payments Using Payzen',
        help='It installs the module payment_payzen'
    )
