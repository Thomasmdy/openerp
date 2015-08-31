###################################################################################### 
# Shipping General Payment Received       
######################################################################################

import time
from datetime import datetime
from lxml import etree
import decimal_precision as dp
import netsvc
import pooler
from osv import fields, osv, orm
from tools.translate import _

import logging
_logger = logging.getLogger(__name__)

def _get_period(self, cr, uid, context=None):
    ctx = dict(context or {}, account_period_prefer_normal=True)
    period_ids = self.pool.get('account.period').find(cr, uid, context=ctx)
    return period_ids[0]
        
def dt2d(dt,from_fmt='%Y-%m-%d %H:%M:%S',to_fmt='%Y-%m-%d'):
    """Convert  datetime to date"""
    return time.strftime(to_fmt,time.strptime(dt,from_fmt))  
      
#Payment Lines
class payment_move_line(osv.osv):
    _name = "payment.move.line"
    _description = "Cash Payment Line"
    _columns = {
            'name': fields.char('Name', size=16),
            'amount': fields.float('Amount', help="The amount expressed in an optional other currency."),
            'currency_id': fields.many2one('res.currency', 'Currency'),  
            'general_payment_id':fields.many2one('shipping.general.payment','General Payment', ondelete='cascade'),
            }
    
payment_move_line()

class shipping_general_payment(osv.osv):
        
    def _amount_paid(self, cr, uid, ids, name, args, context=None):
        vals = {}
        paid_cash= 0.0
        for advanced in self.browse(cr, uid, ids):
            for cash in advanced.cash_line_ids:
                paid_cash += cash.amount
            paid_total = paid_cash
            vals[advanced.id] = {
                    "paid_cash":paid_cash,
                    "paid_total": paid_total,
            }
        return vals

    def _remaining(self, cr, uid, ids, name,args,context=None):
        vals = {}
        for pay_receive in self.browse(cr, uid, ids, context=context): 
            tot_adv = pay_receive.cash_total
        return vals

    _name = "shipping.general.payment"
    _description = "Shipping General Payment Received"
    
    _columns = {
            'name': fields.char('Name', size=16),
            'origin': fields.char('Original', size=50),
            'invoice': fields.char('Invoice', size=50),
            'company_id': fields.many2one('res.company', 'Company', required=True, readonly=True, states={'draft':[('readonly',False)]}),
            'journal_id':fields.many2one('account.journal', 'Journal', required=True, readonly=True, states={'draft':[('readonly',False)]}),
            'cash_line_ids':fields.one2many('payment.move.line','general_payment_id','Payment Lines',readonly=True, states={'draft':[('readonly',False)]}),
            'journal_entry_id':fields.many2one('account.move','Journal Entry',readonly=True),
            'doc_date':fields.date('Doc Date', required=True, select=True, help="Effective date for accounting entries", readonly=True, states={'draft':[('readonly',False)]}),
            'auto_posted': fields.boolean('Auto Posted', readonly=True, states={'draft':[('readonly',False)]}, help="Check this box if you want to post the Journal Entry automatically."),
            'paid_cash': fields.function(_amount_paid,method=True,string='Paid Cash', type='float',multi="amount_paid"),
            'paid_total': fields.function(_amount_paid,method=True,string='Paid Total', type='float',multi="amount_paid"),
            'amount_total': fields.float('Amount Total'),
            'amount_currency': fields.float('Amount Currency', help="The amount expressed in an optional other currency."),
            'currency_id': fields.many2one('res.currency', 'Currency'),
            'partner_id': fields.many2one('res.partner', 'Partner'),
            'debit_account_id': fields.many2one('account.account', 'Debit'),
            'credit_account_id': fields.many2one('account.account', 'Credit'),
            'state':fields.selection(
                    [('draft','Draft'),
                    ('paid','Paid'),
                    ('cancel','Cancel')
                    ], 'State', readonly=True, size=32),
                    
            'ref': fields.char('Reference', size=16),
            'resource': fields.char('Resource', size=50),
            'notes':fields.char('Notes',size=300,),
            'period_id': fields.many2one('account.period', 'Period', required=True, states={'posted':[('readonly',True)]}),            
            }

    _defaults = {
        'name':'/',
        'state': 'draft',
        'period_id': _get_period,
        'company_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
        }

    def create(self, cr, uid, vals, context=None):
        if vals.get('name','/')=='/':
            vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'shipping.general.payment') or '/'
        return super(shipping_general_payment, self).create(cr, uid, vals, context=context)
        
    def button_validate_payment(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
            
        self.create_payment_move_lines(cr, uid, ids, context=context)
        
        if self.test_paid(cr, uid, ids, context = context):
            self.write(cr, uid, ids, {'state':'paid'}, context = context)
            
        return True

    def create_payment_move_lines(self, cr, uid, ids, context=None):
        move_pool = self.pool.get('account.move')
        period_pool = self.pool.get('account.period')
        account_journal_pool = self.pool.get('account.journal.mapping')
        journal_pool = self.pool.get('account.journal')
        account_pool = self.pool.get('account.account')
        cur_obj = self.pool.get('res.currency')
        
        timenow = time.strftime('%Y-%m-%d')
        
        for payment in self.browse(cr, uid, ids, context=context):
            journal_obj= payment.journal_id
                
            line_ids = []

            period_id = payment.period_id.id
            journal_id= payment.journal_id.id
    
            name = payment.name            
            move = {
                'narration': payment.notes,
                'date': payment.doc_date,
                'ref': payment.ref,                
                'journal_id': journal_obj.id,
                'period_id': period_id,
            }
            company=self.pool.get('res.users').browse(cr,uid,uid).company_id
            
            debit_account_id= payment.debit_account_id.id
            credit_account_id = payment.credit_account_id.id
            
            amount_total= 0
            amount_currency= 0
            amount_currency_total = 0
            
            for line in payment.cash_line_ids:

                if line.currency_id.id != company.currency_id.id:
                    amount_currency = line.amount
                    amt = cur_obj.compute(cr, uid, journal_obj.default_debit_account_id.currency_id.id, journal_obj.default_debit_account_id.company_id.currency_id.id, amount_currency, context=context)
                else:
                    amt = line.amount
                    
                amount_currency_total += amount_currency
                amount_total += amt
                    
                if debit_account_id:

                    debit_line = (0, 0, {
                    'name': payment.name,
                    'date': payment.doc_date or timenow,
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
                'name': payment.name,
                'date': payment.doc_date or timenow,
                'account_id': credit_account_id,
                'journal_id': journal_id,
                'period_id': period_id,
                'amount_currency': amount_currency_total,
                'debit': amount_total < 0.0 and -amount_total or 0.0,
                'credit': amount_total > 0.0 and amount_total or 0.0,
            })
                line_ids.append(credit_line)
                
            move.update({'line_id': line_ids})
            move_id = move_pool.create(cr, uid, move, context=context)
        
        return True
        
    def button_cancel(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'cancel'}, context= context)
        return True

    def test_paid(self, cr, uid, ids, context=None):
        """Payment is paid when the sum of amount total equal to paid amount
        @return: True
        """
        for payment in self.browse(cr, uid, ids, context=context):
            if payment.cash_line_ids and not payment.amount_total:
                return True
            if payment.cash_line_ids and (abs(payment.amount_total-payment.paid_total) > 0.00001):
                return False
        return True
        
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
    
    def print_report(self, cr, uid, ids, context=None):
        company=self.pool.get('res.users').browse(cr,uid,uid).company_id
        comm_obj=self.browse(cr,uid,ids[0],context=context)
        
        report_param={
            'company_name':company and company.name or '',
            'address':company.partner_id.complete_address,
            'tel_fax':company and "Tel/Fax: %s , %s " % (company.phone and company.phone or '' , company.fax and company.fax or '' ),
            'invoice_id':ids[0],
        }

        return {
            'type': 'ir.actions.report.xml',
            'report_name':'general.receipt.invoice',
            'datas': { 'parameters':report_param },
        }		
        

shipping_general_payment() 

