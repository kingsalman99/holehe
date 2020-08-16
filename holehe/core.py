import requests,re,mechanize,json,random,string
from bs4 import BeautifulSoup
from mechanize import Browser
try:
    import cookielib
except:
    import http.cookiejar as cookielib

from fake_useragent import UserAgent
from tqdm import tqdm
import argparse
from termcolor import colored
from threading import Thread
import queue,time

ua = UserAgent(verify_ssl=False,use_cache_server=False)

def adobe(email):
    headers = {
        'User-Agent': ua.chrome,
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'X-IMS-CLIENTID': 'adobedotcom2',
        'Content-Type': 'application/json;charset=utf-8',
        'Origin': 'https://auth.services.adobe.com',
        'DNT': '1',
        'Connection': 'keep-alive',
    }

    data = '{"username":"'+email+'","accountType":"individual"}'
    r =requests.post('https://auth.services.adobe.com/signin/v1/authenticationstate', headers=headers, data=data).json()
    if "errorCode" in str(r.keys()):
        return({"rateLimit":False,"exists":False,"emailrecovery":None,"phoneNumber":None,"others":None})
    headers = {
        'User-Agent': ua.chrome,
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'X-IMS-CLIENTID': 'adobedotcom2',
        'X-IMS-Authentication-State': r['id'],
        'DNT': '1',
        'Connection': 'keep-alive',
    }
    params = (
        ('purpose', 'passwordRecovery'),
    )
    response = requests.get('https://auth.services.adobe.com/signin/v2/challenges', headers=headers, params=params).json()
    return({"rateLimit":False,"exists":True,"emailrecovery":response['secondaryEmail'],"phoneNumber":response['securityPhoneNumber'],"others":None})
def ebay(email):

    s = requests.session()
    s.headers = {
        'User-Agent': ua.chrome,
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Origin': 'https://www.ebay.com',
        'DNT': '1',
        'Connection': 'keep-alive',
    }
    try:
        srt=s.get("https://www.ebay.com/signin/").text.split('"csrfAjaxToken":"')[1].split('"')[0]
    except IndexError as e:
        return({"rateLimit":True,"exists":None,"emailrecovery":None,"phoneNumber":None,"others":None})

    data = {
      'identifier': email,
      'srt': srt
    }

    response = s.post('https://signin.ebay.com/signin/srv/identifer', data=data).json()
    if "err" in response.keys():
        return({"rateLimit":False,"exists":False,"emailrecovery":None,"phoneNumber":None,"others":None})
    else:
        return({"rateLimit":False,"exists":True,"emailrecovery":None,"phoneNumber":None,"others":None})
def facebook(email):
    s = requests.Session()
    req = s.get('https://www.facebook.com/login/identify?ctx=recover&lwv=110')
    token = re.findall(r'"token":"([a-zA-Z0-9_-]+)"', req.text)[0]
    if not token:
        return({"rateLimit":True,"exists":None,"emailrecovery":None,"phoneNumber":None,"others":{"FullName":None,"profilePicture":None}})

    pattern = r'"_js_datr","([a-zA-Z0-9_-]+)"'
    jsdatr = re.findall(pattern, req.text)[0]
    if not jsdatr:
        return({"rateLimit":True,"exists":None,"emailrecovery":None,"phoneNumber":None,"others":{"FullName":None,"profilePicture":None}})

    data = {'lsd': token,
            'email': email,
            'did_submit': 'Search',
            '__user': 0,
            '__a': 1}
    cookies = {'_js_datr': jsdatr + ';'}
    headers = {'referer': 'https://www.facebook.com/login/identify?ctx=recover&lwv=110'}
    req = s.post('https://www.facebook.com/ajax/login/help/identify.php?ctx=recover', cookies=cookies, data=data, headers=headers)

    pattern = r'ldata=([a-zA-Z0-9-_]+)\\"'
    try:
        ldata = re.findall(pattern, req.text)[0]
    except IndexError:
        return({"rateLimit":False,"exists":False,"emailrecovery":None,"phoneNumber":None,"others":{"FullName":None,"profilePicture":None}})
    if not ldata:
        return({"rateLimit":False,"exists":False,"emailrecovery":None,"phoneNumber":None,"others":{"FullName":None,"profilePicture":None}})

    req = s.get('https://www.facebook.com/recover/initiate?ldata=%s' % ldata)
    soup = BeautifulSoup(req.content,features="lxml")
    full_name = soup.find('div', attrs={'class': 'fsl fwb fcb'})
    profile_picture = soup.find('img', attrs={'class': 'img'}).get("src")
    try:
        emailrecovery = req.text.split('</strong><br /><div>')[1].split("</div>")[0].replace("&#064;","@")
        if emailrecovery==email:
            emailrecovery=None

    except IndexError:
        emailrecovery=None
    try:
        phone = req.text.split('</strong><br /><div dir="ltr">+')[1].split("</div>")[0]
    except IndexError:
        phone=None
    if full_name == None:
        full_name = ""
    else:
        if full_name != email:
            full_name = full_name.text

    return({"rateLimit":False,"exists":True,"emailrecovery":emailrecovery,"phoneNumber":phone,"others":{"FullName":full_name,"profilePicture":profile_picture}})
def instagram(email):

    try:
        s = requests.session()
        s.headers = {
            'User-Agent': ua.chrome,
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Origin': 'https://www.instagram.com',
            'DNT': '1',
            'Connection': 'keep-alive',
        }

        freq=s.get("https://www.instagram.com/accounts/emailsignup/")
        token= freq.text.split('{"config":{"csrf_token":"')[1].split('"')[0]
        data = {
          'email': email,
          'username': '',
          'first_name': '',
          'opt_into_one_tap': 'false'
        }

        check = s.post("https://www.instagram.com/accounts/web_create_ajax/attempt/",data=data,headers={"x-csrftoken": token}).json()
        if 'email' in check["errors"].keys():
            if check["errors"]["email"][0]["code"]=="email_is_taken":
                return({"rateLimit":False,"exists":True,"emailrecovery":None,"phoneNumber":None,"others":None})
        else:
            return({"rateLimit":False,"exists":False,"emailrecovery":None,"phoneNumber":None,"others":None})
    except:
        return({"rateLimit":True,"exists":False,"emailrecovery":None,"phoneNumber":None,"others":None})
def tumblr(email):

    s = requests.session()

    s.headers = {
        'User-Agent': ua.chrome,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en,en-US;q=0.5',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    firstreq=s.get("https://www.tumblr.com/login")
    #print(firstreq.text)
    data = [
      ('determine_email', email),
      ('user[email]', ''),
      ('user[password]', ''),
      ('tumblelog[name]', ''),
      ('user[age]', ''),
      ('context', 'no_referer'),
      ('version', 'STANDARD'),
      ('follow', ''),
      ('form_key', firstreq.text.split('<meta name="tumblr-form-key" id="tumblr_form_key" content="')[1].split('"')[0]),
      ('seen_suggestion', '0'),
      ('used_suggestion', '0'),
      ('used_auto_suggestion', '0'),
      ('about_tumblr_slide', ''),
      ('random_username_suggestions', firstreq.text.split('id="random_username_suggestions" name="random_username_suggestions" value="')[1].split('"')[0]),
      ('action', 'signup_determine'),
      ('action', 'signup_determine'),
      ('tracking_url', '/login'),
      ('tracking_version', 'modal'),
    ]

    response = s.post('https://www.tumblr.com/svc/account/register', data=data)
    if response.text=='{"redirect":false,"redirect_method":"GET","errors":[],"signup_success":false,"next_view":"signup_magiclink"}':
        return({"rateLimit":False,"exists":True,"emailrecovery":None,"phoneNumber":None,"others":None})
    else:
        return({"rateLimit":False,"exists":False,"emailrecovery":None,"phoneNumber":None,"others":None})
def github(email):
    s = requests.session()
    freq = s.get("https://github.com/join")
    token_regex = re.compile(r'<auto-check src="/signup_check/username[\s\S]*?value="([\S]+)"[\s\S]*<auto-check src="/signup_check/email[\s\S]*?value="([\S]+)"')
    token = re.findall(token_regex,freq.text)
    data={"value": email, "authenticity_token": token[0]}
    #print(data)
    req = s.post("https://github.com/signup_check/email",data=data)
    if "Your browser did something unexpected." in req.text:
        return({"rateLimit":True,"exists":None,"emailrecovery":None,"phoneNumber":None,"others":None})
    if req.status_code==422:
        return({"rateLimit":False,"exists":True,"emailrecovery":None,"phoneNumber":None,"others":None})
    if req.status_code==200:
        return({"rateLimit":False,"exists":False,"emailrecovery":None,"phoneNumber":None,"others":None})
    else:
        return({"rateLimit":True,"exists":None,"emailrecovery":None,"phoneNumber":None,"others":None})
def twitter(email):
    req = requests.get("https://api.twitter.com/i/users/email_available.json",params={"email": email})
    if str(req.json()["taken"])=="True":
        return({"rateLimit":False,"exists":True,"emailrecovery":None,"phoneNumber":None,"others":None})
    else:
        return({"rateLimit":False,"exists":False,"emailrecovery":None,"phoneNumber":None,"others":None})
def pinterest(email):
    req = requests.get("https://www.pinterest.com/_ngjs/resource/EmailExistsResource/get/",params={"source_url": "/", "data": '{"options": {"email": "'+email+'"}, "context": {}}'})
    if req.json()["resource_response"]["data"]:
        return({"rateLimit":False,"exists":True,"emailrecovery":None,"phoneNumber":None,"others":None})
    else:
        return({"rateLimit":False,"exists":False,"emailrecovery":None,"phoneNumber":None,"others":None})
def lastfm(email):
    req = requests.get("https://www.last.fm/join")
    token = req.cookies["csrftoken"]
    data = {"csrfmiddlewaretoken": token, "userName": "", "email": email}
    headers = {
        "Accept": "*/*",
        "Referer": "https://www.last.fm/join",
        "X-Requested-With": "XMLHttpRequest",
        "Cookie": f"csrftoken={token}",
    }
    check = requests.post("https://www.last.fm/join/partial/validate",headers=headers,data=data).json()
    if check["email"]["valid"]:
        return({"rateLimit":False,"exists":False,"emailrecovery":None,"phoneNumber":None,"others":None})
    else:
        return({"rateLimit":False,"exists":True,"emailrecovery":None,"phoneNumber":None,"others":None})
def spotify(email):
    headers = {
        'User-Agent': ua.chrome,
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'DNT': '1',
        'Connection': 'keep-alive',
    }

    params = (
        ('validate', '1'),
        ('email', email),
    )

    req = requests.get('https://spclient.wg.spotify.com/signup/public/v1/account', headers=headers, params=params)
    if req.json()["status"] == 1:
        return({"rateLimit":False,"exists":False,"emailrecovery":None,"phoneNumber":None,"others":None})
    elif req.json()["status"] == 20:
        return({"rateLimit":False,"exists":True,"emailrecovery":None,"phoneNumber":None,"others":None})
    else:
        return({"rateLimit":True,"exists":None,"emailrecovery":None,"phoneNumber":None,"others":None})
def firefox(email):
    req = requests.post("https://api.accounts.firefox.com/v1/account/status",data={"email": email})
    if "false" in req.text:
        return({"rateLimit":False,"exists":False,"emailrecovery":None,"phoneNumber":None,"others":None})
    elif "true" in req.text:
        return({"rateLimit":False,"exists":True,"emailrecovery":None,"phoneNumber":None,"others":None})
    else:
        return({"rateLimit":True,"exists":False,"emailrecovery":None,"phoneNumber":None,"others":None})
def office365(email):
    user_agent = 'Microsoft Office/16.0 (Windows NT 10.0; Microsoft Outlook 16.0.12026; Pro)'
    headers = {'User-Agent': user_agent, 'Accept': 'application/json'}
    r = requests.get('https://outlook.office365.com/autodiscover/autodiscover.json/v1.0/{}?Protocol=Autodiscoverv1'.format(email), headers=headers, allow_redirects=False)
    if r.status_code == 200:
         return({"rateLimit":False,"exists":True,"emailrecovery":None,"phoneNumber":None,"others":None})
    else:
        return({"rateLimit":False,"exists":False,"emailrecovery":None,"phoneNumber":None,"others":None})
def live(email):
    try:
        brows = Browser()
        brows.set_handle_robots(False)
        brows._factory.is_html = True
        brows.set_cookiejar(cookielib.LWPCookieJar())
        brows.addheaders = [('User-agent',ua.firefox)]
        brows.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(),max_time=1)
        url = "https://account.live.com/password/reset"
        brows.open(url, timeout=10)
        brows.select_form(nr=0)
        brows.form['iSigninName'] = email
        brows.method = "POST"
        submit = brows.submit()
        data = json.loads(str('{"name":"'+str(submit.read().decode("utf-8")).split('"},{"name":"')[1].split('],"showExpirationCheckbox')[0]))
        if data["type"]=="Email":
            return({"rateLimit":False,"exists":True,"emailrecovery":data["name"],"phoneNumber":None,"others":None})
        elif data["type"]=="Sms":
            return({"rateLimit":False,"exists":True,"emailrecovery":None,"phoneNumber":data["name"],"others":None})
    except:
        pass

    session= requests.session()
    session.headers={
        'User-Agent': ua.firefox,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en,en-US;q=0.5',
        'Referer': 'https://account.live.com/ResetPassword.aspx',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://account.live.com',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'TE': 'Trailers',
    }

    req = session.get('https://account.live.com/password/reset')
    uaid=req.text.split('"clientTelemetry":{"uaid":"')[1].split('"')[0]
    amtcxt=req.text.split('<input type="hidden" id="amtcxt" name="amtcxt" value="')[1].split('"')[0]
    canary=req.text.split('<input type="hidden" id="canary" name="canary" value="')[1].split('"')[0]
    params = (
        ('uaid', uaid),
    )

    data = {
      'iAction': 'SignInName',
      'iRU': 'https://account.live.com/SummaryPage.aspx',
      'amtcxt': amtcxt,
      'uaid': uaid,
      'network_type': '',
      'isSigninNamePhone': 'False',
      'canary': canary,
      'PhoneCountry': '',
      'iSigninName': email
    }

    response = session.post('https://account.live.com/password/reset', params=params, data=data)
    if response.status_code==200:
        if int(str(len(response.text))[:2])<15:
            return({"rateLimit":False,"exists":False,"emailrecovery":None,"phoneNumber":None,"others":None})
        else:
            return({"rateLimit":False,"exists":True,"emailrecovery":None,"phoneNumber":None,"others":None})
    else:
        return({"rateLimit":True,"exists":False,"emailrecovery":None,"phoneNumber":None,"others":None})
def evernote(email):

    ses = requests.session()
    headers = {
        'User-Agent': ua.firefox,
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'en,en-US;q=0.5',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
        'Origin': 'https://www.evernote.com',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Referer': 'https://www.evernote.com/Login.action',
        'TE': 'Trailers',
    }
    ses.headers=headers
    data = ses.get("https://www.evernote.com/Login.action")
    data = {
      'username': email,
      'evaluateUsername': '',
      'hpts': data.text.split('document.getElementById("hpts").value = "')[1].split('"')[0],
      'hptsh': data.text.split('document.getElementById("hptsh").value = "')[1].split('"')[0],
      'analyticsLoginOrigin': 'login_action',
      'clipperFlow': 'false',
      'showSwitchService': 'true',
      'usernameImmutable': 'false',
      '_sourcePage': data.text.split('<input type="hidden" name="_sourcePage" value="')[1].split('"')[0],
      '__fp': data.text.split('<input type="hidden" name="__fp" value="')[1].split('"')[0]
    }
    response = ses.post('https://www.evernote.com/Login.action', data=data)
    if "usePasswordAuth" in response.text:
        return({"rateLimit":False,"exists":True,"emailrecovery":None,"phoneNumber":None,"others":None})
    elif "displayMessage" in response.text:
        return({"rateLimit":False,"exists":False,"emailrecovery":None,"phoneNumber":None,"others":None})
    else:
        return({"rateLimit":True,"exists":False,"emailrecovery":None,"phoneNumber":None,"others":None})
def amazon(email):
    brows = Browser()
    brows.set_handle_robots(False)
    brows._factory.is_html = True
    brows.set_cookiejar(cookielib.LWPCookieJar())
    brows.addheaders = [('User-agent',ua.chrome)]
    brows.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(),max_time=1)
    url = "https://www.amazon.com/ap/signin?openid.pape.max_auth_age=0&openid.return_to=https%3A%2F%2Fwww.amazon.com%2F%3F_encoding%3DUTF8%26ref_%3Dnav_ya_signin&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.assoc_handle=usflex&openid.mode=checkid_setup&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0&"
    brows.open(url, timeout=10)
    brows.select_form(nr=0)
    brows.form['email'] = email

    brows.method = "POST"
    submit = brows.submit()
    soup = BeautifulSoup(submit.read().decode("utf-8"),"lxml")
    if soup.find("div", {"id": "auth-password-missing-alert"}):
        return({"rateLimit":False,"exists":True,"emailrecovery":None,"phoneNumber":None,"others":None})
    else:
        return({"rateLimit":False,"exists":False,"emailrecovery":None,"phoneNumber":None,"others":None})
def lastpass(email):
    headers = {
        'User-Agent': ua.firefox,
        'Accept': '*/*',
        'Accept-Language': 'en,en-US;q=0.5',
        'Referer': 'https://lastpass.com/',
        'X-Requested-With': 'XMLHttpRequest',
        'DNT': '1',
        'Connection': 'keep-alive',
        'TE': 'Trailers',
    }
    params = (
        ('check', 'avail'),
        ('skipcontent', '1'),
        ('mistype', '1'),
        ('username', email),
    )

    response = requests.get('https://lastpass.com/create_account.php', params=params,headers=headers)
    if response.text=="no":
        return({"rateLimit":False,"exists":True,"emailrecovery":None,"phoneNumber":None,"others":None})
    if response.text=="ok" or response.text=="emailinvalid":
        return({"rateLimit":False,"exists":False,"emailrecovery":None,"phoneNumber":None,"others":None})
    else:
        return({"rateLimit":True,"exists":False,"emailrecovery":None,"phoneNumber":None,"others":None})
def aboutme(email):

    s = requests.session()
    reqToken = s.get("https://about.me/signup",headers={'User-Agent': ua.firefox}).text.split(',"AUTH_TOKEN":"')[1].split('"')[0]

    headers = {
        'User-Agent': ua.firefox,
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'en-US,en;q=0.5',
        'X-Auth-Token': reqToken,
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'Origin': 'https://about.me',
        'Connection': 'keep-alive',
        'TE': 'Trailers',
    }

    data = '{"user_name":"","first_name":"","last_name":"","allowed_features":[],"counters":{"id":"counters"},"settings":{"id":"settings","compliments":{"id":"compliments"},"follow":{"id":"follow"},"share":{"id":"share"}},"email_address":"'+email+'","honeypot":"","actions":{"id":"actions"},"apps":[],"contact":{"id":"contact"},"contact_me":{"id":"contact_me"},"email_channels":{"id":"email_channels"},"flags":{"id":"flags"},"images":[],"interests":[],"jobs":[],"layout":{"version":1,"id":"layout","color":"305B90"},"links":[],"locations":[],"mapped_domains":[],"portfolio":[],"roles":[],"schools":[],"slack_teams":[],"spotlight":{"type":null,"text":null,"url":null,"id":"spotlight"},"spotlight_trial":{"type":null,"text":null,"url":null,"id":"spotlight_trial"},"store":{"id":"store","credit_card":{"number":"","exp_month":"","exp_year":"","cvc":"","address_zip":"","last4":"","id":"credit_card"},"charges":[],"purchases":[]},"tags":[],"testimonials":{"header":"0","id":"testimonials","items":[]},"video":{"id":"video"},"signup":{"id":"signup","step":"email","method":"email"}}'

    response = s.post('https://about.me/n/signup', headers=headers, data=data)
    if response.status_code==409:
            return({"rateLimit":False,"exists":True,"emailrecovery":None,"phoneNumber":None,"others":None})
    elif response.status_code==200:
            return({"rateLimit":False,"exists":False,"emailrecovery":None,"phoneNumber":None,"others":None})
    else:
        return({"rateLimit":True,"exists":False,"emailrecovery":None,"phoneNumber":None,"others":None})
def discord(email):
    def get_random_string(length):
        letters = string.ascii_lowercase
        result_str = ''.join(random.choice(letters) for i in range(length))
        return(result_str)

    headers = {
        'User-Agent': ua.firefox,
        'Accept': '*/*',
        'Accept-Language': 'en-US',
        'Content-Type': 'application/json',
        'Origin': 'https://discord.com',
        'DNT': '1',
        'Connection': 'keep-alive',
        'TE': 'Trailers',
    }

    data = '{"fingerprint":"","email":"'+email+'","username":"'+get_random_string(20)+'","password":"'+get_random_string(20)+'","invite":null,"consent":true,"date_of_birth":"","gift_code_sku_id":null,"captcha_key":null}'

    response = requests.post('https://discord.com/api/v8/auth/register', headers=headers, data=data)
    responseData=response.json()
    try:
        if "code" in responseData.keys():
            if str(responseData["code"])=="50035":
                try:
                    if responseData["errors"]["email"]["_errors"][0]['code']=="EMAIL_ALREADY_REGISTERED":
                        return({"rateLimit":False,"exists":True,"emailrecovery":None,"phoneNumber":None,"others":None})
                except:
                    return({"rateLimit":True,"exists":False,"emailrecovery":None,"phoneNumber":None,"others":None})
        elif responseData["captcha_key"][0]=="captcha-required":
            return({"rateLimit":False,"exists":False,"emailrecovery":None,"phoneNumber":None,"others":None})
        else:
            return({"rateLimit":True,"exists":False,"emailrecovery":None,"phoneNumber":None,"others":None})
    except:
        return({"rateLimit":True,"exists":False,"emailrecovery":None,"phoneNumber":None,"others":None})

def yahoo(email):
    s = requests.session()
    headers = {
        'User-Agent': ua.firefox,
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://login.yahoo.com',
        'DNT': '1',
        'Connection': 'keep-alive',
    }
    req = s.get("https://login.yahoo.com",headers=headers)

    headers = {
        'User-Agent': ua.firefox,
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'bucket': 'mbr-fe-merge-manage-account',
        'X-Requested-With': 'XMLHttpRequest',
        'Origin': 'https://login.yahoo.com',
        'DNT': '1',
        'Connection': 'keep-alive',
    }

    params = (
        ('.src', 'fpctx'),
        ('.intl', 'ca'),
        ('.lang', 'en-CA'),
        ('.done', 'https://ca.yahoo.com'),
    )
    try:
        data = {
          'acrumb': req.text.split('<input type="hidden" name="acrumb" value="')[1].split('"')[0],
          'sessionIndex': req.text.split('<input type="hidden" name="sessionIndex" value="')[1].split('"')[0],
          'username': email,
          'passwd': '',
          'signin': 'Next',
          'persistent': 'y'
        }

        response = s.post('https://login.yahoo.com/', headers=headers, params=params, data=data)
        response=response.json()
        if "error" in response.keys():
            if response["error"]==False:
                return({"rateLimit":False,"exists":True,"emailrecovery":None,"phoneNumber":None,"others":None})
            else:
                return({"rateLimit":True,"exists":False,"emailrecovery":None,"phoneNumber":None,"others":None})
        elif "render" in response.keys():
            if response["render"]["error"]=="messages.ERROR_INVALID_USERNAME":
                return({"rateLimit":False,"exists":False,"emailrecovery":None,"phoneNumber":None,"others":None})
            else:
                return({"rateLimit":True,"exists":False,"emailrecovery":None,"phoneNumber":None,"others":None})
        else:
            return({"rateLimit":True,"exists":False,"emailrecovery":None,"phoneNumber":None,"others":None})
    except:
            return({"rateLimit":True,"exists":False,"emailrecovery":None,"phoneNumber":None,"others":None})
def vrbo(email):
    headers = {
        'User-Agent': ua.firefox,
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Content-Type': 'application/json',
        'x-homeaway-site': 'vrbo',
        'Origin': 'https://www.vrbo.com',
        'DNT': '1',
        'Connection': 'keep-alive',
        'TE': 'Trailers',
    }

    data = '{"emailAddress":"'+email+'"}'

    response = requests.post('https://www.vrbo.com/auth/aam/v3/status', headers=headers, data=data)
    response=response.json()

    if "authType" in response.keys():
        if response["authType"][0]=="LOGIN_UMS":
            return({"rateLimit":False,"exists":True,"emailrecovery":None,"phoneNumber":None,"others":None})
        elif response["authType"][0]=="SIGNUP":
            return({"rateLimit":False,"exists":False,"emailrecovery":None,"phoneNumber":None,"others":None})
        else:
            return({"rateLimit":True,"exists":False,"emailrecovery":None,"phoneNumber":None,"others":None})
    else:
        return({"rateLimit":True,"exists":False,"emailrecovery":None,"phoneNumber":None,"others":None})
def main():
    start_time = time.time()
    parser = argparse.ArgumentParser(description="Github : https://github.com/megadose/holehe")
    requiredNamed = parser.add_argument_group('required named arguments')
    parser.add_argument("-e", "--email", help="Email of the target",required=True)
    args = parser.parse_args()

    def websiteName(WebsiteFunction,Websitename,email):
        return({Websitename:WebsiteFunction(email)})

    websites=[aboutme,adobe,amazon,discord,ebay,evernote,facebook,firefox,github,instagram,lastfm,lastpass,live,office365,pinterest,spotify,tumblr,twitter,vrbo,yahoo]

    que = queue.Queue()
    infos ={}
    threads_list = []

    for website in websites:
        t = Thread(target=lambda q, arg1: q.put(websiteName(website,website.__name__,args.email)), args=(que, website))
        t.start()
        threads_list.append(t)

    for t in tqdm(threads_list):
        t.join()


    while not que.empty():
        result = que.get()
        key, value = next(iter(result.items()))
        infos[key]=value

    description = colored("Email used","green")+","+colored(" Email not used","magenta")+","+colored(" Rate limit","red")
    print("\033[H\033[J")
    print("*"*25)
    print(args.email)
    print("*"*25)
    for i in sorted(infos):
        key, value = i,infos[i]
        i = value
        if i["rateLimit"]==True:
            websiteprint=colored(key,"red")
        elif i["exists"]==False :
            websiteprint=colored(key,"magenta")
        else:
            toprint=""
            if i["emailrecovery"]!= None:
                toprint+=" "+i["emailrecovery"]
            if i["phoneNumber"]!= None:
                toprint+=" / "+i["phoneNumber"]
            if i["others"]!= None:
                toprint+=" / FullName "+i["others"]["FullName"]

            websiteprint=colored(str(key)+toprint,"green")
        print(websiteprint)

    print("\n"+description)
    print(str(len(websites))+" websites checked in "+str(round(time.time() - start_time,2))+ " seconds")
