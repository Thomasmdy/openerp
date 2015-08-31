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

class shipping_freight(osv.osv):

    _name='shipping.freight'

    def _amount_all(self, cr, uid, ids, name, args, context=None):
        res = {}
        for bl in self.browse(cr, uid, ids, context=context):
            res[bl.id] = {
                'freight_total': 0.0,
            }
            
            freight_total=0.0
            for freight_line in bl.freight_lines:
                if freight_line.freight_term =='collect':
                    freight_total += freight_line.net_amount
            
            res[bl.id]['freight_total'] = freight_total
        return res

    _columns={

        'shipper': fields.many2one('res.partner', 'Consignee', ondelete='cascade', help="Vassel name of coming BL."),
        'name': fields.char('INVOICE', size=128 , translate=True, select=True),
        'vassel_id': fields.many2one('shipping.vassel', 'Vassel Name', readonly=True, required=True, ondelete='cascade', help="Vassel name of coming BL."),
        'in_voyage_no': fields.char('VOYAGE NO', required=True , size=128, readonly=True, help="No. of in voyage."),
        'port_of_loading_id': fields.many2one('shipping.port', 'Port of Loading', readonly=True, required=True, ondelete='cascade', help="The port name to where the vissel will board."),
        'bl_no':fields.char('INVOICE NO', size=128, ondelete='cascade', readonly=True, help="BL no of relative vassel and in_voyage_no."),
        'net_amount': fields.float('NET AMOUNT', digits_compute=dp.get_precision('Account')),
        'date':      fields.date('DATE', required=True, ondelete='cascade', help="DATE OF INVOICE."),
        'state': fields.selection([('draft', 'New'),
                                   ('cancel', 'Cancelled'),
                                   ('confirmed', 'Confirmed'),
                                   ('invoiced', 'Invoiced'),
                                   ('done', 'Done')
                                   ],
                                  'Status', readonly=True),
        'freight_lines': fields.one2many('shipping.freight.line', 'freight_id', 'Freight Lines'),
        'freight_total':fields.function(_amount_all, string='Freight Total' , digits_compute=dp.get_precision('Account'), 
             store={
                'shipping.freight': (lambda self, cr, uid, ids, c={}: ids, ['freight_lines'], 10),
           } , multi='amt-all'),
        'type': fields.selection([('HC', 'HC'),
                                   ('DC', 'DC')],
                                  'Type', readonly=True),
        'ship_line_id':fields.many2one('shipping.bl_order.line','BL ORDER LINE'),
        'move_id':fields.many2one('account.move','Journal Entries For Freights'),
        'move_id2':fields.many2one('account.move','Journal Entries For Commission'),
        'user_id': fields.many2one('res.users', 'User', help="Person who creates the freight invoice"),
        'company_id':fields.many2one('res.company', 'Company', required=True, readonly=True),
        }

    _defaults = {
        'user_id': lambda self, cr, uid, context: uid,
        'type':'HC',
        'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
    }    

    def create_account_move(self, cr, uid, ids, context=None):
        journal_code='DZFR'
        account_code='freight_payable_account'
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
            
        for freight in self.browse(cr, uid, ids, context=context):
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            search_periods = period_pool.find(cr, uid, freight.date, context=context)
            period_id = search_periods[0]
            journal_id= journal_obj.id

            name = _('Freight of BL %s') % (freight.bl_no)            
            move = {
                'narration': name,
                'date': freight.date,
                'ref': freight.bl_no,                
                'journal_id':journal_obj.id,
                'period_id': period_id,
            }
            
            company=self.pool.get('res.users').browse(cr,uid,uid).company_id
            debit_account_id= freight.shipper.property_account_receivable.id
            credit_account_id = journal_obj.default_credit_account_id and journal_obj.default_credit_account_id.id or False
                
            for line in freight.freight_lines:
                if line.freight_term == 'collect':
                    amount_currency = line.net_amount
                    amt = cur_obj.compute(cr, uid, journal_obj.default_debit_account_id.currency_id.id, journal_obj.default_debit_account_id.company_id.currency_id.id, amount_currency, context=context)
                
                    if debit_account_id:
                        debit_line = (0, 0, {
                        'name':line.name.name,
                        'date': freight.date,
                        'partner_id':False,
                        'account_id': debit_account_id,
                        'journal_id': journal_id,
                        'period_id': period_id,
                        'debit': amt > 0.0 and amt or 0.0,
                        'credit': amt < 0.0 and -amt or 0.0,
                        'amount_currency': amount_currency,
                        } )
                            
                        line_ids.append(debit_line)
                    
                    amount_currency = freight.freight_total
                    amt = cur_obj.compute(cr, uid, journal_obj.default_debit_account_id.currency_id.id, journal_obj.default_debit_account_id.company_id.currency_id.id, amount_currency, context=context)
                    
                    if credit_account_id:
                        credit_line = (0, 0, {
                            'name': name,
                            'date': freight.date,
                            'account_id': credit_account_id,
                            'journal_id': journal_id,
                            'period_id': period_id,
                            'debit': amt < 0.0 and -amt or 0.0,
                            'credit': amt > 0.0 and amt or 0.0,
                            'amount_currency': amount_currency,
                        } )
                    
                        line_ids.append(credit_line)
            move.update({'line_id': line_ids})
            move_id = move_pool.create(cr, uid, move, context=context)
                
        return move_id
    
    def create_account_move_payment(self, cr, uid, ids, context=None):
        journal_code='DZFR'
        account_code='freight_payable_account'
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
            
        for freight in self.browse(cr, uid, ids, context=context):
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            search_periods = period_pool.find(cr, uid, freight.date, context=context)
            period_id = search_periods[0]
            journal_id= journal_obj.id

            name = _('Payment For Freight of BL %s') % (freight.bl_no)            
            move = {
                'narration': name,
                'date': freight.date,
                'ref': freight.bl_no,                
                'journal_id':journal_obj.id,
                'period_id': period_id,
            }
            
            company=self.pool.get('res.users').browse(cr,uid,uid).company_id
            #If invoiced, we need just add payment  line for this freight invoice
            debit_account_id= journal_obj.default_debit_account_id and journal_obj.default_debit_account_id.id or False
            credit_account_id = freight.shipper.property_account_receivable.id
            
            for line in freight.freight_lines:
                if line.freight_term =='collect':
                    amount_currency = line.net_amount
                    amt = cur_obj.compute(cr, uid, journal_obj.default_debit_account_id.currency_id.id, journal_obj.default_debit_account_id.company_id.currency_id.id, amount_currency, context=context)
                
                    if debit_account_id:
                        debit_line = (0, 0, {
                        'name':line.name.name,
                        'date': freight.date,
                        'partner_id':False,
                        'account_id': debit_account_id,
                        'journal_id': journal_id,
                        'period_id': period_id,
                        'debit': amt > 0.0 and amt or 0.0,
                        'credit': amt < 0.0 and -amt or 0.0,
                        'amount_currency': amount_currency,
                        } )
                            
                        line_ids.append(debit_line)
                    
            amount_currency = freight.freight_total
            amt = cur_obj.compute(cr, uid, journal_obj.default_debit_account_id.currency_id.id, journal_obj.default_debit_account_id.company_id.currency_id.id, amount_currency, context=context)
            
            if credit_account_id:
                credit_line = (0, 0, {
                    'name': name,
                    'date': freight.date,
                    'partner_id': freight.shipper.id,
                    'account_id': credit_account_id,
                    'journal_id': journal_id,
                    'period_id': period_id,
                    'debit': amt < 0.0 and -amt or 0.0,
                    'credit': amt > 0.0 and amt or 0.0,
                    'amount_currency': amount_currency,
                } )
            
                line_ids.append(credit_line)
            move.update({'line_id': line_ids})
            move_id = move_pool.create(cr, uid, move, context=context)
                
        return move_id
        
    def create_account_move_commission(self, cr, uid, ids, context=None):
        journal_code='DZCM'
        move_pool = self.pool.get('account.move')
        period_pool = self.pool.get('account.period')
        account_journal_pool = self.pool.get('account.journal.mapping')
        journal_pool = self.pool.get('account.journal')
        account_pool = self.pool.get('account.account')
        cur_obj = self.pool.get('res.currency')
        
        timenow = time.strftime('%Y-%m-%d')
        journal= journal_pool.search(cr, uid, [('code','=',journal_code)], context = context)
        
        if journal is None:
            raise osv.except_osv(_('Configuration Error!'),_("Create journal with code name DZCM for commission ."))
        
        journal_obj= journal_pool.browse(cr, uid, journal[0], context=context)
            
        for freight in self.browse(cr, uid, ids, context=context):
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            search_periods = period_pool.find(cr, uid, freight.date, context=context)
            period_id = search_periods[0]
            journal_id= journal_obj.id

            name = _('Commission of BL %s') % (freight.bl_no)            
            move = {
                'narration': name,
                'date': freight.date,
                'ref': freight.bl_no,                
                'journal_id':journal_obj.id,
                'period_id': period_id,
            }
            
            company=self.pool.get('res.users').browse(cr,uid,uid).company_id
            
            for line in freight.freight_lines:
                amount_currency = line.net_amount * 0.025 # 2.5%
                amt = cur_obj.compute(cr, uid, journal_obj.default_debit_account_id.currency_id.id, journal_obj.default_debit_account_id.company_id.currency_id.id, amount_currency, context=context)

                debit_account_id= journal_obj.default_debit_account_id and journal_obj.default_debit_account_id.id or False
                credit_account_id = journal_obj.default_credit_account_id and journal_obj.default_credit_account_id.id or False
                
                if debit_account_id:
                    debit_line = (0, 0, {
                    'name':line.name.name,
                    'date': freight.date,
                    'partner_id':False,
                    'account_id': debit_account_id,
                    'journal_id': journal_id,
                    'period_id': period_id,
                    'amount_currency': amount_currency,
                    'debit': amt > 0.0 and amt or 0.0,
                    'credit': amt < 0.0 and -amt or 0.0,
                    })
                    
                    line_ids.append(debit_line)
                    
                if credit_account_id:

                    credit_line = (0, 0, {
                    'name': line.name.name,
                    'date': freight.date,
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
        
        return  move_id
        
    def button_confirm(self, cr, uid, ids, context=None):
        move_id = self.create_account_move_commission(cr, uid, ids, context = context)

        self.write(cr, uid, ids, {'state':'confirmed', 'move_id': move_id}, context = context)
        return True

    def button_cancel(self, cr, uid, ids, context=None):
        return True

    def create_invoice(self, cr, uid, ids, context=None):
        move_id = self.create_account_move(cr, uid, ids, context = context)

        self.write(cr, uid, ids, {'state':'invoiced', 'move_id': move_id}, context = context)
        return True
    
    def create_payment(self, cr, uid, ids, context=None):
        move_id = self.create_account_move_payment(cr, uid, ids, context = context)
        self.write(cr, uid, ids, {'state':'done'}, context = context)
        return True
        
shipping_freight()


class shipping_freight_line(osv.osv):

    _name='shipping.freight.line'

    _columns={
        'name':fields.many2one('product.product', 'CHARGE', select=1),
        'currency_id':  fields.many2one('res.currency', 'CURRENCY', select=1),
        'amount': fields.float('AMOUNT', digits_compute=dp.get_precision('Account')),
        'per':fields.selection([('P20','P20'), ('P40','P40')], 'PER', required=True, help=""), 
        'quantity': fields.float('Quantity', digits_compute=dp.get_precision('Account')),
        'net_amount': fields.float('NET AMOUNT', digits_compute=dp.get_precision('Account')),
        'freight_id':fields.many2one('shipping.freight','SOURCE ORDER'),
        'freight_term':fields.selection([('prepaid','Prepaid'), ('collect','Collect')], 'Freight Term', required=True, help=""),
        'ship_line_id': fields.many2one('shipping.bl_order.line', 'Line', ondelete='cascade',),
        }

    _defaults = {
        'currency_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.currency_id.id,
        'freight_term': 'collect',
    } 
    
shipping_freight_line()

