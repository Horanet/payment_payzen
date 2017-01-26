# coding: utf8

import logging

from odoo import _, api, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare

_logger = logging.getLogger(__name__)

VADS_AUTH_RESULT = {
    '00': _('Approved or successfully processed transaction'),
    '02': _('Contact the card issuer'),
    '03': _('Invalid acceptor'),
    '04': _('Keep the card'),
    '05': _('Do not honor'),
    '07': _('Keep the card, special conditions'),
    '08': _('Confirm after identification'),
    '12': _('Invalid transaction'),
    '13': _('Invalid amount'),
    '14': _('Invalid cardholder number'),
    '15': _('Unknown issuer'),
    '17': _('Canceled by the buyer'),
    '19': _('Retry later'),
    '20': _('Incorrect response (error on the domain server)'),
    '24': _('Unsupported file update'),
    '25': _('Unable to locate the registered elements in the file'),
    '26': _('Duplicate registration, the previous record has been replaced'),
    '27': _('File update edit error'),
    '28': _('Denied access to file'),
    '29': _('Unable to update'),
    '30': _('Format error'),
    '31': _('Unknown acquirer company ID'),
    '33': _('Expired card'),
    '34': _('Fraud suspected'),
    '38': _('Expired card'),
    '41': _('Lost card'),
    '43': _('Stolen card'),
    '51': _('Insufficient balance or exceeded credit limit'),
    '54': _('Expired card'),
    '55': _('Invalid cardholder number'),
    '56': _('Card absent from the file'),
    '57': _('Transaction not allowed to this cardholder'),
    '58': _('Transaction not allowed to this cardholder'),
    '59': _('Suspected fraud'),
    '60': _('Card acceptor must contact the acquirer'),
    '61': _('Withdrawal limit exceeded'),
    '63': _('Security rules unfulfilled'),
    '68': _('Response not received or received too late'),
    '75': _('Number of attempts for entering the secret code has been exceeded'),
    '76': _('The cardholder is already blocked, the previous record has been saved'),
    '90': _('Temporary shutdown'),
    '91': _('Unable to reach the card issuer'),
    '94': _('Transaction duplicated'),
    '96': _('System malfunction'),
    '97': _('Overall monitoring timeout'),
    '98': _('Server not available, new network route requested'),
    '99': _('Initiator domain incident'),
    '000': _('Approved'),
    '001': _('Approve with ID'),
    '002': _('Partial Approval (Prepaid Cards only)'),
    '100': _('Declined'),
    '101': _('Expired Card / Invalid Expiration Date'),
    '106': _('Exceeded PIN attempts'),
    '107': _('Please Call Issuer'),
    '109': _('Invalid merchant'),
    '110': _('Invalid amount'),
    '111': _('Invalid account / Invalid MICR (Travelers Cheque)'),
    '115': _('Requested function not supported'),
    '117': _('Invalid PIN'),
    '119': _('Cardmember not enrolled / not permitted'),
    '122': _('Invalid card security code (a.k.a., CID, 4DBC, 4CSC)'),
    '125': _('Invalid effective date'),
    '181': _('Format error'),
    '183': _('Invalid currency code'),
    '187': _('Deny — New card issued'),
    '189': _('Deny — Account canceled'),
    '200': _('Deny — Pick up card'),
    '900': _('Accepted - ATC Synchronization'),
    '909': _('System malfunction (cryptographic error)'),
    '912': _('Issuer not available'),
}


class PayzenTransaction(models.Model):
    _inherit = 'payment.transaction'

    @api.model
    def _payzen_form_get_tx_from_data(self, data):
        """ Method called by form_feedback after the transaction

        :param data: data received from the acquirer after the transaction
        :return: payment.transaction record if retrieved or an exception
        """

        reference = data.get('vads_order_id').replace(' ', '/')
        transactions = self.sudo().search([('reference', '=', reference)])

        if not transactions or len(transactions) > 1:
            error_msg = 'Payzen: received bad data for reference {}'.format(reference)

            if not transactions:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'

            _logger.info(error_msg)
            raise ValidationError(error_msg)

        signature = data.get('signature')
        payzen_acquirer = self.env['payment.acquirer'].sudo().search([
            ('provider', '=', 'payzen')
        ])

        if signature != payzen_acquirer.payzen_generate_digital_sign(data):
            error_msg = _('Payzen: signatures mismatch')
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        return transactions

    @api.multi
    def _payzen_form_get_invalid_parameters(self, data):
        invalid_parameters = []

        if self.acquirer_reference and data.get('vads_trans_uuid') != self.acquirer_reference:
            invalid_parameters.append(
                ('vads_trans_uuid', data.get('vads_trans_uuid'), self.acquirer_reference)
            )

        if float_compare(float(data.get('vads_amount', '0.0')) / 100, (self.amount), 2) != 0:
            invalid_parameters.append(
                ('vads_amount', data.get('vads_amount'), '%.2f' % self.amount)
            )

        if self.partner_id.id and int(data.get('vads_cust_id')) != self.partner_id.id:
            invalid_parameters.append(
                ('vads_cust_id', data.get('vads_cust_id'), self.partner_id.id)
            )

        if self.acquirer_id and data.get('vads_site_id') != self.acquirer_id.payzen_shop_id:
            invalid_parameters.append(
                ('vads_shop_id', data.get('vads_site_id'), self.acquirer_id.payzen_shop_id)
            )

        return invalid_parameters

    @api.multi
    def _payzen_form_validate(self, data):
        """Check the status of the transaction and set it accordingly

        :param data: data received from payzen at the end of transaction
        """
        self.ensure_one()

        values = {
            'state_message': VADS_AUTH_RESULT.get(data.get('vads_auth_result')),
            'acquirer_reference': data.get('vads_trans_uuid')
        }

        transaction_status = data.get('vads_trans_status')

        if transaction_status == 'AUTHORISED':
            _logger.info('Validated Payzen payment for transaction %s: set as done' % self.reference)
            values['state'] = 'done'
        elif transaction_status == 'AUTHORISED_TO_VALIDATE':
            _logger.info('Validated Payzen payment for transaction %s: set as done' % self.reference)
            values['state'] = 'authorized'
        elif transaction_status == 'ABANDONED':
            _logger.info('Validated Payzen payment for transaction %s: set as cancelled' % self.reference)
            values['state'] = 'cancel'
        elif transaction_status == 'INITIAL':
            _logger.info('Validated Payzen payment for transaction %s: set as pending' % self.reference)
            values['state'] = 'pending'
        else:
            _logger.info('Validated Payzen payment for transaction %s: set as error' % self.reference)
            values['state'] = 'error'

        return self.write(values)
