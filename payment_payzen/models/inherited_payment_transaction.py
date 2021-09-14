import datetime
import json
import logging
import requests
from json import JSONDecodeError
from requests import Timeout, TooManyRedirects
from requests.auth import HTTPBasicAuth

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare

_logger = logging.getLogger(__name__)

VADS_AUTH_RESULT = {
    '00': _("Approved or successfully processed transaction"),
    '02': _("Contact the card issuer"),
    '03': _("Invalid acceptor"),
    '04': _("Keep the card"),
    '05': _("Do not honor"),
    '07': _("Keep the card, special conditions"),
    '08': _("Confirm after identification"),
    '12': _("Invalid transaction"),
    '13': _("Invalid amount"),
    '14': _("Invalid cardholder number"),
    '15': _("Unknown issuer"),
    '17': _("Canceled by the buyer"),
    '19': _("Retry later"),
    '20': _("Incorrect response (error on the domain server)"),
    '24': _("Unsupported file update"),
    '25': _("Unable to locate the registered elements in the file"),
    '26': _("Duplicate registration, the previous record has been replaced"),
    '27': _("File update edit error"),
    '28': _("Denied access to file"),
    '29': _("Unable to update"),
    '30': _("Format error"),
    '31': _("Unknown acquirer company ID"),
    '33': _("Expired card"),
    '34': _("Fraud suspected"),
    '38': _("Expired card"),
    '41': _("Lost card"),
    '43': _("Stolen card"),
    '51': _("Insufficient balance or exceeded credit limit"),
    '54': _("Expired card"),
    '55': _("Invalid cardholder number"),
    '56': _("Card absent from the file"),
    '57': _("Transaction not allowed to this cardholder"),
    '58': _("Transaction not allowed to this cardholder"),
    '59': _("Suspected fraud"),
    '60': _("Card acceptor must contact the acquirer"),
    '61': _("Withdrawal limit exceeded"),
    '63': _("Security rules unfulfilled"),
    '68': _("Response not received or received too late"),
    '75': _("Number of attempts for entering the secret code has been exceeded"),
    '76': _("The cardholder is already blocked, the previous record has been saved"),
    '90': _("Temporary shutdown"),
    '91': _("Unable to reach the card issuer"),
    '94': _("Transaction duplicated"),
    '96': _("System malfunction"),
    '97': _("Overall monitoring timeout"),
    '98': _("Server not available, new network route requested"),
    '99': _("Initiator domain incident"),
    '000': _("Approved"),
    '001': _("Approve with ID"),
    '002': _("Partial Approval (Prepaid Cards only)"),
    '100': _("Declined"),
    '101': _("Expired Card / Invalid Expiration Date"),
    '106': _("Exceeded PIN attempts"),
    '107': _("Please Call Issuer"),
    '109': _("Invalid merchant"),
    '110': _("Invalid amount"),
    '111': _("Invalid account / Invalid MICR (Travelers Cheque)"),
    '115': _("Requested function not supported"),
    '117': _("Invalid PIN"),
    '119': _("Cardmember not enrolled / not permitted"),
    '122': _("Invalid card security code (a.k.a., CID, 4DBC, 4CSC)"),
    '125': _("Invalid effective date"),
    '181': _("Format error"),
    '183': _("Invalid currency code"),
    '187': _("Deny — New card issued"),
    '189': _("Deny — Account canceled"),
    '200': _("Deny — Pick up card"),
    '900': _("Accepted - ATC Synchronization"),
    '909': _("System malfunction (cryptographic error)"),
    '912': _("Issuer not available"),
}


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

    # region Model methods
    @api.model
    def _payzen_form_get_tx_from_data(self, data):
        """ Method called by form_feedback after the transaction

        :param data: data received from the acquirer after the transaction
        :return: payment.transaction record if retrieved or an exception
        """

        reference = data.get('vads_order_id').replace(' ', '/')
        transactions = self.sudo().search([('reference', '=', reference)])

        if not transactions or len(transactions) > 1:
            error_msg = "Payzen: received bad data for reference {}".format(reference)

            if not transactions:
                error_msg += "; no payment transaction found"
            else:
                error_msg += "; multiple payment transactions found"

            _logger.info(error_msg)
            raise ValidationError(error_msg)

        local_call = self.env.context.get('local_call', False)
        if not local_call:
            transactions._payzen_check_signature(data)

        return transactions

    @api.model
    def payzen_cron_check_draft_payment_transactions(self, minutes_min_check=7, hours_max_check=48):
        """Cron task method used to check all recent draft transactions status with Payzen

        This method will get all draft payment transactions and try to get their
        current Payzen status (like ipn return). We can use two param `minutes_min_check` and `hours_max_check

        :param minutes_min_check: We will take transactions with a creation date greater than this time in minutes
        :type minutes_min_check: int
        :param hours_max_check: We will take transactions with a creation date lower than this time in hours
        :type hours_max_check: int
        """
        # Search payzen acquirers
        payzen_acquirers = self.env['payment.acquirer'].search([
            ('provider', '=', 'payzen'),
        ])

        # Search waiting/draft payment transactions
        payment_transaction_ids = self.env['payment.transaction'].search([
            ('acquirer_id', 'in', payzen_acquirers.ids),
            ('state', 'in', ['draft', 'pending']),
            ('acquirer_reference', '=', False),
            ('create_date', '>=', fields.Datetime.to_string(
                datetime.datetime.now() - datetime.timedelta(hours=hours_max_check)
            )),
            ('create_date', '<=', fields.Datetime.to_string(
                datetime.datetime.now() - datetime.timedelta(minutes=minutes_min_check)
            )),
        ], order="create_date asc")
        if payment_transaction_ids:
            _logger.info(
                f"Payzen Check: Processing of these transactions {payment_transaction_ids.mapped('reference')}"
            )

        for payment_transaction_id in payment_transaction_ids:
            try:
                payment_transaction_id.action_payzen_check_transaction_status(wait=False)
            except Exception as e:
                # When raise exception we trace them in log but not lock the full checkout process
                _logger.warning(e)
                continue

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
            _logger.info("Validated Payzen payment for transaction %s: set as done" % self.reference)
            values['state'] = 'done'
            values['date_validate'] = fields.Datetime.now()
        elif transaction_status == 'AUTHORISED':
            # La transaction est acceptée et sera remise en banque automatiquement à la date prévue.
            _logger.info("Validated Payzen payment for transaction %s: set as done" % self.reference)
            values['state'] = 'done'
            values['date_validate'] = fields.Datetime.now()
        elif transaction_status == 'AUTHORISED_TO_VALIDATE':
            # La transaction, créée en validation manuelle, est autorisée. Le marchand doit valider manuellement la
            # transaction afin qu'elle soit remise en banque.
            _logger.info("Validated Payzen payment for transaction %s: set as done" % self.reference)
            values['state'] = 'authorized'
            values['date_validate'] = fields.Datetime.now()
        elif transaction_status == 'CAPTURED':
            # La transaction est remise en banque.
            _logger.info("Validated Payzen payment for transaction %s: set as done" % self.reference)
            values['state'] = 'authorized'
            values['date_validate'] = fields.Datetime.now()
        elif transaction_status == 'CANCELLED':
            # La transaction est annulée par le marchand.
            _logger.info("Validated Payzen payment for transaction %s: set as cancelled" % self.reference)
            values['state'] = 'cancel'
        elif transaction_status == 'ABANDONED':
            # Paiement abandonné par l’acheteur.
            _logger.info("Validated Payzen payment for transaction %s: set as cancelled" % self.reference)
            values['state'] = 'cancel'
        elif transaction_status == 'INITIAL':
            # Ce statut est spécifique à tous les moyens de paiement nécessitant une intégration par formulaire de
            # paiement en redirection.
            _logger.info("Validated Payzen payment for transaction %s: set as pending" % self.reference)
            values['state'] = 'pending'
        elif transaction_status == 'UNDER_VERIFICATION':
            # Pour les transactions PayPal, cette valeur signifie que PayPal retient la transaction pour suspicion de
            # fraude.
            # Le paiement restera dans l’onglet Transactions en cours jusqu'à ce que les vérifications soient achevées.
            # La transaction prendra alors l'un des statuts suivants: AUTHORISED ou CANCELED.
            _logger.info("Validated Payzen payment for transaction %s: set as pending" % self.reference)
            values['state'] = 'pending'
        elif transaction_status == 'WAITING_AUTHORISATION':
            # Le délai de remise en banque est supérieur à la durée de validité de l'autorisation.
            _logger.info("Validated Payzen payment for transaction %s: set as pending" % self.reference)
            values['state'] = 'pending'
        elif transaction_status == 'WAITING_AUTHORISATION_TO_VALIDATE':
            # Le délai de remise en banque est supérieur à la durée de validité de l'autorisation.
            _logger.info("Validated Payzen payment for transaction %s: set as pending" % self.reference)
            values['state'] = 'pending'
        elif transaction_status == 'CAPTURE_FAILED':
            # La remise de la transaction a échoué.
            _logger.info("Validated Payzen payment for transaction %s: set as error" % self.reference)
            values['state'] = 'error'
        elif transaction_status == 'EXPIRED':
            # La date d'expiration de la demande d'autorisation est atteinte et le marchand n’a pas validé la
            # transaction. Le porteur ne sera donc pas débité.
            _logger.info("Validated Payzen payment for transaction %s: set as error" % self.reference)
            values['state'] = 'error'
        elif transaction_status == 'NOT_CREATED':
            # La transaction n'est pas créée et n'est pas visible dans le Back Office Marchand.
            _logger.info("Validated Payzen payment for transaction %s: set as error" % self.reference)
            values['state'] = 'error'
        elif transaction_status == 'REFUSED':
            # La transaction est refusée.
            _logger.info("Validated Payzen payment for transaction %s: set as error" % self.reference)
            values['state'] = 'error'
        elif transaction_status == 'SUSPENDED':
            # La remise de la transaction est temporairement bloquée par l'acquéreur (AMEX GLOBAL ou SECURE TRADING).
            # Une fois la remise traitée correctement, le statut de la transaction deviendra CAPTURED.
            _logger.info("Validated Payzen payment for transaction %s: set as error" % self.reference)
            values['state'] = 'error'
        else:
            _logger.info(f"Validated Payzen payment for transaction {self.reference}: set as error. "
                         f"Receive Status : {transaction_status}")
            values['state'] = 'error'

        return self.write(values)

    @api.multi
    def action_payzen_check_transaction_status(self, wait=True):
        """Function for check payzen transaction status and recall IPN route."""
        self.ensure_one()

        _logger.info(f"Payzen Check : Start checking {self.reference} status")

        username = self.acquirer_id.payzen_shop_id
        password = self.acquirer_id.payzen_get_api_password()
        url = 'https://api.payzen.eu/api-payment/V4/Order/Get'

        # Get status from web service
        try:
            response = requests.post(
                url,
                json={'orderId': self.reference},
                headers={'Content-Type': 'application/json'},
                auth=HTTPBasicAuth(username, password),
                timeout=2,
            )
        except Timeout as e:
            raise Exception(f"Payzen Check : Timeout error on {url}: {e}")
        except ConnectionError as e:
            raise Exception(f"Payzen Check : Connection error on {url}: {e}")
        except TooManyRedirects as e:
            raise Exception(f"Payzen Check : TooManyRedirects error on {url}: {e}")
        except Exception as e:
            raise Exception(f"Payzen Check : Unexpected error on {url}: {e}")

        # Get json response from payload
        try:
            json_response = response.json()
        except (ValueError, JSONDecodeError):
            raise Exception(f"Payzen Check: An error occured on url {url}, JSON response can't be decoded."
                            f"Response from webservice :\n{response.text}")

        # Check transaction as been received by payzen before build our own ipn data
        # SEE https://payzen.io/fr-FR/rest/V4.0/api/errors-reference.html
        if json_response.get('answer', {}).get('errorCode', '') == 'PSP_010':
            self.write({
                'state': 'error',
                'payzen_status': 'PSP_010',
                'payzen_returned_data': json.dumps(json_response, indent=4, separators=(',', ': ')),
            })
            return

        # Get base url
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        # Check if we need to wait response
        timeout = None if wait else 30
        # Call ipn callback with data
        try:
            requests.post(
                f"{base_url}/payment/payzen/return",
                data=self._payzen_build_ipn_data_from_payzen_api(json_response),
                params={'local_call': True},
                timeout=timeout,
            )
        except Timeout:
            pass
        except Exception as e:
            raise Exception(f"Payzen Check : failed to call ipn on url {url}: {e}")

    @api.multi
    def _payzen_check_signature(self, data):
        self.ensure_one()
        # Get signature compute by Payzen
        signature = data.get('signature')
        # Compare Payzen signature and our own compute signature
        if signature != self.acquirer_id.payzen_generate_digital_sign(data):
            error_msg = _("Payzen: signatures mismatch")
            _logger.error(error_msg)
            raise ValidationError(error_msg)

    @staticmethod
    def _payzen_build_ipn_data_from_payzen_api(data):
        """Build Payzen IPN body from Payzen api data"""
        answer = data.get('answer', {})
        transactions = answer.get('transactions', [])

        if len(transactions) < 1:
            raise Exception(f"Payzen Check : Invalid data structure for build ipn body: {data}")
        transaction = transactions[0]

        return {
            "vads_order_id": answer.get("orderId", ""),
            "vads_trans_uuid": transaction.get("uuid", ""),
            "vads_amount": transaction.get("amount", 0),
            "vads_cust_id": transaction.get("customer", {}).get("reference", ""),
            "vads_site_id": transaction.get("shopId", ""),
            "vads_auth_result": transaction.get("detailedErrorCode", ""),
            "vads_trans_status": transaction.get("detailedStatus", ""),
        }

    # endregion
