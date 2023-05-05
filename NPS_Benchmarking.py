# %%
import time,os,requests,io,datetime
import pandas as pd
import numpy as np
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# %%
# Read the Transactions File

tdf = pd.read_csv("npsTransactions.csv")
def negUnits(x):
    if(x[0] == "("):
        x = -float(x[1:-1])
    else:
        x = float(x)
    return x
tdf['Amt'] = tdf['Amt'].apply(negUnits)

tdf['Date'] = pd.to_datetime(tdf['Date'])
tdf = tdf.sort_values(by='Date',ascending=True, ignore_index=True)
tdf['Date'] = tdf['Date'].dt.strftime('%Y-%m-%d')

fdate = datetime.datetime.strptime(min(tdf["Date"]), "%Y-%m-%d") 
tdate = datetime.datetime.today()

# %%
# HDFC PFM Data
driver = Chrome(service=Service(ChromeDriverManager().install()))

driver.get("https://www.hdfcpension.com/nav/nav-history/")
time.sleep(5)
driver.execute_script("document.getElementById('from_date').value = '%s';"%fdate.strftime("%d-%m-%Y"))
time.sleep(5)
driver.execute_script("document.getElementById('to_date').value = '%s';"%tdate.strftime("%d-%m-%Y"))
time.sleep(5)
driver.find_element(By.ID,'filter').click()
time.sleep(10)
driver.find_element(By.NAME,'filter').click()
time.sleep(30)

with open("tmp.html", "w", encoding="utf-8") as f:
    f.write(driver.page_source)

dfs = pd.read_html("tmp.html")
hdfcdf = dfs[0]

# %%
# SBI PFM Data
driver = Chrome(service=Service(ChromeDriverManager().install()))

driver.get("https://www.sbipensionfunds.com/historical-nav/")
time.sleep(10)
driver.execute_script("document.getElementById('f_date_p1').value = '%s';"%fdate.strftime("%Y-%m-%d"))
time.sleep(5)
driver.execute_script("document.getElementById('f_date_p2').value = '%s';"%tdate.strftime("%Y-%m-%d"))
time.sleep(10)

l = driver.find_element(By.NAME,'mysubmit')#.click()
driver.execute_script("arguments[0].click();", l)
time.sleep(30)

with open("tmp.html", "w", encoding="utf-8") as f:
    f.write(driver.page_source)

dfs = pd.read_html("tmp.html")
sbidf = dfs[1]

# %%
# Save NAV Datas to csv
sbidf.to_csv("SBI_NAV_Data.csv",index=False)
hdfcdf.to_csv("HDFC_NAV_Data.csv",index=False)
os.remove("tmp.html")
driver.quit()

# %%
# Initialization and functions
df = tdf.copy()
sbidf = pd.read_csv("SBI_NAV_Data.csv")
hdfcdf = pd.read_csv("HDFC_NAV_Data.csv")

def sbiT1(date):
    return float(sbidf.loc[sbidf["0"] == "%s"%date]["3"]) #3- t1, 6-t2
def hdfcT1(date):
    return float(hdfcdf.loc[(hdfcdf["Date"]) == "%s"%date]["HDFC Pension Fund Scheme Tier I"]) 
def getNifty(date):
	url="https://archives.nseindia.com/content/indices/ind_close_all_%s.csv"%date
	s=requests.get(url).content
	indicesDf=pd.read_csv(io.StringIO(s.decode('utf-8')))
	indicesDf = indicesDf.loc[indicesDf['Index Name'] == 'Nifty 50']
	niftyClose = indicesDf.at[0,'Closing Index Value']
	return float(niftyClose/100)

# %%
# Units alloted if invested in SBI vs HDFC vs Nifty
df["SBI Units"] = np.zeros(len(df['Date']))
df["HDFC Units"] = np.zeros(len(df['Date']))
df["Nifty Units"] = np.zeros(len(df['Date']))

for i in range(len(df['Date'])):
    inv = float(df.at[i,'Amt'])
    date = datetime.datetime.strptime(df.at[i,'Date'], "%Y-%m-%d")
    try:
        df.at[i,"SBI Units"] = inv/sbiT1(date.strftime("%Y-%m-%d"))
        df.at[i,"HDFC Units"] = inv/hdfcT1(date.strftime("%d-%m-%Y"))
        df.at[i,"Nifty Units"] = inv/getNifty(date.strftime("%d%m%Y"))
    except:
        date = date - datetime.timedelta(days=1)
        df.at[i,"SBI Units"] = inv/sbiT1(date.strftime("%Y-%m-%d"))
        df.at[i,"HDFC Units"] = inv/hdfcT1(date.strftime("%d-%m-%Y"))
        df.at[i,"Nifty Units"] = inv/getNifty(date.strftime("%d%m%Y"))

# %%
# Compute Present Value
df['SBI Units'] = df['SBI Units'].apply(lambda x: round(x, 4))
df['HDFC Units'] = df['HDFC Units'].apply(lambda x: round(x, 4))
df['Nifty Units'] = df['Nifty Units'].apply(lambda x: round(x, 4))

invested = df['Amt'].sum()
sbiUnits = df['SBI Units'].sum()
hdfcUnits = df['HDFC Units'].sum()
niftyUnits = df['Nifty Units'].sum()

date = datetime.datetime.strptime(sbidf.at[len(sbidf["0"])-1,"0"], "%Y-%m-%d")

sbiCurr = sbiUnits*sbiT1(date.strftime("%Y-%m-%d"))
hdfcCurr = hdfcUnits*hdfcT1(date.strftime("%d-%m-%Y"))
niftyCurr = niftyUnits*getNifty(date.strftime("%d%m%Y"))

index = len(df['Date'])
df.at[index,"Date"] = date.strftime("%d-%b-%Y")
df.at[index,"Amt"] = invested
df.at[index,"SBI Units"] = round(sbiCurr,2)
df.at[index,"HDFC Units"] = round(hdfcCurr,2)
df.at[index,"Nifty Units"] = round(niftyCurr,2)

# %%
# Save to file
df.to_csv("NPS_Tier1Equity_Analysis.csv",index=False)


