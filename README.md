# libmonzo 

A Python library for interacting with Monzo bank accounts that can handle OAuth authentication.

### Installation

    pip install libmonzo

### Setup

To use this library, you'll need to create your own client on the Monzo developer site: https://developers.monzo.com/apps/home

The name, logo, and description can be whatever you want it to be. Set the "Confidentiality" to "Not Confidential" and set the redirect URL to "http://localhost:36453/monzo_callback" (or whatever you like if you will be providing the access token).

You'll need to store the client ID, the owner ID and the client secret for use in setup of the client later.

### Example:

    import libmonzo

    client = libmonzo.MonzoClient(client_id, owner_id, client_secret)

    # Via OAuth (it will open a browser window)
    client.authenticate()

    # Or providing the access token directly
    client.access_token = "..."

    # Getting accounts
    for account in client.accounts():
        print(account.owners[0].preferred_name)

    # Get the balance of an account
    account = client.accounts()[0]
    balance_info = client.balance(account_id=account.identifier)
    print(balance_info.balance)

### Supported APIs

* Listing accounts
* Reading balance
* Listing pots
* Depositing into pots
* Withdrawing from pots
* Retrieving a transaction
* Listing transactions
* Creating feed items
* Uploading and setting attachments
* Removing attachments
* Registering webooks
* Listing webhooks
* Removing webhooks

Annotating transactions will be coming soon. There appears to be a minor bug causing problems at this point, so it's not quite ready.


### Known issues

This was written because I needed it for a small personal project. Because of that, there are some issues. I'm open to PRs to fix these though.

* The OAuth setup isn't 100% reliable and could be better
* Limited error checking
* Limited bounds/variable checking
* Lack of useful error messages
* Design could be cleaner
* The tests require a local configuration file to even run
* Plus so many more
