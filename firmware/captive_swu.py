import gc

import util
import uuurequests



def accept_captive_portal() -> bool:
    try:
        # portalDetectResponse = uuurequests.get(
        #     "https://www.hotsplots.de/auth/login.php?res=notyet&uamip=10.0.160.1&uamport=80&challenge=8638ce7ac8088c170ae0076b0d4932cb&called=F6-F0-3E-40-07-DE&mac=E8-80-2E-EA-2A-2D&ip=10.0.175.201&nasid=BVG-Bahnhoefe&sessionid=5f93869200000463&userurl=http%3a%2f%2finit-p01st.push.apple.com%2fbag%3fv%3d1"
        # )
        # portalDetectResponse = uuurequests.get(
        #     "http://clients1.google.com/generate_204"
        # )
        portalDetectResponse = uuurequests.get("http://captive.apple.com")
    except Exception:
        return False

    # if portalDetectResponse.status_code == 204:
    if (
        portalDetectResponse.text.find(
            "<HTML><HEAD><TITLE>Success</TITLE></HEAD><BODY>Success</BODY></HTML>"
        )
        == -1
    ):

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://controller.access.network/",
            "Cookie": "div=1",
            "Connection": "keep-alive",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU OS 12_4_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) FxiOS/29.0  Mobile/15E148 Safari/605.1.15",
        }

        util.syslog("Captive Portal SWU", "Portal detected")

        gc.collect()

        try:
            loginReqest = uuurequests.request(
                "GET",
                "https://controller.access.network/?dst=http%3A%2F%2Fcaptive.apple.com%2F",
                #"http://ubahndepot.com/storage/share/tmp/SWUWIFI/redirect.php",
                #"http://ubahndepot.com/storage/share/tmp/SWUWIFI/second.json",
                headers=headers,
                follow_redirects=False
            )
            loginResponseHeaders = loginReqest.headers
            cookie = loginResponseHeaders["Set-Cookie"]
            cookie = cookie.partition(";")[0]
            headers["Cookie"] = cookie

            util.syslog(
                "Captive Portal SWU",
                "success get cookie: " + cookie,
            )
            gc.collect()

        except Exception:
            util.syslog(
                "Captive Portal SWU",
                "Problem open prerequest stage of captive portal login",
            )
            return False


        try:
            loginReqest = uuurequests.request(
                "POST",
                "https://controller.access.network/portal_api.php",
                #"http://ubahndepot.com/storage/share/tmp/SWUWIFI/first.json",
                headers=headers,
                data="action=init&free_urls=",
            )
            util.syslog(
                "Captive Portal SWU",
                "init success",
            )
            gc.collect()

        except Exception:
            util.syslog(
                "Captive Portal SWU",
                "Problem open init stage of captive portal login",
            )
            return False


        try:
            loginReqest = uuurequests.request(
                "POST",
                "https://controller.access.network/portal_api.php",
                #"http://ubahndepot.com/storage/share/tmp/SWUWIFI/first.json",
                headers=headers,
                data="action=subscribe&type=one&connect_policy_accept=false&user_login=&user_password=&user_password_confirm=&email_address=&prefix=&phone=&policy_accept=false&gender=&interests=",
            )
            loginResponse = loginReqest.json()
            util.syslog(
                "Captive Portal SWU",
                "Got first stage JSON " + loginReqest.text ,
            )
            login = loginResponse["info"]["subscribe"]["login"]
            password = loginResponse["info"]["subscribe"]["password"]
            util.syslog(
                "Captive Portal SWU",
                "login: " + login + " password: " + password,
            )
            gc.collect()

        except Exception:
            util.syslog(
                "Captive Portal SWU",
                "Problem open first stage of captive portal login",
            )
            return False

        try:
            loginReqest = uuurequests.request(
                "POST",
                "https://controller.access.network/portal_api.php",
                #"http://ubahndepot.com/storage/share/tmp/SWUWIFI/second.json",
                headers=headers,
                data="action=authenticate&login="+login+"&password="+password+"&policy_accept=false&from_ajax=true&wispr_mode=false",
            )
            loginResponse = loginReqest.json()
            util.syslog(
                "Captive Portal SWU",
                "Got second stage JSON",
            )
            validity = loginResponse["user"]["validity"]["value"]
            util.syslog(
                "Captive Portal SWU",
                "validity is " + str(validity),
            )
            if (validity>10):
                util.syslog(
                    "Captive Portal SWU",
                    "SWU success",
                )
                return True
            else:
                return False
        except Exception:
            util.syslog(
                "Captive Portal SWU",
                "Problem open second stage of captive portal login",
            )
            return False

            gc.collect()

    else:
        util.syslog("Captive Portal SWU", "No captive portal in place")
        return True
