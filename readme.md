This Python script fetches recent insider trading activity (Forms 3, 4, 5) for any publicly traded U.S. company using data from the SEC EDGAR system.<br>
<br>
Usage:<br>
<br>
	1. Enter a stock ticker (e.g., aapl, tsla).<br>
	2.  Choose whether to export the data to CSV (Y/N)<br>
	&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Example CSV output: *tsla_30days_insider_trades.csv*<br>
	3. Specify the number of past days of filings to include(Default: 30 days).<br>
<br>
<br>
The output includes:<br>
<br>
   - Transaction Date<br>
   - Transaction Code ( https://www.sec.gov/edgar/searchedgar/ownershipformcodes.html )<br>
   - Number of Shares<br>
   - Price<br>
   - Ownership After the Trade<br>
   - Insiders Name<br>
   - Insiders Title<br>
<br>
Installation:<br>
<br>

```bash
        git clone https://github.com/ints101/edik
	cd edik
	pip install -r requirements.txt
	python3 edik.py
```

<br>
<br>
<br>
Screenshot: <br>

<br>

![sample](https://github.com/user-attachments/assets/d4b5afd2-4eeb-4123-a817-efb1a7605271)



