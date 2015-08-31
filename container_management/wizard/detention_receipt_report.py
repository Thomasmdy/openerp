import time
from osv import osv, fields
import time
import pooler
from tools.translate import _
class detention_receipt_report(osv.osv_memory):

	_name = 'detention.receipt.report'		    
	_columns = {
			'date':fields.date('Date', required=True),
			'output_type': fields.selection([(1, 'PDF'), (2, 'XLS')], "Output Type", help = 'Select output type', required=True, size=-1),
    }
    
	def print_report(self, cr, uid, ids, context=None):
		company=self.pool.get('res.users').browse(cr,uid,uid).company_id
		comm_obj=self.browse(cr,uid,ids[0],context=context)
		
		report_param={
			'company_name':company and company.name or '',
            'address':company.partner_id.complete_address,
            'tel_fax':company and "Tel/Fax: %s , %s " % (company.phone and company.phone or '' , company.fax and company.fax or '' ),
			'date':comm_obj.date,
			'cost_month':comm_obj.date,
		}	
		
		return {
			'type': 'ir.actions.report.xml',
			'report_name':'detention.receipt',
			'parameters':report_param
		}		
		
detention_receipt_report()


	

