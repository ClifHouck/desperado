import time
import requests
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP, PKCS1_v1_5
from PIL import Image
from io import BytesIO
import base64

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

def get_current_captcha_gid():
    result = requests.get(LOGIN_API['refresh_captcha']['url'])
    return result.json()['gid']

def get_captcha_image(gid):
    result = requests.get(LOGIN_API['captcha_img']['url'], params = {'gid': gid}) 
    return Image.open(BytesIO(result.content))

def get_rsa_key(username):
    payload = { 'donotcache' : int(time.time()), 'username' : username }
    result = requests.post(LOGIN_API['get_rsa_key']['url'], data=payload)
    return result.json()

def get_encrypted_password(password, rsa_mod, pub_exp):
    """ Encrypts a Steam password for web login using RSA with PKCS1_v1_5. 
        Returns the base64 encoded ciphertext since that's what Steam's login endpoint wants. """
    public_key = RSA.construct((rsa_mod, pub_exp))
    cipher = PKCS1_v1_5.new(public_key)
    ciphertext = cipher.encrypt(bytes(password, 'utf_8'))
    return base64.b64encode(ciphertext)

def do_login(username, encrypted_password, rsa_timestamp, 
             email_auth = '', captcha_gid = '', captcha_text = ''):
    payload = {
            'username'       : username,
            'password'       : encrypted_password,
            'twofactorcode'  : '',
            'emailauth'      : email_auth,
            'loginfriendlyname' : 'Maya Firefox',
            'captchagid'     : captcha_gid,
            'captcha_text'   : captcha_text,
            'emailsteamid'   : '',
            'rsatimestamp'   : rsa_timestamp,
            'remember_login' : 'false'
   }
    result = requests.post(LOGIN_API['do_login']['url'], data=payload)
    return result.json()

def solve_captcha_manual(gid):
    """ Default manual function for solving the Steam login captcha. """
    image = auth.get_captcha_image(gid)
    # FIXME: Use Python's temp file interface.
    image.save("./test.png")
    webbrowser.open_new_tab("./test.png")
    text = input('solve_captcha --->')
    return text

def get_steamguard_code_manual(email_address = ''):
    """ Default manual method for getting the SteamGuard code required by protected Steam accounts. """
    code = input('get_steamguard_code[' + email_address + '] --->')
    return code

def login(username, password, 
          get_steamguard_code = get_steamguard_code_manual, 
          solve_captcha       = solve_captcha_manual,
          max_tries = 5):
    """ Provides a full login sequence to the Steam website. """
    response_dict = auth.get_rsa_key(username)

    # The RSA information is encoded as hex strings.
    # Transform to integers.
    rsa_mod = int(response_dict['publickey_mod'], 16)
    pub_exp = int(response_dict['publickey_exp'], 16)

    encrypted_password = auth.get_encrypted_password(password, rsa_mod, pub_exp)
    timestamp = response_dict['timestamp']

    gid = ''
    text = ''
    email_auth = ''
    are_we_logged_in = False
    tries = 0
    while not are_we_logged_in and tries < max_tries:
        tries += 1
        response_dict = auth.do_login(username, encrypted_password, timestamp, email_auth, gid, text)
        if 'captcha_needed' in response_dict:
            text = solve_captcha(gid)
        elif 'emailauth_needed' in response_dict:
            email_auth = get_steamguard_code_manual()
        elif 'success' in response_dict and response_dict['success']:
            are_we_logged_in = True
        else:
            print response_dict
            raise Exception("I don't understand this state!")

    if tries >= max_tries:
        raise Exception("Too many tries!")

    return response_dict
         
