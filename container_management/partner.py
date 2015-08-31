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

from openerp.osv import fields, osv

class res_partner(osv.osv):
    _inherit = "res.partner"
    
    def _get_address(self, cr, uid, ids, prop, unknow_none,  context=None):
        result= " %s \n %s \n %s \n %s, %s \n %s \n %s \n %s \n"
        if not ids:
            return ''
        if type(ids) == type(1):
            ids= [ids]
        res=[]
        for partner_obj in self.browse(cr, uid, ids, context= context):
            name = partner_obj.name and partner_obj.name
            street1= partner_obj.street and partner_obj.street or ''
            street2= partner_obj.street2 and  partner_obj.street2 or ''
            country = partner_obj.country_id and partner_obj.country_id.name or ''
            city = partner_obj.city and partner_obj.city or ''
            tel = partner_obj.phone and "TEL : " + partner_obj.phone or ''
            attn = partner_obj.contact_id and "ATTN : " + partner_obj.contact_id.name or ''
            postal = partner_obj.zip and "POSTAL CODE: " + partner_obj.zip or ''
            res.append((partner_obj.id , result % ( name, street1, street2, city , country, tel, attn, postal)))
            
        return dict(res)
        
    _columns = {
        'complete_address':fields.function(_get_address , type='char', string='Complete Address', size=500),
        'contact_id': fields.many2one('res.partner', 'Contact Person'),
    }

res_partner()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
