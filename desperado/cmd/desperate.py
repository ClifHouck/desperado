import argparse

from desperado import auth
from desperado import data
from desperado import inventory
from desperado import market

import credentials


def automated_steamguard():
    return auth.get_steamguard_code_automated_imap(*credentials.mail())


def inventory_list(app_id, tradable=False):

    session = auth.login(*credentials.steam(),
                         get_steamguard_code=automated_steamguard)

    inv = inventory.retrieve_profile_inventory(session, app_id)
    items = inv.items

    if tradable:
        items = [i for i in items if i.can_trade()]

    for item in items:
        unicode_print(str(item))


def market_listings():
    session = auth.login(*credentials.steam(),
                         get_steamguard_code=automated_steamguard)

    listings = market.get_current_listings(session)

    for listing in listings:
        print(listing)


def listing_create(item_id, app_name, price_in_cents):
    session = auth.login(*credentials.steam(),
                         get_steamguard_code=automated_steamguard)
    result = market.post_item_for_sale(session,
                                       item_id,
                                       app_id,
                                       price_in_cents)
    print(result.json())


def listing_remove(listing_id):
    session = auth.login(*credentials.steam(),
                         get_steamguard_code=automated_steamguard)
    market.get_current_listings(session)
    result = market.remove_listing(session, listing_id)
    print(result.json())


def unicode_print(unicode_string):
    print(unicode_string.decode("utf_8"))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run commands related to "
                                     "the Steam marketplace and inventory.")
    subparsers = parser.add_subparsers(title="command",
                                       description="Steam commands to run.",
                                       dest='subparser_name',
                                       help="Command to run.")

    # Inventory listing parser
    inv_list_parser = subparsers.add_parser('inventory-list',
                                            help='List the inventory for a '
                                                 'particular steam app.')
    inv_list_parser.add_argument('app_name', help='Name of the steam app.',
                                 choices=data.APP_SHORT_NAME_TO_ID.keys())
    inv_list_parser.add_argument('--tradable', action='store_true',
                                 help='Only list items which are tradable.')

    # Market listing parser
    market_list_parser = subparsers.add_parser('market-listings',
                                               help='List the user\'s current '
                                                    'market listings.')

    # Listing create parser
    listing_create_parser = subparsers.add_parser(
        'listing-create', help='Create a listing on the Steam market '
                               'for an item.')
    listing_create_parser.add_argument(
        'app_name', help='Name of the steam app to which the item belongs.',
        choices=data.APP_SHORT_NAME_TO_ID.keys())
    listing_create_parser.add_argument(
        'item_id', help='The unique item ID as reported by Steam.')
    listing_create_parser.add_argument(
        'price_in_cents', help='The price to use when listing the item. '
                               'Note this is the price you will receive, '
                               'not what the buyer will pay.')

    # Listing remove parser
    listing_remove_parser = subparsers.add_parser(
        'listing-remove', help='Remove a listing from the Steam market.')
    listing_remove_parser.add_argument(
        'listing_id', help='The unique market listing ID as reported '
                           'by Steam.')

    # TODO(ClifHouck) Sub-commands to support
    # - buy - attempt to buy an item from the steam market.

    args = parser.parse_args()

    try:
        app_id = data.app_id(args.app_name)
    except AttributeError:
        pass

    if args.subparser_name == "inventory-list":
        inventory_list(app_id, args.tradable)
    elif args.subparser_name == "market-listings":
        market_listings()
    elif args.subparser_name == "listing-create":
        listing_create(args.item_id, app_id, args.price_in_cents)
    elif args.subparser_name == "listing-remove":
        listing_remove(args.listing_id)
