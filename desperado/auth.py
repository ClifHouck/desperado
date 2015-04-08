from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA
from PIL import Image
from io import BytesIO
from lxml import html
import base64
import email
import imaplib
import os
import pickle
import re
import requests
import time


LOGIN_API = {
        'refresh_captcha' : {
            'url'    : 'https://store.steampowered.com/join/refreshcaptcha/',
            'method' : 'GET'
        },
        'captcha_img' : {
            'url'       : 'https://store.steampowered.com/public/captcha.php',
            'method'    : 'GET',
            'parameters' : {
                'gid' : 'The gid of the captcha to retrieve.'
            }
        },
        'get_rsa_key' : {
            'url'         : 'https://steamcommunity.com/login/getrsakey/',
            'method'      : 'POST',
            'parameters'  : { 
                'username'   : 'The user\'s login name.',
                'donotcache' : 'The current time as returned by JS Date().getTime() method.'
            },
            'return_type' : 'JSON',
            'return_keys' : {
                'publickey_mod' : 'RSA modulus number',
                'publickey_exp' : 'RSA modulus exponent',
                'timestamp'     : 'Server\'s timestamp',
                'success'       : 'Did the request succeed?',
                'token_gid'     : 'Not sure yet.'
            }
        },
        'do_login' : {
            'url'         : 'https://steamcommunity.com/login/dologin/',
            'method'      : 'POST',
            'parameters'  : { 
                'password'          : 'Encrypted user password. See \'get_rsa_key\'.',
                'username'          : 'The user\'s login name.',
                'twofactorcode'     : 'Probably if two-factor authentication is enabled for the Steam account.',
                'emailauth'         : 'The emailed authorization code.',
                'loginfriendlyname' : "The 'friendly name' for the computer/browser logging into this account.",
                'captchagid'        : '???',
                'captcha_text'      : 'Probably necesary text if Steam presented us with a CAPTCHA.',
                'emailsteamid'      : '???',
                'rsatimestamp'      : 'timestamp returned by call to get_rsa_key API point.',
                'remember_login'    : 'Probably want to set this to true.',
                'donotcache'        : 'The current time as returned by JS Date().getTime() method.'

            },
            'return_type' : 'JSON',
            'return_keys' : {
                'login_complete'        : 'Did we succeed in logging in?',
                'requires_twofactor'    : 'Is two-factor authentication required?',
                'success'               : 'Was the request successful?',
                'transfer_parameters'   : {
                    'auth'           : '?',
                    'remember_login' : 'Reflects the input for this API point.',
                    'steamid'        : 'User\'s Steam ID.',
                    'token'          : 'User\'s login token.',
                    'token_secure'   : 'User\'s secure login token.'
                }
            }
        }
}

def __save_authorized_session(session):
    filename = session.username + ".session"
    with open(filename, 'wb') as outfile:
        pickle.dump(session, outfile)

def __load_authorized_session(username):
    filename = username + ".session"
    if not os.path.isfile(filename):
        return None
    with open(filename, 'rb') as infile:
        session = pickle.load(infile)
        return session

def get_current_captcha_gid():
    result = requests.get(LOGIN_API['refresh_captcha']['url'])
    return result.json()['gid']

def get_captcha_image(gid):
    result = requests.get(LOGIN_API['captcha_img']['url'], params = {'gid': gid}) 
    return Image.open(BytesIO(result.content))

def get_rsa_key(session, username):
    payload = { 'donotcache' : int(time.time()), 'username' : username }
    result = session.requests_session.post(LOGIN_API['get_rsa_key']['url'], data=payload)
    return result.json()

def get_encrypted_password(password, rsa_mod, pub_exp):
    """ Encrypts a Steam password for web login using RSA with PKCS1_v1_5. 
        Returns the base64 encoded ciphertext since that's what Steam's login endpoint wants. """
    public_key = RSA.construct((rsa_mod, pub_exp))
    cipher = PKCS1_v1_5.new(public_key)
    ciphertext = cipher.encrypt(bytes(password))
    return base64.b64encode(ciphertext)

def do_login(session, username, encrypted_password, rsa_timestamp, 
             email_auth = '', captcha_gid = '', captcha_text = '', login_friendly_name = 'friendlyname'):
    payload = {
            'username'       : username,
            'password'       : encrypted_password,
            'twofactorcode'  : '',
            'emailauth'      : email_auth,
            'loginfriendlyname' : login_friendly_name,
            'captchagid'     : captcha_gid,
            'captcha_text'   : captcha_text,
            'emailsteamid'   : '',
            'rsatimestamp'   : rsa_timestamp,
            'remember_login' : 'false'
   }
    result = session.requests_session.post(LOGIN_API['do_login']['url'], data=payload)
    return result.json()

def solve_captcha_manual(gid):
    """ Default manual function for solving the Steam login captcha. """
    image = get_captcha_image(gid)
    # TODO: Use Python's temp file interface.
    image.save("./test.png")
    # webbrowser.open_new_tab("./test.png")
    text = input('solve_captcha --->')
    return text

def get_steamguard_code_manual(email_address = ''):
    """ Default manual method for getting the SteamGuard code required by protected Steam accounts. """
    code = input('get_steamguard_code[' + email_address + '] --->')
    return code

def get_steamguard_code_automated_imap(server, login, password, 
                                       mailbox_location = "INBOX.Steam",
                                       max_tries = 10,
                                       poll_wait = 6):
    """ Automated method to get SteamGuard code. """
    AUTH_CODE_REGEX = "<h2>([0-9A-Z]+)</h2>"

    mail = imaplib.IMAP4_SSL(server)
    mail.login(login, password)
    
    # TODO: Is there a more robust way to check?
    # Polling works but an event-driven model would be nicer.
    tries = 0
    latest_email_uid = 0
    while latest_email_uid == 0 and tries < max_tries:
        tries += 1
        # It seems we need to re-select the location to get fresh results from the search.
        result, data = mail.uid('SEARCH', None,
                '(UNSEEN FROM "noreply@steampowered.com" SUBJECT "Access from new device")')
        if result != 'OK':
            raise Exception("Got '%(result)s' result when trying "
                            "to search for emails." % {'result': result})
        if len(data) and len(data[0]):
            latest_email_uid = data[0].split()[-1]
        time.sleep(poll_wait)
    
    if latest_email_uid == 0:
        raise Exception("get_steamguard_code_automated: Timed out waiting for SteamGuard message.")
    
    result, data = mail.uid('fetch', latest_email_uid, '(RFC822)')
    mail.logout()

    # Extract the code from the email's body.
    raw_email = data[0][1]
    message = email.message_from_string(raw_email)

    match = re.search(AUTH_CODE_REGEX, message.as_string())
    auth_code = None
    if match:
        auth_code = match.group(1)
    else:
        raise Exception("get_steamguard_code_automated_imap: Couldn't find SteamGuard code in email!")

    return auth_code

class Session(object):
    def __init__(self, username):
        self.username           = username
        self.requests_session   = requests.Session()
        self.__profile_id       = None
        self.__wallet_balance   = None

    def __scrape_steam_homepage(self):
        """ Scrapes useful information about user from Steam's homepage. """
        # TODO: Abstract scraping into different page classes/objects.
        page = self.requests_session.get("https://steamcommunity.com/")
        tree = html.fromstring(page.text)
        profile_url = tree.xpath('//a[@class="menuitem supernav username"]')[0].attrib['href']
        self.__profile_id = re.search("\/(\d+)\/", profile_url).group(1)
        # TODO: Massage down to a number.
        # wallet_balance_raw = tree.xpath('//a[@id="header_wallet_balance"]/text()')[0]
        # self.__wallet_balance = wallet_balance_raw
        # for string in [self.wallet_balance, self.profile_id]:
        # print(string)

    # FIXME: TODO: We need a way to validate that the session is still good. 
    # and if it's not, then log back in.
    def __validate_session(self):
        pass

    def wallet_balance(self):
        if not hasattr(self, '__wallet_balance') or self.__wallet_balance == None:
            self.__scrape_steam_homepage()
        return self.__wallet_balance

    def profile_id(self):
        if not hasattr(self, '__profile_id') or self.__profile_id == None:
            self.__scrape_steam_homepage()
        return self.__profile_id


class InvalidLoginState(Exception):
    def __init__(self, reason, response_json_dict):
        self.reason             = reason
        self.response_json_dict = response_json_dict

# FIXME: Should this be put into the Session object itself?
def login(username, password, 
          get_steamguard_code = get_steamguard_code_manual, 
          solve_captcha       = solve_captcha_manual,
          max_tries = 5):
    """ Provides a fully automated login sequence to the Steam website. Depends on automated
        functions being passed. Returns a Session object.
        username - Steam username
        password - Plaintext Steam password 
        get_steamguard_code - A function taking no arguments that retrieves the steamguard code
                              for this account.
        solve_captcha       - A function taking 1 argument - The current captcha's gid.
        max_tries           - The maximum  number of times to try to login. If we keep failing 
                              the captcha or steamguard authentication then this function will 
                              eventually bail."""

    # Try to load the cached session information.
    # FIXME: What if this has expired?
    try:
        session = __load_authorized_session(username)
    except ValueError:
        print("Couldn't load old session!")
        session = None
        
    if session != None:
        return session

    session = Session(username)

    response_dict = get_rsa_key(session, username)

    # The RSA information is encoded as hex strings.
    # Transform to integers.
    rsa_mod = long(response_dict['publickey_mod'], 16)
    pub_exp = long(response_dict['publickey_exp'], 16)

    encrypted_password = get_encrypted_password(password, rsa_mod, pub_exp)
    timestamp = response_dict['timestamp']

    gid = ''
    text = ''
    email_auth = ''
    tries = 0
    while tries < max_tries:
        tries += 1
        response_dict = do_login(session, username, encrypted_password, timestamp, email_auth, gid, text)
        if 'captcha_needed' in response_dict:
            text = solve_captcha(gid)
        elif 'emailauth_needed' in response_dict:
            email_auth = get_steamguard_code()
        elif 'success' in response_dict and response_dict['success']:
            break
        else:
            raise InvalidLoginState("I don't understand this state!", response_dict)

    if tries >= max_tries:
        raise Exception("Too many tries!")

    # Save the new session for later use.
    __save_authorized_session(session)

    return session
