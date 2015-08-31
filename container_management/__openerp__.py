# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
	'name': 'Container Tracking And Planning',
	"version": "1.1",
    "author": 'BA,Business Automation',
    "website": "",
    "license" : "AGPL-3",
    "price": 99.99,
    "currency": 'USD',
    "category" : "Inventory",
	'depends': ['base','account','stock','product'],
	'data': [
	            'container_view.xml',
	            'product_view.xml',
	            'shipping_sequence.xml',
	            'shipping_data.xml',
	            'freight_invoice_view.xml',
	            'shipping_report.xml',
	            'res_partner_view.xml',
	            'release_order_view.xml',
	            'company_view.xml',
	            'detention_collection_view.xml',
	            'booking_view.xml',
	            'shipping_general_payment_view.xml',
	            'shipping_config_view.xml',
	            'wizard/detention_collection_report_view.xml',
	            'wizard/inward_commission_view.xml',
	            'wizard/outward_commission_view.xml',
	            'wizard/soa_reports_view.xml',
	            'security/shipping_security.xml',
			],
	'test': [
    ],
	'installable': True,
    'auto_install': False,
}

