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

from openerp import tools
from openerp.osv import osv, fields
from openerp.tools.translate import _

import openerp.addons.decimal_precision as dp
from tools.translate import _

import logging
_logger=logging.getLogger(__name__)

DATETIME_FORMAT = "%Y-%m-%d"

class shipping_config(osv.osv):

    _name= "shipping.config"
    _description = "Shipping Configuration"

    _columns={				
                'bl_fees':fields.float('BL FEES', digits_compute=dp.get_precision('Account'),required=True),
                'ro_amount':fields.float('RO Charge', digits_compute=dp.get_precision('Account'),required=True),
                'date': fields.date('Effective Date', required=True, ondelete='cascade', ),
            }
    
    _defaults= {
        'date': fields.date.today,
    }
    
    def get_ro_amount(self, cr, uid, context=None):
        res=20000.0
        ids= self.search(cr, uid, [])
        data = self.read(cr, uid, ids[0])
        res= data['ro_amount']
        
        return res
    
    def get_bl_fees(self, cr, uid, context=None):
        res=20000.0
        ids= self.search(cr, uid, [])
        data = self.read(cr, uid, ids[0])
        res= data['bl_fees']
        
        return res
        
shipping_config()

