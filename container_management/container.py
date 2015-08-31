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

from datetime import datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal
import logging
import pdb
import time

import math
import re
from _common import rounding
from openerp import tools
from openerp.osv import osv, fields
from openerp.tools.translate import _

import openerp.addons.decimal_precision as dp
from tools.translate import _
import logging
_logger=logging.getLogger(__name__)

DATETIME_FORMAT = "%Y-%m-%d"

class shipping_container_inventory(osv.osv):
    _name='shipping.container.inventory'
    _description=' Containers Inventory Transaction'
    _order ='in_date,name'
    
    CONTAINER_STATE=[   ('DF', 'Decharge Full'),
                        ('DE', 'Decharge Empty'),
                        ('LD', 'Local Devending'),
                        ('TD', 'Terminal Devending'),
                        ('TE', 'Terminal Empty'),
                        ('TF', 'Terminal Full'),
                        ('LVE','Local Vending Empty'),
                        ('LVF','Local Vending Full'),
                        ('VE', 'Vassel Empty'),
                        ('VF', 'Vassel Full')]

    _columns={
        'name':fields.char('Container', size=128, ondelete='cascade', readonly=True),		
        'state': fields.selection(CONTAINER_STATE,'Status', readonly=True),
        'in_date':fields.date('IN-Date',required=True),
        'out_date':fields.date('OUT-Date'),
        'vassel_id': fields.many2one('shipping.vassel', 'Vassel Name', ondelete='cascade',),
        'shipper': fields.many2one('res.partner', 'Shipper',  ondelete='cascade') ,
        'inventory_lines': fields.one2many('shipping.container.inventory.line', 'inventory_id', 'Container Move Lines', readonly=True),
        }
    
    _defaults={
        'in_date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
    }
    
    def create(self, cr, uid, vals, context= None):
        if vals.get('name',False):
            is_exist=self.search(cr, uid, [('name','=',vals.get('name'))], context =context)
            if is_exist and len(is_exist)>0:
                self.write(cr, uid, is_exist[0], vals, context=context)
                return is_exist[0]
                
        super(shipping_container_inventory, self).create(cr, uid, vals, context=context)
        
    def update_state(self, cr, uid, name, state, context=None):
        ids= self.search(cr, uid, [('name','=',name)], context=context)
        if ids:
            container= self.browse(cr, uid, ids[0], context= context)
            if container.state =='LVE':
                state='TE'
            elif container.state =='LVF':
                state='TF'
                
            self.write(cr, uid, ids, {'state': state }, context= context)
        return True
    
shipping_container_inventory()

class shipping_container_inventory_line(osv.osv):
    _name='shipping.container.inventory.line'
    _description=' Containers Inventory Transaction Lines'
    _order ='in_date,name'
    
    CONTAINER_STATE=[   ('DF', 'Decharge Full'),
                        ('DE', 'Decharge Empty'),
                        ('LD', 'Local Devending'),
                        ('TD', 'Terminal Devending'),
                        ('TE', 'Terminal Empty'),
                        ('TF', 'Terminal Full'),
                        ('LVE','Local Vending Empty'),
                        ('LVF','Local Vending Full'),
                        ('VE', 'Vassel Empty'),
                        ('VF', 'Vassel Full')]

    _columns={
        'name':fields.char('Container', size=128, ondelete='cascade', readonly=True),		
        'state': fields.selection(CONTAINER_STATE,'Status', readonly=True),
        'in_date':fields.date('IN-Date'),
        'out_date':fields.date('OUT-Date'),
        'move_type': fields.selection([('in','IN'),('out','OUT'),('etc','Other')],'Movement', readonly=True),
        'vassel_id': fields.many2one('shipping.vassel', 'Vassel Name', ondelete='cascade',),
        'inventory_id': fields.many2one('shipping.container.inventory', 'Inventory', ondelete='cascade',),
        'bl_id': fields.many2one('shipping.bl_order.line', 'Source', ondelete='cascade',),
        'shipper': fields.many2one('res.partner', 'Shipper',  ondelete='cascade') ,
        }
    
    _defaults={
        'move_type': 'in',
    }
    
shipping_container_inventory()

class shipping_vassel(osv.osv):

    _name= "shipping.vassel"
    _table = "shipping_vassel"
    _description = "Vassel"
    _order = 'name,code'

    def _get_image(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = tools.image_get_resized_images(obj.image, avoid_resize_medium=True)
        return result

    def _set_image(self, cr, uid, id, name, value, args, context=None):
        return self.write(cr, uid, [id], {'image': tools.image_resize_image_big(value)}, context=context)

    _columns={
            'name': fields.char('Name', size=128, required=True, translate=True, select=True),
            'code': fields.char('Code', size=128, translate=True, select=True),
            'description': fields.text('Description',translate=True),
            'volume': fields.float('Volume', help="The volume in m3."),
            'weight': fields.float('Gross Weight', digits_compute=dp.get_precision('Stock Weight'), help="The gross weight in Kg."),
            'weight_net': fields.float('Net Weight', digits_compute=dp.get_precision('Stock Weight'), help="The net weight in Kg."),
            'color': fields.integer('Color Index'),
            'active': fields.boolean('Active', help="If unchecked, it will allow you to hide the vassel without removing it."),
            # image: all image fields are base64 encoded and PIL-supported
            'image': fields.binary("Image",
                help="This field holds the image used as image for the vassel, limited to 1024x1024px."),
            'image_medium': fields.function(_get_image, fnct_inv=_set_image,
                string="Medium-sized image", type="binary", multi="_get_image",
                store={
                    'shipping.vassel': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
                },
                help="Medium-sized image of the vassel. It is automatically "\
                     "resized as a 128x128px image, with aspect ratio preserved, "\
                     "only when the image exceeds one of those sizes. Use this field in form views or some kanban views."),
            'image_small': fields.function(_get_image, fnct_inv=_set_image,
                string="Small-sized image", type="binary", multi="_get_image",
                store={
                    'shipping.vassel': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
                },
                help="Small-sized image of the vassel. It is automatically "\
                     "resized as a 64x64px image, with aspect ratio preserved. "\
                     "Use this field anywhere a small image is required."),
            'company_id': fields.many2one('res.company', 'Company', select=1),
    }

    _defaults= {
            'active': True,
        }
        
    def name_get(self, cr, user, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not len(ids):
            return []
        def _name_get(d):
            name = d.get('name','')
            code = d.get('code',False)
            if code:
                name = '[%s] %s' % (code,name)
            return (d['id'], name)

        result = []
        for vassel in self.browse(cr, user, ids, context=context):
            mydict = {
                      'id': vassel.id,
                      'name': vassel.name,
                      'default_code': vassel.code,
                      }
            result.append(_name_get(mydict))
        return result

    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if name:
            ids = self.search(cr, user, [('code','=',name)]+ args, limit=limit, context=context)
            if not ids:
                # Do not merge the 2 next lines into one single search, SQL search performance would be abysmal
                # on a database with thousands of matching vassel, due to the huge merge+unique needed for the
                # OR operator (and given the fact that the 'name' lookup results come from the ir.translation table
                # Performing a quick memory merge of ids in Python will give much better performance
                ids = set()
                ids.update(self.search(cr, user, args + [('code',operator,name)], limit=limit, context=context))
                if not limit or len(ids) < limit:
                    # we may underrun the limit because of dupes in the results, that's fine
                    ids.update(self.search(cr, user, args + [('name',operator,name)], limit=(limit and (limit-len(ids)) or False) , context=context))
                ids = list(ids)
            if not ids:
                ptrn = re.compile('(\[(.*?)\])')
                res = ptrn.search(name)
                if res:
                    ids = self.search(cr, user, [('code','=', res.group(2))] + args, limit=limit, context=context)
        else:
            ids = self.search(cr, user, args, limit=limit, context=context)
        result = self.name_get(cr, user, ids, context=context)
        return result
        

shipping_vassel()

class shipping_port(osv.osv):

    _name= "shipping.port"
    _table = "shipping_port"
    _description = "Ports"
    _order = 'name,code'

    def _get_image(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = tools.image_get_resized_images(obj.image, avoid_resize_medium=True)
        return result

    def _set_image(self, cr, uid, id, name, value, args, context=None):
        return self.write(cr, uid, [id], {'image': tools.image_resize_image_big(value)}, context=context)


    _columns={
            'name': fields.char('Name', size=128, required=True, translate=True, select=True),
            'code': fields.char('Code', size=128, translate=True, select=True),
            'description': fields.text('Description',translate=True),
            'active': fields.boolean('Active', help="If unchecked, it will allow you to hide the vassel without removing it."),
            # image: all image fields are base64 encoded and PIL-supported
            'image': fields.binary("Image",
                help="This field holds the image used as image for the vassel, limited to 1024x1024px."),
            'image_medium': fields.function(_get_image, fnct_inv=_set_image,
                string="Medium-sized image", type="binary", multi="_get_image",
                store={
                    'shipping.port': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
                },
                help="Medium-sized image of the vassel. It is automatically "\
                     "resized as a 128x128px image, with aspect ratio preserved, "\
                     "only when the image exceeds one of those sizes. Use this field in form views or some kanban views."),
            'image_small': fields.function(_get_image, fnct_inv=_set_image,
                string="Small-sized image", type="binary", multi="_get_image",
                store={
                    'shipping.port': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
                },
                help="Small-sized image of the vassel. It is automatically "\
                     "resized as a 64x64px image, with aspect ratio preserved. "\
                     "Use this field anywhere a small image is required."),
            'company_id': fields.many2one('res.company', 'Company', select=1),
            'city': fields.char('City', size=128),
            'state_id': fields.many2one("res.country.state", 'State'),
            'amount_20': fields.float('20 Feet', digits_compute=dp.get_precision('Account')),
            'amount_40': fields.float('40 Feet', digits_compute=dp.get_precision('Account')),
            'country_id': fields.many2one('res.country', 'Country'),
    }

    _defaults= {
            'active': True,
        }
        
    def name_get(self, cr, user, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not len(ids):
            return []
        def _name_get(d):
            name = d.get('name','')
            code = d.get('code',False)
            if code:
                name = '[%s] %s' % (code,name)
            return (d['id'], name)

        result = []
        for vassel in self.browse(cr, user, ids, context=context):
            mydict = {
                      'id': vassel.id,
                      'name': vassel.name,
                      'default_code': vassel.code,
                      }
            result.append(_name_get(mydict))
        return result

    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if name:
            ids = self.search(cr, user, [('code','=',name)]+ args, limit=limit, context=context)
            if not ids:
                # Do not merge the 2 next lines into one single search, SQL search performance would be abysmal
                # on a database with thousands of matching vassel, due to the huge merge+unique needed for the
                # OR operator (and given the fact that the 'name' lookup results come from the ir.translation table
                # Performing a quick memory merge of ids in Python will give much better performance
                ids = set()
                ids.update(self.search(cr, user, args + [('code',operator,name)], limit=limit, context=context))
                if not limit or len(ids) < limit:
                    # we may underrun the limit because of dupes in the results, that's fine
                    ids.update(self.search(cr, user, args + [('name',operator,name)], limit=(limit and (limit-len(ids)) or False) , context=context))
                ids = list(ids)
            if not ids:
                ptrn = re.compile('(\[(.*?)\])')
                res = ptrn.search(name)
                if res:
                    ids = self.search(cr, user, [('code','=', res.group(2))] + args, limit=limit, context=context)
        else:
            ids = self.search(cr, user, args, limit=limit, context=context)
        result = self.name_get(cr, user, ids, context=context)
        return result

shipping_port()

class shipping_container_status(osv.osv):
    _name='shipping.container.status'
    _description="Shipping Container"

    _columns={
        'name': fields.char('Status', size=128, required=True, translate=True, select=True),
        'description': fields.char('Description', size=128, required=True, translate=True, select=True),		 
        }	

shipping_container_status()


class shipping_container_move(osv.osv):
    _name='shipping.container.move'
    _description="Daily Container move"

    _columns={
        'port_id': fields.many2one('shipping.port', 'Port Name', required=True, states={'draft': [('readonly', False)]}, readonly=True, ondelete='cascade', help="The port name to where the vissel will board."),
        'date':fields.date('Date',required=True, states={'draft': [('readonly', False)]}, readonly=True),
        'source':fields.char('Source',size=128, states={'draft': [('readonly', False)]}, readonly=True),
        'state': fields.selection([('draft', 'New'),
                                   ('cancel', 'Cancelled'),
                                   ('confirmed', 'Confirmed'),
                                   ('done', 'Done')],
                                  'Status', readonly=True),
        'move_lines': fields.one2many('shipping.container.move.line', 'move_id','Container Move Line', required=True, states={'draft': [('readonly', False)]}, readonly=True) ,
        'out_move_lines': fields.one2many('shipping.container.move.line', 'out_move_id','Container Move Line', required=True, states={'draft': [('readonly', False)]}, readonly=True) ,
    }			

    _defaults= {
            'state': 'draft',
        }

    def button_confirm(self, cr, uid, ids, context=None):
        container_inv_obj = self.pool.get('shipping.container.inventory')
        self.write(cr, uid, ids, {'state':'confirmed'}, context= context )
        for move in self.browse(cr, uid, ids, context= context):
            for move_line in move.move_lines:
                context.update({'force': True } )
                state=False
                if move_line.condition=='AV':
                    state ='TE'
                else:
                    state ='TE'
                
                container_inv_obj.update_state(cr, uid, move_line.container.name,state  ,context= context) 
            
            for move_line in move.out_move_lines:
                context.update({'force': True } )
                state=False
                if move_line.condition=='AV':
                    state ='TE'
                else:
                    state ='TE'
                
                container_inv_obj.update_state(cr, uid, move_line.container.name,state  ,context= context)
            if move.move_lines:
                return self.create_detention_invoice(cr, uid, ids, context= context)
                
        return True

    def create_detention_invoice(self, cr, uid, ids, context=None):
        receipt_obj= self.pool.get('detention.charge.receipt')
        detention_charge_obj= self.pool.get('shipping.detention.collection')

        receipt_val={}
        move_vals={}
        receipt_line_p20={}
        receipt_line_p40={}

        for move in self.browse(cr, uid, ids, context= context):

            container_20=0
            container_40=0
            for move_line in move.move_lines:
                receipt_line_list=[]
                charge_list = detention_charge_obj.create_detention_charge_line(cr, uid, move_line.container.name , move_line.container.ship_line_id.bl_no, move.date)
                if move_line.container.feet_20:
                    receipt_line_p20={}
                    container_20 +=1
                    for charge in charge_list:
                        receipt_line_p20={
                            'name':charge['name'],
                            'quantity':1,
                            'type': '20',
                            'charge': charge['charge'],
                            'number_of_day':charge['number_of_day'],
                            'period_id': charge['period_id'],
                            'container':move_line.container.name,
                            'eta_ygn': charge['eta_ygn'],
                            'date_free_to': charge['date_free_to'],
                            'period_type': charge['period_type'],
                            'date_from': charge['date_to'],
                            'date_to': charge['date_to'],

                            }

                        receipt_line_list.append((0,0,receipt_line_p20))
                elif move_line.container.feet_40:
                    container_40 +=1
                    charge_list = detention_charge_obj.create_detention_charge_line(cr, uid, move_line.container.name , move_line.container.ship_line_id.bl_no, move.date)
                    receipt_line_p40={}
                    for charge in charge_list:
                        receipt_line_p40={
                            'name':charge['name'],
                            'quantity':1,
                            'type': '40',
                            'charge':charge['charge'],
                            'number_of_day':charge['number_of_day'],
                            'period_id': charge['period_id'],
                            'container':move_line.container.name,
                            'eta_ygn': charge['eta_ygn'],
                            'date_free_to': charge['date_free_to'],
                            'period_type': charge['period_type'],
                            'date_from': charge['date_to'],
                            'date_to': charge['date_to'],

                            }
                        receipt_line_list.append((0,0,receipt_line_p40))

                if len(receipt_line_list)>0:
                    #receipt_val['receipt_lines']=receipt_line_list
                    if move_line.shipper.id in move_vals:
                        for line in receipt_line_list:
                            move_vals[move_line.shipper.id]['receipt_lines'].append(line)
                    else:
                        move_vals[move_line.shipper.id]={ 
                                'date': move.date,
                                'source':move.source,
                                'consignee':move_line.shipper.id,
                                'state':'draft',
                                'receipt_lines':receipt_line_list
                        }
        result=[]
        for key,val in move_vals.items():
            #val.update({'qty_total': "20\' %s : 40\' %s " % (container_20, container_40)}),
            result.append( receipt_obj.create(cr, uid, val) )

        return self.action_view_invoice(cr, uid, result, context= context)

    def action_view_invoice(self, cr, uid, receipt_ids, context=None):
        '''
        This function returns an action that display existing invoices of given sales order ids. It can either be a in a list or in a form view, if there is only one invoice to show.
        '''
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        
        result = mod_obj.get_object_reference(cr, uid, 'container_management', 'open_view_detention_charge_receipt_list')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]

        #choose the view_mode accordingly
        if len(receipt_ids)>1:
            result['domain'] = "[('id','in',["+','.join(map(str, receipt_ids))+"])]"
        else:
            res = mod_obj.get_object_reference(cr, uid, 'container_management', 'detention_charge_receipt_form_view')
            result['views'] = [(res and res[1] or False, 'form')]
            result['res_id'] =  receipt_ids[0]
        
        return result
        
shipping_container_move()

class shipping_container_move_line(osv.osv):

    _name='shipping.container.move.line'
    _description="Daily Container move Line"

    def _get_container_status(self, cr, uid, context=None):
        cr.execute("select name, description from shipping_container_status")
        data= cr.fetchall()
        res=[]
        for d in data:
            res.append(d)
        return res
        
    _columns={
        'container':fields.many2one('shipping.container','Container',required=True),
        'vassel_id': fields.many2one('shipping.vassel', 'Vassel Name', ondelete='cascade',),
        'shipper': fields.many2one('res.partner', 'Shipper', required=True, ondelete='cascade') ,
        'move_id': fields.many2one('shipping.container.move', 'Move', ondelete='cascade',),
        'out_move_id': fields.many2one('shipping.container.move', 'Move', ondelete='cascade',),
        'condition': fields.selection(_get_container_status, 'Condition'),
    }

    def create(self, cr, uid, vals, context=None):		
        container_id = vals.get('container',False)
        consignee = vals.get('shipper', False)
        return super(shipping_container_move_line,self).create(cr, uid, vals, context=context)

shipping_container_move_line()

class export_container_line(osv.osv):
    _name='export.container.line'
    _description="Export Container Line"

    _columns={
        'container_id':fields.many2one('shipping.container.inventory','Container',required=True),
        'seal_no': fields.char('Sael No', size=128, required=True , select=True),
        'ship_line_id': fields.many2one('shipping.bl_order.line', 'Line', ondelete='cascade',),
    }
    
export_container_line()

class export_freight_line(osv.osv):

    _name='export.freight.line'

    def _amount_line(self, cr, uid, ids, name, args, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = line.amount * line.quantity
        return res
        
    _columns={
        'name':fields.many2one('product.product', 'Freight', required=True, select=True),
        'currency_id':  fields.many2one('res.currency', 'CURRENCY', select=1),
        'amount': fields.float('AMOUNT', digits_compute=dp.get_precision('Account')),
        'per':fields.selection([('P20','P20'), ('P40','P40')], 'PER', required=True, help=""), 
        'quantity': fields.float('Quantity', digits_compute=dp.get_precision('Account')),
        #'net_amount': fields.float('NET', digits_compute=dp.get_precision('Account')),
        'freight_term':fields.selection([('prepaid','Prepaid'), ('collect','Collect')], 'Freight Term', required=True, help=""),
        'ship_line_id': fields.many2one('shipping.bl_order.line', 'Line', ondelete='cascade',),
        'payment_id': fields.many2one('shipping.general.payment', 'Payment', ondelete='cascade', readonly=True, help="Payment for current booking's seals."),
        'net_amount':fields.function(_amount_line, string='NET' , digits_compute=dp.get_precision('Account'),
            store={
                    'export.freight.line': (lambda self, cr, uid, ids, c={}: ids, ['amount','quantity'], 10),
               }), 
        }

    _defaults = {
        'currency_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.currency_id.id,
    } 
    
    def freight_payment(self, cr, uid, ids, context= None):
        return self.action_view_export_freights_payment(cr, uid, ids, context=context)
    
    def action_view_export_freights_payment(self, cr, uid, ids, context=None):
        journal_code='DZFRE'
        payment_pool = self.pool.get('shipping.general.payment')
        period_pool = self.pool.get('account.period')
        account_journal_pool = self.pool.get('account.journal.mapping')
        journal_pool = self.pool.get('account.journal')
        account_pool = self.pool.get('account.account')
        cur_obj = self.pool.get('res.currency')
        
        timenow = time.strftime('%Y-%m-%d')
        journal= journal_pool.search(cr, uid, [('code','=',journal_code)], context = context)
        
        if journal is None:
            raise osv.except_osv(_('Configuration Error!'),_("Create journal with code name DZBK for Booking related Charge."))
        
        journal_obj= journal_pool.browse(cr, uid, journal[0], context=context)
        
        for line in self.browse(cr, uid, ids, context=context):
            if line.payment_id:
                return payment_pool.action_view_payment(cr, uid, [line.payment_id.id], context= context)
            
            search_periods = period_pool.find(cr, uid, line.ship_line_id.bl_date, context=context)
            period_id = search_periods[0]
            
            journal_id= journal_obj.id
    
            name = _('Payment for %s') % (line.name.name)      
            company=self.pool.get('res.users').browse(cr,uid,uid).company_id
            
            debit_account_id= line.name.property_account_expense.id 
            credit_account_id = line.ship_line_id.shipper.property_account_receivable.id
            
            amount_total = line.net_amount
            payment_vals = {
                'notes': name,
                'doc_date': line.ship_line_id.bl_date,
                'state': 'draft',
                'ref':line.ship_line_id.bl_no,
                'origin': line.name.name,
                'resource': 'export.freight.line,%s' % line.id,          
                'journal_id':journal_obj.id,
                'period_id': period_id,
                'credit_account_id':credit_account_id,
                'debit_account_id':debit_account_id,
                'amount_total': amount_total,
            }
            
            payment_id = payment_pool.create(cr, uid, payment_vals, context=context)
            self.write(cr, uid, ids, {'payment_id': payment_id}, context= context)
            
        return payment_pool.action_view_payment(cr, uid, [payment_id], context= context)
    
export_freight_line()

class shipping_container(osv.osv):
    _name='shipping.container'
    _description="Shipping Container"

    def _get_container_status(self, cr, uid, context=None):
        cr.execute("select name, description from shipping_container_status")
        data= cr.fetchall()
        res=[]
        for d in data:
            res.append(d)
        return res
        
    def _check_vassel(self, cr, uid, ids, context=None):

        new_obj= self.browse(cr, uid, ids[0], context= context)
        feet=new_obj.feet_40 and ('feet_20','=',True) or new_obj.feet_20 and ('feet_40','=',True)
        is_exist=self.search(cr, uid, [('prefix','=',new_obj.prefix),('digit6','=',new_obj.digit6),('check1','=',new_obj.check1),feet])

        return (not is_exist)

    _columns={
        'name': fields.char('Name', size=128, required=True, translate=True, select=True),
        'prefix': fields.char('Prefix', size=4 , required=True, help="4 char at the start of container name"),
        'digit6': fields.integer('6 digit number' , required=True, help="6 digit number."),
        'check1': fields.integer('Check Digit' , required=True, help="1 check digit of number."),
        'feet_40': fields.boolean('40\'', select=1, help="Check this if container is 40\'."),
        'feet_20': fields.boolean('20\'', select=1, help="Check this if container is 20\'."),
        'high_cube': fields.boolean('HC', select=1, help="Check this if container high cube(HC)."),
        'type': fields.char('Type', size=2 , required=True, help="2 for container type (DC, HC,DH)"),
        'serial_no': fields.char('Serial No',size=128, select=1, help="Serial No. of container "),
        'ship_line_id':fields.many2one('shipping.bl_order.line','BL Order Line'),
        'status': fields.selection(_get_container_status, 'Condition'),
        'pack_type': fields.selection([('full','Full'),('part','Part')], 'Full/Part'),
        'in_voyage_no': fields.char('IN Voyage No', required=True, size=128, help="No. of in voyage."),
        'bl_no':fields.char('BL No', size=128, ondelete='cascade', help="BL no of relative vassel and in_voyage_no."),
        }


    _defaults = {
        'feet_40': lambda *a: True,
        'feet_20': lambda *a: False,
        'high_cube': lambda *a: False,
        'status':'used',
        'pack_type':'full',
        }

    _constraints = [
        (_check_vassel, 'Incorrect Entry!\nThe vassel name and its size should be unique.',['name']),
    ]

    def create(self, cr, uid, vals, context=None):
        feet_40= vals.get('feet_40',False)
        feet_20=vals.get('feet_20',False)
        high_cube=vals.get('high_cube',False)
        feet=feet_40 and '40' or feet_20 and '20'
        bl_line= vals.get('ship_line_id',False)
        ship_line_id= self.pool.get('shipping.bl_order.line').browse(cr, uid, bl_line)
        vals['in_voyage_no'] = ship_line_id.in_voyage_no
        vals['bl_no']= ship_line_id.bl_no
        
        name ="%s%s%s%s" % (vals.get('prefix'), vals.get('digit6'), vals.get('check1'), feet)

        vals['name'] = name

        container_id = super(shipping_container,self).create(cr, uid, vals, context=context)
        
        return container_id
    
shipping_container()

class shipping_cargo(osv.osv):
    _name='shipping.cargo'
    
    _columns={
            'name': fields.char('Name', size=128, required=True, translate=True, select=True),
            'type': fields.selection([('dry','Dry'), ('refer','Refer'), ('hazard','Hazard'), ('non-hazard','Non-Hazard'), ('out-gate','Out Of Gate')], 'Type Of Cargo', required=True, help=""),
            'cargo_description': fields.text('Cargo Description',translate=True),
            'quantity': fields.float('Qty', digits_compute=dp.get_precision('Account')),
            'uom': fields.many2one('product.uom', 'UoM', select=1),
            'gross_weight': fields.float('Weight', digits_compute=dp.get_precision('Account')),
            'weight_uom': fields.many2one('product.uom', 'Weight UoM', select=1),
            'measurement': fields.float('Measurement', digits_compute=dp.get_precision('Account')   ),
            'measurement_uom': fields.many2one('product.uom', 'UoM', select=1),
            'container_id': fields.many2one('shipping.container', 'Related Container', select=1),
            'ship_line_id':fields.many2one('shipping.bl_order.line','BL Order Line'),
        }
    
shipping_cargo()

class shipping_cargo_export(osv.osv):
    _name='shipping.cargo.export'
    _inherit='shipping.cargo'
    
    _columns={
            'name': fields.char('Name', size=128, required=True, translate=True, select=True),
            'type': fields.selection([('dry','Dry'), ('refer','Refer'), ('hazard','Hazard'), ('non-hazard','Non-Hazard'), ('out-gate','Out Of Gate')], 'Type Of Cargo', required=True, help=""),
            'cargo_description': fields.text('Cargo Description',translate=True),
            'quantity': fields.float('Qty', digits_compute=dp.get_precision('Account')),
            'uom': fields.many2one('product.uom', 'UoM', select=1),
            'gross_weight': fields.float('Weight', digits_compute=dp.get_precision('Account')),
            'weight_uom': fields.many2one('product.uom', 'Weight UoM', select=1),
            'measurement': fields.float('Measurement', digits_compute=dp.get_precision('Account')   ),
            'measurement_uom': fields.many2one('product.uom', 'UoM', select=1),
            'container_id': fields.many2one('shipping.container.inventory', 'Related Container', select=1),
            'ship_line_id':fields.many2one('shipping.bl_order.line','BL Order Line'),
        }
    
shipping_cargo()


class shipping_bl_order(osv.osv):

    _name= "shipping.bl_order"
    _description = "Pre BL Order"
    _order = 'name'

    def _get_type(self, cr, uid, context=None):
        if context is None:
            context={}
        return context.get('type',False)
        
    _columns={
            'name': fields.char('Name', size=128, required=True, translate=True, select=True),
            'vassel_id': fields.many2one('shipping.vassel', 'Vassel Name', required=True, states={'draft': [('readonly', False)]}, readonly=True, ondelete='cascade', help="Vassel name of coming BL."),
            'in_voyage_no': fields.char('IN Voyage No', required=True, size=128, states={'draft': [('readonly', False)]}, readonly=True, help="No. of in voyage."),
            'total_no_of_bl': fields.integer('Total No of BL(s)', select=1, readonly=True),
            'feet_40': fields.integer('40\'', select=1, states={'draft': [('readonly', False)]}, readonly=True),
            'feet_20': fields.integer('20\'', select=1, states={'draft': [('readonly', False)]}, readonly=True),
            'total_no_of_container': fields.integer('Total No of Container(s)', select=1),
            'type': fields.selection([('import','Import'),('export','Export')],'Type'),
            'bl_nos': fields.text('BL Nos', states={'draft': [('readonly', False)]}, readonly=True),
            'company_id': fields.many2one('res.company', 'Company', select=1),
            'state': fields.selection([('draft', 'New'),
                                   ('confirmed', 'Confirmed'),
                                   ('cancel', 'Cancelled'),],
                                  'Status', readonly=True),
        }

    _defaults = {
        'state': 'draft',
        'type': _get_type,
    }
    
    def create(self, cr, uid, vals, context=None):
        vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'shipping.bl_order') or '/'
        vals['total_no_of_container']= vals['feet_40'] + vals['feet_20']

        bl_id= super(shipping_bl_order, self).create(cr, uid, vals, context=context)

        return bl_id

    def write(self, cr, uid, ids, vals, context=None):
        if type(ids)==type(1):
            ids=[ids]
        if vals.get('feet_20',vals.get('feet_40',False)):
            order_obj= self.browse(cr, uid, ids[0], context)
            vals['total_no_of_container']= vals.get('feet_20',order_obj.feet_20) + vals.get('feet_40',order_obj.feet_40)

        res= super(shipping_bl_order,self).write(cr, uid, ids, vals, context= context)

        return res    


    def on_change_feet_40(self, cr, uid, ids, feet_40=0, feet_20=0, context=None):
        return {'value': {'total_no_of_container': feet_40 + feet_20 } }

    def on_change_feet_20(self, cr, uid, ids, feet_40=0, feet_20=0, context=None):
        return {'value': {'total_no_of_container': feet_40 + feet_20 } }

    def on_change_blnos(self, cr, uid, ids, bl_nos='', context=None):
        bl_string=''
        bl_list=[]
        result={}
        if bl_nos and len(bl_nos)>0:
            bl_nos_list = bl_nos.split('\n')
            bl_list=list(set(bl_nos_list))

        if bl_list:
            bl_list_extract= [x for x in bl_list if len(x)>4]
            bl_list_extract.sort()
            bl_string= '\n'.join(bl_list_extract)
            
        if len(bl_list)>0:
            result['total_no_of_bl']= len(bl_list_extract)
            result['bl_nos']= bl_string
            
        return {'value': result }

    def create_blnos(self, cr, uid,ids, context=None):
        bl_string=''
        bl_list=[]
        result={}
        rel_obj= self.pool.get('blno.blorder.rel')

        if type(ids)== type(1):
            ids=[ids]

        old_bl= rel_obj.search(cr, uid, [('bl_no','=',ids[0])] , context= context)
        if old_bl:
            rel_obj.unlink(cr, uid, old_bl, context)

        for bl in self.browse(cr, uid, ids, context= context):
            if bl.bl_nos and len(bl.bl_nos)>0:
                bl_nos_list =  bl.bl_nos.split('\n')
                bl_list=list(set(bl_nos_list))

            if bl_list:
                for nos in bl_list:
                    bl_val={'name': nos,'vassel_id': bl.vassel_id.id, 'in_voyage_no':bl.in_voyage_no,'bl_no':bl.id }
                    rel_obj.create(cr, uid, bl_val, context= context)
        return True

    def button_confirm(self, cr, uid, ids, context=None):
        self.create_blnos(cr, uid, ids, context= context)
        self.write(cr, uid, ids,{'state':'confirmed'}, context= context)
        
        return True

    def button_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids,{'state':'cancel'}, context= context)
        
        return True

shipping_bl_order()

class blno_blorder_rel(osv.osv):
    _name="blno.blorder.rel"
    _columns={
            'name': fields.char('Name', size=128, required=True, translate=True, select=True),
            'vassel_id': fields.many2one('shipping.vassel', 'Vassel Name', required=True, ondelete='cascade', help="Vassel name of coming BL."),
            'in_voyage_no': fields.char('IN Voyage No', size=128, help="No. of in voyage."),
            'bl_no':fields.many2one('shipping.bl_order', 'BL Name', required=True, ondelete='cascade', help="Vassel name of coming BL."),
    }
    
blno_blorder_rel()

class shipping_bl_order_line_amendment(osv.osv):

    _name= "shipping.bl_order.line.amendment"
    _description = "BL Order Line Amendment"
    _order = 'name'
    
    def _get_name(self, cr, uid, context=None):
        return self.pool.get('ir.sequence').get(cr, uid, 'shipping.bl_order.line.amendment') or '/'
        
    _columns={
                'name': fields.char('Name', size=128, required=True, readonly=True,translate=True, select=True),
                'change_count': fields.integer('Amendment Count', readonly=True),
                'changes': fields.text('Amendments', required=True, readonly=True, translate=True),
                'amount': fields.float('AMOUNT', digits_compute=dp.get_precision('Account'), states={'draft': [('readonly', False)]}, readonly=True),
                'date': fields.date('Date', required=True, states={'draft': [('readonly', False)]}, readonly=True),
                'state': fields.selection([('draft', 'New'),
                                   ('cancel', 'Cancelled'),
                                   ('received', 'Received')],
                                  'Status', readonly=True),
                'received_by': fields.many2one('res.partner', 'Received',  ondelete='cascade', ),
                'ship_line_id':fields.many2one('shipping.bl_order.line', 'Source', required=True, ondelete='cascade', readonly=True, help="Vassel name of coming BL."),
            }
    
    _defaults={
        'name': _get_name,
        'state': 'draft',
        'date': time.strftime('%Y-%m-%d'),
        }
    
    def button_am_receipt_invoice(self, cr, uid, ids ,context=None):
        company=self.pool.get('res.users').browse(cr,uid,uid).company_id

        am_obj=self.browse(cr, uid, ids[0], context= context)
        shipping_obj = am_obj.ship_line_id
        bl_order_obj=  self.pool.get('shipping.bl_order.line')
        report_param ={        
                'am_id': ids[0],
                'company_name':company and company.name or '',
                'address':company.partner_id.complete_address,
                'tel_fax':company and "Tel/Fax: %s , %s " % (company.phone and company.phone or '' , company.fax and company.fax or '' ),
             }
        print report_param
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'amm.receipt.invoice',
            'datas': { 'parameters':report_param },
            }
            
            
    def button_receive(self, cr, uid, ids, context=None):
        journal_code='DZAMM'
        account_code='ammendment_account'
        move_pool = self.pool.get('account.move')
        period_pool = self.pool.get('account.period')
        account_journal_pool = self.pool.get('account.journal.mapping')
        journal_pool = self.pool.get('account.journal')
        account_pool = self.pool.get('account.account')
        cur_obj = self.pool.get('res.currency')
        
        timenow = time.strftime('%Y-%m-%d')
        
        account_data = account_journal_pool.get_account(cr, uid, account_code, context= context)
        journal= journal_pool.search(cr, uid, [('code','=',journal_code)], context = context)
        
        if account_data and account_data[0] is None:
            raise osv.except_osv(_('Configuration Error!'),_("Agent Income Account is not defined in Account Journal Mapping."))
            
        if journal is None:
            raise osv.except_osv(_('Configuration Error!'),_("Create journal with code name DZHC for Handling Charge."))
        
        journal_obj= journal_pool.browse(cr, uid, journal[0], context=context)
        account_obj = account_pool.browse(cr, uid, account_data[0], context= context)
            
        for line in self.browse(cr, uid, ids, context=context):
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            search_periods = period_pool.find(cr, uid, timenow, context=context)
            period_id = search_periods[0]
            journal_id= journal_obj.id
    
            name = _('Ammendment of %s') % (line.ship_line_id.bl_no)
            move = {
                'narration': name,
                'date': timenow,
                'ref':line.ship_line_id.bl_no,                
                'journal_id':journal_obj.id,
                'period_id': period_id,
            }
            
            company=self.pool.get('res.users').browse(cr,uid,uid).company_id
            debit_account_id=journal_obj.default_debit_account_id and journal_obj.default_debit_account_id.id or False
            credit_account_id = journal_obj.default_credit_account_id and journal_obj.default_credit_account_id.id or False
            
            amt = line.amount
            
            if debit_account_id:

                debit_line = (0, 0, {
                'name': name,
                'date': timenow,
                'partner_id':False,
                'account_id': debit_account_id,
                'journal_id': journal_id,
                'period_id': period_id,
                'debit': amt > 0.0 and amt or 0.0,
                'credit': amt < 0.0 and -amt or 0.0,
            })
                line_ids.append(debit_line)

            if credit_account_id:

                credit_line = (0, 0, {
                'name': name,
                'date': timenow,
                'account_id': credit_account_id,
                'journal_id': journal_id,
                'period_id': period_id,
                'debit': amt < 0.0 and -amt or 0.0,
                'credit': amt > 0.0 and amt or 0.0,
            })
                line_ids.append(credit_line)
                
            move.update({'line_id': line_ids})
            move_id = move_pool.create(cr, uid, move, context=context)
        
        return self.write(cr, uid, ids, {'state': 'received'} , context = context)
        
class shipping_bl_order_line(osv.osv):

    _name= "shipping.bl_order.line"
    _description = "BL Order"
    _order = 'name'

    def _qty_all(self, cr, uid, ids, name, args, context=None):
        res = {}
        for bl in self.browse(cr, uid, ids, context=context):
            res[bl.id] = {
                'total_container': 0,
                'total_container_20': 0,
                'total_container_40': 0,
            }
            total_container=0
            total_container_20=0
            total_container_40=0
            if bl.type=='import':
                for container in bl.container_lines:
                    if container.feet_20:
                        total_container_20 +=1
                    if container.feet_40:
                        total_container_40 +=1
            if bl.type=='export':            
                for container in bl.export_container_lines:
                    if container.container_id.name[-2:]=="20":
                        total_container_20 +=1
                    if container.container_id.name[-2:]=="40":
                        total_container_40 +=1
                    
            res[bl.id]['total_container'] = total_container_20 + total_container_40
            res[bl.id]['total_container_20'] = total_container_20
            res[bl.id]['total_container_40'] = total_container_40
            
        return res

    def _weight_all(self, cr, uid, ids, name, args, context=None):
        res = {}
        for bl in self.browse(cr, uid, ids, context=context):
            res[bl.id] = {
                'measurement': 0.0,
                'gross_weight':0.0,
                'total_quantity':0.0,
            }
            
            measurement=0.0
            weight=0.0
            total_quantity=0.0
            clines =bl.cargo_lines
            if bl.type=='export':
                clines = bl.export_cargo_lines
                
            for weight_line in clines:
                total_quantity += weight_line.quantity
                weight += weight_line.gross_weight
                measurement += weight_line.measurement
            
            res[bl.id]['total_quantity'] = total_quantity
            res[bl.id]['measurement'] = measurement
            res[bl.id]['gross_weight'] = weight
            
        return res

    def _get_cargo(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('shipping.cargo').browse(cr, uid, ids, context=context):
            result[line.ship_line_id.id] = True
        return result.keys()

    def _get_type(self, cr, uid, context=None):
        if context is None:
            context={}
        return context.get('type',False)
        
        
    _columns={
            'name': fields.char('Name', size=128, readonly=True, translate=True, select=True),
            'vassel_id': fields.many2one('shipping.vassel', 'Vassel Name', states={'draft': [('readonly', False)]}, readonly=True, required=True, ondelete='cascade', help="Vassel name of coming BL."),
            'first_vassel_id': fields.many2one('shipping.vassel', 'Pre-Carriage', states={'draft': [('readonly', False)]}, readonly=True, ondelete='cascade', help="Pre-Carriage name of coming BL."),
            'first_in_voyage_no': fields.char('First IN Voyage No' , size=128, states={'draft': [('readonly', False)]}, readonly=True, help="No. of in voyage."),
            'in_voyage_no': fields.char('IN Voyage No', required=True, states={'draft': [('readonly', False)]}, readonly=True , size=128, help="No. of in voyage."),
            'bl_no':fields.char('BL No', size=128, ondelete='cascade', required=True, states={'draft': [('readonly', False)]}, readonly=True, help="BL no of relative vassel and in_voyage_no."),
            'shipper': fields.many2one('res.partner', 'Shipper', ondelete='cascade', states={'draft': [('readonly', False)]}, readonly=True, help="Vassel name of coming BL."),
            'feeder_line': fields.many2one('res.partner', 'Feeder Operator', ondelete='cascade', states={'draft': [('readonly', False)]}, readonly=True, help="Feeder Operator of coming BL."),  
            'type': fields.selection([('import','Import'),('export','Export')],'Type'),
            'consignee': fields.many2one('res.partner', 'Consignee', required=True, ondelete='cascade', states={'draft': [('readonly', False)]}, readonly=True, help="Vassel name of coming BL."),
            'notify_party': fields.many2one('res.partner', 'Notify Party',  ondelete='cascade', states={'draft': [('readonly', False)]}, readonly=True, help="Notify Party name of coming BL."),
            'notify_party1': fields.many2one('res.partner', 'Notify Party1',  ondelete='cascade', states={'draft': [('readonly', False)]}, readonly=True, help="Notify Party1 of coming BL."),
            'notify_party2': fields.many2one('res.partner', 'Notify Party2',  ondelete='cascade', states={'draft': [('readonly', False)]}, readonly=True, help="Notify Party2 of coming BL."),
            'co_forwarder_id': fields.many2one('res.partner', 'C/O Forwarder', ondelete='cascade', states={'draft': [('readonly', False)]}, readonly=True, help="Vassel name of coming BL."),

            'booking_id': fields.many2one('shipping.booking', 'Booking No',  ondelete='cascade', states={'draft': [('readonly', False)]}, readonly=True, help="Choose booking number."),
            'export_container_lines': fields.one2many('export.container.line', 'ship_line_id', 'Export Container', states={'draft': [('readonly', False)]}, readonly=True),
            'export_freight_lines': fields.one2many('export.freight.line', 'ship_line_id', 'Freights', states={'draft': [('readonly', False)]}, readonly=True),
            'export_cargo_lines': fields.one2many('shipping.cargo.export', 'ship_line_id', 'Export Cargo Lines', states={'draft': [('readonly', False)]}, readonly=True),
          
            'blfee_payment_id': fields.many2one('shipping.general.payment', 'Payment', ondelete='cascade', readonly=True, help="Payment for current booking's seals."),
          
            'container_lines': fields.one2many('shipping.container', 'ship_line_id', 'Container Lines', states={'draft': [('readonly', False)]}, readonly=True),
            'cargo_lines': fields.one2many('shipping.cargo', 'ship_line_id', 'Cargo Lines', states={'draft': [('readonly', False)]}, readonly=True),
            'amendment_lines': fields.one2many('shipping.bl_order.line.amendment', 'ship_line_id', 'Cargo Lines', states={'draft': [('readonly', False)]}, readonly=True),
            
            'release_status':fields.selection([('seaway','Seaway Bill'), ('origin','Origin'), ('surrender','Currender'), ('without','Without')], 'Release Status', states={'draft': [('readonly', False)]}, readonly=True, required=True, help=""),
            
            #'freight_term':fields.selection([('prepaid','Prepaid'), ('collect','Collect')], 'Freight Term', required=True, states={'draft': [('readonly', False)]}, readonly=True, help=""),
            'etb':      fields.date('ETA/ETD YGN', required=True, ondelete='cascade', states={'draft': [('readonly', False)]}, readonly=True, help="ETB of vassel to port."),
            'port_id': fields.many2one('shipping.port', 'Port Name', required=True, states={'draft': [('readonly', False)]}, readonly=True, ondelete='cascade', help="The port name to where the vissel will board."),
            'port_of_loading_id': fields.many2one('shipping.port', 'Port of Loading' , ondelete='cascade', states={'draft': [('readonly', False)]}, readonly=True, help="The port name to where the vissel will load."),
            'port_of_delivery_id': fields.many2one('shipping.port', 'Port of Delivery' , ondelete='cascade', states={'draft': [('readonly', False)]}, readonly=True, help="The port name to where the vissel will delivery."),
            'bl_date': fields.date('BL Date', required=True, ondelete='cascade', states={'draft': [('readonly', False)]}, readonly=True, help="ETB of vassel to port."),
            'freetime_exception': fields.float('Freetime exception', states={'draft': [('readonly', False)]}, readonly=True, help="Freetime exception in days."),
            'total_container_20':fields.function(_qty_all,type="integer",
                store={
                    'shipping.bl_order.line': (lambda self, cr, uid, ids, c={}: ids, ['container_lines', 'export_container_lines'], 20),
                 }, multi='container'),
             'total_container_40':fields.function(_qty_all, type="integer",
            store={
                'shipping.bl_order.line': (lambda self, cr, uid, ids, c={}: ids, ['container_lines', 'export_container_lines'], 20),
             }, multi='container'),
            'total_container':fields.function(_qty_all, string='Total Container', type="integer",
                store={
                    'shipping.bl_order.line': (lambda self, cr, uid, ids, c={}: ids, ['container_lines', 'export_container_lines'], 20),
                 }, multi='container'),
            'total_quantity': fields.function(_weight_all, string='Quantity' , digits_compute=dp.get_precision('Account') ,
                 store={
                    'shipping.bl_order.line': (lambda self, cr, uid, ids, c={}: ids, ['cargo_lines','export_cargo_lines'], 10),
                    'shipping.cargo': (_get_cargo, ['quantity', 'gross_weight', 'measurement', 'product_uom_qty'], 10),
                 }, multi='all'),
            'uom': fields.many2one('product.uom', 'UoM', states={'draft': [('readonly', False)]}, readonly=True, select=1),
            'gross_weight':fields.function(_weight_all, string='Gross Weight' , digits_compute=dp.get_precision('Account'),
                store={
                'shipping.bl_order.line': (lambda self, cr, uid, ids, c={}: ids, ['cargo_lines','export_cargo_lines'], 10),
                'shipping.cargo': (_get_cargo, ['quantity', 'gross_weight', 'measurement'], 10),
                }, multi='all'),
            'weight_uom': fields.many2one('product.uom', 'Weight UOM', states={'draft': [('readonly', False)]}, readonly=True, select=1),
            'measurement': fields.function(_weight_all, string='Measurement' , digits_compute=dp.get_precision('Account'), 
                 store={
                    'shipping.bl_order.line': (lambda self, cr, uid, ids, c={}: ids, ['cargo_lines','export_cargo_lines'], 10),
                    'shipping.cargo': (_get_cargo, ['quantity', 'gross_weight', 'measurement'], 10),
               } , multi='all'),
            'measurement_uom': fields.many2one('product.uom', 'UOM', states={'draft': [('readonly', False)]}, readonly=True, select=1),
            
            'state': fields.selection([('draft', 'New'),
                                   ('cancel', 'Cancelled'),
                                   ('confirmed', 'Confirmed'),
                                   ('export', 'Ready To Export'),
                                   ('invoiced', 'Invoiced'),
                                   ('done', 'Done')],
                                  'Status', readonly=True),
            'freight_lines': fields.one2many('shipping.freight.line', 'ship_line_id', 'Freights', states={'draft': [('readonly', False)]}, readonly=True),
            'freight_id': fields.many2one('shipping.freight', 'Freight', select=1),
            'ro_id': fields.many2one('shipping.release.order', 'RO', select=1),
            'description': fields.text('Description',translate=True),
            'company_id': fields.many2one('res.company', 'Company', states={'draft': [('readonly', False)]}, readonly=True, select=1),
            'operator_code':fields.char('Operator Code', states={'draft': [('readonly', False)]}, readonly=True ,size=10),
            'payable_at': fields.char('Payable At' , size=128, states={'draft': [('readonly', False)]}, readonly=True ),
            'prepaid_at': fields.char('Prepaid At' , size=128, states={'draft': [('readonly', False)]}, readonly=True ),
    }

    _defaults = {
        'state': 'draft',
        'bl_date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'freetime_exception': 7.0,
        'type': _get_type,
    }


    def copy(self, cr, uid, id, default=None, context=None, done_list=None, local=False):
        default = {} if default is None else default.copy()
        if done_list is None:
            done_list = []
        part = self.is_part_bl(cr, uid, id, context= context)
        
        if not part:
            default['container_lines'] = []
            default['export_freight_lines'] = []
            default['freight_lines'] = []
            default['export_container_lines'] = []
        
        return super(shipping_bl_order_line, self).copy(cr, uid, id, default, context=context)

    def is_part_bl(self, cr, uid, id, context=None):
        part=False
        for container in self.browse(cr, uid, id).container_lines:
            if not part and container.pack_type =='part':
                part =True
        return part 
        
    def create(self, cr, uid, vals, context=None):
        vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'shipping.bl_order.line') or '/'
        res=self.check_bl(cr, uid, [], vals.get('vassel_id'), vals.get('in_voyage_no'), vals.get('bl_no'), context)
    		
        return super(shipping_bl_order_line, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        if type(ids) == type(1):
            ids=[ids]

        changes=[]
        bl_obj= self.browse(cr, uid, ids[0], context)
        
        for key in vals:
            amend="Change on %s from %s to %s"
            if bl_obj._columns[key]._obj and bl_obj._columns[key]._type =='many2one':
                amend_obj = self.pool.get(bl_obj._columns[key]._obj).browse(cr, uid, vals[key])
                changes.append(amend % (bl_obj._columns[key].string, bl_obj[key].name, amend_obj.name))
            else:
                changes.append(amend % (bl_obj._columns[key].string, bl_obj[key], vals[key]))
        
        if len(changes)>0:
            vals.update({'amendment_lines':[(0, 0, {'changes':'\n'.join(changes),'change_count':len(changes)})]})
             
        if vals.get('bl_no',False):
            res=self.check_bl(cr, uid, ids, vals.get('vassel_id',bl_obj.vassel_id.id), vals.get('in_voyage_no', bl_obj.in_voyage_no),vals.get('bl_no', bl_obj.bl_no), context)

        return super(shipping_bl_order_line, self).write(cr, uid,ids, vals, context=context)


    def on_change_bl_line(self, cr, uid, ids, vassel_id=False, in_voyage_no=False, bl_no='', context= None):
        if not vassel_id and not in_voyage_no:
            return {'value': {'bl_no':''} }

        self.check_bl(cr, uid, ids , vassel_id, in_voyage_no, bl_no , context= context)
        return {'value': {'bl_no': bl_no } }

    def on_change_booking(self, cr, uid, ids, booking_id=False, context= None):
        booking_obj = self.pool.get('shipping.booking')
        res={
            'shipper':False,
            'consignee':False,
            'feeder_line': False,
            'vassel_id':False,
            'in_voyage_no':False,
            'operator_code':False,
            'etb':False,
            'export_container_lines':[],
        }
        
        if not booking_id:
            return {'value': res }
        booking= booking_obj.browse(cr, uid, booking_id)
        if booking:
            c_line=[]
            for bkl in booking.booking_lines:
                c_line.append((0,0,{'container_id': bkl.container_id.id, 'seal_no':''}))
            res={}
            res={
            'shipper':booking.shipper.id,
            'feeder_line':booking.shipper.id,
            'consignee':booking.consignee.id,
            'vassel_id':booking.vassel_id.id,
            'in_voyage_no':booking.voyage_no,
            'operator_code':booking.operator_code,
            'etb': booking.etd,
            'export_container_lines':c_line,
            }
            
        return {'value': res }

    def check_bl(self, cr, uid, ids, vassel_id=False, in_voyage_no=False, bl_no='', context= None):
    
        vassel_id= vassel_id and vassel_id or 0
        in_voyage_no= in_voyage_no and in_voyage_no or ''
        bl_no = bl_no and bl_no or ''
        vassel_obj= self.pool.get('shipping.vassel').browse(cr, uid, vassel_id)
        rel_obj= self.pool.get('blno.blorder.rel')
        is_exist = rel_obj.search(cr, uid, [('vassel_id','=',vassel_id), ('in_voyage_no','=',in_voyage_no),('name','=',bl_no)], context= context)

        if not is_exist:
            raise osv.except_osv(_('Invalid BL No!'),_("\n Please check the following \n BL No %s.\n for Vassel name: %s \n IN_Voyage_no: %s.") % (bl_no, vassel_obj.name, in_voyage_no))

        return True

    def button_confirm(self, cr, uid, ids, context=None):
        for bl in self.browse(cr, uid, ids, context):
            if bl.type=='import':
                self.create_container_inventory(cr, uid, [bl.id], context= context)
                
                #Create HC to account move line
                self.create_handaling_charges(cr, uid, [bl.id], context = context) 
                
                self.write(cr, uid, ids,{'state':'confirmed'}, context= context)
                #Create Commission for Freight(All Types)
                self.create_invoice(cr, uid, [bl.id], context = context)
                
            elif bl.type=='export':

                self.update_container_inventory(cr, uid, [bl.id], context= context)
                
                #If no cargo, no need for bl_fee calculation 
                if bl.export_cargo_lines>0:
                    #Process account move for freights[OFT]
                    self.create_export_invoice(cr, uid, [bl.id], context= context)
                    
                    #Create BL FEEs to account move lines
                    self.create_export_bl_fees(cr, uid, [bl.id], context= context)
                
                    #Create commission of OFT to account move line
                    self.create_export_outward_comm(cr, uid, [bl.id], context = context)
                
                #Create export HC to account move line 
                self.create_export_handaling_charges(cr, uid, [bl.id], context = context)
                
                self.write(cr, uid, ids,{'state':'export'}, context= context)

        return True

    def create_handaling_charges(self, cr, uid, ids, context=None):
        journal_code='DZHC'
        account_code='agent_income_account'
        move_pool = self.pool.get('account.move')
        period_pool = self.pool.get('account.period')
        account_journal_pool = self.pool.get('account.journal.mapping')
        journal_pool = self.pool.get('account.journal')
        account_pool = self.pool.get('account.account')
        cur_obj = self.pool.get('res.currency')
        
        timenow = time.strftime('%Y-%m-%d')
        
        account_data = account_journal_pool.get_account(cr, uid, account_code, context= context)
        journal= journal_pool.search(cr, uid, [('code','=',journal_code)], context = context)
        
        if account_data and account_data[0] is None:
            raise osv.except_osv(_('Configuration Error!'),_("Agent Income Account is not defined in Account Journal Mapping."))
            
        if journal is None:
            raise osv.except_osv(_('Configuration Error!'),_("Create journal with code name DZHC for Handling Charge."))
        
        journal_obj= journal_pool.browse(cr, uid, journal[0], context=context)
        account_obj = account_pool.browse(cr, uid, account_data[0], context= context)
            
        for bl_line in self.browse(cr, uid, ids, context=context):
            if len(bl_line.container_lines) <1:
                return True
                
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            search_periods = period_pool.find(cr, uid, bl_line.bl_date, context=context)
            period_id = search_periods[0]
            journal_id= journal_obj.id
    
            name = _('HC of %s') % (bl_line.name)            
            move = {
                'narration': name,
                'date': bl_line.bl_date,
                'ref':bl_line.bl_no,                
                'journal_id':journal_obj.id,
                'period_id': period_id,
            }
            company=self.pool.get('res.users').browse(cr,uid,uid).company_id
            debit_account_id= journal_obj.default_debit_account_id and journal_obj.default_debit_account_id.id or False
            credit_account_id = journal_obj.default_credit_account_id and journal_obj.default_credit_account_id.id or False
            
            amount_currency = len(bl_line.container_lines) * 5
            amt = cur_obj.compute(cr, uid, journal_obj.default_debit_account_id.currency_id.id, journal_obj.default_debit_account_id.company_id.currency_id.id, amount_currency, context=context)
            
            if debit_account_id:

                debit_line = (0, 0, {
                'name': bl_line.bl_no,
                'date': timenow,
                'partner_id':False,
                'account_id': debit_account_id,
                'journal_id': journal_id,
                'period_id': period_id,
                'debit': amt > 0.0 and amt or 0.0,
                'credit': amt < 0.0 and -amt or 0.0,
                'amount_currency': amount_currency,
            })
                line_ids.append(debit_line)

            if credit_account_id:

                credit_line = (0, 0, {
                'name': bl_line.bl_no,
                'date': timenow,
                'account_id': credit_account_id,
                'journal_id': journal_id,
                'period_id': period_id,
                'amount_currency': amount_currency,
                'debit': amt < 0.0 and -amt or 0.0,
                'credit': amt > 0.0 and amt or 0.0,
            })
                line_ids.append(credit_line)
                
            move.update({'line_id': line_ids})
            move_id = move_pool.create(cr, uid, move, context=context)
        
        return True
    
    def print_customer_report(self, cr, uid, ids, context=None):
        context= context or {}
        
        context.update({'customer':'customer'})
        return self.print_report( cr, uid, ids, context=context)
        
    def print_report(self, cr, uid, ids, context=None):
        #import jasper_reports
        export_obj = self.browse(cr, uid, ids[0], context= context)
        context= context or {}
        
        company=self.pool.get('res.users').browse(cr,uid,uid).company_id
        comm_obj=self.browse(cr,uid,ids[0],context=context)

        report_param={
            'shipper':export_obj.shipper.complete_address or '',
            'consignee': export_obj.consignee.complete_address or '',
            'notifyparty': export_obj.notify_party.complete_address or '',
            'receipt_place': comm_obj.port_of_delivery_id and comm_obj.port_of_delivery_id.name or '',
            'vassel': comm_obj.vassel_id and comm_obj.vassel_id.name or '',
            'invoyage_no': comm_obj.in_voyage_no,
            'pol': comm_obj.port_of_loading_id.name,
            'pod': comm_obj.port_of_delivery_id.name,
            'delivery_port':comm_obj.port_of_delivery_id and comm_obj.port_of_delivery_id.name or '',
            'shipped_date': comm_obj.bl_date,
            'bl_no': export_obj.bl_no,
            'por': comm_obj.port_of_delivery_id.name,
            'destination':comm_obj.port_of_delivery_id and comm_obj.port_of_delivery_id.name or '',
            'place_of_issue': comm_obj.port_of_loading_id.state_id.name,
            'date_of_issue': comm_obj.bl_date,
            'ship_line_id': ids[0],
            'description': comm_obj.description or '',
            'payable_at': comm_obj.payable_at or '',
            'prepaid_at': comm_obj.prepaid_at or '',
            'customer': context.get('customer','internal'),
        }
        
        return {
            'type': 'ir.actions.report.xml',
            'report_name':'export.bl.data',
            'datas' :{'parameters': report_param },
        }
    
    def print_container(self, cr, uid, ids, context=None):
        #import jasper_reports
        company=self.pool.get('res.users').browse(cr,uid,uid).company_id
        comm_obj=self.browse(cr,uid,ids[0],context=context)

        report_param={
            'ship_line_id': ids[0],
            'bl_no': comm_obj.bl_no,
        }	
        return {
            'type': 'ir.actions.report.xml',
            'report_name':'export.container.attached',
            'datas' :{'parameters': report_param },
        }
        
    def button_cancel(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids,{'state':'cancel'}, context= context)

    def button_release_order_report(self, cr, uid, ids, context=None):
        return True

    def button_release_order(self, cr, uid, ids, context=None):
        relase_order_obj=  self.pool.get('shipping.release.order')

        if type(ids)==type(1):
            ids= [ids]
        ro_id=False
        bl = self.browse(cr, uid, ids[0], context= context)
        
        is_exist= relase_order_obj.search(cr, uid,[('ship_line_id','=',ids[0])])
        if not is_exist:
            ro_val={ 
                'name':bl.bl_no,
                'operator_code':bl.operator_code,
                'feeder_line':bl.feeder_line.id,
                'release_status':bl.release_status,
                'bl_no':bl.bl_no,
                'shipper':bl.shipper.id,
                'consignee':bl.consignee and bl.consignee.id or False,
                'notify_party':bl.notify_party and bl.notify_party.id or False,
                'notify_party1':bl.notify_party1 and bl.notify_party1.id or False,
                'notify_party2':bl.notify_party2 and bl.notify_party2.id or False,
                'vassel_id':bl.vassel_id.id,
                'ship_line_id':bl.id,
                'state':'draft',
                'ro_date':bl.bl_date,
                'etb': bl.etb,
                'in_voyage_no': bl.in_voyage_no,
                }
            ro_id = relase_order_obj.create(cr, uid, ro_val)
            self.write(cr, uid, bl.id, {'ro_id': ro_id } , context = context)
        else:
            self.write(cr, uid, bl.id, {'ro_id': is_exist[0]} , context = context)
            ro_id= is_exist[0]
            relase_order_obj.write(cr, uid, ro_id, {'etb': bl.etb, 'in_voyage_no': bl.in_voyage_no } , context = context)

        return self.action_view_release_order(cr, uid, ro_id, context=context)

    def create_invoice(self, cr, uid, ids, context=None):
        freight_obj= self.pool.get('shipping.freight')
        oft_obj= self.pool.get('product.product').search(cr, uid, [('name','=','OFT')])
        freight_val={}
        freight_line={}
        freight_line_list=[]
        end_with ='A,B,C,D,E,F,G,H,a,b,c,d,e,f,g,h'.split(',')
        for bl in self.browse(cr, uid, ids, context= context):
            if bl.type=='import' and bl.bl_no and bl.bl_no[-1:] in end_with:
                return True 
                
            freight_val={ 
                'shipper':bl.consignee.id,
                'vassel_id':bl.vassel_id.id,
                'in_voyage_no':bl.in_voyage_no,
                'port_of_loading_id': bl.port_of_loading_id.id,
                'bl_no':bl.bl_no,
                'name':bl.bl_no,
                'state':'draft',
                'ship_line_id':bl.id,
            }
            for freight in bl.freight_lines:
                if freight.name.name =='OFT':
                    freight_line={
                            'name': freight.name.id,
                            'amount':freight.amount,
                            'quantity':freight.quantity,
                            'net_amount':freight.net_amount,
                            'per':freight.per,
                            'freight_term': freight.freight_term,
                            }
                        
                freight_line_list.append((0,0,freight_line))

            if len(freight_line_list)>0:
                freight_val['freight_lines']=freight_line_list

            freight_id = freight_obj.create(cr, uid, freight_val)
            freight_obj.button_confirm( cr, uid, [freight_id], context=context)
            
            self.write(cr, uid, bl.id, {'state':'invoiced', 'freight_id': freight_id}, context= context)
            #If part bl, other related bl freight invoice must be same with main bl
            #ie 1, 1A, 1B  must have be same freight invoice 
            part= self.is_part_bl(cr, uid, bl.id)
            bl_ids = self.search(cr, uid, [('bl_no','like',bl.bl_no)])
            self.write(cr, uid, bl_ids, {'state':'invoiced', 'freight_id': freight_id}, context= context)
            
        return self.action_view_invoice(cr, uid, freight_id, context= context)

    def create_container_inventory(self, cr, uid, ids, context=None):
        container_inv_obj= self.pool.get('shipping.container.inventory')
        container_obj= self.pool.get('shipping.container')
        container_full=[]
        container_empty=[]
        for bl_line in self.browse(cr, uid, ids, context= context):
            full_container= [ x.container_id.id for x in bl_line.cargo_lines]
            empty_container= [ x.id for x in bl_line.container_lines if x.id not in full_container]

            if len(full_container)>0:
                for container in container_obj.browse(cr, uid, full_container):
                    vals={}
                    vals['name']= container.name
                    vals['vassel_id']= bl_line.vassel_id.id
                    vals['shipper']=bl_line.shipper.id
                    vals['state']='DF'
                    vals['in_date']= bl_line.bl_date
                    
                    move_line= vals.copy()
                    move_line.update({'move_type':'in', 'bl_id': bl_line.id })
                    move_lines=(0,0, move_line)
                    
                    vals.update({'inventory_lines': [move_lines] } )
                    
                    container_inv_obj.create(cr, uid, vals, context= context)
                    
            if len(empty_container)>0:
                for container in container_obj.browse(cr, uid, empty_container):
                    vals={}
                    vals['name']= container.name
                    vals['vassel_id']= bl_line.vassel_id.id
                    vals['shipper']=bl_line.shipper.id
                    
                    vals.update({'state':'DE' , 'in_date':bl_line.bl_date})
                    
                    move_line= vals.copy()
                    move_line.update({'move_type':'in', 'bl_id': bl_line.id })
                    move_lines=(0,0, move_line)
                    
                    vals.update({'inventory_lines': [move_lines] })
                    
                    container_inv_obj.create(cr, uid, vals, context= context)
        return True
    
    def update_container_inventory(self, cr, uid, ids, context=None):
        container_inv_obj= self.pool.get('shipping.container.inventory')
        container_obj= self.pool.get('shipping.container')
        container_full=[]
        container_empty=[]
        for bl_line in self.browse(cr, uid, ids, context= context):
            full_container= [ x.container_id.id for x in bl_line.export_cargo_lines]
            empty_container= [ x.container_id.id for x in bl_line.export_container_lines if x.id not in full_container]

            if len(full_container)>0:
                for container in container_inv_obj.browse(cr, uid, full_container):
                    vals={}
                    vals['name']= container.name
                    vals['vassel_id']= bl_line.vassel_id.id
                    vals['shipper']=bl_line.shipper.id
                    vals.update({'state':'VF', 'out_date':bl_line.bl_date })
                    
                    move_line= vals.copy()
                    move_line.update({'move_type':'out', 'bl_id': bl_line.id })
                    move_lines=(0,0, move_line)
                    
                    vals.update({'inventory_lines': [move_lines] } )
                    
                    container_inv_obj.create(cr, uid, vals, context= context)
                        
            if len(empty_container)>0:
                for container in container_inv_obj.browse(cr, uid, empty_container):
                    vals={}
                    vals['name']= container.name
                    vals['vassel_id']= bl_line.vassel_id.id
                    vals['shipper']=bl_line.shipper.id
                    vals.update({'state':'VE', 'out_date':bl_line.bl_date })
                    
                    move_line= vals.copy()
                    move_line.update({'move_type':'out', 'bl_id': bl_line.id })
                    move_lines=(0,0, move_line)
                    
                    vals.update({'inventory_lines': [move_lines] } )
                    
                    container_inv_obj.create(cr, uid, vals, context= context)
        return True
                    
    def view_invoice(self, cr, uid, ids, context=None):
        bl_obj = self.browse(cr, uid, ids[0], context= context)
        return self.action_view_invoice(cr, uid, bl_obj.freight_id.id, context= context)

    def action_view_amendment(self, cr, uid, ids, context=None):
        '''
        This function returns an action that display existing invoices of given bl order ids. 
        '''
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        if type(ids) is type(1):
            ids= [ids]
            
        result = mod_obj.get_object_reference(cr, uid, 'container_management', 'open_shipping_bl_order_line_amendment')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        
        result['domain'] = "[('ship_line_id','='," + str(ids[0]) + ")]"

        return result
    
    def action_view_bl_fee(self, cr, uid, ids, context=None):
        '''
        This function returns an action that display existing invoices of given bl order ids. 
        '''
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        if type(ids) is type(1):
            ids= [ids]
            
        result = mod_obj.get_object_reference(cr, uid, 'container_management', 'open_shipping_bl_order_line_amendment')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        
        result['domain'] = "[('ship_line_id','='," + str(ids[0]) + ")]"

        return result
        
        
    def action_view_invoice(self, cr, uid, freight_id, context=None):
        '''
        This function returns an action that display existing invoices of given bl order ids. 
        '''
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')

        result = mod_obj.get_object_reference(cr, uid, 'container_management', 'open_view_shipping_freight_list')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]

        res = mod_obj.get_object_reference(cr, uid, 'container_management', 'shipping_freight_form_view')
        result['views'] = [(res and res[1] or False, 'form')]
        result['res_id'] =  freight_id

        return result

    def action_view_release_order(self, cr, uid, ro_id, context=None):
        '''
        This function returns an action that display existing invoices of given RO ids. 
        '''
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')

        result = mod_obj.get_object_reference(cr, uid, 'container_management', 'open_view_shipping_release_order_form')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]

        res = mod_obj.get_object_reference(cr, uid, 'container_management', 'shipping_release_order_form_view')
        result['views'] = [(res and res[1] or False, 'form')]
        result['res_id'] =ro_id

        return result
    
    #Export Function for Accounting
    def create_export_invoice(self, cr, uid, ids, context=None):
        journal_code='DZFRE'
        move_pool = self.pool.get('account.move')
        period_pool = self.pool.get('account.period')
        account_journal_pool = self.pool.get('account.journal.mapping')
        journal_pool = self.pool.get('account.journal')
        account_pool = self.pool.get('account.account')
        cur_obj = self.pool.get('res.currency')
        
        timenow = time.strftime('%Y-%m-%d')
        
        journal= journal_pool.search(cr, uid, [('code','=',journal_code)], context = context)
        
        if journal is None:
            raise osv.except_osv(_('Configuration Error!'),_("Create journal with code name DZHC for Handling Charge."))
        
        journal_obj= journal_pool.browse(cr, uid, journal[0], context=context)
            
        for bl_line in self.browse(cr, uid, ids, context=context):
            if len(bl_line.export_freight_lines) <1:
                return True
                
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            search_periods = period_pool.find(cr, uid, bl_line.bl_date, context=context)
            period_id = search_periods[0]
            journal_id= journal_obj.id
    
            name = _('Export OFT of %s') % (bl_line.name)            
            move = {
                'narration': name,
                'date': bl_line.bl_date,
                'ref':bl_line.bl_no,
                'bl_no': bl_line.bl_no,    
                'journal_id':journal_obj.id,
                'period_id': period_id,
            }
            
            company=self.pool.get('res.users').browse(cr,uid,uid).company_id
            debit_account_id= bl_line.shipper.property_account_receivable.id
            credit_account_id = False
            
            amount_currency=0
            for line in bl_line.export_freight_lines:
                if line.name.name=='OFT':
                    amt = line.net_amount
                    amount_currency=0
                    credit_account_id = line.name.property_account_export and line.name.property_account_export.id or False
                    
                    if line.currency_id.id != company.currency_id.id:
                        amount_currency = line.net_amount
                        amt = cur_obj.compute(cr, uid, line.currency_id.id, journal_obj.default_debit_account_id.company_id.currency_id.id, amount_currency, context=context)
            
                    if debit_account_id:

                        debit_line = (0, 0, {
                        'name': "DR of BL %s" % bl_line.name,
                        'date': timenow,
                        'partner_id':False,
                        'account_id': debit_account_id,
                        'journal_id': journal_id,
                        'period_id': period_id,
                        'debit': amt > 0.0 and amt or 0.0,
                        'credit': amt < 0.0 and -amt or 0.0,
                        'amount_currency': amount_currency,
                    })
                        line_ids.append(debit_line)

                    if credit_account_id:

                        credit_line = (0, 0, {
                        'name': 'CR on OFT of %s' % bl_line.name,
                        'date': timenow,
                        'account_id': credit_account_id,
                        'journal_id': journal_id,
                        'period_id': period_id,
                        'amount_currency': amount_currency,
                        'debit': amt < 0.0 and -amt or 0.0,
                        'credit': amt > 0.0 and amt or 0.0,
                    })
                        line_ids.append(credit_line)
            
            if len(line_ids)>0:
                move.update({'line_id': line_ids})
                move_id = move_pool.create(cr, uid, move, context=context)
        
        return True
        
    #Create outward commission for Export OFT
    def create_export_outward_comm(self, cr, uid, ids, context=None):
        journal_code='DZCME'
        move_pool = self.pool.get('account.move')
        period_pool = self.pool.get('account.period')
        account_journal_pool = self.pool.get('account.journal.mapping')
        journal_pool = self.pool.get('account.journal')
        account_pool = self.pool.get('account.account')
        cur_obj = self.pool.get('res.currency')
        
        timenow = time.strftime('%Y-%m-%d')
        
        journal= journal_pool.search(cr, uid, [('code','=',journal_code)], context = context)
        
        if journal is None:
            raise osv.except_osv(_('Configuration Error!'),_("Create journal with code name DZHC for Handling Charge."))
        
        journal_obj= journal_pool.browse(cr, uid, journal[0], context=context)
            
        for bl_line in self.browse(cr, uid, ids, context=context):
            if len(bl_line.export_freight_lines) <1:
                return True
                
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            search_periods = period_pool.find(cr, uid, bl_line.bl_date, context=context)
            period_id = search_periods[0]
            journal_id= journal_obj.id
    
            name = _('Export commission of %s') % (bl_line.name)            
            move = {
                'narration': name,
                'date': bl_line.bl_date,
                'ref':bl_line.bl_no,                
                'journal_id':journal_obj.id,
                'period_id': period_id,
            }
            company=self.pool.get('res.users').browse(cr,uid,uid).company_id
            debit_account_id=journal_obj.default_debit_account_id and journal_obj.default_debit_account_id.id or False
            credit_account_id = journal_obj.default_credit_account_id and journal_obj.default_credit_account_id.id or False
            
            amount_currency=0
            for line in bl_line.export_freight_lines:
                    amount_currency = line.amount * 0.05
                    
                    amt = cur_obj.compute(cr, uid, journal_obj.default_debit_account_id.currency_id.id, journal_obj.default_debit_account_id.company_id.currency_id.id, amount_currency, context=context)
                    
                    if debit_account_id:

                        debit_line = (0, 0, {
                        'name': "% on OFT",
                        'date': timenow,
                        'partner_id':False,
                        'account_id': debit_account_id,
                        'journal_id': journal_id,
                        'period_id': period_id,
                        'debit': amt > 0.0 and amt or 0.0,
                        'credit': amt < 0.0 and -amt or 0.0,
                        'amount_currency': amount_currency,
                    })
                        line_ids.append(debit_line)

                    if credit_account_id:

                        credit_line = (0, 0, {
                        'name': '% on OFT',
                        'date': timenow,
                        'account_id': credit_account_id,
                        'journal_id': journal_id,
                        'period_id': period_id,
                        'amount_currency': amount_currency,
                        'debit': amt < 0.0 and -amt or 0.0,
                        'credit': amt > 0.0 and amt or 0.0,
                    })
                        line_ids.append(credit_line)
            
            if len(line_ids)>0:
                move.update({'line_id': line_ids})
                move_id = move_pool.create(cr, uid, move, context=context)
        
        return True
    
    def create_export_handaling_charges(self, cr, uid, ids, context=None):
        journal_code='DZHCE'
        move_pool = self.pool.get('account.move')
        period_pool = self.pool.get('account.period')
        account_journal_pool = self.pool.get('account.journal.mapping')
        journal_pool = self.pool.get('account.journal')
        account_pool = self.pool.get('account.account')
        cur_obj = self.pool.get('res.currency')
        
        timenow = time.strftime('%Y-%m-%d')
        
        journal= journal_pool.search(cr, uid, [('code','=',journal_code)], context = context)
        
        if not any(journal):
            raise osv.except_osv(_('Configuration Error!'),_("Create journal with code name DZHCE for Handling Charge."))
        
        journal_obj= journal_pool.browse(cr, uid, journal[0], context=context)
        
        for bl_line in self.browse(cr, uid, ids, context=context):
            if len(bl_line.export_container_lines) <1:
                return True
                
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            search_periods = period_pool.find(cr, uid, bl_line.bl_date, context=context)
            period_id = search_periods[0]
            journal_id= journal_obj.id
    
            name = _('Export HC of %s') % (bl_line.name)            
            move = {
                'narration': name,
                'date': bl_line.bl_date,
                'ref':bl_line.bl_no,                
                'journal_id':journal_obj.id,
                'period_id': period_id,
            }
            company=self.pool.get('res.users').browse(cr,uid,uid).company_id
            
            debit_account_id=journal_obj.default_debit_account_id and journal_obj.default_debit_account_id.id or False
            credit_account_id = journal_obj.default_credit_account_id and journal_obj.default_credit_account_id.id or False
            
            amount_currency = len(bl_line.export_container_lines) * 5
            amt = cur_obj.compute(cr, uid, journal_obj.default_debit_account_id.currency_id.id, journal_obj.default_debit_account_id.company_id.currency_id.id, amount_currency, context=context)
            
            if debit_account_id:

                debit_line = (0, 0, {
                'name': bl_line.bl_no,
                'date': timenow,
                'partner_id':False,
                'account_id': debit_account_id,
                'journal_id': journal_id,
                'period_id': period_id,
                'debit': amt > 0.0 and amt or 0.0,
                'credit': amt < 0.0 and -amt or 0.0,
                'amount_currency': amount_currency,
            })
                line_ids.append(debit_line)

            if credit_account_id:

                credit_line = (0, 0, {
                'name': bl_line.bl_no,
                'date': timenow,
                'account_id': credit_account_id,
                'journal_id': journal_id,
                'period_id': period_id,
                'amount_currency': amount_currency,
                'debit': amt < 0.0 and -amt or 0.0,
                'credit': amt > 0.0 and amt or 0.0,
            })
                line_ids.append(credit_line)
                
            move.update({'line_id': line_ids})
            move_id = move_pool.create(cr, uid, move, context=context)
        
        return True
    
    def create_export_prepaid_charges(self, cr, uid, ids, context=None):
        journal_code='DZHCE'
        move_pool = self.pool.get('account.move')
        period_pool = self.pool.get('account.period')
        account_journal_pool = self.pool.get('account.journal.mapping')
        journal_pool = self.pool.get('account.journal')
        account_pool = self.pool.get('account.account')
        cur_obj = self.pool.get('res.currency')
        
        timenow = time.strftime('%Y-%m-%d')
        
        journal= journal_pool.search(cr, uid, [('code','=',journal_code)], context = context)
        
        if not any(journal):
            raise osv.except_osv(_('Configuration Error!'),_("Create journal with code name DZHCE for Handling Charge."))
        
        journal_obj= journal_pool.browse(cr, uid, journal[0], context=context)
        
        for bl_line in self.browse(cr, uid, ids, context=context):
            if len(bl_line.export_freight_lines) <1:
                return True
                
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            search_periods = period_pool.find(cr, uid, bl_line.bl_date, context=context)
            period_id = search_periods[0]
            journal_id= journal_obj.id
    
            name = _('Freight Prepaid of %s') % (bl_line.name)            
            move = {
                'narration': name,
                'date': bl_line.bl_date,
                'ref':bl_line.bl_no,                
                'journal_id':journal_obj.id,
                'period_id': period_id,
            }
            company=self.pool.get('res.users').browse(cr,uid,uid).company_id
            
            debit_account_id=journal_obj.default_debit_account_id and journal_obj.default_debit_account_id.id or False
            credit_account_id = journal_obj.default_credit_account_id and journal_obj.default_credit_account_id.id or False
            
            amount_currency=0
            for line in bl_line.export_freight_lines:
                #Only prepaid items are need to be recorded
                if line.freight_term =='prepaid':
                    amount_currency = line.amount
                    amt = cur_obj.compute(cr, uid, journal_obj.default_debit_account_id.currency_id.id, journal_obj.default_debit_account_id.company_id.currency_id.id, amount_currency, context=context)
                    
                    if debit_account_id:
                        debit_line = (0, 0, {
                            'name': "Paid for %s" % line.name.name,
                            'date': timenow,
                            'partner_id':False,
                            'account_id': debit_account_id,
                            'journal_id': journal_id,
                            'period_id': period_id,
                            'debit': amt > 0.0 and amt or 0.0,
                            'credit': amt < 0.0 and -amt or 0.0,
                            'amount_currency': amount_currency,
                        })
                        line_ids.append(debit_line)

            if credit_account_id:
                credit_line = (0, 0, {
                    'name': bl_line.bl_no,
                    'date': timenow,
                    'account_id': credit_account_id,
                    'journal_id': journal_id,
                    'period_id': period_id,
                    'amount_currency': amount_currency,
                    'debit': amt < 0.0 and -amt or 0.0,
                    'credit': amt > 0.0 and amt or 0.0,
                })
                line_ids.append(credit_line)
                
            move.update({'line_id': line_ids})
            move_id = move_pool.create(cr, uid, move, context=context)
        
        return True
    
        
    def create_export_bl_fees(self, cr, uid, ids, context=None):
        journal_code='DZBLF'
        move_pool = self.pool.get('account.move')
        period_pool = self.pool.get('account.period')
        account_journal_pool = self.pool.get('account.journal.mapping')
        journal_pool = self.pool.get('account.journal')
        account_pool = self.pool.get('account.account')
        cur_obj = self.pool.get('res.currency')
        sc = self.pool.get('shipping.config')
        timenow = time.strftime('%Y-%m-%d')
        
        journal= journal_pool.search(cr, uid, [('code','=',journal_code)], context = context)
        
        if not any(journal):
            raise osv.except_osv(_('Configuration Error!'),_("Create journal with code name DZHCE for Handling Charge."))
        
        journal_obj= journal_pool.browse(cr, uid, journal[0], context=context)
        
        for bl_line in self.browse(cr, uid, ids, context=context):
                
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            search_periods = period_pool.find(cr, uid, bl_line.bl_date, context=context)
            period_id = search_periods[0]
            journal_id= journal_obj.id
    
            name = _('BL Fee of %s') % (bl_line.name)            
            move = {
                'narration': name,
                'date': bl_line.bl_date,
                'ref':bl_line.bl_no,                
                'journal_id':journal_obj.id,
                'period_id': period_id,
            }
            company=self.pool.get('res.users').browse(cr,uid,uid).company_id
            
            debit_account_id = bl_line.shipper.property_account_receivable.id
            credit_account_id = journal_obj.default_credit_account_id and journal_obj.default_credit_account_id.id or False
            credit_account_id1 = bl_line.feeder_line.property_account_payable.id
            
            amt = sc.get_bl_fees(cr, uid)
            
            if debit_account_id:
                debit_line = (0, 0, {
                    'name': "BL Fees for %s" % bl_line.name,
                    'date': timenow,
                    'partner_id':False,
                    'account_id': debit_account_id,
                    'journal_id': journal_id,
                    'period_id': period_id,
                    'debit': amt > 0.0 and amt or 0.0,
                    'credit': amt < 0.0 and -amt or 0.0,
                })
                line_ids.append(debit_line)

            if credit_account_id:
                credit_line = (0, 0, {
                    'name': "BL Fees for %s" % bl_line.name,
                    'date': timenow,
                    'account_id': credit_account_id,
                    'journal_id': journal_id,
                    'period_id': period_id,
                    'debit': amt < 0.0 and -amt/2 or 0.0,
                    'credit': amt > 0.0 and amt/2 or 0.0,
                })
                line_ids.append(credit_line)
            
            if credit_account_id1:
                credit_line = (0, 0, {
                    'name': "BL Fees for %s" % bl_line.name,
                    'date': timenow,
                    'account_id': credit_account_id1,
                    'journal_id': journal_id,
                    'period_id': period_id,
                    'debit': amt < 0.0 and -amt/2 or 0.0,
                    'credit': amt > 0.0 and amt/2 or 0.0,
                })
                line_ids.append(credit_line)
                
            move.update({'line_id': line_ids})
            move_id = move_pool.create(cr, uid, move, context=context)
        
        return True
    
    def action_bl_fees_payment(self, cr, uid, ids, context=None):
        journal_code='BNK1'
        payment_pool = self.pool.get('shipping.general.payment')
        period_pool = self.pool.get('account.period')
        account_journal_pool = self.pool.get('account.journal.mapping')
        journal_pool = self.pool.get('account.journal')
        account_pool = self.pool.get('account.account')
        cur_obj = self.pool.get('res.currency')
        
        timenow = time.strftime('%Y-%m-%d')
        
        journal= journal_pool.search(cr, uid, [('code','=',journal_code)], context = context)
        
        if not any(journal):
            raise osv.except_osv(_('Configuration Error!'),_("Create journal with code name DZHCE for Handling Charge."))
        
        journal_obj= journal_pool.browse(cr, uid, journal[0], context=context)
            
        for line in self.browse(cr, uid, ids, context=context):
            if line.blfee_payment_id:
                return payment_pool.action_view_payment(cr, uid, [line.blfee_payment_id.id], context= context)
            
            search_periods = period_pool.find(cr, uid, line.bl_date, context=context)
            period_id = search_periods[0]
            
            journal_id= journal_obj.id
    
            name = _('Payment for BL Fees')
            company=self.pool.get('res.users').browse(cr,uid,uid).company_id
            
            debit_account_id = journal_obj.default_debit_account_id and journal_obj.default_debit_account_id.id or False
            credit_account_id = line.shipper.property_account_receivable.id
            
            amount_total = sc.get_bl_fees(cr, uid)
            payment_vals = {
                'notes': name,
                'doc_date': line.bl_date,
                'state': 'draft',
                'ref': line.bl_no,
                'origin': 'BL_FEES',
                'resource': 'shipping.bl_order.line,%s' % line.id,          
                'journal_id':journal_obj.id,
                'period_id': period_id,
                'credit_account_id':credit_account_id,
                'debit_account_id':debit_account_id,
                'amount_total': amount_total,
            }
            
            payment_id = payment_pool.create(cr, uid, payment_vals, context=context)
            self.write(cr, uid, ids, {'blfee_payment_id': payment_id}, context= context)
            
        return payment_pool.action_view_payment(cr, uid, [payment_id], context= context)
        
    #End of Accounting Function for Export
    
shipping_bl_order_line()

class po_request_view(osv.osv):
    _name = "po.request.view"
    _description = "PO Request"
    _auto = False
    _order='bl_date,name'
    
    _columns = {
        'name': fields.char('PO#', readonly=True),
        'agent_cd': fields.char('AGENT_CD', readonly=True),
        'sub_agent_cd': fields.char('SUB_AGENT_CD', readonly=True),
        'bl_no': fields.char('LOCAL_DOC#', readonly=True),
        'operator_code': fields.char('OPERATOR_FLAG', readonly=True),
        'line': fields.char('LINE', readonly=True),
        'vassel': fields.char('VASSEL', readonly=True),
        'voyage': fields.char('VOYAGE', readonly=True),
        'port_of_loading_id': fields.char('PORT', readonly=True),
        'account_id': fields.char('AC', readonly=True),
        'currency_id': fields.char('CUR', readonly=True),
        'bl_date': fields.char('ACTIVITY_DATE', readonly=True),
        'bl_month': fields.char('BL_MONTH', readonly=True),
        'bl_year': fields.char('BL_YEAR', readonly=True),
        'quantity': fields.float('QTY', readonly=True),
        'unit_price': fields.float('UNIT_PRICE', readonly=True),
        'uoc': fields.char('UNIT_OF_CHARGE', readonly=True),
    }

    def init(self, cr):
        cr.execute("""create or replace view po_request_view as
            select  row_number() over (order by tbl.agent_cd)::int as id, row_number() over (order by tbl.agent_cd)::int as name,tbl.agent_cd, tbl.sub_agent_cd, tbl.bl_no, tbl.operator_code, tbl.line, tbl.vassel,
            tbl.voyage, tbl.port_of_loading_id, tbl.account_id, tbl.currency_id, tbl.bl_date, tbl.bl_month, tbl.bl_year,
            tbl.quantity, tbl.unit_price, tbl.uoc FROM 
            (
            select (bol.id+72412) as aid,(select agent_code from res_company limit 1) as agent_cd, 
            (select sub_agent_code from res_company limit 1) as sub_agent_cd, 
            bol.bl_no, bol.operator_code,''::char(24) line,''::char(24) vassel,''::char(24) voyage,
            bol.port_of_loading_id,'72292'::char(24) account_id,
            (select name from res_currency where id in (select currency_id from res_company limit1)) as currency_id,
            bl_date::char(24) bl_date,  EXTRACT(YEAR FROM bl_date)||'-'||to_char(bl_date,'Month') as bl_month, EXTRACT(YEAR FROM bl_date) as bl_year,1 as quantity, (sf.p20 + sf.p40)*5 as unit_price, 'LUMP'::char(10) as uoc from (
            ----Freight And QTY start
            select sf.ship_line_id , sf.shipper, sf.port_of_loading_id, sf.vassel_id ,sf.bl_no, sf.type, res_qty.* 
            from shipping_freight sf
            left join 
            -----freight QTY and rate Start-----
            (select * from (
            select freight_id, sum(p20) as p20, sum(p40) as p40 from (
            select freight_id, sum(quantity) as p20 , 0 as p40 from shipping_freight_line 
            where per='P20' and freight_id is not null
            group by freight_id
            union
            select  freight_id,0 as p20, sum(quantity) as p40 from shipping_freight_line 
            where per='P40' 
            and freight_id is not null
            group by freight_id
            ) qty
            group by freight_id
            )
            qty -----freight QTY 
            ) res_qty
            on sf.id = res_qty.freight_id

            ----Freight And QTY End
            ) sf 
            left  join shipping_bl_order_line bol on bol.id = sf.ship_line_id

            union

            select(bol.id +92297) as aid, (select agent_code from res_company limit 1) as agent_code, 
            (select sub_agent_code from res_company limit 1) as sub_agent_code, 
            bol.bl_no, bol.operator_code,''::char(24) line,''::char(24) vassel,''::char(24) voyage,
            bol.port_of_loading_id,'72412'::char(24) account_id,
            (select name from res_currency where id in (select currency_id from res_company limit1)) as currency_id,
            bl_date::char(24) bl_date, EXTRACT(YEAR FROM bl_date)||'-'||to_char(bl_date,'Month') as bl_month, EXTRACT(YEAR FROM bl_date) as bl_year,1 as quantity, (sf.f20 + sf.f40)*0.025 as unit_price, 'LUMP'::char(10) as uoc from (
            ----Freight Rate start
            select sf.ship_line_id , sf.shipper, sf.port_of_loading_id, sf.vassel_id ,sf.bl_no, sf.type, rate_res.* 
            from shipping_freight sf
            left join 
            ----- Rate Start-----
            (select freight_id, sum(f20) as f20, sum(f40) as f40 from (
            select freight_id, sum(net_amount) as f20 , 0 as f40 from shipping_freight_line 
            where per='P20' and freight_id is not null
            group by freight_id
            union
            select  freight_id,0 as f20, sum(net_amount) as f40 from shipping_freight_line 
            where per='P40' 
            and freight_id is not null
            group by freight_id
            ) rate group by freight_id
            ) rate_res 
            on sf.id = rate_res.freight_id
            ----Freight And QTY End
            ) sf 
            left  join shipping_bl_order_line bol on bol.id = sf.ship_line_id
            ) tbl
        """)
        
    def init1(self, cr):
        cr.execute("""create or replace view po_request_view as
            select (bol.id+72412) as id,bol.id as name,(select agent_code from res_company limit 1) as agent_cd, 
            (select sub_agent_code from res_company limit 1) as sub_agent_cd, 
             bol.bl_no, bol.operator_code,''::char(24) line,''::char(24) vassel,''::char(24) voyage,
             bol.port_of_loading_id,'72292'::char(24) account_id,
             (select name from res_currency where id in (select currency_id from res_company limit1)) as currency_id,
             bl_date::char(24) bl_date,  EXTRACT(YEAR FROM bl_date)||'-'||to_char(bl_date,'Month') as bl_month, EXTRACT(YEAR FROM bl_date) as bl_year,1 as quantity, (sf.p20 + sf.p40)*5 as unit_price, 'LUMP'::char(10) as uoc from (
            ----Freight And QTY start
            select sf.ship_line_id , sf.shipper, sf.port_of_loading_id, sf.vassel_id ,sf.bl_no, sf.type, res_qty.* 
            from shipping_freight sf
            left join 
            -----freight QTY and rate Start-----
            (select * from (
            select freight_id, sum(p20) as p20, sum(p40) as p40 from (
            select freight_id, sum(quantity) as p20 , 0 as p40 from shipping_freight_line 
            where per='P20' and freight_id is not null
            group by freight_id
            union
            select  freight_id,0 as p20, sum(quantity) as p40 from shipping_freight_line 
            where per='P40' 
            and freight_id is not null
             group by freight_id
             ) qty
            group by freight_id
             )
             qty -----freight QTY 
             ) res_qty
            on sf.id = res_qty.freight_id

            ----Freight And QTY End
            ) sf 
            left  join shipping_bl_order_line bol on bol.id = sf.ship_line_id

            union

            select(bol.id +92297) as id, bol.id as name, (select agent_code from res_company limit 1) as agent_code, 
            (select sub_agent_code from res_company limit 1) as sub_agent_code, 
             bol.bl_no, bol.operator_code,''::char(24) line,''::char(24) vassel,''::char(24) voyage,
             bol.port_of_loading_id,'72412'::char(24) account_id,
             (select name from res_currency where id in (select currency_id from res_company limit1)) as currency_id,
             bl_date::char(24) bl_date, EXTRACT(YEAR FROM bl_date)||'-'||to_char(bl_date,'Month') as bl_month, EXTRACT(YEAR FROM bl_date) as bl_year,1 as quantity, (sf.f20 + sf.f40)*0.025 as unit_price, 'LUMP'::char(10) as uoc from (
            ----Freight Rate start
            select sf.ship_line_id , sf.shipper, sf.port_of_loading_id, sf.vassel_id ,sf.bl_no, sf.type, rate_res.* 
            from shipping_freight sf
            left join 
            ----- Rate Start-----
            (select freight_id, sum(f20) as f20, sum(f40) as f40 from (
            select freight_id, sum(net_amount) as f20 , 0 as f40 from shipping_freight_line 
            where per='P20' and freight_id is not null
            group by freight_id
            union
            select  freight_id,0 as f20, sum(net_amount) as f40 from shipping_freight_line 
            where per='P40' 
            and freight_id is not null
             group by freight_id
            ) rate group by freight_id
            ) rate_res 
            on sf.id = rate_res.freight_id
            ----Freight And QTY End
            ) sf 
            left  join shipping_bl_order_line bol on bol.id = sf.ship_line_id
        """)
    
po_request_view()

class po_request(osv.osv):

    _name = 'po.request'		    
    _columns = {
            'date':fields.date('Date', required=True),
            'output_type': fields.selection([(1, 'PDF'), (2, 'XLS')], "Output Type", help = 'Select output type', required=True, size=-1),
    }
    
    _defaults= {
        'output_type': 1,
        'date': lambda *a: time.strftime('%Y-%m-%d'),
    }
    
    def print_report(self, cr, uid, ids, context=None):
        company=self.pool.get('res.users').browse(cr,uid,uid).company_id
        comm_obj=self.browse(cr,uid,ids[0],context=context)
        dtt = datetime.strptime(comm_obj.date, '%Y-%m-%d')
        
        report_param={
            'company_name':company and company.name or '',
            'address':company.partner_id.complete_address,
            'tel_fax':company and "Tel/Fax: %s , %s " % (company.phone and company.phone or '' , company.fax and company.fax or '' ),
            'date':comm_obj.date,
            'cost_month':comm_obj.date,
            'int_cost_month':dtt.month,
            'int_cost_year': dtt.year,
            'output_type':comm_obj.output_type,
        }	
        report_name='po.request'
        if comm_obj.output_type==1:
            output = 'pdf'
        else:
            output = 'xls'	    
            report_name='po.request.xls'

        jas = self.pool.get('ir.actions.report.xml').search(cr,uid,[('report_name','=',report_name)])	
        self.pool.get('ir.actions.report.xml').write(cr,uid,jas[0],{'report_type':output,'jasper_output':output},context=context)

        return {
            'type': 'ir.actions.report.xml',
            'report_name':report_name,
            'datas': { 'parameters':report_param },
        }		

po_request()
