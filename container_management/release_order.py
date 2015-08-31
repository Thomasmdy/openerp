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


class shipping_release_order(osv.osv):

    _name= "shipping.release.order"
    _description = "Release Order"
    _order = 'name'

    def _get_ro_amount(self, cr, uid, context=None):
        config_obj= self.pool.get('shipping.config')
        return config_obj.get_ro_amount(cr, uid, context= context)
        
    _columns={				
                'name': fields.char('Name', size=128, required=True, translate=True, select=True),	
                'received_no':fields.char('Received No',size=50),	
                'received_by': fields.many2one('res.partner', 'Received',  ondelete='cascade', ),
                'container_state': fields.selection([('LD', 'Local Devending'),
                                                    ('TD', 'Terminal Devending')], 'Container State'),
                'operator_code':fields.char('Operator Code',size=10,readonly=True),
                'ref':fields.char('Reference', size=128, ondelete='cascade',readonly=True,),
                'feeder_line': fields.many2one('res.partner', 'Feeder Operator', ondelete='cascade', help="Feeder Operator of coming BL." ,readonly=True),
                'release_status':fields.selection([('seaway','Seaway Bill'), ('origin','Origin'), ('cylinder','Cylender'), ('without','Without')], 'Release Status', required=True, help=""),
                'bl_no':fields.char('BL No', size=128, ondelete='cascade', help="BL no of relative vassel and in_voyage_no." ,readonly=True),
                'shipper': fields.many2one('res.partner', 'Shipper', ondelete='cascade', help="Vassel name of coming BL." ,readonly=True),
                'consignee': fields.many2one('res.partner', 'Consignee', required=True, ondelete='cascade', help="Vassel name of coming BL." ,readonly=True) ,
                'notify_party': fields.many2one('res.partner', 'Notify Party',  ondelete='cascade', help="Notify Party name of coming BL." ,readonly=True),
                'notify_party1': fields.many2one('res.partner', 'Notify Party1',  ondelete='cascade', help="Notify Party1 of coming BL." ,readonly=True),
                'notify_party2': fields.many2one('res.partner', 'Notify Party2',  ondelete='cascade', help="Notify Party2 of coming BL." ,readonly=True),
                'vassel_id': fields.many2one('shipping.vassel', 'Vassel Name', required=True, ondelete='cascade', help="Vassel name of coming BL." ,readonly=True),
                #'container_lines': fields.one2many('shipping.container', 'ship_line_id', 'Container Lines'),		    
                'ro_date': fields.date('RO Date' , ondelete='cascade', readonly=True),
                'state': fields.selection([('draft', 'New'),
                                   ('cancel', 'Cancelled'),
                                   ('received', 'Recieved')],
                                  'Status', readonly=True),
                'etb':      fields.date('ETA/ETD YGN', required=True, states={'draft': [('readonly', False)]}, readonly=True , help="ETA of vassel to port."),
                'ship_line_id':fields.many2one('shipping.bl_order.line','Source Document'),
                'in_voyage_no': fields.char('IN Voyage No', required=True, states={'draft': [('readonly', False)]}, readonly=True , size=128, help="No. of in voyage."),
                'amount': fields.float('AMOUNT', digits_compute=dp.get_precision('Account')),
#				'period_id': fields.many2one('account.period', 'Force Period',states={'draft': [('readonly', False)]}, readonly=True, domain=[('state','<>','done')], help="Keep empty to use the period of the validation(Payslip) date."),
                'journal_id': fields.many2one('account.journal', 'RO Journal',states={'draft': [('readonly', False)]}, readonly=True),
                'move_id': fields.many2one('account.move', 'Accounting Entry', readonly=True),				
                }

    _defaults = {
        'state': 'draft',
        'amount': _get_ro_amount, 
        'container_state':'LD',
    }					
        
    def create(self, cr, uid, vals, context= None):
        vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'shipping.release.order') or '/'
        ro_id = super(shipping_release_order,self).create(cr, uid, vals, context= context)
        self.create_ro_line(cr, uid, [ro_id], context=context)
        
        return ro_id
        
    def update_container(self, cr, uid, ids, context=None):
        container_inv_obj = self.pool.get('shipping.container.inventory')
        
        for release in self.browse(cr, uid, ids, context=context):
            for container in release.ship_line_id.container_lines:
                container_inv_obj.update_state(cr, uid, container.name, release.container_state, context= context )

        return True
    
    def create_ro_line(self, cr, uid, ids, context=None):
        move_pool = self.pool.get('account.move')
        period_pool = self.pool.get('account.period')
        timenow = time.strftime('%Y-%m-%d')
        self.update_container( cr, uid, ids, context=context)
        
        journal_code='DZRO'
        account_code='releaseorder_account'
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
        
        for release in self.browse(cr, uid, ids, context=context):
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            ctx = dict(context or {}, account_period_prefer_normal=True)
            search_periods = period_pool.find(cr, uid, release.ro_date, context=ctx)
            period_id = search_periods[0]
            journal_id=journal_obj.id
            default_partner_id = release.consignee
            if not default_partner_id:
                raise osv.except_osv(_('Error!'),_("\n Please Fill Received Person and Received No"))
                            
            name = _('RO of %s') % (release.bl_no)            
            move = {
                'narration': name,
                'date': release.ro_date,
                'ref':release.name,                
                'journal_id':journal_id,
                'period_id': period_id,
            }
            company=self.pool.get('res.users').browse(cr,uid,uid).company_id
            debit_account_id= release.consignee.property_account_receivable.id
            credit_account_id = journal_obj.default_credit_account_id and journal_obj.default_credit_account_id.id or False
            amt = release.amount

            if debit_account_id:

                debit_line = (0, 0, {
                'name': release.bl_no,
                'date': timenow,
                'partner_id':False,
                'account_id': debit_account_id,
                'journal_id': journal_id,
                'period_id': period_id,
                'debit': amt > 0.0 and amt or 0.0,
                'credit': amt < 0.0 and -amt or 0.0,
            })
                line_ids.append(debit_line)
                debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']

            if credit_account_id:

                credit_line = (0, 0, {
                'name': release.bl_no,
                'date': timenow,
                'partner_id': default_partner_id.id,
                'account_id': credit_account_id,
                'journal_id': journal_id,
                'period_id': period_id,
                'debit': amt < 0.0 and -amt or 0.0,
                'credit': amt > 0.0 and amt or 0.0,
            })
                line_ids.append(credit_line)
                credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']
                
        move.update({'line_id': line_ids})
        move_pool.create(cr, uid, move, context=context)
        
        return True
        
    def button_receive(self, cr, uid, ids, context=None):
        move_pool = self.pool.get('account.move')
        period_pool = self.pool.get('account.period')
        timenow = time.strftime('%Y-%m-%d')
        self.update_container( cr, uid, ids, context=context)
        
        journal_code='DZRO'
        account_code='releaseorder_account'
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
        
        for release in self.browse(cr, uid, ids, context=context):
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            ctx = dict(context or {}, account_period_prefer_normal=True)
            search_periods = period_pool.find(cr, uid, release.ro_date, context=ctx)
            period_id = search_periods[0]
            journal_id=journal_obj.id
            default_partner_id = release.received_by
            if not default_partner_id:
                raise osv.except_osv(_('Error!'),_("\n Please Fill Received Person and Received No"))
                            
            name = _('RO of %s') % (release.received_by.name)            
            move = {
                'narration': name,
                'date': release.ro_date,
                'ref':release.name,                
                'journal_id':journal_id,
                'period_id': period_id,
            }
            company=self.pool.get('res.users').browse(cr,uid,uid).company_id
            debit_account_id= journal_obj.default_debit_account_id and journal_obj.default_debit_account_id.id or False
            credit_account_id = release.consignee.property_account_receivable.id
            amt = release.amount

            if debit_account_id:

                debit_line = (0, 0, {
                'name': release.bl_no,
                'date': timenow,
                'partner_id':False,
                'account_id': debit_account_id,
                'journal_id': journal_id,
                'period_id': period_id,
                'debit': amt > 0.0 and amt or 0.0,
                'credit': amt < 0.0 and -amt or 0.0,
            })
                line_ids.append(debit_line)
                debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']

            if credit_account_id:

                credit_line = (0, 0, {
                'name': release.bl_no,
                'date': timenow,
                'partner_id': default_partner_id.id,
                'account_id': credit_account_id,
                'journal_id': journal_id,
                'period_id': period_id,
                'debit': amt < 0.0 and -amt or 0.0,
                'credit': amt > 0.0 and amt or 0.0,
            })
                line_ids.append(credit_line)
                credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']
                
        move.update({'line_id': line_ids})
        move_id = move_pool.create(cr, uid, move, context=context)
        self.write(cr, uid, [release.id], {'move_id': move_id,'state':'received'}, context=context)
        return True

    def button_release_order(self, cr, uid, ids ,context=None):
        company=self.pool.get('res.users').browse(cr,uid,uid).company_id

        ro_obj=self.browse(cr, uid, ids[0], context= context)
        shipping_obj = ro_obj.ship_line_id
        relase_order_obj=  self.pool.get('shipping.bl_order.line')
        datas = {
             'parameters': {
                        'ship_line_id': ro_obj.ship_line_id.id,
             			'rec_no':ro_obj.received_no and ro_obj.received_no or '',
             			'tel': ro_obj.received_by.phone and ro_obj.received_by.phone or '',
             			'nrc':ro_obj.received_by.nrc and ro_obj.received_by.nrc or '',
             			'rec_name':ro_obj.received_by.name,
             			'org':ro_obj.received_by.organization and ro_obj.received_by.organization or '',
             			'ro_date':ro_obj.ro_date,
                     }
            }

        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'release.order',
            'datas': datas,
            'nodestroy' : True
            }

    def button_ro_receipt_invoice(self, cr, uid, ids ,context=None):
        company=self.pool.get('res.users').browse(cr,uid,uid).company_id

        ro_obj=self.browse(cr, uid, ids[0], context= context)
        shipping_obj = ro_obj.ship_line_id
        relase_order_obj=  self.pool.get('shipping.bl_order.line')
        report_param ={        
                'ro_id': ids[0],
                'company_name':company and company.name or '',
                'address':company.partner_id.complete_address,
                'tel_fax':company and "Tel/Fax: %s , %s " % (company.phone and company.phone or '' , company.fax and company.fax or '' ),
             }

        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'ro.receipt.invoice',
            'datas': { 'parameters':report_param },
            }
            
shipping_release_order()

class res_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
        'nrc' : fields.char('NRC', size=24, ),
        'organization' : fields.char('Organization', size=50, ),
    }
res_partner()
