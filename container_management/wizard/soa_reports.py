import time
from osv import osv, fields
import pooler
from tools.translate import _
from datetime import datetime, timedelta

class soa_reports(osv.osv_memory):

    SOA_LIST=[('csl','CSL'), ('jcd', 'JCD'), ('ens','ENS'), ('dynamic','Freight SOA')]
    
    _name = 'soa.reports'		    
    _columns = {
            'date':fields.date('Date', required=True),
            'freight_type': fields.selection(SOA_LIST, "Freight Type",  help = 'Select Freight type', required=True, size=10	),
            'bl_type': fields.selection([(1, 'KLIS'), (2, 'KKK')], "BL Type", help = 'Select BL type', required=True, size=-1),
            'output_type': fields.selection([(1, 'PDF'), (2, 'XLS')], "Output Type", help = 'Select output type', required=True, size=-1),
    }

    _defaults= {
        'bl_type': 1,
        'freight_type': 'dynamic',
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
            'date': comm_obj.date,
            'cost_month': dtt.strftime('%m-%Y'),
            'int_cost_month': dtt.month,
            'int_cost_year': dtt.year,
        }
        
        report_name='freight.soa.%s' % comm_obj.freight_type


        return {
            'type': 'ir.actions.report.xml',
            'report_name':report_name,
            'datas': {'parameters':report_param }
        }		

soa_reports()




