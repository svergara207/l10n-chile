# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Electronic Invoicing for Chile",
    "summary": "Sign your documents and send them to SII.",
    "version": "12.0.1.0.0",
    "category": "Localization/Chile",
    "author": "Daniel Santibáñez Polanco, "
              "Cooperativa OdooCoop, "
              "Konos, "
              "Open Source Integrators, "
              "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/l10n-chile",
    "license": "AGPL-3",
    "depends": [
        "l10n_cl_dte_account",
        "stock",
    ],
    "data": [
        "data/res_company_document.xml",
    ],
    "application": True,
    "development_status": "Beta",
    "maintainers": ["nelsonramirezs"],
}
