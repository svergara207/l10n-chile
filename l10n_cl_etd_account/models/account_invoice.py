# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class AccountInvoice(models.Model):
    _name = 'account.invoice'
    _inherit = ['account.invoice', 'etd.mixin']

    amount_base_tax = fields.Monetary(
        string='Untaxed Amount', store=True, readonly=True,
        compute='_compute_amount', track_visibility='always')

    @api.one
    @api.depends(
        'invoice_line_ids.price_subtotal', 'tax_line_ids.amount',
        'tax_line_ids.amount_rounding', 'currency_id', 'company_id',
        'date_invoice', 'type')
    def _compute_amount(self):
        super()._compute_amount()
        self.amount_base_tax = \
            sum(line.price_subtotal
                for line in self.invoice_line_ids
                if not line.invoice_line_tax_ids)

    def _compute_class_id_domain(self):
        return [('document_type', 'in', ('invoice', 'invoice_in',
                                         'debit_note', 'credit_note'))]

    def get_etd_document(self):
        res = super().get_etd_document()
        res = res.filtered(
            lambda x: x.invoicing_policy == self.partner_id.invoicing_policy
            or not x.invoicing_policy)
        return res

    @api.multi
    def invoice_validate(self):
        res = super().invoice_validate()
        sign = self._name in [x.model for x in self.company_id.etd_ids]
        auto_sign = self.company_id.backend_acp_id.auto_sign
        for invoice in self:
            if auto_sign and sign and invoice.type in \
                    ('out_invoice', 'out_refund'):
                self.with_delay().document_sign()
        return res
