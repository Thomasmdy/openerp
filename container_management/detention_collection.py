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

from datetime import datetime, timedelta
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

def get_date_list(date_from, date_to):
    dtf = datetime.strptime(date_from, '%Y-%m-%d')
    dtt = datetime.strptime(date_to, '%Y-%m-%d')
    no = dtt - dtf
    date_list=[]
    [date_list.append((dtf + timedelta(days=x)).strftime('%Y-%m-%d')) for x in range(int(no.days + 1))]
    date_list.sort()
    return date_list
    
class shipping_detention_charge(osv.osv):

    _name= "shipping.detention.charge"
    _description = "Detention Charge"
    _order = 'date,type,day_from,period_type,charges'

    _columns={				
                'name': fields.char('Name', size=128, required=True, translate=True, select=True),	
                'day_from':fields.integer('Day From', required=True),	
                'day_to':fields.integer('Day To', required=True, help="0 means unlimit"),	
                'type': fields.selection([('20_gp', '20\' GP'),('40_gp', '40\' GP & HQ')], 'Type',required=True),
                'period_type': fields.selection([('free', 'Free Period'),('first', 'First Period'),('second', 'Second Period'),('third', 'Third Period')], 'Period', size=16, required=True, help="first: First Period, second: Second Period, third: Third Period"),
                'date': fields.date('Effective Date', required=True, ondelete='cascade', ),
                'charges':fields.float('Charge/day', digits_compute=dp.get_precision('Account'),required=True),
            }

    _defaults ={
        'date': fields.date.today,
    }
    
    
    def get_charge(self, cr, uid, date_from, date_to, period_type, c_type='20_gp', context=None):
        """
        Get charge amount for different effected date
        Each deduct_date must be greater than each effected date
        param:
        date_from: start date to deducted
        date_to  : end date to deduct
        period_type: first or second or third
        c_type : container type (20' or 40')
        
        return:
            if only deduct charge rate exit, return 0
            else return total deduct amount for each date 
        """
        charge_ids= self.search(cr, uid, [('period_type','=',period_type),('type','=',c_type),], order='date desc', context =context)
        charge_amount=0.0
        charge_amount_by_date=0.0
        charge_rate =0
        date_done=[]
        date_charged={}
        remark=[]
        date_list = get_date_list(date_from, date_to)
        if len(charge_ids)==1:
            return 0
            
        for charge in self.browse(cr, uid, charge_ids):
            charge_amount_by_date=0.0
            for date in date_list:
                if charge.date <= date and date not in date_done:
                    charge_amount += charge.charges
                    charge_amount_by_date += charge.charges
                    date_done.append(date)
            if charge_amount_by_date>0:
                date_charged[charge.date] = charge.charges
        #If only date for charge rate
        if len(date_charged)==1:
            #Return amount , charge rate
            return charge_amount,date_charged[date_charged.keys()[0]], ''
        elif len(date_charged)>1:
            #If more than one, only return remark
            for key, val in date_charged.iteritems():
                rmk ='Charge rate %s starting from date %s' % (val, key )
                remark.append(rmk)
                
        return charge_amount, 0, '\n'.join(remark)
        
        
shipping_detention_charge()

class shipping_detention_collection(osv.osv):

    _name='shipping.detention.collection'

    def _qty_all(self, cr, uid, ids, name, args, context=None):
        res = {}
        for bl in self.browse(cr, uid, ids, context=context):
            res[bl.id] = {
                'container_total': 0.0,
            }
            
            detention_total= bl.detention_lines and len(bl.detention_lines) or 0.0
            
            res[bl.id]['container_total'] = detention_total
        return res

    _columns={
        'name': fields.char('INVOICE', size=128 , translate=True, select=True),
        'vassel_id': fields.many2one('shipping.vassel', 'Vassel Name', readonly=True, required=True, states={'draft': [('readonly', False)]}, ondelete='cascade', help="Vassel name of coming BL."),
        'consignee': fields.many2one('res.partner', 'Consignee', required=True,states={'draft': [('readonly', False)]}, ondelete='cascade', help="Consignee." ,readonly=True) ,
        'in_voyage_no': fields.char('VOYAGE NO', required=True , size=128, readonly=True,states={'draft': [('readonly', False)]}, help="No. of in voyage."),
        'port_of_loading_id': fields.many2one('shipping.port', 'Port of Loading', readonly=True, required=True,states={'draft': [('readonly', False)]}, ondelete='cascade', help="The port name to where the vissel will board."),
        'bl_no':fields.char('BL NO', size=128, ondelete='cascade', required=True, readonly=True,states={'draft': [('readonly', False)]}, help="BL no of relative vassel and in_voyage_no."),
        'ship_line_id':fields.many2one('shipping.bl_order.line','BL ORDER LINE'),
        'date':      fields.date('DATE', required=True, ondelete='cascade', help="DATE OF INVOICE.",states={'draft': [('readonly', False)]}),
        'state': fields.selection([('draft', 'New'),
                                   ('cancel', 'Cancelled'),
                                   ('confirmed', 'Confirmed'),
                                   ('invoiced', 'Invoiced')],
                                  'Status', readonly=True),
        'detention_lines': fields.one2many('shipping.detention.line', 'detention_id', 'Detention Containers Lines', readonly=True ,states={'draft': [('readonly', False)]}),
        'receipt_id': fields.many2one('detention.charge.receipt', 'Charge', readonly=True),
        'container_total':fields.function(_qty_all, string='Container Total' , digits_compute=dp.get_precision('Account'), 
             store={
                'shipping.detention.collection': (lambda self, cr, uid, ids, c={}: ids, ['detention_lines'], 10),
           } , multi='qty-all'),
        'user_id': fields.many2one('res.users', 'User', help="Person who creates the freight invoice"),
        'company_id':fields.many2one('res.company', 'Company', required=True, readonly=True),
        }

    _defaults = {
        'user_id': lambda self, cr, uid, context: uid,
        'state'  : 'draft',
        'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
    }

    def _get_number_of_days(self, date_from, date_to):
        """Returns a float equals to the timedelta between two dates given as string."""
        from_dt = datetime.strptime(date_from, DATETIME_FORMAT)
        to_dt = datetime.strptime(date_to, DATETIME_FORMAT)
        timedelta = to_dt - from_dt
        diff_day = timedelta.days + 1 + float(timedelta.seconds) / 86400
        return diff_day
    
    def get_charge_for_days(self, cr, uid, days, c_type='20',paid_days=0, context= None):
        """
         bl_no: BL data line which contain relative bl information for each container
         receipt_date: Date to which charge will be collect from etb of BL
        """
        period_obj= self.pool.get('shipping.detention.charge')
        cr.execute('select day_from, day_to, type, charges, name, id from shipping_detention_charge where charges>0 order by id limit 6 ')
        data=cr.fetchall()
        charges_20=[ {'id': x[5], 'name': x[4] , 'day_from': x[0], 'day_to':x[1], 'type': x[2], 'charge': x[3]} for x in data  if x[2] =='20_gp' ]
        charges_40=[ {'id': x[5], 'name': x[4] , 'day_from': x[0], 'day_to':x[1], 'type': x[2], 'charge': x[3]} for x in data if x[2] =='40_gp']
        charges_list_20=[]
        if c_type=='20':
            for charge in charges_20:
                day_list={}
                period_type = str(period_obj.browse(cr, uid, charge['id']).period_type)
                if charge['day_to']>0:
                    if charge['day_from'] < days and charge['day_to'] < days:
                        if paid_days >=charge['day_from'] and paid_days <= charge['day_to']:
                            day_list['day_from']= paid_days
                            day_list['name']= charge['name']
                            day_list['id']= charge['id']
                            day_list['day_to']= charge['day_to']
                            day_list['charge']	= float(charge['charge'])
                            day_list['period_type']	= period_type
                            paid_days +=  day_list['day_to'] - day_list['day_from'] +1
                        elif paid_days <= charge['day_from'] and paid_days <= charge['day_to']:
                            day_list['name']= charge['name']
                            day_list['id']= charge['id']
                            day_list['day_from']= charge['day_from']
                            day_list['day_to']= charge['day_to']
                            day_list['charge']	= float(charge['charge'])
                            day_list['period_type']	= period_type,
                            paid_days +=  day_list['day_to'] - day_list['day_from'] +1
                    elif charge['day_from'] < days and charge['day_to'] > days:
                        if paid_days==0 or paid_days>= charge['day_to']:
                            day_list['name']= charge['name']
                            day_list['id']= charge['id']
                            day_list['day_from']=charge['day_from']
                            day_list['day_to']= charge['day_to']
                            day_list['charge']	= float(charge['charge'])
                            day_list['period_type']	= period_type
                            paid_days +=  day_list['day_to'] - day_list['day_from'] +1
                        elif paid_days >= charge['day_from'] and paid_days <= charge['day_to']:
                            day_list['name']= charge['name']
                            day_list['id']= charge['id']
                            day_list['day_from']= charge['day_from']
                            day_list['day_to']= days
                            day_list['charge']	= float(charge['charge'])
                            day_list['period_type']	= period_type
                            paid_days +=  day_list['day_to'] - day_list['day_from'] +1
                else:
                    if charge['day_from'] <= days:
                        if paid_days>= charge['day_from'] and paid_days<= days:
                            day_list['name']= charge['name']
                            day_list['id']= charge['id']
                            day_list['day_from']= paid_days
                            day_list['day_to']= days
                            day_list['charge']	= float(charge['charge'])
                            day_list['period_type']	= period_type
                            paid_days +=  day_list['day_to'] - day_list['day_from'] +1
                        elif paid_days <= charge['day_from']  and paid_days<= days:
                            day_list['name']= charge['name']
                            day_list['id']= charge['id']
                            day_list['day_from']= charge['day_from']
                            day_list['day_to']= days
                            day_list['charge']	= float(charge['charge'])
                            day_list['period_type']	= period_type
                            paid_days +=  day_list['day_to'] - day_list['day_from'] +1

                if day_list.get('charge',False):
                    charges_list_20.append(day_list)

        charges_list_40=[]
        if c_type=='40':
            for charge in charges_40:
                day_list={}
                period_type = str(period_obj.browse(cr, uid, charge['id']).period_type)
                if charge['day_to']>0:
                    if charge['day_from'] < days and charge['day_to'] < days:
                        if paid_days >=charge['day_from'] and paid_days <= charge['day_to']:
                            day_list['name']= charge['name']
                            day_list['id']= charge['id']
                            day_list['day_from']= paid_days
                            day_list['day_to']= charge['day_to']
                            day_list['charge']	= float(charge['charge'])
                            day_list['period_type']	= period_type
                            paid_days +=  day_list['day_to'] - day_list['day_from'] +1
                        elif paid_days <= charge['day_from'] and paid_days <= charge['day_to']:
                            day_list['name']= charge['name']
                            day_list['id']= charge['id']
                            day_list['day_from']= charge['day_from']
                            day_list['day_to']= charge['day_to']
                            day_list['charge']	= float(charge['charge'])
                            day_list['period_type']	= period_type
                            paid_days +=  day_list['day_to'] - day_list['day_from'] +1
                    elif charge['day_from'] < days and charge['day_to'] > days:
                        if paid_days==0 or paid_days>= charge['day_to']:
                            day_list['name']= charge['name']
                            day_list['id']= charge['id']
                            day_list['day_from']=charge['day_from']
                            day_list['day_to']= charge['day_to']
                            day_list['charge']	= float(charge['charge'])
                            day_list['period_type']	= period_type
                            paid_days +=  day_list['day_to'] - day_list['day_from'] +1
                        elif paid_days >= charge['day_from'] and paid_days <= charge['day_to']:
                            day_list['name']= charge['name']
                            day_list['id']= charge['id']
                            day_list['day_from']= charge['day_from']
                            day_list['day_to']= days
                            day_list['charge']	= float(charge['charge'])
                            day_list['period_type']	= period_type
                            paid_days +=  day_list['day_to'] - day_list['day_from'] +1
                else:
                    if charge['day_from'] <= days:
                        if paid_days>= charge['day_from'] and paid_days<= days:
                            day_list['name']= charge['name']
                            day_list['id']= charge['id']
                            day_list['day_from']= paid_days
                            day_list['day_to']= days
                            day_list['charge']	= float(charge['charge'])
                            day_list['period_type']	= period_type
                            paid_days +=  day_list['day_to'] - day_list['day_from'] +1
                        elif paid_days <= charge['day_from']  and paid_days<= days:
                            day_list['name']= charge['name']
                            day_list['id']= charge['id']
                            day_list['day_from']= charge['day_from']
                            day_list['day_to']= days
                            day_list['charge']	= float(charge['charge'])
                            day_list['period_type']	= period_type
                            paid_days +=  day_list['day_to'] - day_list['day_from'] +1

                if day_list.get('charge',False):
                    charges_list_40.append(day_list)

        return (c_type=='20' and charges_list_20 or charges_list_40)


    def create_detention_charge_line(self, cr, uid, container, bl_no, receipt_date=None, context= None):
        """
         bl_no: BL data line which contain relative bl information for each container
         receipt_date: Date to which charge will be collect from etb of BL
        """
        tran_obj= self.pool.get('container.detention.transaction')
        bl_obj = self.pool.get('shipping.bl_order.line')
        bl_id = bl_obj.search(cr, uid, [('bl_no','=',bl_no)], context= context)[0]
        ship_line_id= bl_obj.browse(cr, uid, bl_id, context)
        paid_days=ship_line_id.freetime_exception
        #Get last_charge_date from container transaction
        last_charged_trans = tran_obj.get_last_charge_date(cr, uid, container, bl_no)
        last_charged_date=False
        if last_charged_trans:
            last_charged_date=last_charged_trans['date_charged']
        
        c_type= container[-2:]
        
        today= receipt_date and receipt_date or datetime.today().strftime(DATETIME_FORMAT)

        #Calculate day count from start to today or receipt_date
        days = self._get_number_of_days(ship_line_id.etb, today)
        if last_charged_date:
            paid_days =self._get_number_of_days(ship_line_id.etb, last_charged_date)

        charge_list = self.get_charge_for_days(cr, uid, days, c_type, paid_days + 1) # +1 to paid_days to start next day
        start_date =datetime.strptime(ship_line_id.etb, '%Y-%m-%d')
        charges_list_40=[]
        charges_list_20=[]

        for charge in charge_list:
            day_from= int(charge['day_from']) -1
            day_to = int(charge['day_to']) -1
            
            date1=(start_date  + relativedelta(days=+day_from)).strftime('%d/%m')
            date2=(start_date  + relativedelta(days=+day_to)).strftime('%d/%m')
            
            date_from = (start_date  + relativedelta(days=+day_from)).strftime(DATETIME_FORMAT)
            date_to =(start_date  + relativedelta(days=+day_to)).strftime(DATETIME_FORMAT)
            
            day_list={}
            day_list['name']= "%s-%s-%s" % (charge['name'],date1, date2 )
            day_list['number_of_day']= int(charge['day_to']) - int(charge['day_from']) + 1
            day_list['charge']	= float(charge['charge'])
            day_list['period_id']	= charge['id']
            day_list['eta_ygn']	= ship_line_id.etb
            day_list['date_free_to']= (start_date  + relativedelta(days=+ ship_line_id.freetime_exception-1)).strftime('%Y-%m-%d')
            
            day_list['period_type']	= charge['period_type']
            day_list['date_from']= date_from
            day_list['date_to'] = date_to
            
            if c_type=='20':
                charges_list_20.append( day_list )
            else:
                charges_list_40.append( day_list )

        return ( c_type=='20' and charges_list_20 or charges_list_40)

    def create_invoice(self, cr, uid, ids, context=None):
        receipt_obj= self.pool.get('detention.charge.receipt')
        charges_obj= self.pool.get('shipping.detention.charge')
        
        receipt_val={}
        receipt_line_p20={}
        receipt_line_p40={}
        receipt_line_list=[]
        for receipt in self.browse(cr, uid, ids, context= context):

            receipt_val={ 
                'consignee':receipt.consignee.id,
                'bl_no': receipt.bl_no,
                'date': receipt.date,
                'source':receipt.name,
                'state':'draft',
            }
            container_20=0
            container_40=0
            for receipt_line in receipt.detention_lines:
                charge_list = self.create_detention_charge_line(cr, uid, receipt_line.container_id.name , receipt.bl_no, receipt.date)
                if receipt_line.container_id.feet_20:
                    receipt_line_p20={}
                    container_20 +=1
                    for charge in charge_list:
                        charge_amount, charge_rate, remark= charges_obj.get_charge(cr, uid, charge['date_from'], charge['date_to'], charge['period_type'], context=context)
                        receipt_line_p20={
                            'name':charge['name'],
                            'quantity':1,
                            'type': '20',
                            'charge_amount': charge_amount,
                            'charge': charge_rate>0 and charge_rate or charge['charge'],
                            'period_id': charge['period_id'],
                            'number_of_day':charge['number_of_day'],
                            'container':receipt_line.container_id.name,
                            'eta_ygn': charge['eta_ygn'],
                            'date_free_to': charge['date_free_to'],
                            'period_type': charge['period_type'],
                            'date_from': charge['date_from'],
                            'date_to': charge['date_to'],
                            'remark': remark,
                            }

                        receipt_line_list.append((0,0,receipt_line_p20))
                elif receipt_line.container_id.feet_40:
                    container_40 +=1
                    charge_list = self.create_detention_charge_line(cr, uid, receipt_line.container_id.name , receipt.bl_no, receipt.date)
                    receipt_line_p40={}
                    for charge in charge_list:
                        charge_amount, charge_rate, remark= charges_obj.get_charge(cr, uid, charge['date_from'], charge['date_to'], charge['period_type'], '40_gp', context=context)
                        
                        receipt_line_p40={
                            'name':charge['name'],
                            'quantity':1,
                            'type': '40',
                            'charge_amount': charge_amount,
                            'charge': charge_rate>0 and charge_rate or charge['charge'],
                            'period_id': charge['period_id'],
                            'number_of_day':charge['number_of_day'],
                            'container':receipt_line.container_id.name,
                            'eta_ygn': charge['eta_ygn'],
                            'date_free_to': charge['date_free_to'],
                            'period_type': charge['period_type'],
                            'date_from': charge['date_from'],
                            'date_to': charge['date_to'],
                            'remark': remark,
                            }
                        receipt_line_list.append((0,0,receipt_line_p40))

            if len(receipt_line_list)>0:
                receipt_val['receipt_lines']=receipt_line_list

            receipt_val.update({'qty_total': "20\' %s : 40\' %s " % (container_20, container_40)}),			
            receipt_id = receipt_obj.create(cr, uid, receipt_val)

            self.write(cr, uid, receipt.id,{'state':'invoiced', 'receipt_id': receipt_id}, context= context)

        self.create_detention_trans(cr, uid, ids, context= context)

        return self.action_view_invoice(cr, uid, receipt_id, context= context)

    def action_view_invoice(self, cr, uid, receipt_id, context=None):
        '''
        This function returns an action that display existing invoices of given receipt ids. 
        '''
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')

        result = mod_obj.get_object_reference(cr, uid, 'container_management', 'open_view_detention_charge_receipt_list')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]

        res = mod_obj.get_object_reference(cr, uid, 'container_management', 'detention_charge_receipt_form_view')
        result['views'] = [(res and res[1] or False, 'form')]
        result['res_id'] =  receipt_id

        return result

    def onchange_bl_no(self, cr, uid, ids, bl_no,vassel_id, in_voyage_no, context= None):
        res={}
        bl_line = self.pool.get('shipping.bl_order.line').search(cr, uid, [('bl_no','=', bl_no),('vassel_id','=',vassel_id), ('in_voyage_no','=',in_voyage_no)], context= context)
        if bl_line:
            res={'ship_line_id': bl_line[0]}
        return {'value': res}

    def button_confirm(self, cr, uid, ids, context=None):

        return self.write(cr, uid, ids, { 'state':'confirmed' } , context= context)

    def button_cancel(self, cr, uid, ids, context=None):
        return True

    def create_detention_trans(self, cr, uid, ids, context=None):
        tran_obj= self.pool.get('container.detention.transaction')
        for receipt in self.browse(cr, uid, ids, context= context):
            vals={
                'date_charged': receipt.date,
                'charged_detention_id':receipt.id,
                'consignee': receipt.consignee.id,
                'bl_no': receipt.bl_no,
            }

            for receipt_line in receipt.detention_lines:
                vals.update({'container':receipt_line.container_id.name})
                tran_obj.create(cr, uid, vals)

        return True

shipping_detention_collection()


class shipping_detention_line(osv.osv):

    _name='shipping.detention.line'

    _columns={
        'container_id':fields.many2one('shipping.container', 'Container No', select=1),
        'last_charged_date':fields.date('Last Charge Date', select=1),
        'last_charged_detention_id':fields.many2one('shipping.detention.collection', 'Last Charged Detention', select=1),
        'detention_id':fields.many2one('shipping.detention.collection', 'Detention', select=1),
        }

    def onchange_container(self, cr, uid, ids, date_charge=None, in_voyage_no=None , bl_no=None, context= None):
        res={}

        return {'value': res}

shipping_detention_line()

class container_detention_transaction(osv.osv):

    _name='container.detention.transaction'
    _description=' Containers Detention Transaction '

    _order= 'date_charged desc'

    _columns={
        'container':fields.char('Container', size=128, ondelete='cascade', readonly=True),
        'date_charged':fields.date('Last Charge Date', select=1),
        'charged_detention_id':fields.many2one('shipping.detention.collection', 'Last Charged Detention', select=1),
        'location_id':fields.many2one('stock.location', 'Location', select=1),
        'location_dest_id':fields.many2one('stock.location', 'Destination Location', select=1),
        'state': fields.selection([('draft', 'New'),
                                   ('cancel', 'Cancelled'),
                                   ('confirmed', 'Confirmed'),
                                   ('done', 'Receipt')],
                                  'Status', readonly=True),
        'consignee': fields.many2one('res.partner', 'Consignee', required=True,states={'draft': [('readonly', False)]}, ondelete='cascade', help="Consignee." ,readonly=True) ,
        'bl_no':fields.char('BL NO', size=128, ondelete='cascade', readonly=True,states={'draft': [('readonly', False)]}, help="BL no of relative vassel and in_voyage_no."),
        }

    def get_last_charge_date(self, cr, uid, container, bl_no, context=None):
        tran_ids=self.search(cr, uid, [('container','=',container),('bl_no','=',bl_no)], context= context)
        if tran_ids:
            return self.read(cr, uid, tran_ids[0], ['date_charged','charged_detention_id'], context)

        return None

    _defaults = {
        'state'  : 'draft',
    }
    
container_detention_transaction()

class detention_charge_receipt(osv.osv):

    _name='detention.charge.receipt'

    def _amount_all(self, cr, uid, ids, name, args, context=None):
        res = {}
        for receipt in self.browse(cr, uid, ids, context=context):
            res[receipt.id] = 0.0
            net_total=0.0
            for line in receipt.receipt_lines:
                net_total += line.charge_amount>0 and line.charge_amount or line.charge * line.quantity * line.number_of_day
            res[receipt.id]=net_total
        return res

    def _get_receipt(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('detention.change.receipt.line').browse(cr, uid, ids, context=context):
            result[line.order_id.id] = True

        return result.keys()
        
    _columns={
        'name': fields.char('Receipt No',readonly=True , size=128 , translate=True, select=True),
        'consignee': fields.many2one('res.partner', 'Consignee', required=True,states={'draft': [('readonly', False)]}, ondelete='cascade', help="Consignee." ,readonly=True) ,
        'bl_no':fields.char('BL NO', size=128, ondelete='cascade', readonly=True,states={'draft': [('readonly', False)]}, help="BL no of relative vassel and in_voyage_no."),
        'date':      fields.date('DATE', required=True,readonly=True , ondelete='cascade', help="DATE OF INVOICE.",states={'draft': [('readonly', False)]}),
        'state': fields.selection([('draft', 'New'),
                                   ('cancel', 'Cancelled'),
                                   ('confirmed', 'Confirmed'),
                                   ('received', 'Receipt')],
                                  'Status', readonly=True),
        'receipt_lines': fields.one2many('detention.charge.receipt.line', 'receipt_id', 'Receipt Lines', readonly=True ,states={'draft': [('readonly', False)]}),
        'qty_total':fields.char('Total Qty', size=128, readonly=True,states={'draft': [('readonly', False)]}),
        'net_total':fields.function(_amount_all, string='Net Total' , digits_compute=dp.get_precision('Account'), 
             store={
                'detention.charge.receipt': (lambda self, cr, uid, ids, c={}: ids, ['receipt_lines'], 10)
                }),
        'source': fields.char('Source Document', size=128 , select=True),
        'description': fields.text('Description', readonly=True, states={'draft': [('readonly', False)]}),
        'user_id': fields.many2one('res.users', 'User', help="Person who creates the freight invoice"),
        'company_id':fields.many2one('res.company', 'Company', required=True, readonly=True),
        }

    _defaults = {
        'user_id': lambda self, cr, uid, context: uid,
        'state'  : 'draft',
        'name': lambda obj, cr, uid, context: '/',
        'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
    }    

    def create(self, cr, uid, vals, context=None):
        vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'detention.charge.receipt') or '/'

        return super(detention_charge_receipt, self).create(cr, uid, vals, context=context)
        
    def button_confirm(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, { 'state':'confirmed' } , context= context)

    def button_cancel(self, cr, uid, ids, context=None):
        return True

    def button_print_invoice(self, cr, uid, ids, context=None):
        return self.print_report(cr, uid, ids, context= context)
        
    def print_report(self, cr, uid, ids, context=None):
        #import jasper_reports
        export_obj = self.browse(cr, uid, ids[0], context= context)
        
        company=self.pool.get('res.users').browse(cr,uid,uid).company_id
        comm_obj=self.browse(cr,uid,ids[0],context=context)

        report_param={
            'invoice_id': ids[0],
        }	

        return {
            'type': 'ir.actions.report.xml',
            'report_name':'detention.receipt.invoice',
            'datas' :{'parameters': report_param },
        }
        
    def create_invoice(self, cr, uid, ids, context=None):
        journal_code='DZDT'
        account_code='detention_payable_account'
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
            
        for receipt in self.browse(cr, uid, ids, context=context):
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            search_periods = period_pool.find(cr, uid, receipt.date, context=context)
            period_id = search_periods[0]
            journal_id= journal_obj.id
    
            name = _('Detention of %s') % (receipt.name)
            move = {
                'narration': name,
                'date': receipt.date,
                'ref':receipt.name,                
                'journal_id':journal_obj.id,
                'period_id': period_id,
            }
            company=self.pool.get('res.users').browse(cr,uid,uid).company_id
            debit_account_id= journal_obj.default_debit_account_id and journal_obj.default_debit_account_id.id or False
            credit_account_id = journal_obj.default_credit_account_id and journal_obj.default_credit_account_id.id or False # account_obj.id
                
            for line in receipt.receipt_lines:
                amt = line.amount_total
                
                if debit_account_id:

                    debit_line = (0, 0, {
                    'name':line.name,
                    'date': receipt.date,
                    'partner_id':False,
                    'account_id': debit_account_id,
                    'journal_id': journal_id,
                    'period_id': period_id,
                    'debit': amt > 0.0 and amt or 0.0,
                    'credit': amt < 0.0 and -amt or 0.0,
                })
                    line_ids.append(debit_line)

            amt = receipt.net_total
            if credit_account_id:

                credit_line = (0, 0, {
                'name': line.name,
                'date': receipt.date,
                'account_id': credit_account_id,
                'journal_id': journal_id,
                'period_id': period_id,
                'debit': amt < 0.0 and -amt or 0.0,
                'credit': amt > 0.0 and amt or 0.0,
            })
            line_ids.append(credit_line)
                
            move.update({'line_id': line_ids})
            move_id = move_pool.create(cr, uid, move, context=context)
        self.write(cr, uid, ids, {'state':'received'}, context =context)
        return True

detention_charge_receipt()

class detention_charge_receipt_line(osv.osv):

    _name='detention.charge.receipt.line'

    def _get_peroid(self, cr, uid, ids, name, args, context=None):
        res = {}
        for charge in self.browse(cr, uid, ids, context=context):
            res[charge.id] = {
                'period_from': charge.name[-11:][:5],
                'period_to': charge.name[-11:][-5:],
                }
        return res
            
    
    def _amount_line(self, cr, uid, ids, name, args, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = line.charge_amount>0 and line.charge_amount or line.charge * line.quantity * line.number_of_day
        return res

    _columns={

        'name':fields.char('Particular', size=128, required=True),
        'quantity':fields.integer("Contain Qty",required=True),
        'type': fields.char('Type', size=24, required=True),
        'charge_amount': fields.float('All Day Charge', required=True),
        'charge': fields.float('1 Day Charge', required=True),
        'number_of_day': fields.integer('Day', required=True),
        'container':fields.char('Containers', help="Container"),
        'amount_total':fields.function(_amount_line, string='Amount' , digits_compute=dp.get_precision('Account'),
        store={
                'detention.charge.receipt.line': (lambda self, cr, uid, ids, c={}: ids, ['charge_amount','quantity','charge','number_of_day'], 10),
           }), 
        'receipt_id':fields.many2one('detention.charge.receipt', 'Receipt', select=1),
        'period_id':fields.many2one('shipping.detention.charge', 'Period', select=1),
        'period_from': fields.function(_get_peroid, string='Period From',type='char', size=10, store=True, multi='all'),
        'period_to': fields.function(_get_peroid, string='Period To' ,type='char', size=10, store=True, multi='all'),
        'eta_ygn': fields.date('ETA/YGN' ,readonly=True),
        'date_free_to': fields.date('DATE FREE TO' ,readonly=True),
        'period_type': fields.selection([('first', 'First Period'),('second', 'Second Period'),('third', 'Third Period')], 'Type', size=16, required=True, help="first: First Period, second: Second Period, third: Third Period"),
        'date_from': fields.date('Date From', required=True, ondelete='cascade', ),
        'date_to': fields.date('Date To', required=True, ondelete='cascade', ),
        'remark': fields.text('Remark'),
        }

    _defaults= {
            'type':'20',
            'charge_amount': 0.0,
        }

detention_charge_receipt_line()

