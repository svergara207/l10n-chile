from odoo import fields, models


class Guias_sii(models.Model):
    _inherit = "stock.picking"

    transport_type = fields.Selection(
        [
            ('2', 'Despacho por cuenta de empresa'),
            ('1', 'Despacho por cuenta del cliente'),
            ('3', 'Despacho Externo'),
            ('0', 'Sin Definir')
        ],
        string="Tipo de Despacho",
        default="2",
        readonly=False, states={'done': [('readonly', True)]},
    )

    move_reason = fields.Selection(
        [
            ('1', 'Operación constituye venta'),
            ('2', 'Ventas por efectuar'),
            ('3', 'Consignaciones'),
            ('4', 'Entrega Gratuita'),
            ('5', 'Traslados Internos'),
            ('6', 'Otros traslados no venta'),
            ('7', 'Guía de Devolución'),
            ('8', 'Traslado para exportación'),
            ('9', 'Ventas para exportación')
        ],
        string='Razón del traslado',
        default="2",
        readonly=False, states={'done': [('readonly', False)]},
    )
