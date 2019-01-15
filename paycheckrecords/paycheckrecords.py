from getpass import getpass
import threading
import mechanicalsoup
from bs4 import BeautifulSoup
from .paystub import paystub
from datetime import datetime
from datetime import timedelta


class paycheckrecords:
    _br = mechanicalsoup.StatefulBrowser()
    _browserSem = threading.Semaphore()
    _thread = None
    _stop = False
    _timer = None
    _threadSleep = threading.Event()

    def __init__(self, username, password):
        #self._br.set_handle_robots(False)
        self._br.open("https://www.paycheckrecords.com")
        self._br.select_form()

        self._br["userStrId"] = username
        self._br["password"] = password

        self._br.submit_selected()

        self._thread = threading.Thread(target=self.preventTimeOut)
        self._thread.start()

    def preventTimeOut(self):
        while not self._stop:
            self._browserSem.acquire()
#            print "aquired lock"
            url = self._br.get_url()
            #print "url = ", url
            self._br.open(url)
#            print "refreshed"
            self._browserSem.release()
#            print "reload page from thread"
            self._threadSleep.wait(30)
#            print "awake"
            self._threadSleep.clear()



    def getLatestPayStub(self):
        self._browserSem.acquire()
        originalurl = self._br.get_url()
        paystubResponse = self._br.open("https://www.paycheckrecords.com/in/paychecks.jsp")

        ret = self._getPaystubsFromTable(paystubResponse.read(), list(range(1, 2)))

        self._br.open(originalurl)
        self._browserSem.release()
        return ret[0]

    def getPayStubsInRange(self, startDate, endDate, sequence = 0):
        self._browserSem.acquire()
        originalurl = self._br.get_url()
        paystubResponse = self._br.open("https://www.paycheckrecords.com/in/paychecks.jsp")
        self._br.select_form("#dateSelect")
        self._br["startDate"] = startDate.strftime("%m/%d/%Y")
        self._br["endDate"] = endDate.strftime("%m/%d/%Y")
        paystubResponse = self._br.submit_selected()
        ret = self._getPaystubsFromTable(paystubResponse.text,sequence)

        self._br.open(originalurl)
        self._browserSem.release()
        return ret

    def _getPayStubDetails(self, html):
        soup    = BeautifulSoup(html, "lxml")
        details = soup.find_all("table", { "class" : [ "detailsWages", "detailsPart" ] })
        rv      = []

        # Paystub details seem to contain 4 elements, each consisting of one or more rows:
        #  [0] Pay        (e.g. salary, bonus, ... )
        #  [1] Deductions (e.g. 401k, healthcare, ... )
        #  [2] Taxes      (e.g. federal, state, SS, medicare, ... )
        #  [3] Summary
        for d in range( 0, len(details) ):
            for r in details[d].find_all('tr')[1:]:
                tds = r.find_all('td')
                if( d == 0 ): # Pay field has extra elements: hours and rate
                    rv.append( { 'name'    : tds[0].text.strip(),
                                 'hours'   : float(tds[1].text.strip() or 0.0),
                                 'rate'    : float(tds[2].text.strip() or 0.0),
                                 'current' : float(tds[3].text.strip()),
                                 'ytd'     : float(tds[4].text.strip()) } )
                else:
                    rv.append( { 'name'    : tds[0].text.strip(),
                                 'current' : float(tds[1].text.strip()),
                                 'ytd'     : float(tds[2].text.strip()),
                                 # Make post-processing easier
                                 'hours'   : float(0.0),
                                 'rate'    : float(0.0) } )

        # List of dictionaries containing name/hours/rate/current/ytd
        # information for each line-item of a paystub
        return rv

    def _getPaystubsFromTable(self, html, sequence, GetHtml = True):
        soup = BeautifulSoup(html, "lxml")
        PayStubTable = soup.find("table", { "class" : "report" })
        payrows = PayStubTable.findAll('tr')
        headerCols = payrows[0].findAll('td')
        ret = []
        i = 0
        DateIndex = -1
        NetIndex = -1
        TotalIndex = -1

        for col in headerCols:
            colName = col.string
            if colName == 'Pay Date' and DateIndex == -1:
                DateIndex = i
            elif colName == 'Total Pay' and TotalIndex == -1:
                TotalIndex = i
            elif colName == 'Net Pay' and NetIndex == -1:
                NetIndex = i
            i = i + 1
        if sequence == 0:
            sequence = list(range(1, len(payrows)))
        for index in sequence:
            paystubHtml = None
            rowCols = payrows[index].findAll('td')
            rowDate = rowCols[DateIndex].a.string.strip()
            rowTotalPay = float(rowCols[TotalIndex].string.strip().strip("$").translate(dict.fromkeys(list(map(ord,',')),None)))
            rowNetPay = float(rowCols[NetIndex].string.strip().strip("$").translate(dict.fromkeys(list(map(ord,',')),None)))
            tmpDateTime = datetime.strptime(rowDate, '%m/%d/%Y')
            if GetHtml:
                paystubResponse = self._br.open_relative(rowCols[DateIndex].a['href'])
                paystubHtml = paystubResponse.text
                stubDetails = self._getPayStubDetails(paystubHtml)
                #self._br.back()
            tmpPayStub = paystub(tmpDateTime, rowTotalPay, rowNetPay, stubDetails, paystubHtml)
            ret.append(tmpPayStub)

        return ret



    def close(self):
        #print "Closing Instance"
        self._stop = True
        #print "_stop set"
        self._threadSleep.set()
        #print "_threadSleep set"
        self._thread.join()
        #print "thread joined"
        self._br.close()
        #print "Closing Done"
