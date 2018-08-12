#!/usr/bin/env python3

"""Monzo provider."""

import logging
import os
from typing import Any, ClassVar, Dict, List, Optional
import webbrowser

import requests

from libmonzo.exceptions import *
from libmonzo.types import Account, Attachment, Balance, Color, Pot, Transaction, Webhook, WhoAmI
from libmonzo import utilities


#pylint: disable=too-many-public-methods


class MonzoClient():
    """Monzo API wrapper."""

    REDIRECT_PORT: ClassVar[int] = 36453
    REDIRECT_PATH: ClassVar[str] = "monzo_callback"

    log: logging.Logger
    client_id: str
    client_secret: str
    owner_id: str
    access_token: Optional[str]
    account_id: Optional[str]
    state_token: str

    def __init__(self, client_id: str, owner_id: str, client_secret: str) -> None:
        self.log = logging.getLogger("monzo")
        self.client_id = client_id
        self.owner_id = owner_id
        self.client_secret = client_secret
        self.access_token = None
        self.account_id = None
        self.state_token = utilities.random_string(20)
        super().__init__()

    def authenticate(self) -> bool:
        """Authenticates the client."""
        self.log.info("Authenticating")

        # 1. Aquire authorization code

        server = utilities.OAuthServer(MonzoClient.REDIRECT_PORT)

        url = 'https://auth.monzo.com/'
        url += f'?client_id={self.client_id}'
        url += f'&redirect_uri={MonzoClient.redirect_uri()}'
        url += f'&response_type=code'
        url += f'&state={self.state_token}'

        webbrowser.open(url)

        self.log.info("Waiting for response...")
        parameters = server.wait_for_call()

        if parameters is None:
            raise MonzoAPIError("Failed to authenticate correctly. The response parameters were invalid.")

        authorization_code = parameters["code"]

        if len(parameters["state"]) != 1:
            raise Exception("Invalid return state")

        state_value = parameters["state"][0]

        if self.state_token != state_value:
            raise Exception("State did not match")

        # 2. Exchange for access token

        response = requests.post(
            'https://api.monzo.com/oauth2/token',
            data={
                "grant_type": "authorization_code",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": MonzoClient.redirect_uri(),
                "code": authorization_code
            }
        )

        # {'access_token': '[snip]', 'client_id': '[snip]', 'expires_in': 107999,
        #  'scope': 'third_party_developer_app', 'token_type': 'Bearer', 'user_id': '[snip]'}
        data = response.json()

        self.access_token = data["access_token"]

        self.log.info("Authentication complete")

        return True

    def _handle_response(self, response):
        """Handle errors in API calls."""

        self.log.debug("Handling response: %d", response.status_code)

        error_map = {
            400: MonzoBadRequestError,
            401: MonzoUnauthorizedError,
            403: MonzoForbiddenError,
            404: MonzoNotFoundError,
            405: MonzoMethodNotAllowedError,
            406: MonzoNotAcceptableError,
            429: MonzoTooManyRequestsError,
            500: MonzoInternalServerError,
            504: MonzoGatewayTimeoutError,
        }

        if response.status_code < 200 or response.status_code >= 300:
            error_class = error_map.get(response.status_code, MonzoAPIError)
            raise error_class(f"Error fetching request: ({response.status_code}): {response.text}")

        return response

    def get(self, path: str):
        """Perform a GET request to the API."""
        url = f'https://api.monzo.com/{path}'
        self.log.debug("Performing GET: %s", url)
        return self._handle_response(requests.get(
            url,
            headers={'Authorization': f'Bearer {self.access_token}'}
        ))

    def post(self, path: str, data: Optional[Dict[str, Any]] = None, json: Optional[Dict[str, Any]] = None):
        """Perform a PUT request to the API."""
        url = f'https://api.monzo.com/{path}'
        self.log.debug("Performing POST: %s", url)
        return self._handle_response(requests.post(
            url,
            data=data,
            json=json,
            headers={'Authorization': f'Bearer {self.access_token}'}
        ))

    def put(self, path: str, data: Dict[str, Any]):
        """Perform a PUT request to the API."""
        url = f'https://api.monzo.com/{path}'
        self.log.debug("Performing PUT: %s", url)
        return self._handle_response(requests.put(
            url,
            data=data,
            headers={'Authorization': f'Bearer {self.access_token}'}
        ))

    def patch(self, path: str, data: str):
        """Perform a PATCH request to the API."""
        url = f'https://api.monzo.com/{path}'
        self.log.debug("Performing PATCH: %s", url)
        return self._handle_response(requests.patch(
            url,
            data=data,
            headers={'Authorization': f'Bearer {self.access_token}'}
        ))

    def delete(self, path: str):
        """Perform a PATCH request to the API."""
        url = f'https://api.monzo.com/{path}'
        self.log.debug("Performing DELETE: %s", url)
        return self._handle_response(requests.delete(
            url,
            headers={'Authorization': f'Bearer {self.access_token}'}
        ))

    def whoami(self) -> WhoAmI:
        """Return basic whoami data."""
        self.log.debug("Requesting whoami.")
        response = self.get('ping/whoami')
        return WhoAmI.from_json(response.json())

    def accounts(self) -> List[Account]:
        """Return the list of accounts the user has."""
        self.log.debug("Requesting account list.")
        response = self.get('accounts')
        return Account.from_json(response.json())

    def balance(self, *, account_id: str) -> Balance:
        """Get the balance of an account."""
        self.log.debug("Requesting balance for account: %s", account_id)
        response = self.get(f'balance?account_id={account_id}')
        return Balance.from_json(response.json())

    def pots(self) -> List[Pot]:
        """Return the list of pots the user has."""
        self.log.debug("Requesting pots.")
        response = self.get('pots')
        return Pot.from_json(response.json())

    def deposit_into_pot(
            self,
            *,
            pot_id: str,
            source_account_id: str,
            amount: int,
            dedupe_id: str = utilities.random_string(20)
        ) -> Pot:
        """Deposit the value into the pot from the account."""

        self.log.debug("Depositing into pot (%s) from account (%s): %d", pot_id, source_account_id, amount)
        response = self.put(
            f'pots/{pot_id}/deposit',
            {
                'source_account_id': source_account_id,
                'amount': amount,
                'dedupe_id': dedupe_id
            }
        )
        return Pot.from_json(response.json())[0]

    def withdraw_from_pot(
            self,
            *,
            pot_id: str,
            destination_account_id: str,
            amount: int,
            dedupe_id: str = utilities.random_string(20)
        ) -> Pot:
        """Withdraw the value from the pot into the account."""

        self.log.debug("Withdrawing from pot (%s) into account (%s): %d", pot_id, destination_account_id, amount)
        response = self.put(
            f'pots/{pot_id}/withdraw',
            {
                'destination_account_id': destination_account_id,
                'amount': amount,
                'dedupe_id': dedupe_id
            }
        )
        return Pot.from_json(response.json())[0]

    def transactions(self, *, account_id: str) -> List[Transaction]:
        """Retrieve a list of transactions."""
        self.log.debug("Requesting transaction list for account: %s", account_id)
        response = self.get(f'transactions?account_id={account_id}')
        return Transaction.from_json(response.json())

    def transaction(self, *, identifier: str) -> Transaction:
        """Get an individual transaction."""
        self.log.debug("Requesting transaction: %s", identifier)
        response = self.get(f'transactions/{identifier}?expand[]=merchant')
        return Transaction.from_json(response.json())[0]

    def remove_transaction_annotation(self, *, identifier: str, key: str) -> Transaction:
        """Remove the annotation from the transaction."""
        self.log.debug("Removing transaction (%s) annotation: %s", identifier, key)
        return self.annotate_transaction(identifier=identifier, key=key, value="")

    def annotate_transaction(self, *, identifier: str, key: str, value: str) -> Transaction:
        """Add or change an annotation on a transaction."""
        self.log.debug("Annotating transaction (%s) with %s=%s", identifier, key, value)
        response = self.patch(
            f'transactions/{identifier}',
            f"metadata[{key}]={value}"
        )
        return Transaction.from_json(response.json())[0]

    def create_feed_item(
            self,
            *,
            account_id: str,
            title: str,
            image_url: str,
            body: Optional[str] = None,
            background_color: Optional[Color] = None,
            body_color: Optional[Color] = None,
            title_color: Optional[Color] = None,
            url: Optional[str] = None
        ) -> None:
        """Create a new item in the feed for the account."""

        self.log.debug("Creating feed item on %s: %s -> %s (%s)", account_id, title, body, url if url else "")

        post_data = {
            "type": "basic",
            "account_id": account_id,
            "params[title]": title,
            "params[image_url]": image_url
        }

        if body is not None:
            post_data["params[body]"] = body

        if background_color is not None:
            post_data["params[background_color]"] = background_color.hex_code

        if body_color is not None:
            post_data["params[body_color]"] = body_color.hex_code

        if title_color is not None:
            post_data["params[title_color]"] = title_color.hex_code

        if url is not None:
            post_data["url"] = url

        self.post(
            f'feed',
            data=post_data
        )

    def register_attachment(self, *, transaction_id: str, url: str, mime_type: str) -> Attachment:
        """Register an attachment against a URL."""
        self.log.debug("Registering attachment on %s: %s", transaction_id, url)
        response = self.post(
            'attachment/register',
            data={
                "external_id": transaction_id,
                "file_type": mime_type,
                "file_url": url
            }
        )
        data = response.json()
        return Attachment.from_json(data["attachment"])

    def unregister_attachment(self, *, attachment_id: str) -> None:
        """Unregister an attachment."""
        self.log.debug("Unregistering attachment: %s", attachment_id)
        self.post(
            'attachment/deregister',
            data={
                "id": attachment_id
            }
        )

    def upload_attachment(self, *, file_path: str, mime_type: str) -> str:
        """Upload an attachment (which can then be registered with the returned url)."""
        self.log.debug("Uploading attachment: %s", file_path)
        upload_link_response = self.post(
            'attachment/upload',
            data={
                "file_name": os.path.basename(file_path),
                "file_type": mime_type
            }
        )

        upload_link_data = upload_link_response.json()

        file_url = upload_link_data["file_url"]
        upload_url = upload_link_data["upload_url"]

        self.log.debug("Retrieved upload location: %s", upload_url)

        with open(file_path, 'rb') as attachment_file:
            # Reading this into memory before sending isn't the most efficient,
            # but it seems that S3 is ignoring some headers otherwise and
            # keeping them in the file which means it doesn't render correctly
            # when you re-fetch it.
            self.log.debug("Beginning upload")
            self._handle_response(requests.put(
                upload_url,
                data=attachment_file.read(),
                headers={
                    'content-type': mime_type
                },
                params={
                    'file':file_path
                }
            ))
            self.log.debug("Upload complete. File can be accessed: %s", file_url)

        return file_url

    def list_webhooks(self, *, account_id: str) -> List[Webhook]:
        """List the webhooks for an account."""
        self.log.debug("Retrieving webhooks for: %s", account_id)
        response = self.get(f'webhooks?account_id={account_id}')
        return Webhook.from_json(response.json())

    def register_webhook(self, *, account_id: str, url: str) -> Webhook:
        """Register a webhook."""
        self.log.debug("Registering webhooks on %s: %s", account_id, url)
        response = self.post(
            'webhooks',
            data={
                "account_id": account_id,
                "url": url
            }
        )
        return Webhook.from_json(response.json())[0]

    def delete_webhook(self, *, webhook_id: str) -> None:
        """Register a webhook."""
        self.log.debug("Deleting webhook: %s", webhook_id)
        self.delete(f'webhooks/{webhook_id}')

    @staticmethod
    def redirect_uri():
        """The redirect URI for OAuth callbacks."""
        return f"http://localhost:{MonzoClient.REDIRECT_PORT}/{MonzoClient.REDIRECT_PATH}"
