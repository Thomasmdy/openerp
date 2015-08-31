Import 
1) HC
2) Commission                               -Done
3) Freight Amount Line (each freight )      -Done
4) Freight payment line                     -Done
5) RO                                       -Done
6) RO Payment Line                          -Done
7) Ammendment                               -Done
8) Detention                                -Done

When confirmed

HC 
COmmission(P/C) ---Need to add all freight line in import as in Export freight line
Freight Collect

RO print receives 
Vassel Name
Invoyage
ETA 

Booking
#[CSL]
DZBK-Seal Charges
credit_account_id =journal_obj.default_credit_account_id and journal_obj.default_credit_account_id.id or False
debit_account_id= bk_line.shipper.property_account_receivable.id

Seal Payments
credit_account_id =journal_obj.default_credit_account_id and journal_obj.default_credit_account_id.id or False
debit_account_id= bk_line.shipper.property_account_receivable.id

DZBK-GOH
debit_account_id = goh_product.property_account_export.id
credit_account_id= goh_product.property_account_expense.id

#Need to add GOH payments[ This payment should be paid from GP]
debit_account_id= goh_product.property_account_expense.id

Cancelled:
    delete journal entries automatically
    Renew booking 

Export 
When Confirmed
#Need to add
#Journal DZFRE[DONE]

OFT . export(cr) -> credit
    . shipper.receivable_account > debit

#When paid [DONE]
OFT . export(DR) -> debit 
    . shipper.receivable_account -> credit 

#Remark All prepaid item in export frights lines 
#NOTICE

#This is Done by BOOKING
For CSL, 
service.product.export(DR) -> debit 
service.product.export(CR) -> credit

For GOH,
No need account entries 

BL_FEES
journal_code='DZBLF'
debit_account_id = bl_line.shipper.property_account_receivable.id
credit_account_id = journal_obj.default_credit_account_id and journal_obj.default_credit_account_id.id or False
credit_account_id1 = bl_line.feeder_line.property_account_payable.id

HC
journal_code='DZHCE'
debit_account_id=journal_obj.default_debit_account_id and journal_obj.default_debit_account_id.id or False
credit_account_id = journal_obj.default_credit_account_id and journal_obj.default_credit_account_id.id or False

Outward commission for Export OFT
#Only name == OFT

journal_code='DZCME'
debit_account_id=journal_obj.default_debit_account_id and journal_obj.default_debit_account_id.id or False
credit_account_id = journal_obj.default_credit_account_id and journal_obj.default_credit_account_id.id or False

Freight Payments
journal_code='DZFRE'

debit_account_id=journal_obj.default_debit_account_id and journal_obj.default_debit_account_id.id or False
credit_account_id = journal_obj.default_credit_account_id and journal_obj.default_credit_account_id.id or False

#Tracking for Empty Conainer
BL(export) Confirmed
No BL_FEES

1) HC
2) Tracking


