import copy
import requests
import math
import unittest
import urllib
import re
from lxml import html

from desperdao import currency

import pdb

class RequestFailure(Exception):
    def __init__(self, reason, arguments):
        self.reason    = reason
        self.arguments = arguments

class ItemPriceOverviewRetreivalFailure(RequestFailure):
    pass


# FIXME: Need a way to invalidate old data.
class PriceDataCache(object):
    def __init__(self, session):
        self.__session = session
        self.__cache = {}
    
    def get_data(self, app_id, market_hash_name):
        if (app_id, market_hash_name) not in self.__cache:
            return None
        return self.__cache[(app_id, market_hash_name)]

    def set_data(self, app_id, market_hash_name, data):
        self.__cache[(app_id, market_hash_name)] = data

class ItemPriceData(object):
    def __init__(self, low_price, volume, median_price):
        self.low_price    = currency.Dollars.from_string(low_price)
        self.volume       = volume
        self.median_price = currency.Dollars.from_string(median_price)

    def __str__(self):
        return " ".join(["Low:", str(self.low_price), 
                         "Median:", str(self.median_price), 
                         "Volume:", str(self.volume)])

# FIXME: Abstract out caching functionality.
def get_item_price_overview(session, app_id, market_hash_name, country = "US", currency = 1):
    # Init cache if it hasn't been yet.
    if not hasattr(get_item_price_overview, 'PRICE_DATA_CACHE'):
        get_item_price_overview.PRICE_DATA_CACHE = PriceDataCache(session)

    # See if we've already made the request. If so, return that data.
    cached_data = get_item_price_overview.PRICE_DATA_CACHE.get_data(app_id, market_hash_name)
    if cached_data != None:
        return cached_data

    result = session.requests_session.get('https://steamcommunity.com/market/priceoverview/', params = {
            'country'  : country,
            'currency' : currency,
            'appid'    : app_id,
            'market_hash_name' : market_hash_name})

    json_dict = result.json()

    if not json_dict['success']:
        raise ItemPriceOverviewRetreivalFailure("item_price_overview: Got failure!", 
                (session, app_id, market_hash_name, country, currency))

    if ('volume' not in json_dict or
        'median_price' not in json_dict):
        data = ItemPriceData(json_dict['lowest_price'], 0, "$0.00")
    else:
        print(json_dict)
        data = ItemPriceData(json_dict['lowest_price'], json_dict['volume'], json_dict['median_price'])

    get_item_price_overview.PRICE_DATA_CACHE.set_data(app_id, market_hash_name, data)

    return data

# TODO: Flesh out.
class ItemPriceHistory(object):
    def __init__(self, json_dict):
        self.json_dict = json_dict

class ItemPriceHistoryRetreivalFailure(RequestFailure):
    pass

# XXX: Use with caution, this returns about 50KB worth of data per call.
# Probably call this once and store in a database and periodically refresh.
def get_item_price_history(session, app_id, market_hash_name):
    result = session.requests_session.get('https://steamcommunity.com/market/pricehistory/', params = {
                'appid' : app_id,
                # FIXME: In the javascript for this endpoint, it defaults to the 'market_name' if 'market_hash_name' is undefined...
                'market_hash_name' : market_hash_name})

    json_dict = result.json()

    if not json_dict['success']: 
        raise ItemPriceHistoryRetreivalFailure("get_item_price_history: Got failure response!",
                (session, app_id, market_hash_name))

    return ItemPriceHistory(json_dict) 

class ItemSaleError(RequestFailure):
    pass

def post_item_for_sale(session, item, price_in_cents):
    """ price_in_cents - The price (before fees!) to post the item at. """
    headers = {
            'Referer'    : 'https://steamcommunity.com/profiles/' + str(session.profile_id()) + '/inventory',
            'User-Agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2062.120 Safari/537.36'
    }
    session_id = copy.deepcopy(session.requests_session.cookies['sessionid'])
    session_id = urllib.parse.unquote(session_id)
    payload = { 'sessionid' : session_id,
                'appid'     : int(item.app_id()),
                'contextid' : 2, # TODO: Why is this 2? Is that inventory context?
                'assetid'   : item.id(),
                'amount'    : 1, # TODO: Is this ever not 1?
                'price'     : price_in_cents}

    result = session.requests_session.post('https://steamcommunity.com/market/sellitem/', headers = headers, data = payload)

    if result.status_code != 200:
        pdb.set_trace()
        raise ItemSaleError("post_item_for_sale: Item sale request error!",
                (session, item, price_in_cents, result))

    return result

class MarketListing(object):
    def __init__(self, listing_id, item_name, item_link, game_name):
        self.id         = listing_id
        self.item_name  = item_name
        self.item_link  = item_link
        self.game_name  = game_name

    def __str__(self):
        return "".join(["[", str(self.id), "]: ", self.item_name])

def get_current_listings(session):
    page = session.requests_session.get('https://steamcommunity.com/market/')
    tree = html.fromstring(page.text)
    listing_divs = tree.xpath('//div[@class="market_listing_item_name_block"]') 

    listings = []
    for div in listing_divs:
        name_id = div[0].attrib['id']
        listing_id = re.search("(\d+)", name_id).group(1)
    
        try: 
            item_anchor = div[0][0]
        except IndexError:
            continue

        item_link = item_anchor.attrib['href']
        item_name = item_anchor.text
        game_name = div[2].text
        listings.append(MarketListing(listing_id, item_name, item_link, game_name))

    return listings

class ListingRemovalError(RequestFailure):
    pass

def remove_listing(session, listing_id):
    headers = {
            'referer'    : 'https://steamcommunity.com/market/',
            'User-Agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2062.120 Safari/537.36'
    }

    session_id = copy.deepcopy(session.requests_session.cookies['sessionid'])
    session_id = urllib.parse.unquote(session_id)
    payload = { 'sessionid' : session_id }
    result = session.requests_session.post('https://steamcommunity.com/market/removelisting/' + str(listing_id), 
                headers = headers, data = payload)

    if result.status_code != 200:
        raise ListingRemovalError("remove_listing: Failed to remove listing.",
                (session, listing_id, result))

    return result

WALLET_MINIMUM_FEE    = 1
WALLET_BASE_FEE       = 0
PUBLISHER_MINIMUM_FEE = 1

def get_desired_price(total_price_in_cents,
        steam_fee_percent = 0.05,
        publisher_fee_percent = 0.10):
    """ Get the desired list price to achieve the total_price_cents """
    desired_price = math.ceil(total_price_in_cents / (1 + steam_fee_percent + publisher_fee_percent))
    steam_fee, publisher_fee = calculate_fees(desired_price)

    calculated_total = desired_price + steam_fee + publisher_fee

    difference = total_price_in_cents - calculated_total

    if difference == 0:
        return desired_price
    # Handle off by one case
    elif difference == 1:
        return desired_price + 1
    # Here one or more fees are too small.
    elif difference < 0:
        return total_price_in_cents - max(steam_fee, WALLET_MINIMUM_FEE) - max(publisher_fee, PUBLISHER_MINIMUM_FEE)
    else:
        raise Exception("get_desired_price: Could not properly calculate the desired amount! Difference: " + str(difference))

def calculate_fees(price_in_cents, 
        steam_fee_percent = 0.05, 
        publisher_fee_percent = 0.10):
    steam_fee = math.floor(max(price_in_cents * steam_fee_percent, 
                               WALLET_MINIMUM_FEE) 
                           + WALLET_BASE_FEE)
    publisher_fee = 0 
    if publisher_fee_percent > 0.0:
       publisher_fee = math.floor(max(price_in_cents * publisher_fee_percent, 
                                      PUBLISHER_MINIMUM_FEE))

    return (steam_fee, publisher_fee)

class TestDesiredPriceFunction(unittest.TestCase):
    def test_desired_price_calculation(self):
        """ Tests that we can extract the desired price from the total price 
            using get_desired_price, and knowing some basics about the 
            fees associated with using the market. """
        for desired_price in range(1, 40000):
            steam_fee, publisher_fee = calculate_fees(desired_price)
            total_price = desired_price + steam_fee + publisher_fee
            calculated_desired_price = get_desired_price(total_price)
            self.assertEqual(desired_price, calculated_desired_price)
            
if __name__ == '__main__':
    unittest.main()
