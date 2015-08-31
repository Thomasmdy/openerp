[INVENTORY CONTROL]

if container arrive at port of myanmar
(In bl data )

[DONE: Import BL]
Container contains cargo -> DF (Decharge Full )
Container is empty -> DF (Decharge Empty )

--Need to link container with cargo
[!Warning]
    Container must be key in before any cargo line key in.
    
[DONE: RO]
After receiving released order, (can also ask user LD or TD?)
    State change to LD ( Local Devending ) which also means consignee already received Released Order
    State TD Terminal Devending -> Container which own by more than one consignee or having more than one BL No,

[DONE: TE-List]
Incoming from ICD,
Container 
        condition = AV, container status -> TE 
        condition != AV, container status -> TU

For TU, If container condition contains with post-fix 'OK', container state need to change to TE

[BOOKING]
If container has TE status, those containers are ready for Booking.
System need to generate booking reference
For booking container booking need to follow FIFO rule on date.
After Booking confirmed, container state change to 
[LV- Local Vending -> LVE (Empty) , LVF to shipper to fill cargos ( Full )]

[OUT-GOING  FROM ICD]
LVE state changes to TE, LVF changes to TF

Now ready for export:
[Export BL]
If we know which contanier is on whick vassel,
State changes to VE ( Vassel Empty ) if container is empty (ie come for LVE -> TE ) , 
State changes to VF ( Vassel Full ) if container contains cargos (ie come for LVF -> TF ) , 

Now BL for Export need to be enter by user for each container and vassel, voyage
BL no starts with KKLURGN

In daily container movement,[INCOMING] for incoming condition is AV we need to collect charge
In daily container movement, [OUTGOING] for incoming condition is AV we DON'T need to collect charge

[SUMMARY CONTAINER STATUS]
1)    DF - Decharge Full
2)    DF - Decharge Empty
3)    LD - Local Devending
4)    TD - Terminal Devending 
5)    TE - Terminal Empty
6)    TF - Terminal Full
7)    LVE - Local Vending Empty
8)    LVF - Local Vending Full
9)    VE - Vassel Empty
10)   VF - Vassel Full

Total State (10)

#10-28-2014
Container Master List

#REMARK
All date format MM/dd/YYYY 

#Change on 18-Mar-2015
To add related BL for conbine freight

#Report 
KKLU(Inward) -> 

#Add carry charge to Port for 20 and 40 each


#Change on 19-Mar-2015
Want to preview before approved in booking 

Export BL_FEES
Port of Discharge
Place of Delivery
Final Destination

Payable at 

Prepaid at

#Change on 26-Mar-2015[Booking]-DONE

Add in vassel name in booking container lines

To limit 5 container line in booking print form
To print container line as attached 



