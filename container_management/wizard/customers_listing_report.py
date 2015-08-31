import time
from osv import osv,fields 
from tools.translate import _

class customers_listing_report(osv.osv_memory):
	_name = 'customers.listing.report'
	_description = 'Customers Listing Report'

	_columns = {
        'date':fields.date('Date', required=True),        
        'company_id':fields.many2one('res.company', 'Company', required=True),        
		'output_type': fields.selection([(1, 'PDF'), (2, 'XLS')], "Output Type", help = 'Select output type', required=True, size=-1),		
		'child':fields.boolean('Inclusive of child company'),
    }
	_defaults = {
		'output_type':1,
		'company_id':lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,        
        'date': lambda *a: time.strftime('%Y-%m-%d'),
        
    }
    
	def onChange_company(self,cr,uid,ids,context=None):
		res={}
		res['value']={'child':False}		
		return res    
	
	def print_report(self, cr, uid, ids, context=None): 
	
		if context is None:
		    context = {}
		datas = {'ids': context.get('active_ids', [])}
		res = self.read(cr, uid, ids, ['date','company_id','output_type','child'], context=context)					
		res = res and res[0] or {}               
		datas['form'] = res
		if res.get('id',False):
			datas['ids']=[res['id']]
						 
		return {
		    'type': 'ir.actions.report.xml',
		    'report_name': 'customers.listing.report',
		    'datas': datas,
	}			
	
		
	def onChange_multiCompanyCheckbox(self,cr,uid,ids,company_id,child,context=None):
		res={}
		if child==True:
			if company_id==False:
				raise osv.except_osv(_('Message!'),_('You must choose company!'))				
			comObj = self.pool.get("res.company").browse(cr,uid,company_id,context=None)
			parent_id = comObj.parent_id.id
			child_ids = comObj.child_ids
			if(parent_id != False):
				res={'value':{'child':False}}
				raise osv.except_osv(_('Message!'),_('This company has no child company,choose another company'))
		return res
		
	def myRecursive(self,cr,uid,ids,cate_ids,categ,context):		
		cate_ids=self.pool.get("product.category").search(cr,uid,[('parent_id','in',cate_ids)])		
		if cate_ids:	
			categ+=cate_ids												
			categ=self.myRecursive(cr,uid,ids,cate_ids,categ,context)					
		return categ	

customers_listing_report()
