# -*- coding: utf-8 -*-

try:
    import simplejson as json
except ImportError:
    import json

import werkzeug

from openerp import http
from openerp.http import request


class PayzenController(http.Controller):
    _return_url = '/payment/payzen/return'

    @http.route(['/payment/payzen/return', ], type='http', auth='none')
    def payzen_return(self, **post):
        """Route called after a transaction with payzen"""
        request.env['payment.transaction'].form_feedback(post, 'payzen')

        return_url = post.pop('return_url', '')

        if not return_url:
            data = '' + post.pop('ADD_RETURNDATA', '{}').replace("'", "\"")
            custom = json.loads(data)
            return_url = custom.pop('return_url', '/')

        return werkzeug.utils.redirect(return_url)
