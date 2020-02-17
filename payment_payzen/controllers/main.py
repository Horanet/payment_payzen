import werkzeug

from odoo import http
from odoo.http import request


class PayzenController(http.Controller):
    @http.route(['/payment/payzen/return'], type='http', auth='public', csrf=False)
    def payzen_return(self, **kw):
        """Route called after a transaction with payzen

        :param kw: dict that contains POST values received from Payzen
        :return: response object
        """

        request.env['payment.transaction'].form_feedback(kw, 'payzen')

        return werkzeug.utils.redirect('/')
