#======================================================
# This program generate forecast household control totals for Urbansim 
# Numpy and matplotlib are required python components to run this program
# Tested with Python 2.6.5, Numpy 1.6, matplotlib 1.1
# Data inputs (tab delimited tables):
#    1) REMI population forecast by 8 large area.
#       Forecast files were exported from REMI excel tables (using excel macro) and saved to text format.
#       File names are combinations of large area, race and gender, for example, "pop detroit black females.xls.txt". Total 64 files.
#       Field names: "age_group    2010    2011    2012.......	2039	2040"
#    2) Census household population for base year (2010), summarized by large_area,gender,race,age_group
#       Field names: "large_area	gender	race	age_group	hh_pop
#    3) Synthesized household table
#       Field format: "large_area_id	HOUSEHOLD_ID	building_id	persons	workers	age_of_head	income	children	race	cars	zone_id"
#       HOUSEHOLD_ID, building_id,zone_id are not needed. Please make sure lst_8at_cols has correct column id. 1st column is 0, 2nd is 1 and so on.
#   * All input files should be in the "input" subfolder of this program
#
# Output: household_control_totals.csv in current folder
#
# * Before running this program, please make sure all input files are in correct format and located in 'input' subfolder
#===========================================================


import os
from numpy import *
from matplotlib import mlab
from numpy.lib import recfunctions as rfn
from time import time
#sr
#to verify imtermediate result, use "outcsv(array, name)" to export array as csv file

inputdir='./input/'  #where input files are
census_hhpop_file=inputdir+'census_reg_hh_pop.txt'
syn_hh_file=inputdir+'syn_households.txt'

start=time()
years=[str(x) for x in range(2010,2041)]
baseyear='2010'

dic_la={"detroit":5,"wayne balance":3, "macomb":99,"livingston":93, "monroe":115,"oakland":125,"st clair":147, "washtenaw":161}
dic_race={"white":1,"black":2, "hispanic":3,"other":4}
dic_gend={"males":1, "females":2}

bin_agegrp=array([0,5,10,15,18,20,21,22,25,30,35,40,45,50,55,60,61,65,66,70,75,80,85,101])
bin_agehead=array([0,5,18,35,65,101])
bin_agp2aoh=array([1,2,5,11,18,24]) #boundaries of bin_agegrp

lst_8at=['large_area','race','age_of_head','persons','children','cars','workers','income']
lst_8at_cols=[0,8,5,3,7,9,4,6] #column positions corresponding to lst_8at in file "syn_hh_file"
lst_8at_values=[[3,5,93,99,115,125,147,161],[1,2,3,4],[1,2,3,4,5],[1,2,3,4,5,6,7],[0,1,2,3],[0,1,2,3],[0,1,2,3],[1,2,3,4]] #value ranges corresponding to lst_at8
lst_4at=['large_area','gender','race','age_group']
lst_3at=['large_area','race','age_of_head']


def extend_ratios(arydata, fld_num, fld_denom, fldlst):
    ratio=arydata[fld_num]/arydata[fld_denom]
    ratio[isinf(ratio)]=0
    ratio[isnan(ratio)]=0
    for fld in fldlst:
        arydata[fld]=multiply(ratio,arydata[fld])
    return arydata

def quartile_adj(ary_data):
    count=0
    vdiff,hdiff,tdiff=100,100,1000 
    ary_qrtl=ary_data.reshape(-1,4)
    #quart=array([round(ary_data.sum()/4,0)]*4)
    quart=array([ary_data.sum()/4.0]*4)
    hsum0=(ary_qrtl.sum(axis=1))[:,newaxis].astype(float)
    while not(abs(vdiff)<50 and abs(hdiff)<50) and count<=100:
        vsum=ary_qrtl.sum(axis=0)
        vratio=(quart/vsum).astype(float)
        ary_qrtl=around(ary_qrtl*vratio)
        vdiff=abs((ary_qrtl.sum(axis=0)-quart).sum())
        hsum=(ary_qrtl.sum(axis=1))[:,newaxis]
        hratio=(hsum0/hsum).astype(float)
        hratio[isinf(hratio)]=0
        hratio[isnan(hratio)]=0
        ary_qrtl=around(ary_qrtl*hratio)
        hdiff=abs((ary_qrtl.sum(axis=1)[:,newaxis]-hsum0).sum())
       # print vdiff, hdiff
        if (vdiff+hdiff)<tdiff:
            ary_min=ary_qrtl
            tdiff=vdiff+hdiff
        count=count+1
   # print vdiff, hdiff
    return ary_min.reshape(1,-1)    

def outcsv(array, name):
    mlab.rec2csv(array, name+'.csv', delimiter=',', withheader=True)

def out3csv(ary_hhs,sums,outname):
    hhs=mlab.rec_groupby(ary_hhs, ('large_area','race','age_of_head'),  tuple(sums))
    outcsv(hhs, outname)
    
### Step 1. Compute REMI total pop: combine 64 file; recode age to age_groups (23 Census groups); aggregate population by 4 attributes)
# 1.1 read and combine REMI population files ( 64 converted txt files)
print "Step 1. Combine REMI total pop and aggregate by large area, gender, race and age_groups"
newhead='large_area'+'\t'+'gender'+'\t'+'race'+'\t'
firstfile=1
fileout=open('remi_temp.txt','w')
for larea in dic_la.keys():
    for gender in dic_gend.keys():
        for race in dic_race.keys():
            filname=inputdir+"pop "+larea+" "+race+" "+gender+".xls.txt"
            try:
                filein=open(filname,'r')
            except:
                print filname+" is missing!"
                exit()
            line=filein.readline()
            if firstfile==1:
                fileout.write(newhead+line)
                firstfile=0
            line=filein.readline()
            while line:
                fileout.write(str(dic_la[larea])+'\t'+str(dic_gend[gender])+'\t'+str(dic_race[race])+'\t'+line)
                line=filein.readline()
            filein.close()    
fileout.close()

remi_totl_pop=genfromtxt('remi_temp.txt',names=True, delimiter="\t", dtype=[('int')]*4+[('float')]*len(years))
for year in years: #original data unit is 1000
    remi_totl_pop[year]=multiply(remi_totl_pop[year],1000)
os.remove('remi_temp.txt')

# 1.2 recode age to age group using agegrp dictionary
remi_totl_pop['age_group'] = digitize(remi_totl_pop['age_group'], bin_agegrp)

# 1.3 Aggregate total population by large area, gender, race and age groups
sum_years=[]
for year in years:
    sum_years.append((year,sum,year))
remi_totl_pop_4sum=mlab.rec_groupby(remi_totl_pop, tuple(lst_4at), tuple(sum_years))

### Step 2. Process Census HH pop: aggregate Census HH pop by 4 attributes:large area, gender, race and age groups
#'census_reg_hh_pop.txt' field names should be 'large_area','gender','race','age_group','hh_pop'
print "Step 2. Read Census HH pop by 4 attributes"
census_hh_pop_4sum=genfromtxt(census_hhpop_file,names=True, dtype=[(int), (int), (int),(int),(float)])

### Step 3. Compute REMI HH pop
print "Step 3. Compute REMI HH pop from REMI total pop and Census HH pop"
#Join REMI total pop and Census HH pop by 4 attributes and convert REMI total pop to HH pop based on ratio=Census pop/base year REMI
if remi_totl_pop_4sum.shape[0]<>census_hh_pop_4sum.shape[0]:
    print "warning, REMI total pop and census HH pop have different attribute combinations ", ary_lgra_pop.shape[0],census_hh_pop_4sum.shape[0]
join_ttlpop_hhpop=mlab.rec_join(tuple(lst_4at), remi_totl_pop_4sum, census_hh_pop_4sum, jointype='outer')
remi_hh_pop=extend_ratios(join_ttlpop_hhpop,'hh_pop',baseyear,years)


### Step 4. Aggregate REMI HH pop to 3 attributes 'large_area','race','age_of_head'
print "Step 4. Aggregate REMI HH pop by large_area,race,age_of_head"
 #4.1 rename and recode REMI HH pop age to age_of_head
remi_hh_pop=rfn.rename_fields(remi_hh_pop,{'age_group':'age_of_head'})
remi_hh_pop['age_of_head'] = digitize(remi_hh_pop['age_of_head'], bin_agp2aoh)

 #4.2 sum REMI HH pop by 3 attributes: large area, race and age groups
remi_hh_pop_3sum=mlab.rec_groupby(remi_hh_pop, tuple(lst_3at), (tuple(sum_years)))


### Step 5. Compute synthesized HHs by 3 attributes 'large_area','race','age_of_head'
print "Step 5. Read synthesized HHs and aggregate by large_area,race,age_of_head"
 #5.1 read synthesized HHs and recode 'age_of_head','workers','cars','children','income'
syn_hhs=genfromtxt(syn_hh_file ,skip_header=1,names=lst_8at, delimiter="\t", usecols=lst_8at_cols,dtype=[('int32')]*8)
syn_hhs['age_of_head'] = digitize(syn_hhs['age_of_head'], bin_agehead)

for at in ['workers','cars','children']:
    syn_hhs[at][syn_hhs[at] >3] = 3

quartile=mlab.prctile(syn_hhs['income'],p=(0.0, 25.0, 50.0, 75.0, 100.0))
syn_hhs['income'] = digitize(syn_hhs['income'], quartile)
syn_hhs['income'][syn_hhs['income'] > 4] = 4
print '    * income quartile: ', quartile

 #5.2 aggregate synthesized HHs3 by 3 attributes 'large_area','race','age_of_head'
syn_hhs_3sum=mlab.rec_groupby(syn_hhs, tuple(lst_3at), (('large_area',len,'hhs3'),))

### Step 6. Compute REMI HHs
 #6.1 join synthesized HH and census HH pop and calculate forecast HHs
print "Step 6. derive REMI HHs for forecast years from REMI HH pop and syn HHs"
if syn_hhs_3sum.shape[0]<>remi_hh_pop_3sum.shape[0]:
    lsyn=unique(syn_hhs_3sum[lst_3at])
    lrem=unique(remi_hh_pop_3sum[lst_3at])
    dif=list(set(lsyn)-set(lrem))
    sdif=[str(x) for x in dif]
    sdif.sort()
    print "  * Warning, Syn HHs and REMI HH pop have different sub-categories", syn_hhs_3sum.shape[0],remi_hh_pop_3sum.shape[0]
    print ('  |').join(sdif)+"\n"

join_hh_hhpop=mlab.rec_join(tuple(lst_3at), syn_hhs_3sum, remi_hh_pop_3sum, jointype='outer')
remi_hhs_3sum=extend_ratios(join_hh_hhpop,'hhs3',baseyear,years)
#outcsv(remi_hhs_3sum,'remi_hhs_3sum')

###Step 7. Extend REMI HHs from 3 attributes to 8 attributes
print "Step 7. Extend REMI HHs from 3 attributes to 8 attributes"

 #7.1 aggregate synthesized HHs by all 8 attributes
print '   Aggregating synthesized HHs by 8 attributes'
syn_hhs_8sum=mlab.rec_groupby(syn_hhs, tuple(lst_8at), (('large_area',len,'hhs8'),))

 #7.2 Get combination of 8 attributes, first 7 at must be unique from aggregation. income must have all 4 (1-4) categories for each parent category, result must be sorted 
print '   Creating attribute table based on aggregation result'
tmp_table=syn_hhs_8sum.copy()
tmp_table['income']=1
tmp_table=unique(tmp_table[lst_8at]) 
at_table=tmp_table.copy()
for i in range(2,5):
    tmp_table['income']=i
    at_table=concatenate((at_table,tmp_table),axis=1)
at_table.sort()

 #7.3 Join aggregate HHs by 8 attr to id table
syn_hhs_8all=mlab.rec_join(tuple(lst_8at),at_table,syn_hhs_8sum,jointype='outer')

 #7.4 Continue to join aggregate HHs by 3 attr to id table,
 #since in id_table the combination of first 3 ids are no longer unique, rec_join cannot use it as key for joinning. Have to use dictionary to look up values
print "   Building look up table from remi HHs table"
dic_at3={}
for i in range(0,remi_hhs_3sum.shape[0]): # go through each row and build dictionary using 3 attributes as key
    dic_at3[tuple(remi_hhs_3sum[lst_3at][i])]=remi_hhs_3sum[years][i]

print '   Adding forecast years as new fields'   
zdata=zeros(syn_hhs_8all.shape[0])
for year in years: # append new fields (2010 to 2040) to table, set all values to 0s. Appending one by one is faster than appending multiple at once.
    syn_hhs_8all=rfn.append_fields(syn_hhs_8all, year, data=zdata, dtypes=float)


print '   Assigning HHs to new fields'
skey=dic_at3.keys()
skey.sort()
for key in skey:
    condition=(syn_hhs_8all[lst_3at[0]]==key[0])&(syn_hhs_8all[lst_3at[1]]==key[1])&(syn_hhs_8all[lst_3at[2]]==key[2])
    for year in years: # use mask to replace values in syn_hhs_8all table
        place(syn_hhs_8all[year],condition ,dic_at3[key][years.index(year)])
syn_hhs_8all=ma.getdata(syn_hhs_8all)

print '   Computing forecast year Hhs by 8 attributes'
#7.5 Derive REMI HHs by ratio = syn HH 8 attributes / REMI HH base year 3 attributes
syn_hhs_8all=extend_ratios(syn_hhs_8all,'hhs8',baseyear,years)
for name in syn_hhs_8all.dtype.names:
    ind=isnan(syn_hhs_8all[name])
    syn_hhs_8all[name][ind]=0


### Step 8. Adjust income quartiles for each forecast year
print "Step 8. Adjust income quartiles"
inc_years=years[:]
inc_years.remove(baseyear) #no need to adjust for 2010 baseyear
for year in inc_years:
    inputary=syn_hhs_8all[year]
    #inputary=around(syn_hhs_8all[year],decimals=0) # adjust by integer
    adj_income=quartile_adj(inputary)
    syn_hhs_8all[year]=adj_income
out3csv(syn_hhs_8all, sum_years,'hh_step8')  


### Step 9. change final format
print "Step 9. Reformat result"

#9.1 filter out rows with 0s from 2010 to 2040, this could reduce array size significantly
condition=(syn_hhs_8all['2010']>0)|(syn_hhs_8all['2040']>0)|(syn_hhs_8all['2020']>0)|(syn_hhs_8all['2030']>0)
hhsnew=syn_hhs_8all.take(mlab.find(condition))
 
print "   Changing layout of final table"
#target format: ('year'),('large_area_id'),('race'),('age_of_head_min'),('age_of_head_max'),('persons_min'),
#               ('persons_max'),('children_min'),('children_max'),('cars_min'),('cars_max'),('workers_min'),
#               ('workers_max'),('income_min'),('income_max'),('total_number_of_households')
for year in years:
    ary_temp=vstack((hhsnew['large_area'],hhsnew['large_area'],hhsnew['race'],hhsnew['age_of_head'],hhsnew['age_of_head']
                     ,hhsnew['persons'],hhsnew['persons'],hhsnew['children'],hhsnew['children'],hhsnew['cars'],hhsnew['cars']
                     ,hhsnew['workers'],hhsnew['workers'],hhsnew['income'],hhsnew['income'],hhsnew[year]))
    ary_temp[0]=float(year)
    ary_trn=ary_temp.transpose().copy() #transpose to get correct row/column layout
    try:
        ary_all=vstack((ary_all,ary_trn))      
    except:
        ary_all=ary_trn        
ary_all.dtype=[('year',float),('large_area_id',float),('race_id',float),('age_of_head_min',float),('age_of_head_max',float),('persons_min',float),
               ('persons_max',float),('children_min',float),('children_max',float),('cars_min',float),('cars_max',float),('workers_min',float),
               ('workers_max',float),('income_min',float),('income_max',float),('total_number_of_households',float)]

print "   Recoding min and max values"
dic_v={'income':list(quartile),'age_of_head':list(bin_agehead)}
for key in dic_v.keys(): 
    for v in unique(ary_all[key+'_min']):
        ind=ary_all[key+'_min']==v
        ary_all[key+'_min'][ind]=dic_v[key][int(v)-1]
        ary_all[key+'_max'][ind]=dic_v[key][int(v)]-1
        
for name in ['age_of_head','persons','children','cars','workers','income']:
    ind=ary_all[name+'_max']==max(ary_all[name+'_max'])
    ary_all[name+'_max'][ind]=-1



ary_all=ary_all.flatten()
print "   Exporting 'household_control_totals.csv' table"
outcsv(ary_all, 'household_control_totals')    

#*aggregate back to remi age and race and see the differences
print 'All done. ', round(time()-start,1)," secs"
 








