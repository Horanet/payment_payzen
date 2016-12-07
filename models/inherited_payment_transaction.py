# -*- coding: utf-8 -*-

from openerp import models, fields, api


class PaymentTransactionModel(models.Model):
    """ This class represent a model : Explanation """

    # region Private attributes
    _inherit = 'payment.transaction'
    # endregion

    # region Default methods
    # endregion

    # region Fields declaration
    voucher_ids = fields.Many2many(
        string='Vouchers',
        comodel_name='account.voucher',
    )

    transaction_number = fields.Char(string='Transaction number', readonly=True)
    # endregion

    # region Fields method
    # endregion

    # region Constrains and Onchange
    @api.constrains('state')
    def onchange_state(self):
        for record in self:
            if record.state == 'done':
                record._send_voucher_signal('proforma_voucher')
            elif record.state == 'error' or record.state == 'cancel':
                record._send_voucher_signal('proforma_cancel')
    # endregion

    # region CRUD (overrides)
    @api.model
    def create(self, values):
        rec = super(PaymentTransactionModel, self).create(values)
        rec.transaction_number = '000000{}'.format(rec.id % 899999)[-6:]

        rec._update_vouchers_references()

        return rec
    # endregion

    # region Actions
    # endregion

    # region Model methods
    def _update_vouchers_references(self):
        for voucher in self.voucher_ids:
            voucher.reference = self.reference

    @api.multi
    def _send_voucher_signal(self, signal):
        for voucher in self.voucher_ids:
            voucher.signal_workflow(signal)
    # endregion

    pass
