from osv import osv, fields
import time
import pooler
from datetime import datetime, timedelta

from tools.translate import _
class detention_collection_report(osv.osv_memory):

    _name = 'detention.collection.report'	    
    _columns = {
            'date_from':fields.date('Date From', required=True),
            'date_to':fields.date('Date To', required=True),
            'exchange_rate': fields.integer('Exchange Rate', required=True),
            'output_type': fields.selection([(1, 'PDF')], "Output Type", help = 'Select output type', required=True, size=-1),
    }
    
    _defaults ={
        'date_from': lambda *a: time.strftime('%Y-%m-%d'),
        'date_to': lambda *a: time.strftime('%Y-%m-%d'),
        'output_type':1,
        'exchange_rate': 1000,
    }
        
    def print_report(self, cr, uid, ids, context=None):
        company=self.pool.get('res.users').browse(cr,uid,uid).company_id
        comm_obj=self.browse(cr,uid,ids[0],context=context)

        dtt = datetime.strptime(comm_obj.date_from, '%Y-%m-%d')
        dtt.strftime('%m-%Y')
        report_param={
           'company_name':company and company.name or '',
            'address':company.partner_id.complete_address,
            'tel_fax':company and "Tel/Fax: %s , %s " % (company.phone and company.phone or '' , company.fax and company.fax or '' ),
            'date_from': comm_obj.date_from,
            'date_to': comm_obj.date_to,
            'date': dtt.strftime('%m-%d-%Y'),
            'cost_month': dtt.strftime('%m-%Y'),
            'exchange_rate': comm_obj.exchange_rate,
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name':'detention.receipt',
            'datas' :{'parameters': report_param },
        }		

detention_collection_report()




