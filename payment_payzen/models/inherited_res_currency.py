from odoo import fields, models


class Currency(models.Model):
    _inherit = 'res.currency'

    number = fields.Char(string="Alphanumeric code")
