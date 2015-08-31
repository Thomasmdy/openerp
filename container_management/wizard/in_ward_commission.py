import time
from osv import osv, fields
import pooler
from tools.translate import _
from datetime import datetime

class inward_commission(osv.osv_memory):

    _name = 'inward.commission'		    
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
            'date':comm_obj.date,
            'tel_fax':company and "Tel/Fax: %s , %s " % (company.phone and company.phone or '' , company.fax and company.fax or '' ),
            'cost_month':dtt.strftime('%m-%Y'),
            'int_cost_month':dtt.month,
            'int_cost_year':dtt.year,
        }	

        return {
            'type': 'ir.actions.report.xml',
            'report_name':'inward.commission',
            'datas': { 'parameters':report_param }
        }		

inward_commission()




