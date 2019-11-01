# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    class_id = fields.Many2one("sii.document.class", string="SII Document")

    @api.multi
    def action_done(self):
        res = super().action_done()
        sign = self._name in [x.model for x in self.company_id.document_ids]
        for picking in self:
            if sign and picking.location_dest_id.usage == 'customer':
                self.with_delay().document_sign()
        return res
