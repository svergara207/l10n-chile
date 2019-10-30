# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import base64
import logging
import os
from collections import namedtuple
from jinja2 import Environment, FileSystemLoader
from lxml import etree
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from ...queue_job.job import job
from ...queue_job.exception import RetryableJobError

_logger = logging.getLogger(__name__)

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    _env = None
    _etd = ()
    File_details = namedtuple('file_details', ['filename', 'filecontent'])
    template_path = '{}/../data/xml/'.format(os.path.dirname(__file__))

    @api.model
    def set_jinja_env(self):
        """Set the Jinja2 environment.
        The environment will helps the system to find the templates to render.
        :param api_version: string, odoo api
        :return: jinja2.Environment instance.
        """
        if self._env is None:
            self._env = Environment(
                lstrip_blocks=True,
                trim_blocks=True,
                loader=FileSystemLoader(self.template_path))
        return self._env

    def build_xml(self):
        self.set_jinja_env()
        document_id = self.company_id.document_ids.filtered(
            lambda x: x.name == self.partner_id.invoicing_policy)
        kwargs = {}
        # Get the template
        template = self._env.get_template(document_id.xml)
        # Additional keywords used in the template
        kwargs.update({
            'o': self,
            'now': fields.datetime.now(),
            'today': fields.datetime.today(),
        })
        # Render the XML
        xml_file = self.File_details(self.number + '.xml',
                                     template.render(kwargs))
        xml = str.encode(xml_file.filecontent)
        # Attache XML file to the invoice
        self.env['ir.attachment'].create({
            'name': xml_file.filename,
            'type': 'binary',
            'datas': base64.b64encode(xml_file.filecontent.encode("utf-8")),
            'datas_fname': xml_file.filename,
            'res_model': 'account.invoice',
            'res_id': self.id})
        # Check the rendered XML against the XSD
        # xsd_file = document_id.xsd
        # try:
        #     xmlschema_doc = etree.parse(os.path.join(
        #         self.template_path, '../xsd/' + xsd_file))
        #     xmlschema = etree.XMLSchema(xmlschema_doc)
        #     xml_doc = etree.fromstring(xml)
        #     result = xmlschema.validate(xml_doc)
        #     if not result:
        #         xmlschema.assert_(xml_doc)
        #     return xml
        # except AssertionError as e:
        #     _logger.warning(etree.tostring(xml_doc))
        #     raise UserError(_("XML Malformed Error: %s") % e.args)

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
                message = _("ETD has been sent to SII but failed with"
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
                message = _("""ETD has been sent to %s but failed
                                with the following message: <b>%s</b>""" %
                            (self.company_id.backend_id.name, reply))
                self.message_post(body=message)
                raise RetryableJobError(reply)

    @api.multi
    def invoice_validate(self):
        res = super().invoice_validate()
        sign = self.partner_id.invoicing_policy in \
               [x.name for x in self.company_id.document_ids]
        for invoice in self:
            if sign and invoice.type in ('out_invoice', 'out_refund'):
                invoice.with_delay().invoice_sign()
        return res
