import re
import httpx
import requests
import pandas as pd
import xml.etree.ElementTree as ET, io,textwrap, html
from urllib.parse import urljoin 
import time
from datetime import datetime,timedelta,timezone


pd.set_option("display.max_columns", None)   # show ALL columns
pd.set_option("display.width",       None)   # don’t wrap lines
pd.set_option("display.max_colwidth", None)  # don’t truncate long strings

headers = {"User-Agent":"Edik@edik.ee","Accept-Encoding":"gzip, deflate","Host":"www.sec.gov"}
headers2 = {"User-Agent":"Edik@edik.ee","Accept-Encoding":"gzip, deflate","Host":"data.sec.gov"}
ticker = input("Enter the ticker: ").lower()
export = input("Export to CSV Y/N:").upper()
now = datetime.now()
CTRL_LOW  = set(range(0x00, 0x20)) - {0x09, 0x0A, 0x0D}   # allow TAB, LF, CR
CTRL_HIGH = set(range(0x7F, 0xA0))                        # DEL & 0x80-0x9F
ILLEGAL   = CTRL_LOW | CTRL_HIGH

try:
    days = int(input(f"Trades for the Last x Days:"))
except:
    days = 30



def get_cik(ticker):                              # map ticker to cik from ticker.txt
    
    file = requests.get("https://www.sec.gov/include/ticker.txt", headers = headers)
    r = file.text
    for line in r.splitlines():
        word = line.split()
        if ticker in word:
            cik = (word[1])
            
            return(cik)

def get_filing(cik):                                                   # gets a list of filings reads into dataframe

    cik = cik.zfill(10)                                                # add leading zeroes to cik for correct format
    client = httpx.Client(headers=headers2,http2=True)                 # needs to be http/2 
    filings = client.get(f"https://data.sec.gov/submissions/CIK{cik}.json")
    client.close()
    respobj = filings.json()
    recent0 = pd.DataFrame(respobj["filings"]["recent"])               # creates DataFrame of the metadata
    insider = recent0[recent0["form"].isin(["4", "5"])]
    return insider





def get_trades(row, cik):                                                 # generator: yield one dict per <nonDerivativeTransaction>
    url = get_xml_url(row, cik)

    print(url)

    raw  = requests.get(url, headers=headers, timeout=40).content         # get .xml file
    raw  = sanitize_bytes(raw)                                            # strip bad control bytes
 

    tree = ET.fromstring(raw)                                             # parse the .xml

    txn = tree.findall('.//{*}nonDerivativeTransaction')                  # try namespace .xml
    if not txn:                                  
        txn = tree.findall('.//nonDerivativeTransaction')                 # try non-namespace


    txo = tree.findall('.//{*}derivativeTransaction')                  # try namespace .xml
    if not txo:                                  
        txo = tree.findall('.//derivativeTransaction')                 # try non-namespace
    

    for t in txn:                                                         
        yield {
            "Type"      : "non-Derivative",

            "Date"      :  t.findtext('.//{*}transactionDate/{*}value')
                           or t.findtext('.//transactionDate/value'),
            "Code"      : t.findtext('.//{*}transactionCoding/{*}transactionCode')
                           or t.findtext('.//transactionCoding/transactionCode'),
            "Shares"    : t.findtext('.//{*}transactionShares/{*}value')
                           or t.findtext('.//transactionShares/value'),
            "Price"     : t.findtext('.//{*}transactionPricePerShare/{*}value')
                           or t.findtext('.//transactionPricePerShare/value'),
            "OwnedAfter": t.findtext('.//{*}sharesOwnedFollowingTransaction/{*}value')
                           or t.findtext('.//sharesOwnedFollowingTransaction/value'),
            "Name"      : tree.findtext('.//{*}reportingOwner/{*}reportingOwnerId/{*}rptOwnerName')
                           or tree.findtext('.//reportingOwner/reportingOwnerId/rptOwnerName'),
            "Title"     : tree.findtext(".//{*}reportingOwnerRelationship/{*}officerTitle") 
                           or tree.findtext(".//reportingOwnerRelationship/officerTitle"),
            "link"      : url,
        }
   
     
    for s in txo:                                                         
        yield {
            "Type"      : "Derivative",

            "Date"      : s.findtext('.//{*}transactionDate/{*}value')
                           or s.findtext('.//transactionDate/value'),
            "Code"      : s.findtext('.//{*}transactionCoding/{*}transactionCode')
                           or s.findtext('.//transactionCoding/transactionCode'),
            "Shares"    : s.findtext('.//{*}transactionShares/{*}value')
                           or s.findtext('.//transactionShares/value'),
            "Exercise Price"     : s.findtext('.//{*}conversionOrExercisePrice/{*}value')
                           or s.findtext('.//conversionOrExercisePrice/value'),
            "Security"  : s.findtext('.//{*}securityTitle/{*}value')
                           or s.findtext('.//securityTitle/value'),
            "OwnedAfter": s.findtext('.//{*}sharesOwnedFollowingTransaction/{*}value')
                           or s.findtext('.//sharesOwnedFollowingTransaction/value'),
            "Name"      : tree.findtext('.//{*}reportingOwner/{*}reportingOwnerId/{*}rptOwnerName')
                           or tree.findtext('.//reportingOwner/reportingOwnerId/rptOwnerName'),
            "Title"     : tree.findtext(".//{*}reportingOwnerRelationship/{*}officerTitle") 
                           or tree.findtext(".//reportingOwnerRelationship/officerTitle"),
            "ExpirationDate" : s.findtext('.//{*}expirationDate/{*}value')
                           or s.findtext('.//expirationDate/value'),
            "link"      : url,
        }


    time.sleep(0.11)                  # < 10 req/s cap SEC requirement
    








def sanitize_bytes(raw: bytes) -> bytes:                             # sanitize .xml
    raw = bytes(b for b in raw if b not in ILLEGAL)                  # nuke all illegal bytes
    raw = raw.replace(b"\xa0", b" ")                                 # replace NBSP with space
    raw = re.sub(rb"&(?!(amp|lt|gt|apos|quot|#))", b"&amp;", raw)    # fix &
    return raw




def get_xml_url(row,cik):                                           # get .xml url
    cik = cik.lstrip("0")                                           # remove leading zeroes from cik
    acc = row["accessionNumber"].replace("-", "")                   # format acc nr.
    base = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/"  # root directory for filings
    listing = requests.get(base, headers=headers, timeout=30).text  # get directory listing
    xmls = re.findall(r'href="([^"]+\.xml)"', listing, flags=re.I)  # extract .xml links from directory listing
    
    if not xmls:
        raise FileNotFoundError("No .xml files in Form-4 folder")

    best = next((x for x in xmls if "form4" in x.lower()), xmls[0])  # prefer any file whose name contains "form4"
    url = urljoin(base, best)                                        # build absolute URL 
    print(url)
    return url


cik = get_cik(ticker)                              # map ticker to cik from ticker.txt
if cik:
    print("Checking:"+ticker.upper())
else:
    print("Ticker Not Found")


insider = get_filing(cik)                           # gets a list of filings reads into dataframe


cutoff = (now - timedelta(days=days)).strftime("%Y-%m-%d")               # filter by date 
recent = insider[insider["filingDate"] >= cutoff]  

print("\nLinks:")

trades = pd.DataFrame(                                                   # build DataFrame from generator
    t for _, row in recent.iterrows()
      for t in get_trades(row, cik)
)

if trades.empty:
    print(f"No Form 4/5 activity for {ticker.upper()} in the last {days} days.")

else:
    non_deriv = trades[trades["Type"] == "non-Derivative"].copy()
    deriv     = trades[trades["Type"] == "Derivative"].copy()   
    non_cols = ["Date", "Code", "Shares", "Price",
    "OwnedAfter", "Name"]
    der_cols = ["Date", "Code", "Security", "Shares", "Exercise Price", "ExpirationDate", 
    "OwnedAfter", "Name"]
    non_block = non_deriv[non_cols]
    der_block = deriv[der_cols]
    print("\n---------------non-derivative trades----------------")
    print(non_block.to_string(index=False))
    print("\n----------------derivative trades--------------------")
    print(der_block.to_string(index=False))




    if export == "Y":                                                        # export to .csv
        date = now.strftime("%m_%d_%Y")
        non_block.to_csv(ticker+"_"+str(days)+"days"+"_insider_trades.csv", index=False)
        der_block.to_csv(ticker+"_"+str(days)+"days"+"_insiderder_trades.csv", index=False)






