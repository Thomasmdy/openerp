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

class shipping_booking(osv.osv):

    _name= "shipping.booking"
    _description = "Booking"
    _order = 'name'

    def _qty_all(self, cr, uid, ids, name, args, context=None):
        res = {}
        for bk in self.browse(cr, uid, ids, context=context):
            res[bk.id] = {
                'total_no_of_container': 0,
                'feet_40': 0,
                'feet_20': 0,
            }
            total_container=0
            total_container_20=0
            total_container_40=0
            for container in bk.booking_lines:
                if container.container_id.name[-2:]=="20":
                    total_container_20 +=1
                if container.container_id.name[-2:]=="40":
                    total_container_40 +=1
                    
            res[bk.id]['total_no_of_container'] = total_container_20 + total_container_40
            res[bk.id]['feet_20'] = total_container_20
            res[bk.id]['feet_40'] = total_container_40
            
        return res
        
    _columns={
            'name': fields.char('Booking Reference', size=128, required=True, translate=True, select=True),
            'shipper': fields.many2one('res.partner', 'Shipper', ondelete='cascade', help="Vassel name of coming BL." ,readonly=True,states={'draft': [('readonly', False)]}),
            'consignee': fields.many2one('res.partner', 'Consignee', required=True, ondelete='cascade', help="Vassel name of coming BL." ,readonly=True,states={'draft': [('readonly', False)]}) ,
            'vassel_id': fields.many2one('shipping.vassel', 'Vassel Name', required=True, ondelete='cascade', help="Vassel name of coming BL.",states={'draft': [('readonly', False)]}),
            'voyage_no': fields.char('Voyage No', required=True, size=128, help="No. of in voyage.",readonly=True,states={'draft': [('readonly', False)]}),
            'destination': fields.char('Destination', required=True, size=128, help="Destination.",readonly=True,states={'draft': [('readonly', False)]}),
            'total_no_of_bl': fields.integer('Total No of BL(s)', select=1),
            'feet_40':fields.function(_qty_all, type="integer",
                    store={
                        'shipping.booking': (lambda self, cr, uid, ids, c={}: ids, ['booking_lines'], 20),
                     }, multi='container'),
            'feet_20':fields.function(_qty_all, type="integer",
                    store={
                        'shipping.booking': (lambda self, cr, uid, ids, c={}: ids, ['booking_lines'], 20),
                     }, multi='container'),
            'operator_code':fields.char('Operator Code',size=10,readonly=True,states={'draft': [('readonly', False)]}),
            'commodity':fields.char('Commodity',size=255,readonly=True,states={'draft': [('readonly', False)]}),
            'container_yard':fields.char('Container Yard',size=128,readonly=True,states={'draft': [('readonly', False)]}),
            'booking_lines': fields.one2many('shipping.booking.container', 'booking_id', 'Booking Lines',readonly=True,states={'draft': [('readonly', False)]}),

            'seal_lines': fields.one2many('container.seal', 'booking_id', 'Seals Lines',readonly=True,states={'draft': [('readonly', False)]}),
            'payment_id': fields.many2one('shipping.general.payment', 'Payment', ondelete='cascade', readonly=True, help="Payment for current booking's seals."),

            'total_no_of_container':fields.function(_qty_all, type="integer",
                    store={
                        'shipping.booking': (lambda self, cr, uid, ids, c={}: ids, ['booking_lines'], 20),
                     }, multi='container'),
            'date': fields.date('Date', required=True),
            'etd': fields.date('ETD', required=True),
            'company_id': fields.many2one('res.company', 'Company', select=1),
            'state': fields.selection([('draft', 'New'),
                                   ('cancel', 'Cancelled'),
                                   ('approved', 'Approved'),
                                   ('done', 'Done')],
                                  'Status', readonly=True),
        }

    def create(self, cr, uid, vals, context=None):
        vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'shipping.booking') or '/'
        return super(shipping_booking, self).create(cr, uid, vals, context=context)
        
    _defaults = {
        'state': 'draft',
        'name': '/',
        'etd': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
    }

    def button_cancel(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids,{'state':'cancel'}, context= context)
    
    def button_seal_payment(self, cr, uid, ids, context=None):
        return self.view_seal_payment(cr, uid, ids, context= context)
        
    def button_approved(self, cr, uid, ids, context=None):
        container_inv_obj = self.pool.get('shipping.container.inventory')
        
        #Seal charg account move lines
        self.create_seal_charges(cr, uid, ids, context= context)
        
        #GOH account move lines
        self.create_goh_charges(cr, uid, ids, context=context)
        
        for line in self.browse(cr, uid, ids, context= context):
            for booking_line in line.booking_lines:
                context.update({'force': True } )
                state=False
                if booking_line.type=='LVE':
                    state ='LVE'
                else:
                    state ='LVF'
                
                container_inv_obj.update_state(cr, uid, booking_line.container_id.name,state  ,context= context) 
                
        self.write(cr, uid, ids,{'state':'approved'}, context= context)
        return True

    def view_seal_payment(self, cr, uid, ids, context=None):
        journal_code='DZBK'
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
            
        for bk_line in self.browse(cr, uid, ids, context=context):
            if len(bk_line.seal_lines) <1:
                return True
            if bk_line.payment_id:
                return self.action_view_payment(cr, uid, [bk_line.payment_id.id], context= context)
                
            search_periods = period_pool.find(cr, uid, bk_line.date, context=context)
            period_id = search_periods[0]
            journal_id= journal_obj.id
            name = _('Payment for Seals Charge of Booking %s') % (bk_line.name)            
            company=self.pool.get('res.users').browse(cr,uid,uid).company_id

            credit_account_id =bk_line.shipper.property_account_receivable.id
            debit_account_id= journal_obj.default_debit_account_id and journal_obj.default_debit_account_id.id or False

            amount_total=0
            
            for seal in bk_line.seal_lines:
                amt = seal.product_id.list_price
                amount_total = amount_total + amt
                
            payment_vals = {
                'notes': name,
                'doc_date': bk_line.date,
                'state': 'draft',
                'ref':bk_line.name,  
                'resource': 'shipping.booking,%s' % bk_line.id,          
                'journal_id':journal_obj.id,
                'period_id': period_id,
                'credit_account_id':credit_account_id,
                'debit_account_id':debit_account_id,
                'amount_total': amount_total,
            }
            
            payment_id = payment_pool.create(cr, uid, payment_vals, context=context)
            self.write(cr, uid, ids, {'payment_id': payment_id}, context= context)
            
        return self.action_view_payment(cr, uid, [payment_id], context= context)
    
    def action_view_payment(self, cr, uid, payment_ids, context=None):
        '''
        This function returns an action that display existing invoices of given sales order ids. It can either be a in a list or in a form view, if there is only one invoice to show.
        '''
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        result = mod_obj.get_object_reference(cr, uid, 'container_management', 'action_shipping_general_payment')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]

        #choose the view_mode accordingly
        if len(payment_ids)>1:
            result['domain'] = "[('id','in',["+','.join(map(str, payment_ids))+"])]"
        else:
            res = mod_obj.get_object_reference(cr, uid, 'container_management', 'view_shipping_general_payment_form')
            result['views'] = [(res and res[1] or False, 'form')]
            result['res_id'] = payment_ids and payment_ids[0] or False
        return result
        
    def create_seal_charges(self, cr, uid, ids, context=None):
        journal_code='DZBK'
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
            
        for bk_line in self.browse(cr, uid, ids, context=context):
            if len(bk_line.seal_lines) <1:
                return True
                
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            search_periods = period_pool.find(cr, uid, bk_line.date, context=context)
            period_id = search_periods[0]
            journal_id= journal_obj.id
            name = _('Seals Charge of %s') % (bk_line.name)            
            
            move = {
                'narration': name,
                'date': bk_line.date,
                'ref':bk_line.name,                
                'journal_id':journal_obj.id,
                'period_id': period_id,
            }
            
            company=self.pool.get('res.users').browse(cr,uid,uid).company_id
            credit_account_id =journal_obj.default_credit_account_id and journal_obj.default_credit_account_id.id or False
            debit_account_id= bk_line.shipper.property_account_receivable.id
            amount_total=0
            
            if debit_account_id:
                for seal in bk_line.seal_lines:
                    amt = seal.price
                    amount_total = amount_total + amt
                    debit_line = (0, 0, {
                    'name': 'Seals Of %s' % seal.product_id.name,
                    'date': bk_line.date or timenow,
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
                'name': bk_line.name,
                'date': bk_line.date or timenow,
                'account_id': credit_account_id,
                'journal_id': journal_id,
                'period_id': period_id,
                'debit': amount_total < 0.0 and -amount_total or 0.0,
                'credit': amount_total > 0.0 and amount_total or 0.0,
                })
                
                line_ids.append(credit_line)
                
            move.update({'line_id': line_ids})
            move_id = move_pool.create(cr, uid, move, context=context)
        
        return True
    
    def create_goh_charges(self, cr, uid, ids, context=None):
        journal_code='DZBK'
        product_name='GOH'
        
        move_pool = self.pool.get('account.move')
        period_pool = self.pool.get('account.period')
        account_journal_pool = self.pool.get('account.journal.mapping')
        journal_pool = self.pool.get('account.journal')
        account_pool = self.pool.get('account.account')
        cur_obj = self.pool.get('res.currency')
        product_pool = self.pool.get('product.product')
        
        timenow = time.strftime('%Y-%m-%d')
        journal= journal_pool.search(cr, uid, [('code','=',journal_code)], context = context)
        
        if journal is None:
            raise osv.except_osv(_('Configuration Error!'),_("Create journal with code name DZHC for Handling Charge."))
        
        journal_obj= journal_pool.browse(cr, uid, journal[0], context=context)
            
        for bk_line in self.browse(cr, uid, ids, context=context):
            if len(bk_line.booking_lines) <1:
                return True
                
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            search_periods = period_pool.find(cr, uid, bk_line.date, context=context)
            period_id = search_periods[0]
            journal_id= journal_obj.id
            name = _('GOH Amount of %s') % (bk_line.name)            
            product_ids= product_pool.search(cr, uid, [('name','=',product_name)], context= context)
            if not any(product_ids):
                raise osv.except_osv(_('Configuration Error!'),_("Create freight term with name GOH to store GOH amount."))
        
            move = {
                'narration': name,
                'date': bk_line.date,
                'ref':bk_line.name,                
                'journal_id':journal_obj.id,
                'period_id': period_id,
            }
            
            company=self.pool.get('res.users').browse(cr,uid,uid).company_id
            
            goh_product= product_pool.browse(cr, uid, product_ids[0], context)
            debit_account_id = goh_product.property_account_expense.id
            credit_account_id= goh_product.property_account_export.id #
            amount_total=0
            #USD amount_currency
            
            if debit_account_id:
                for goh in bk_line.booking_lines:
                    amt = goh.goh_amount
                    amount_total = amount_total + amt
                    debit_line = (0, 0, {
                    'name': 'GOH for %s' % goh.container_id.name,
                    'date': bk_line.date or timenow,
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
                'name': "GOH Receivable From SG",
                'date': bk_line.date or timenow,
                'account_id': credit_account_id,
                'journal_id': journal_id,
                'period_id': period_id,
                'debit': amount_total < 0.0 and -amount_total or 0.0,
                'credit': amount_total > 0.0 and amount_total or 0.0,
                })
                
                line_ids.append(credit_line)
                
            move.update({'line_id': line_ids})
            move_id = move_pool.create(cr, uid, move, context=context)
        
        return True
        
    def print_report(self, cr, uid, ids, context=None):
        user_obj =self.pool.get('res.users').browse(cr,uid,uid)
        company=user_obj.company_id
        comm_obj=self.browse(cr,uid,ids[0],context=context)

        report_param={
            'booking_id': ids[0],
            'user_name': user_obj.name,
        }	

        return {
            'type': 'ir.actions.report.xml',
            'report_name':'booking.report',
            'datas' :{'parameters': report_param },
        }
        
    def print_attached_report(self, cr, uid, ids, context=None):
        user_obj =self.pool.get('res.users').browse(cr,uid,uid)
        company=user_obj.company_id
        comm_obj=self.browse(cr,uid,ids[0],context=context)

        report_param={
            'booking_id': ids[0],
            'user_name': user_obj.name,
            'subject': "ATTACHED CONTAINER NUMBER FOR MV %s V. %s, ETD %s" % (comm_obj.vassel_id.name, comm_obj.voyage_no, comm_obj.etd),
            'shipper_name': "SHIPPER : %s " % comm_obj.shipper.name,
        }	

        return {
            'type': 'ir.actions.report.xml',
            'report_name':'booking.report.attached',
            'datas' :{'parameters': report_param },
        }
        
shipping_booking()

class shipping_booking_container(osv.osv):

    _name= "shipping.booking.container"
    _description = "Booking Container"

    _columns={
            'container_id': fields.many2one('shipping.container.inventory', 'Container', required=True, ondelete='cascade', help="Vassel name of coming BL." ) ,
            'type': fields.selection([('LVE', 'Empty Evacuation'),
                                   ('LVF', 'Lander For Export')],
                                  'Booking Type', required=True),
            'booking_id': fields.many2one('shipping.booking', 'Booking', ondelete='cascade'),
            'goh_amount': fields.float('GOH Amount', digits_compute=dp.get_precision('Account')),
            'vassel_id': fields.many2one('shipping.vassel', 'IN Vassel', required=True),
            'voyage_no': fields.char('Voyage No',  size=128),
        }
    
    _defaults ={
        'type':'LVE',
    }
shipping_booking_container()

class container_seal(osv.osv):

    _name= "container.seal"
    _description = "Seals Numbers"

    _columns={
            'booking_id': fields.many2one('shipping.booking', 'Booking', ondelete='cascade'),
            'product_id':fields.many2one('product.product', 'Product', select=1),
            'price': fields.float('Price', digits_compute=dp.get_precision('Account')),
            'seal_no': fields.char('Sael No', size=128, required=True , select=True),
        }
    
container_seal()

