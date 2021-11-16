# coding: utf8

import logging
import pprint
import werkzeug

from odoo import http
from odoo.http import request
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger()


class PayzenController(http.Controller):
    @http.route(['/payment/payzen/return', '/payment/payzen/local/return/'], type='http', auth='public', csrf=False)
    def payzen_return(self, local_call=None, **kw):
        """Route called after a transaction with payzen

        :param boolean local_call: Define is was call from local server or by Payzen
        :param dict kw: dict that contains POST values received from Payzen
        :return: response object
        """
        _logger.info('PayZen: entering IPN form_feedback with post data')

        local_call = safe_eval(local_call or 'False')

        request.env['payment.transaction'].with_context(local_call=local_call).form_feedback(kw, 'payzen')

        return werkzeug.utils.redirect('/')
