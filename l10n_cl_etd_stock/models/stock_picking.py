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


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    class_id = fields.Many2one("sii.document.class", string="SII Document")
    signature_id = fields.Many2one("ssl.signature", string="SSL Signature")

    _env = None
    File_details = namedtuple('file_details', ['filename', 'filecontent'])
    template_path = '{}/../data/xml/'.format(os.path.dirname(__file__))

    @api.model
    def set_jinja_env(self):
        """Set the Jinja2 environment.
        The environment will helps the system to find the templates to render.
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
            lambda x: x.name == 'picking')
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
        xml_file = self.File_details(self.name + '.xml',
                                     template.render(kwargs))
        xml = str.encode(xml_file.filecontent)
        # Attache XML file to the picking
        self.env['ir.attachment'].create({
            'name': xml_file.filename,
            'type': 'binary',
            'datas': base64.b64encode(xml_file.filecontent.encode("utf-8")),
            'datas_fname': xml_file.filename,
            'res_model': 'stock.picking',
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
        return True

    @job
    def picking_sign(self):
        # Build the XML of the picking
        xml = self.build_xml()
        if self.company_id.signer == 'odoo':
            # Use the SSL Certificate to sign the XML
            signed_xml = self.sign_xml(xml)
            # Send the signed XML to SII for validation
            reply = self.sii_validate_signed_xml(signed_xml)
            if reply:
                # Check the status of the picking
                status = self.sii_check_status()
                message = _("SII Status: <b>%s</b>" % (status))
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
                # Check the status of the picking
                status = self.company_id.backend_id.check_status()
                message = _("%s Status: <b>%s</b>" %
                            (self.company_id.backend_id.name, status))
                self.message_post(body=message)
            else:
                message = _("""ETD has been sent to %s but failed
                                with the following message: <b>%s</b>""" %
                            (self.company_id.backend_id.name, reply))
                self.message_post(body=message)
                raise RetryableJobError(reply)

    @api.multi
    def action_done(self):
        res = super().action_done()
        sign = 'picking' in [x.name for x in self.company_id.document_ids]
        for picking in self:
            if sign and picking.location_dest_id.usage == 'customer':
                picking.with_delay().picking_sign()
        return res
