# coding: utf8

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
        _logger.info("Payzen transaction request: transaction starting")
        start_time = time.time()
        try:
            request.env['payment.transaction'].form_feedback(kw, 'payzen')
        finally:
            timed = time.time() - start_time
            post = kw if isinstance(kw, dict) else {}
            vads_order_id = post.get('vads_order_id', 'vads_order_id not found')
            vads_trans_id = post.get('vads_trans_id', 'vads_trans_id not found')
            vads_trans_date = post.get('vads_trans_date', 'vads_trans_date not found')
            vads_amount = post.get('vads_amount', 'vads_amount not found')
            vads_trans_status = post.get('vads_trans_status', 'vads_trans_status not found')
            _logger.info(
                "Payzen transaction request: order_id {order_id} and trans_id {trans_id} "
                "at date {trans_date} for {amount}€ "
                "done in {actual_time} seconds with status {trans_status}".format(
                    order_id=vads_order_id,
                    trans_id=vads_trans_id,
                    trans_date=vads_trans_date,
                    amount=vads_amount,
                    actual_time=format(timed, '.3f'),
                    trans_status=vads_trans_status)
            )

        return werkzeug.utils.redirect('/', 303)
