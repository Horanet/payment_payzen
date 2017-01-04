# -*- coding: utf-8 -*-

import logging
import urlparse
from datetime import datetime
from hashlib import sha1

from openerp import api, fields, models
from openerp.addons.payment.models.payment_acquirer import ValidationError

_logger = logging.getLogger(__name__)

CURRENCY_CODE = {
    'EUR': 978,
    'USD': 840,
    'CAD': 124,
}


class AcquirerPayzen(models.Model):
    """ Acquirer Model. Each specific acquirer can extend the model by adding
    its own fields, using the acquirer_name as a prefix for the new fields.
    Using the required_if_provider='<name>' attribute on fields it is possible
    to have required fields that depend on a specific acquirer.

    Each acquirer has a link to an ir.ui.view record that is a template of
    a button used to display the payment form. See examples in ``payment_ogone``
    and ``payment_paypal`` modules.

    Methods that should be added in an acquirer-specific implementation:

     - ``<name>_form_generate_values(self, cr, uid, id, reference, amount, currency,
       partner_id=False, partner_values=None, tx_custom_values=None, context=None)``:
       method that generates the values used to render the form button template.
     - ``<name>_get_form_action_url(self, cr, uid, id, context=None):``: method
       that returns the url of the button form. It is used for example in
       ecommerce application, if you want to post some data to the acquirer.
     - ``<name>_compute_fees(self, cr, uid, id, amount, currency_id, country_id,
       context=None)``: computed the fees of the acquirer, using generic fields
       defined on the acquirer model (see fields definition).

    Each acquirer should also define controllers to handle communication between
    OpenERP and the acquirer. It generally consists in return urls given to the
    button form and that the acquirer uses to send the customer back after the
    transaction, with transaction details given as a POST request.
    """
    _inherit = 'payment.acquirer'

    @api.model
    def _get_providers(self):
        """Add payzen to providers and return it"""
        providers = super(AcquirerPayzen, self)._get_providers()
        providers.append(['payzen', 'Payzen'])
        return providers

    @api.model
    def get_payzen_urls(self):
        """Return payzen URL corresponding to current environment"""
        if self.environment == 'prod':
            return 'https://secure.payzen.eu/vads-payment/'
        else:
            return 'https://secure.payzen.eu/vads-payment/'

    payzen_websitekey = fields.Char(string='Website ID', required_if_provider='payzen')
    payzen_secretkey = fields.Char(string='SecretKey', required_if_provider='payzen')

    @api.model
    def _payzen_generate_digital_sign(self, acquirer, vads_values):
        """Returns signature required by payzen to ensure integrity

        :param acquirer: payment.acquirer record
        :param vads_values: transaction values
        :return: unique generated signature
        """

        signature = ''

        for key in sorted(vads_values.iterkeys()):
            if key.find('payzen_vads_') == 0:
                signature += str(vads_values[key]).decode('utf-8') + '+'

        signature += acquirer.payzen_secretkey
        shasign = sha1(signature.encode('utf-8')).hexdigest()

        return shasign

    @api.model
    def payzen_form_generate_values(self, acquirer_id, partner_values, tx_values):
        """Generates the values used to render the form button template

        :param acquirer_id: id of payment.acquirer to use
        :param partner_values: a dictionary of partner-related values
        :param tx_values: a dictionnary of transaction related values
        :return: partner_values and payzen_tx_values which is tx_values with more values
        """
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        acquirer = self.browse(acquirer_id)

        if acquirer.environment == 'test':
            mode = 'TEST'
        elif acquirer.environment == 'prod':
            mode = 'PRODUCTION'
        payzen_tx_values = dict(tx_values)
        payzen_tx_values.update({
            'payzen_vads_site_id': acquirer.payzen_websitekey,
            'payzen_vads_amount': int(tx_values['amount'] * 100),
            'payzen_vads_currency': CURRENCY_CODE.get(tx_values['currency'].name, 0),
            'payzen_vads_trans_date': datetime.utcnow().strftime('%Y%m%d%H%M%S'),
            'payzen_vads_trans_id': tx_values.get('transaction_number', '000000'),
            'payzen_vads_ctx_mode': mode,
            'payzen_vads_page_action': 'PAYMENT',
            'payzen_vads_action_mode': 'INTERACTIVE',
            'payzen_vads_payment_config': 'SINGLE',
            'payzen_vads_version': 'V2',
            'payzen_vads_url_return': urlparse.urljoin(base_url, tx_values.get('return_url', '')),
            'payzen_vads_return_mode': 'POST',
            'payzen_vads_order_id': tx_values.get('reference').replace('/', ''),
            # customer info
            'payzen_vads_cust_name': partner_values['name'] and partner_values['name'][0:126].encode('utf-8') or '',
            'payzen_vads_cust_first_name': partner_values['first_name'] and partner_values['first_name'][0:62].encode('utf-8') or '',
            'payzen_vads_cust_last_name': partner_values['last_name'] and partner_values['last_name'][0:62].encode('utf-8') or '',
            'payzen_vads_cust_address': partner_values['address'] and partner_values['address'][0:254].encode('utf-8'),
            'payzen_vads_cust_zip': partner_values['zip'] and partner_values['zip'][0:62].encode('utf-8') or '',
            'payzen_vads_cust_city': partner_values['city'] and partner_values['city'][0:62].encode('utf-8') or '',
            'payzen_vads_cust_state': partner_values['state'] and partner_values['state'].name[0:62].encode('utf-8') or '',
            'payzen_vads_cust_country': partner_values['country'].code and partner_values['country'].code.upper() or '',
            'payzen_vads_cust_email': partner_values['email'] and partner_values['email'][0:126].encode('utf-8') or '',
            'payzen_vads_cust_phone': partner_values['phone'] and partner_values['phone'][0:31].encode('utf-8') or '',
        })

        payzen_tx_values['payzen_signature'] = self._payzen_generate_digital_sign(acquirer, payzen_tx_values)

        return partner_values, payzen_tx_values

    @api.model
    def payzen_get_form_action_url(self, acquirer_id):
        """Returns the form action URL

        :param acquirer_id: id of the payment.acquirer to return urls
        :return: url corresponding to the environment
        """

        acquirer = self.browse(acquirer_id)
        return acquirer.get_payzen_urls()

_AUTH_RESULT = {
    '00': u'transaction approuvée ou traitée avec succès',
    '02': u'contacter l’émetteur de carte',
    '03': u'accepteur invalide',
    '04': u'conserver la carte',
    '05': u'ne pas honorer',
    '07': u'conserver la carte, conditions spéciales',
    '08': u'approuver après identification',
    '12': u'transaction invalide',
    '13': u'montant invalide',
    '14': u'numéro de porteur invalide',
    '15': u'Emetteur de carte inconnu',
    '17': u'Annulation client',
    '19': u'Répéter la transaction ultérieurement',
    '20': u'Réponse erronée (erreur dans le domaine serveur)',
    '24': u'Mise à jour de fichier non supportée',
    '25': u'Impossible de localiser l’enregistrement dans le fichier',
    '26': u'Enregistrement dupliqué, ancien enregistrement remplacé',
    '27': u'Erreur en « edit » sur champ de lise à jour fichier',
    '28': u'Accès interdit au fichier',
    '29': u'Mise à jour impossible',
    '30': u'erreur de format',
    '31': u'identifiant de l’organisme acquéreur inconnu',
    '33': u'date de validité de la carte dépassée',
    '34': u'suspicion de fraude',
    '38': u'Date de validité de la carte dépassée',
    '41': u'carte perdue',
    '43': u'carte volée',
    '51': u'provision insuffisante ou crédit dépassé',
    '54': u'date de validité de la carte dépassée',
    '55': u'Code confidentiel erroné',
    '56': u'carte absente du fichier',
    '57': u'transaction non permise à ce porteur',
    '58': u'transaction interdite au terminal',
    '59': u'suspicion de fraude',
    '60': u'l’accepteur de carte doit contacter l’acquéreur',
    '61': u'montant de retrait hors limite',
    '63': u'règles de sécurité non respectées',
    '68': u'réponse non parvenue ou reçue trop tard',
    '75': u'Nombre d’essais code confidentiel dépassé',
    '76': u'Porteur déjà en opposition, ancien enregistrement conservé',
    '90': u'arrêt momentané du système',
    '91': u'émetteur de cartes inaccessible',
    '94': u'transaction dupliquée',
    '96': u'mauvais fonctionnement du système',
    '97': u'échéance de la temporisation de surveillance globale',
    '98': u'serveur indisponible routage réseau demandé à nouveau',
    '99': u'incident domaine initiateur',
}


class TxPayzen(models.Model):
    _inherit = 'payment.transaction'

    state_message = fields.Text(string='Transaction log')
    authresult_message = fields.Char(string='Transaction error')

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------
    @api.model
    def _payzen_form_get_tx_from_data(self, data):
        """ Method called by form_feedback after the transaction

        :param data: data received from the acquirer after the transaction
        :return: payment.transaction record if retrieved or an exception
        """
        signature = data.get('signature')
        result = data.get('vads_result')
        reference = data.get('vads_order_id').encode('utf-8')

        # We need to recreate the reference to the invoice if it's a invoice transaction
        if reference[:3] == 'SAJ':
            reference = reference[:3] + '/' + reference[3:7] + '/' + reference[7:]
        # Or if it's a weird wharehouse invoice ?
        elif reference[:2] == 'WH':
            reference = reference[:2] + '/' + reference[2:5] + '/' + reference[5:]

        if not reference or not signature or not result:
            error_msg = 'Payzen : received bad data %s' % (data)
            _logger.error(error_msg)
            raise ValidationError(error_msg)

        tx_ids = self.search([('reference', '=', reference)])

        if not tx_ids or len(tx_ids) > 1:
            error_msg = 'Payzen: received data for reference %s' % (reference)
            if not tx_ids:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        transaction = self.env['payment.transaction'].browse(tx_ids[0].id)

        # TODO: check this
        # shasign_check = self.env['payment.acquirer']._payzen_generate_digital_sign(tx.acquirer_id, data)
        # if shasign_check != signature.upper :
        #     error_msg = 'Payzen : invalid shasign, received %s, computed %s, for data %s' % (signature, shasign_check, data)
        #     _logger.error(error_msg)
        #     raise ValidationError(error_msg)

        return transaction

    @api.model
    def _payzen_form_get_invalid_parameters(self, transaction, data):
        invalid_parameters = []

        # TODO: COMPLETE THIS AS IT DOES NOTHING FOR NOW..

        return invalid_parameters

    @api.model
    def _payzen_form_validate(self, transaction, data):
        """Check the state of the transaction and set it accordingly

        :param transaction: payment.transaction record to act on
        :param data: data received from payzen at the end of transaction
        """
        payzen_status = {
            'valide': ['00'],
            'cancel': ['17', ''],
        }
        status_code = data.get('vads_auth_result')

        if status_code in payzen_status['valide']:
            transaction.sudo().write({
                'state': 'done',
                'state_message': '%s' % (data),
            })

            return True

        elif status_code in payzen_status['cancel']:
            transaction.sudo().write({
                'state': 'cancel',
                'state_message': '%s' % (data),
            })
            return True
        else:
            authresult_message = ''
            if status_code in _AUTH_RESULT:
                authresult_message = _AUTH_RESULT[status_code]
            error = 'Payzen error'
            _logger.info(error)
            transaction.sudo().write({
                'state': 'error',
                'state_message': '%s' % (data),
                'authresult_message': authresult_message,
            })
            return False
