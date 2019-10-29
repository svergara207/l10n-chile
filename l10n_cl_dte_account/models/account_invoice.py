# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, models, _
from ...queue_job.job import job
from ...queue_job.exception import RetryableJobError


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    def build_xml(self):
        # Build the XML of the invoice
        return True

    def check_xml(self, xml):
        # Check the generate XML against the XSD
        return True

    def sign_xml(self, xml):
        # Use the SSL Certificate to sign the XML
        return True

    def sii_validate_signed_xml(self, xml):
        # Send the signed XML to SII to validate
        return True

    def sii_check_status(self):
        # Check the status
        res = True
        # Post the status on the ticket
        message = _("""SII Status: <b>%s</b>""" % (res))
        self.message_post(body=message)
        return True

    @job
    def invoice_sign(self):
        # Build the XML of the invoice
        xml = self.build_xml()
        # Check the generate XML against the XSD
        if self.check_xml(xml):
            # Sign the invoice
            if self.company_id.signer == 'odoo':
                # Use the SSL Certificate to sign the XML
                signed_xml = self.sign_xml(xml)
                # Send the signed XML to SII for validation
                reply = self.sii_validate_signed_xml(signed_xml)
                if reply:
                    # Check the status of the invoice
                    status = self.sii_check_status()
                    message = _("Status: <b>%s</b>" % (status))
                    self.message_post(body=message)
                else:
                    message = _("Invoice has been sent to SII but failed with"
                                " the following message: <b>%s</b>" %
                                (reply))
                    self.message_post(body=message)
                    raise RetryableJobError(reply)
            else:
                # Send the XML to the Third Party backend
                reply = self.company_id.backend_id.send(xml)
                if reply:
                    # Check the status of the invoice
                    status = self.company_id.backend_id.check_status()
                    message = _("Status: <b>%s</b>" % (status))
                    self.message_post(body=message)
                else:
                    message = _("""Invoice has been sent to SII but failed
                                with the following message: <b>%s</b>""" %
                                (reply))
                    self.message_post(body=message)
                    raise RetryableJobError(reply)

    @api.multi
    def invoice_validate(self):
        res = super().invoice_validate()
        sign = 'account.invoice' in self.company_id.document_ids
        for invoice in self:
            if sign and invoice.type in ('out_invoice', 'out_refund'):
                invoice.invoice_sign()
        return res
