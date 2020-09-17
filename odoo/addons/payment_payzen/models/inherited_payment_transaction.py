# coding: utf8

import base64
import datetime
import json
import logging
# from urllib2 import HTTPError, Request, urlopen
import requests

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
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

API_ENDPOINT = 'https://api.payzen.eu/api-payment'
REQUEST_ORDER_GET_URL = '%s/V4/Order/Get' % API_ENDPOINT
URLOPEN_TIMEOUT = 10
PAYZEN_VALID_TX_STATUS = ['PAID']
PAYZEN_PENDING_TX_STATUS = ['RUNNING']
PAYZEN_INVALID_TX_STATUS = ['UNPAID']

class PayzenTransaction(models.Model):
    _inherit = 'payment.transaction'

    payzen_status = fields.Char(
        string='Status',
        help='Status from PayZen WebService',
    )

    payzen_returned_data = fields.Text(
        string='Returned data',
        help='Data returned from PayZen WebService',
    )

    is_payzen = fields.Boolean(
        compute='_compute_is_payzen',
        search='_search_is_payzen',
    )

    @api.multi
    @api.depends('acquirer_id')
    def _compute_is_payzen(self):
        """Define if a transaction is a PayZen transaction."""
        for rec in self:
            rec.is_payzen = rec.acquirer_id and rec.acquirer_id.provider == 'payzen'

    @api.multi
    def _search_is_payzen(self, operator, value):
        """
        Search for 'is_payzen' field.

        :param operator: Operator used for research.
        :type operator: str
        :param value: Value used for research.
        :type value: str
        :return: Search domain
        :rtype: array
        """
        if operator not in ['=', '!=']:
            raise NotImplementedError("Got operator '%s' (expected '=' or '!=')" % operator)

        search_domain = [('acquirer_id.provider', '=', 'payzen')]

        # Negative domain if research on negation
        if bool(operator not in expression.NEGATIVE_TERM_OPERATORS) != bool(value):
            search_domain.insert(0, expression.NOT_OPERATOR)

        return search_domain

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
        if signature != transactions.acquirer_id.payzen_generate_digital_sign(data):
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

        transaction_status = data.get('vads_trans_status')

        values = {
            'state_message': VADS_AUTH_RESULT.get(data.get('vads_auth_result')),
            'acquirer_reference': data.get('vads_trans_uuid'),
            'payzen_status': transaction_status,
            'payzen_returned_data': json.dumps(data, indent=4, separators=(',', ': ')),
        }

        if transaction_status == 'ACCEPTED':
            # Statut d'une transaction de type VERIFICATION dont l'autorisation ou la demande de renseignement a été
            # acceptée.
            _logger.info('Validated Payzen payment for transaction %s: set as done' % self.reference)
            values['state'] = 'done'
            values['date_validate'] = fields.Datetime.now()
        elif transaction_status == 'AUTHORISED':
            # La transaction est acceptée et sera remise en banque automatiquement à la date prévue.
            _logger.info('Validated Payzen payment for transaction %s: set as done' % self.reference)
            values['state'] = 'done'
            values['date_validate'] = fields.Datetime.now()
        elif transaction_status == 'AUTHORISED_TO_VALIDATE':
            # La transaction, créée en validation manuelle, est autorisée. Le marchand doit valider manuellement la
            # transaction afin qu'elle soit remise en banque.
            _logger.info('Validated Payzen payment for transaction %s: set as done' % self.reference)
            values['state'] = 'authorized'
            values['date_validate'] = fields.Datetime.now()
        elif transaction_status == 'CAPTURED':
            # La transaction est remise en banque.
            _logger.info('Validated Payzen payment for transaction %s: set as done' % self.reference)
            values['state'] = 'authorized'
            values['date_validate'] = fields.Datetime.now()
        elif transaction_status == 'CANCELLED':
            # La transaction est annulée par le marchand.
            _logger.info('Validated Payzen payment for transaction %s: set as cancelled' % self.reference)
            values['state'] = 'cancel'
        elif transaction_status == 'ABANDONED':
            # Paiement abandonné par l’acheteur.
            _logger.info('Validated Payzen payment for transaction %s: set as cancelled' % self.reference)
            values['state'] = 'cancel'
        elif transaction_status == 'INITIAL':
            # Ce statut est spécifique à tous les moyens de paiement nécessitant une intégration par formulaire de
            # paiement en redirection.
            _logger.info('Validated Payzen payment for transaction %s: set as pending' % self.reference)
            values['state'] = 'pending'
        elif transaction_status == 'UNDER_VERIFICATION':
            # Pour les transactions PayPal, cette valeur signifie que PayPal retient la transaction pour suspicion de
            # fraude.
            # Le paiement restera dans l’onglet Transactions en cours jusqu'à ce que les vérifications soient achevées.
            # La transaction prendra alors l'un des statuts suivants: AUTHORISED ou CANCELED.
            _logger.info('Validated Payzen payment for transaction %s: set as pending' % self.reference)
            values['state'] = 'pending'
        elif transaction_status == 'WAITING_AUTHORISATION':
            # Le délai de remise en banque est supérieur à la durée de validité de l'autorisation.
            _logger.info('Validated Payzen payment for transaction %s: set as pending' % self.reference)
            values['state'] = 'pending'
        elif transaction_status == 'WAITING_AUTHORISATION_TO_VALIDATE':
            # Le délai de remise en banque est supérieur à la durée de validité de l'autorisation.
            _logger.info('Validated Payzen payment for transaction %s: set as pending' % self.reference)
            values['state'] = 'pending'
        elif transaction_status == 'CAPTURE_FAILED':
            # La remise de la transaction a échoué.
            _logger.info('Validated Payzen payment for transaction %s: set as error' % self.reference)
            values['state'] = 'error'
        elif transaction_status == 'EXPIRED':
            # La date d'expiration de la demande d'autorisation est atteinte et le marchand n’a pas validé la
            # transaction. Le porteur ne sera donc pas débité.
            _logger.info('Validated Payzen payment for transaction %s: set as error' % self.reference)
            values['state'] = 'error'
        elif transaction_status == 'NOT_CREATED':
            # La transaction n'est pas créée et n'est pas visible dans le Back Office Marchand.
            _logger.info('Validated Payzen payment for transaction %s: set as error' % self.reference)
            values['state'] = 'error'
        elif transaction_status == 'REFUSED':
            # La transaction est refusée.
            _logger.info('Validated Payzen payment for transaction %s: set as error' % self.reference)
            values['state'] = 'error'
        elif transaction_status == 'SUSPENDED':
            # La remise de la transaction est temporairement bloquée par l'acquéreur (AMEX GLOBAL ou SECURE TRADING).
            # Une fois la remise traitée correctement, le statut de la transaction deviendra CAPTURED.
            _logger.info('Validated Payzen payment for transaction %s: set as error' % self.reference)
            values['state'] = 'error'
        else:
            _logger.info('Validated Payzen payment for transaction %s: set as error' % self.reference)
            values['state'] = 'error'

        return self.write(values)

    def _payzen_s2s_validate(self):
        tree = self._payzen_s2s_get_tx_status() or {}
        return self._payzen_s2s_validate_tree(tree)

    def _payzen_s2s_validate_tree(self, tree, tries=2):
        if self.state not in ('draft', 'pending'):
            _logger.info('Payzen: trying to validate an already validated tx (ref %s)', self.reference)
            return True

        status = tree.get('status', '')
        if status in PAYZEN_VALID_TX_STATUS:
            self.write({
                'state': 'done',
                'date_validate': datetime.date.today().strftime(DEFAULT_SERVER_DATE_FORMAT),
            })
            return True
        elif status in PAYZEN_PENDING_TX_STATUS:
            self.write({
                'state': 'pending',
            })
            return True
        elif status in PAYZEN_INVALID_TX_STATUS:
            self.write({
                'state': 'cancel',
            })
            return True

        return False

    def _payzen_s2s_get_tx_status(self):
        if not self.sale_order_id:
            return False

        acquirer = self.acquirer_id

        user = acquirer.payzen_api_user
        password = False
        if acquirer.environment == 'test':
            password = acquirer.payzen_api_test_password
        elif acquirer.environment == 'prod':
            password = acquirer.payzen_api_prod_password

        authorization = '%s:%s' % (user, password)
        encoded_authorization = base64.b64encode(authorization)

        response = requests.post(
            REQUEST_ORDER_GET_URL,
            data=json.dumps({"orderId": self.sale_order_id.name}),
            headers={
                'Content-Type': 'application/json',
                'Authorization': 'Basic %s' % encoded_authorization,
            })

        if response.status_code != requests.codes.ok:
            return False

        data = json.loads(response.content)

        if data['status'] == 'ERROR':
            _logger.warn(_("Failed to call {} for payment transaction {}: {}".format(
                REQUEST_ORDER_GET_URL, self.id, data['answer']['errorMessage']
            )))
            return False

        if 'transactions' not in data['answer']:
            return False

        return data['answer']['transactions'][0]
