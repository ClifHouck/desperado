import pdb

from desperado import auth
from desperado import market

import credentials


def steamguard():
    return auth.get_steamguard_code_automated_imap(*credentials.mail())

if __name__ == '__main__':
    session = auth.login(*credentials.steam(), get_steamguard_code = steamguard)
    listings = market.get_current_listings(session)

    for listing in listings:
        print("Removing: " + str(listing))
        try:
            market.remove_listing(session, listing.id)
        except market.ListingRemovalError as e:
            pdb.set_trace()
            quit()
