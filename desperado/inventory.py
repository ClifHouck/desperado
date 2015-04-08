import requests

from desperado import market

INVENTORY_API = {
        'application_inventory' : {
            'url' : "https://steamcommunity.com/profiles/{profile_id}/inventory/json/{app_id}/{context_id}/",
            'url_args' : {
                'profile_id' : 'The ID of the user\'s profile in question.',
                'app_id'     : 'The ID of the application to get the inventory for.',
                'context_id' : '???'
             },
            'method' : 'GET'
         }
}

class InventoryIterator(object):
    def __init__(self, inventory_obj):
        self.index = -1
        self.length = len(inventory_obj.items)
        self.items = inventory_obj.items

    def next(self):
        self.index += 1
        if self.index >= self.length:
            raise StopIteration("No more items in the inventory!")
        return self.items[self.index]

    def __iter__(self):
        return self
        

class Inventory(object):
    def __init__(self, profile_id, items):
        self.profile_id = profile_id
        self.items      = items

    def __iter__(self):
        return InventoryIterator(self)

class InventoryItem(object):
    def __init__(self, id_json, description_json):
        self._id_json = id_json
        self._description_json = description_json
        self.tags = {}
        self.__parse_tags()
        self.price_data = None

    def __str__(self):
        market_name = str(''.join([c for c in self.market_name() if ord(c) < 128]))
        return ' '.join([str(self.id()), ":", market_name, "-",
                         "Tradable" if self.can_trade() else "Not tradable"  ])

    def get_price_data(self, session):
        if not self.can_trade():
            # TODO: This feels a bit gnarly. We are reaching into the market module.
            # Maybe we need to integrate the price data directly into the inventory item object.
            return market.ItemPriceData("$0.00", 0, "$0.00")

        self.price_data = market.get_item_price_overview(session, self.app_id(), self.market_hash_name())
        return self.price_data

    def __parse_tags(self):
        for tag in self._description_json['tags']:
            self.tags[tag['category']] = tag['name']

    def has_tag(self, category):
        return category in self.tags

    def tag_contains(self, category, search_str):
        if self.has_tag(category):
            return search_str.lower() in self.tags[category].lower()
        return False

    def id(self):
        return self._id_json['id']

    def instance_id(self):
        return self._id_json['instanceid']

    def class_id(self):
        return self._id_json['classid']

    def app_id(self):
        return self._description_json['appid']

    # TODO: Is this ever greater than 1?
    def amount(self):
        return self._id_json['amount']

    # TODO: Does the market_hash_name always equal the market_name?
    def market_name(self):
        return self._description_json['market_name']

    # FIXME: May need to default to the 'market_name' if this is undefined.
    def market_hash_name(self):
        return self._description_json['market_hash_name']

    def can_trade(self):
        return int(self._description_json['tradable']) == 1

def __build_inventory_get_url(profile_id, app_id, context_id):
    return "/".join(["https://steamcommunity.com/profiles", str(profile_id), "inventory/json", str(app_id), str(context_id)]) + "/"

class InventoryRetrievalError(Exception):
    def __init__(self, reason, arguments, response):
        self.reason     = reason
        self.arguments  = arguments
        self.response   = response

# TODO: I don't know why context_id should be 2...
def retrieve_profile_inventory(session, app_id, context_id = 2):
    # FIXME: Handle cases where we need to retrieve more...
    profile_id = session.profile_id()
    url = __build_inventory_get_url(profile_id, app_id, context_id)
    result = session.requests_session.get(url) 
    result_dict = result.json()

    if result_dict['more']:
        raise InventoryRetrievalError('retrieve_profile_inventory: More inventory available! NOT IMPLEMENTED YET!',
                                      (session, profile_id, app_id, context_id),
                                      result_dict)

    if not result_dict['success']:
        raise InventoryRetrievalError('retrieve_inventory: Could not retrieve inventory!', 
                                      (session, profile_id, app_id, context_id),
                                      result_dict)

    items = []

    # Build Items by matching each item with its description.
    for item in result_dict['rgInventory'].values():
        class_id    = item['classid']
        instance_id = item['instanceid'] 
        description = result_dict['rgDescriptions'][str(class_id) + "_" + str(instance_id)]
        items.append(InventoryItem(item, description))

    return Inventory(profile_id, items)
