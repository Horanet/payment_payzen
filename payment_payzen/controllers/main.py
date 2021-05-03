import logging
import time
import werkzeug

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PayzenController(http.Controller):
    @http.route(['/payment/payzen/return'], type='http', auth='public', csrf=False)
    def payzen_return(self, **kw):
        """Route called after a transaction with payzen.

        :param kw: dict that contains POST values received from Payzen
        :return: response object
        """
        start_time = time.time()
        try:
            request.env['payment.transaction'].form_feedback(kw, 'payzen')
        finally:
            if isinstance(kw, dict):
                _logger.info(
                    f"Payzen transaction request: Reference {kw.get('vads_order_id', 'Unfindable id')} "
                    f"was done in {format(time.time() - start_time, '.3f') } seconds")
            else:
                _logger.warning("kw is not a dictionary")

        return werkzeug.utils.redirect('/')