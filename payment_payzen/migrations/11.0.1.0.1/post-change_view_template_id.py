import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Migrate v10 to v11.

    - Set payzen_form as view_template_id for all existing payzen acquirers
    """
    if not version:
        return

    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})

        payzen_form = env.ref('payment_payzen.payzen_form')
        payzen_acquirers = env['payment.acquirer'].with_context(active_test=False).search([
            ('provider', '=', 'payzen')
        ])
        payzen_acquirers.write({'view_template_id': payzen_form.id})
