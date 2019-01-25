#!/usr/bin/env python2

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from bs4 import BeautifulSoup
import re
from getpass import getpass
import os
import sys
sys.path.append("../")
from paycheckrecords import *

def checkRowForAll(row):
    for col in row.findAll('td'):
        if "Federal Income Tax" in str(col):
            return True
        if "Social Security" in str(col):
            return True
        if "Medicare" in str(col):
            return True
        if "NY Income Tax" in str(col):
            return True
        if "Cell Phone" in str(col):
            return True
        if "Deductions" in str(col):
            return True
        if "Taxes" in str(col):
            return True

    return False

def blackOut(html):
    soup = BeautifulSoup(html, "lxml")

    #blackout net pay
    tmp = soup.findAll('u')
    for tag in tmp:
        if "Net Pay" in str(tag.parent):
            tag["style"] = "background-color:black; -webkit-print-color-adjust: exact;"
    tableList = ["paystub_pay_tbl", "paystub_ee_taxes_tbl", "paystub_summary_tbl"]

    #black out all
    for curTable in tableList:
        tmpTable = soup.find("table", {"id": curTable})
        allrows = tmpTable.findAll('tr')
        for row in allrows:
            if checkRowForAll(row):
                for col in row.findAll('td'):
                    if '.' in str(col):
                        col["style"] = "background-color:black;  -webkit-print-color-adjust: exact;"



    #black out netthispay
    elem = soup.find(text=re.compile('.*Net This Check:.*'))
    elem = elem.findNext('td')
    elem["style"] = "background-color:black;  -webkit-print-color-adjust: exact;"

    #black out account
    elem = soup.find(text=re.compile('.*Acct#.*'))

    nelem = elem.findNext('td')
    nelem["style"] = "background-color:black;  -webkit-print-color-adjust: exact;"

    contents = elem.string
    contentsList = contents.split("#")
    newcontent = contentsList[0] + "#<span style = \"background-color:black;  -webkit-print-color-adjust: exact;\">"
    contentsList = contentsList[1].split(":")
    newcontent = newcontent + contentsList[0] + "</span>:" + contentsList[1]
    elem.replaceWith(newcontent)

    return str(soup.prettify(formatter=None))

def printSimpleSummary( stubs ):
    gross    = 0.0
    totalnet = 0.0

    print("")
    print("QUICK SUMMARY:")
    print("")

    print("----------------------------------------------")
    print(('{: <20} {: >12} {: >12}'.format( "Date",
                                            "Total Pay",
                                            "Net Pay" )))
    print("----------------------------------------------")
    for stub in stubs:
        print(('{: <20} {: >12} {: >12}'.format( stub.PayDate.strftime("%Y-%m-%d"),
                                                stub.TotalPay,
                                                stub.NetPay )))
        gross    = gross    + stub.TotalPay
        totalnet = totalnet + stub.NetPay

    print("----------------------------------------------")
    print(('{: <20} {: >12} {: >12}'.format( "",
                                            str(gross),
                                            str(totalnet) )))
    print("")

def printDetailedSummary( stubs ):
    summary = {}
    for stub in stubs:
        for f in stub.StubDetails:
            if f['name'] in summary:
                summary[f['name']]['hours']   += f['hours']
                summary[f['name']]['rate']    += f['rate']
                summary[f['name']]['current'] += f['current']
            else:
                summary[f['name']] = { 'hours'   : f['hours'],
                                       'rate'    : f['rate'],
                                       'current' : f['current'] }

    print("")
    print("DETAILED TOTALS:")
    print("")

    print("-----------------------------------------------------------")
    print(('{: <20} {: >12} {: >12} {: >12}'.format( "Field",
                                                    "Total Hours",
                                                    "Total Rate",
                                                    "Total" )))
    print("-----------------------------------------------------------")
    for s in summary:
        print(('{: <20} {: >12.2f} {: >12.2f} {: >12.2f}'.format( s,
                                                                 summary[s]['hours'],
                                                                 summary[s]['rate'],
                                                                 summary[s]['current'] )))
    print("")


def savePayStubs( stubs, redact=False ):
    for stub in stubs:
        filename = "paystub-" + stub.PayDate.strftime("%Y-%m-%d")

        if os.path.isfile(filename + ".html"):
            i = 1
            while os.path.isfile(filename + "_" + str(i) + ".html"):
                i += 1
                if i == 100:
                    print("There seem to be a lot of duplicate files? Aborting.")
                    return -1
            filename += '_' + str(i)

        out = open(filename + ".html", "w")
        out.write(stub.HTML)
        out.close()

        if redact:
            out = open(filename + "_redacted.html", "w")
            out.write(blackOut(stub.HTML))
            out.close()

def yesno( x ):
    while True:
        resp = input(x)
        if( resp.lower() == 'y' ):
            return True
        elif( resp.lower() == 'n' ):
            return False
        else:
            print("  Invalid response.")

def get_date( x, fmt='%m/%d/%Y' ):
    while True:
        try:
            #resp = eval(input(x)) or datetime.today().strftime(fmt)
            resp = input(x) or datetime.today().strftime(fmt)
            return datetime.strptime(resp, fmt)
        except ValueError:
            print("  Invalid date or date format provided.")

def main():

    print("")
    print("Print a summary of all pay stubs between the given dates.")
    print("Optionally save off the pay stubs and redacted pay stubs.")
    print("")

    while True:
        startdate = get_date("Start date (MM/DD/YYYY): ", '%m/%d/%Y')
        enddate   = get_date("End date (MM/DD/YYYY): ", '%m/%d/%Y')
        if( startdate <= enddate ):
            break
        else:
            print("  Invalid date range. Start date must be before or equal to end date.")

    savestubs = yesno("Save pay stubs? [Y/n] ")
    if( savestubs ):
        saveredacted = yesno("Save redacted pay stubs? [Y/n] ")
        if( saveredacted ):
            # Deleting the sensitive information is an exercise for the reader ...
            print("  WARNING: redacted pay stubs are intended to be printed. Although")
            print("           it is blacked out, the sensitive information is still")
            print("           present in the document.")
            saveredacted = yesno("  Do you acknowledge and accept the above warning? [Y/n] ")

    print("PaycheckRecords.com Credentials:")

    while True:
        username = input("  Username: ")
        if( username != "" ):
            break

    while True:
        password = getpass("  Password: ")
        if( password != "" ):
            break

    print("")

    paycheckinst = paycheckrecords(username, password)

    try:
        stubs = paycheckinst.getPayStubsInRange(startdate, enddate)

        printSimpleSummary( stubs )
        printDetailedSummary( stubs )

        if savestubs:
            savePayStubs( stubs, saveredacted )

    finally:
        paycheckinst.close()

main()
