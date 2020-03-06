# coding: utf8

from lxml import objectify

from odoo.addons.payment.tests.common import PaymentAcquirerCommon
from odoo.exceptions import ValidationError
from odoo.tests import common

from odoo.tools import mute_logger

@common.post_install(True)
class PayzenCommon(PaymentAcquirerCommon):
    def setUp(self):
        super(PayzenCommon, self).setUp()

        self.payzen = self.env['payment.acquirer'].search([('provider', '=', 'payzen')])


@common.post_install(True)
class PayzenForm(PayzenCommon):

    def test_00_payzen_form_render(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')

        # be sure not to do stupid things
        self.assertEqual(self.payzen.environment, 'test', 'test without test environment')
        self.payzen.payzen_shop_id = 'dummy'

        firstname = self.buyer_values.get('partner_name').split(' ')[0]
        lastname = self.buyer_values.get('partner_name').split(' ')[1]

        self.buyer_values.update({
            'partner_first_name': firstname,
            'partner_last_name': lastname,
            'partner_id': self.buyer_id
        })

        # ----------------------------------------
        # Test: button direct rendering
        # ----------------------------------------

        # Render the button
        res = self.payzen.render(
            'testref0',
            0.01,
            self.currency_euro.id,
            values=self.buyer_values
        )

        form_values = {
            'vads_site_id': 'dummy',
            'vads_amount': '1',
            'vads_currency': '978',
            # 'vads_trans_date': ignored
            # 'vads_trans_id': ignored
            'vads_ctx_mode': 'TEST',
            'vads_page_action': 'PAYMENT',
            'vads_action_mode': 'INTERACTIVE',
            'vads_payment_config': 'SINGLE',
            'vads_version': 'V2',
            'vads_return_mode': 'GET',
            # 'vads_url_return': ignored
            'vads_order_id': 'testref0',

            'vads_cust_id': str(self.buyer_id),
            'vads_cust_first_name': self.buyer_values.get('partner_first_name')[0:62],
            'vads_cust_last_name': self.buyer_values.get('partner_last_name')[0:62],
            'vads_cust_address': self.buyer_values.get('partner_address')[0:254],
            'vads_cust_zip': self.buyer_values.get('partner_zip')[0:62],
            'vads_cust_city': self.buyer_values.get('partner_city')[0:62],
            'vads_cust_state': self.buyer_values.get('partner_state') and self.buyer_values.get('partner_state').name[0:127] or '',
            'vads_cust_country': self.buyer_values.get('partner_country').code,
            'vads_cust_email': self.buyer_values.get('partner_email')[0:126],
            'vads_cust_phone': self.buyer_values.get('partner_phone')[0:31],

            # 'signature': ignored
        }

        # Check form result
        tree = objectify.fromstring(res)
        self.assertEqual(
            tree.get('action'),
            self.payzen.payzen_form_action_url,
            'payzen: wrong form POST URL'
        )

        for form_input in tree.input:
            if form_input.get('name') in ['submit']:
                continue

            # ignore values that are dynamically defined
            if form_input.get('name') in ['vads_trans_date', 'vads_trans_id',
                                          'vads_url_return', 'signature']:
                continue

            self.assertEqual(
                form_input.get('value'),
                form_values[form_input.get('name')],
                'payzen: wrong value for input %s: received %s instead of %s' % (
                    form_input.get('name'),
                    form_input.get('value'),
                    form_values[form_input.get('name')]
                )
            )
