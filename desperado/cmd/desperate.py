import argparse

from desperado import auth
from desperado import data
from desperado import inventory

import credentials


def automated_steamguard():
    return auth.get_steamguard_code_automated_imap(*credentials.mail())


def inventory_list(app_name, tradable=False):
    if app_name not in data.APP_SHORT_NAME_TO_ID.keys():
        raise Exception("'%(app_name)s' not a recognized app!" % {
                        'app_name': app_name})

    session = auth.login(*credentials.steam(),
                         get_steamguard_code=automated_steamguard)
    inv = inventory.retrieve_profile_inventory(session, data.app_id(app_name))
    items = inv.items

    if tradable:
        items = [i for i in items if i.can_trade()]

    for item in items:
        unicode_print(str(item))


def unicode_print(unicode_string):
    print(unicode_string.decode("utf_8"))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run commands related to "
                                     "the Steam marketplace and inventory.")
    subparsers = parser.add_subparsers(title="command",
                                       description="Steam commands to run.",
                                       dest='subparser_name',
                                       help="Command to run.")

    # Market listing parser
    inv_list_parser = subparsers.add_parser('inventory-list',
                                        help='List the inventory for a '
                                             'particular steam app.')
    inv_list_parser.add_argument('app_name', help='Name of the steam app.')
    inv_list_parser.add_argument('--tradable', action='store_true', 
                                 help='Only list items which are tradable.')

    # TODO(ClifHouck) Sub-commands to support
    # - market-listings list users current market listings
    # - listing-create - list an item on the steam market
    # - listing-delete - delete a listing from the steam market
    # - buy - attempt to buy an item from the steam market.

    args = parser.parse_args()

    if args.subparser_name == "inventory-list":
        inventory_list(args.app_name, args.tradable)
