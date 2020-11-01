import gc
import network
import ubinascii
import utime
from machine import RTC

import util
import uuurequests


WIFI_NAME = b"BVG Wi-Fi"

# collect all hidden form fields from HTML
def parseFormValues(text):
    startIndex = 0
    postFields = []
    postFields.append("termsOK=1")
    postFields.append("button=kostenlos+einloggen")
    while 1:
        nameFindStr = "<input type=\"hidden\" name=\""
        valueFindStr = "value=\""
        findStartIndex = text.find(nameFindStr, startIndex)
        if (findStartIndex == -1):
            break
        nameStartIndex = findStartIndex + len(nameFindStr)
        nameEndIndex = text.find("\"", nameStartIndex)
        name = text[nameStartIndex:nameEndIndex]
        valueStartIndex = text.find(valueFindStr, nameEndIndex) + len(valueFindStr)
        valueEndIndex = text.find("\"", valueStartIndex)
        value = text[valueStartIndex:valueEndIndex]
        postFields.append(name + "=" + value)
        startIndex = valueEndIndex

    return "&".join(postFields)


def accept_captive_portal():
    #get captive portal via captive.apple.com
    #url = "http://ubahndepot.com/storage/share/tmp/captive_demo.html"
    url = "http://captive.apple.com"
    #url = "https://www.hotsplots.de/auth/login.php?res=notyet&uamip=10.0.160.1&uamport=80&challenge=8638ce7ac8088c170ae0076b0d4932cb&called=F6-F0-3E-40-07-DE&mac=E8-80-2E-EA-2A-2D&ip=10.0.175.201&nasid=BVG-Bahnhoefe&sessionid=5f93869200000463&userurl=http%3a%2f%2finit-p01st.push.apple.com%2fbag%3fv%3d1"
    try:
        r = uuurequests.get(url)
    except:
        return False

    text = r.text

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://www.hotsplots.de",
        #"Accept-Encoding": "br, gzip, deflate",
        "Cookie": "div=1",
        "Connection": "keep-alive",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU OS 12_4_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) FxiOS/29.0  Mobile/15E148 Safari/605.1.15"
    }

    if (text.find("<HTML><HEAD><TITLE>Success</TITLE></HEAD><BODY>Success</BODY></HTML>") == -1):
        gc.collect()
        util.syslog("Captive Portal BVG", "Captive Portal detected")

        postData = parseFormValues(text)
        gc.collect()
        loginReqest = uuurequests.request("POST", "https://www.hotsplots.de/auth/login.php", headers=headers, data=postData)
        loginResponse = loginReqest.text
        gc.collect()

        util.syslog("Captive Portal BVG", "Submitted first stage of captive portal")

        redirectSearch = "<meta http-equiv=\"refresh\" content=\"0;url="
        redirectStartIndex = loginResponse.find(redirectSearch) + len(redirectSearch)
        redirectEndIndex = loginResponse.find("\"", redirectStartIndex)
        redirectUrl = loginResponse[redirectStartIndex:redirectEndIndex]
        redirectUrl = redirectUrl.replace("&amp;","&")
        gc.collect()

        util.syslog("Captive Portal BVG", "Detected URL for second stage. Submitting request (probably to local router)")

        try:
            uuurequests.get(redirectUrl)
            gc.collect()
        except:
            util.syslog("Captive Portal BVG", "Problem open second stage of captive portal login")
            return False
        #redirectRequest.text
        util.syslog("Captive Portal BVG", "Successfully logged in into captive portal")
        return True
        
    else:
        util.syslog("Captive Portal BVG", "No captive portal in place")
        return True



