# -*- coding: utf-8 -*-

from openerp import api, fields, models


class PaymentTransactionModel(models.Model):
    """ Transaction Model. Each specific acquirer can extend the model by adding
    its own fields.

    Methods that can be added in an acquirer-specific implementation:

     - ``<name>_create``: method receiving values used when creating a new
       transaction and that returns a dictionary that will update those values.
       This method can be used to tweak some transaction values.

    Methods defined for convention, depending on your controllers:

     - ``<name>_form_feedback(self, cr, uid, data, context=None)``: method that
       handles the data coming from the acquirer after the transaction. It will
       generally receives data posted by the acquirer after the transaction.
    """
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
        """
        Call corresponding workflow of account.voucher when the state
        of the transaction change
        """
        for record in self:
            if record.state == 'done':
                record.send_voucher_signal('proforma_voucher')
            elif record.state in ['error', 'cancel']:
                record.send_voucher_signal('proforma_cancel')
    # endregion

    # region CRUD (overrides)
    @api.model
    def create(self, values):
        """
        Override create method to be able to set a unique (per day, for payzen)
        number and update its vouchers to keep consistency on the reference
        """
        rec = super(PaymentTransactionModel, self).create(values)
        rec.transaction_number = '000000{}'.format(rec.id % 899999)[-6:]

        rec.update_vouchers_references()

        return rec
    # endregion

    # region Actions
    # endregion

    # region Model methods
    @api.multi
    def update_vouchers_references(self):
        """Update voucher reference corresponding to the transaction reference"""
        self.ensure_one()

        for voucher in self.voucher_ids:
            voucher.reference = self.reference

    @api.multi
    def send_voucher_signal(self, signal):
        """Call the account.voucher workflow with the corresponding signal

        :param signal: signal to call the appropriate workflow"""
        self.ensure_one()

        for voucher in self.voucher_ids:
            voucher.signal_workflow(signal)
    # endregion

    pass
