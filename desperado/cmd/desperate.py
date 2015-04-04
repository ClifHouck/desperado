import argparse
from functools import reduce

from desperado import auth
from desperado import inventory
from desperado import data
from desperado import market
from desperado.currency import Dollars

import credentials

#TODO: Support basic operations on inventory and market.
# - List inventory by app
# - list item on market item by id/app
# - list users current market listings
# - rescind listing on market by listing ID
# - support login credentials through command line or environment variables

def automated_steamguard():
    return auth.get_steamguard_code_automated_imap(*credentials.mail())

def try_to_get_inventory():
    session = auth.login(*credentials.steam(), get_steamguard_code = automated_steamguard)
    return inventory.retrieve_profile_inventory(session, data.app_id('csgo'))

def get_to_session():
    session = auth.login(*credentials.steam(), get_steamguard_code = automated_steamguard)
    return session

def is_capsule(item):
    return item.tag_contains('Type', 'Container') and item.market_name().find('Capsule') > 1

def sell_capsules():
    session = auth.login(*credentials.steam(), get_steamguard_code = automated_steamguard)
    csgo_inv = inventory.retrieve_profile_inventory(session, data.app_id('csgo'))

    capsules = [item for item in csgo_inv.items if is_capsule(item)]
    for cap in capsules:
        for tag_name,tag_data in cap.tags.items():
            print (tag_name + ": " + tag_data)
        price_data = cap.get_price_data(session)
        desired_price = market.get_desired_price(price_data.low_price.to_cents())
        print('Sell this item at ' + str(desired_price) + ' [' + str(price_data.low_price) + '] ?')
        response = input('->')
        if response == 'y':
            try:
                market.post_item_for_sale(session, cap, desired_price)
            except market.ItemSaleError:
                print("Got failure! Quitting...")
                quit()
            print('Posted item for sale!')


def inventory_list(app_name):
    if app_name not in data.APP_SHORT_NAME_TO_ID.keys():
        raise Exception("'%(app_name)s' not a recognized app!" % {
                            'app_name': app_name})

    session = auth.login(*credentials.steam(),
                         get_steamguard_code = automated_steamguard)
    inv = inventory.retrieve_profile_inventory(session, data.app_id(app_name))
    for item in inv:
        print(item)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run commands related to "
        "the Steam marketplace and inventory.")
    subparsers = parser.add_subparsers(title="command",
                                       description="Steam commands to run.",
                                       dest='subparser_name',
                                       help="")

    # Market listing parser
    inv_list_parser = subparsers.add_parser('inventory-list',
                                        help='List the inventory for a '
                                             'particular steam app.')
    inv_list_parser.add_argument('app_name', help='Name of the steam app.')

    args = parser.parse_args()
    print(args)

    if args.subparser_name == "inventory-list":
        inventory_list(args.app_name)

    quit()


    session = auth.login(*credentials.steam(), get_steamguard_code = automated_steamguard)
    inv     = inventory.retrieve_profile_inventory(session, data.app_id('csgo'))

    def only_stattrak(item):
        return item.tag_contains('Quality', 'StatTrak')

    non_stattrak = [item for item in inv.items if not only_stattrak(item) and item.can_trade()]

    # get the true value of my inventory
    total = 0
    for item in non_stattrak:
        minimum_price = item.get_price_data(session).low_price
        print(item.market_name() + ": " + str(minimum_price))
        total += market.get_desired_price(minimum_price.to_cents())

    print("Value of non-stattrak CSGO inventory: " + str(Dollars.from_cents(total)))

    response = input('Sell all these items?')
    if response == 'y':
        for item in non_stattrak:
            minimum_price = item.get_price_data(session).low_price
            desired_price = market.get_desired_price(minimum_price.to_cents())
            market.post_item_for_sale(session, item, desired_price)
            print("Posted " + item.market_name() + " at " + str(Dollars.from_cents(desired_price)))

    quit()


    def sum_min_value(dollar_value, item):
        return dollar_value + item.get_price_data(session).low_price

    def sum_median_value(dollar_value, item):
        return dollar_value + item.get_price_data(session).median_price

    def calculate_stats(iterable):
        total_minimum_value = reduce(sum_min_value, iterable, Dollars(0, 0))
        total_median_value  = reduce(sum_median_value, iterable, Dollars(0, 0))
        return (total_minimum_value, total_median_value)

    def print_stats(min_value, median_value):
        print ("Minimum value: " + str(min_value), " Median value: " + str(median_value))

    # for item in inv.items:
    #     for tag_name,tag_data in item.tags.items():
    #         print (tag_name + ": " + tag_data)
    #     print(item.id())
    #    print(item.instance_id())
    #    print(item.class_id())
    #    print(item._description_json['descriptions'])
    #    print("")
#
#    quit()
#
#    sticker_capsules = [item for item in inv.items if only_capsules(item)]
#    total_min_sticker_value, total_median_sticker_value = calculate_stats(sticker_capsules)
#    print("===Stickers===")
#    print_stats(total_min_sticker_value, total_median_sticker_value)
#
#    stattrak_weapons = [item for item in inv.items if only_stattrak(item)]
#    total_stattrak_min_value, total_stattrak_median_value = calculate_stats(stattrak_weapons)
#    print("===StatTrak===")
#    print_stats(total_stattrak_min_value, total_stattrak_median_value)
#
    # total_csgo_min_value, total_csgo_median_value = calculate_stats(inv.items)
    # print("Total csgo min: " + str(total_csgo_min_value) + " Total median csgo: " + str(total_csgo_median_value))

