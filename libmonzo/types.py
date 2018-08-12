"""Classes for the various Monzo API response types."""

import abc
import datetime
import enum
import time
from typing import Any, Dict, List, Optional, Union

# In an API wrapper we don't get to dictate how many variables there are
#pylint: disable=too-many-instance-attributes
#pylint: disable=too-many-locals


def _get_timestamp(string_value):
    """Gets the timestamp from the string provided by the APIs."""

    if not string_value:
        return None

    try:
        timestamp = time.strptime(string_value, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError:
        timestamp = time.strptime(string_value, "%Y-%m-%dT%H:%M:%SZ")
    return datetime.datetime(*timestamp[:6])


class Color():
    """Represents a color for the various APIs."""

    hex_code: str

    def __init__(self, *, hex_code) -> None:
        if not hex_code.startswith('#'):
            hex_code = '#' + hex_code

        if len(hex_code) != 7:
            raise AttributeError("Hex code was invalid")

        self.hex_code = hex_code


class AccountType(enum.Enum):
    """Represents the account type."""

    RETAIL = "uk_retail"
    RETAIL_JOINT = "uk_retail_joint"
    PREPAID = "uk_prepaid"


class MonzoType(abc.ABC):
    """Base class for Monzo types."""

    @staticmethod
    def from_json(response: Dict[str, Any]) -> Any:
        """Convert the JSON from the API response into the object."""
        raise NotImplementedError()


class WhoAmI(MonzoType):
    """Basic user information."""

    authenticated: bool
    client_id: str
    user_id: str

    def __init__(self, *, authenticated: bool, client_id: str, user_id: str) -> None:
        self.authenticated = authenticated
        self.client_id = client_id
        self.user_id = user_id

    def __eq__(self, other):
        return self.user_id == other.user_id and self.client_id == other.client_id

    @staticmethod
    def from_json(response: Dict[str, Any]) -> 'WhoAmI':
        return WhoAmI(
            authenticated=response["authenticated"],
            client_id=response["client_id"],
            user_id=response["user_id"]
        )


class Owner(MonzoType):
    """A Monzo account owner"""

    user_id: str
    preferred_name: str
    preferred_first_name: str

    def __init__(self, *, user_id: str, preferred_name: str, preferred_first_name: str) -> None:
        self.user_id = user_id
        self.preferred_name = preferred_name
        self.preferred_first_name = preferred_first_name

    def __eq__(self, other):
        return self.user_id == other.user_id

    @staticmethod
    def from_json(response: Union[Dict[str, Any], List[Dict[str, Any]]]) -> List['Owner']:

        # Make sure we are always dealing with a list rather than just one
        if isinstance(response, list):
            owners_data = response
        else:
            owners_data = [response]

        results = []

        for owner_data in owners_data:
            results.append(Owner(
                user_id=owner_data["user_id"],
                preferred_name=owner_data["preferred_name"],
                preferred_first_name=owner_data["preferred_first_name"]
            ))

        return results


class Account(MonzoType):
    """A Monzo account"""

    identifier: str
    description: str
    created: datetime.datetime
    is_closed: bool
    account_type: AccountType
    owners: List[Owner]
    account_number: Optional[str]
    sort_code: Optional[str]

    def __init__(
            self,
            *,
            identifier: str,
            description: str,
            created: datetime.datetime,
            is_closed: bool,
            account_type: AccountType,
            owners: List[Owner],
            account_number: Optional[str],
            sort_code: Optional[str]
    ) -> None:
        self.identifier = identifier
        self.description = description
        self.created = created
        self.is_closed = is_closed
        self.account_type = account_type
        self.owners = owners
        self.account_number = account_number
        self.sort_code = sort_code

    def __eq__(self, other):
        return self.identifier == other.identifier

    @staticmethod
    def from_json(response: Dict[str, Any]) -> List['Account']:

        # Make sure we are always dealing with a list rather than just one
        if response.get('accounts') is None:
            accounts = [response]
        else:
            accounts = response['accounts']

        results = []

        for account in accounts:
            created_datetime = _get_timestamp(account["created"])
            results.append(Account(
                identifier=account["id"],
                description=account["description"],
                created=created_datetime,
                is_closed=account["closed"],
                account_type=AccountType(account["type"]),
                owners=Owner.from_json(account["owners"]),
                account_number=account.get("account_number"),
                sort_code=account.get("sort_code")
            ))

        return results


class Balance(MonzoType):
    """A Monzo account balance"""

    balance: int
    total_balance: int  # includes pots
    spend_today: int
    currency: str

    def __init__(self, *, balance: int, total_balance: int, spend_today: int, currency: str) -> None:
        self.balance = balance
        self.total_balance = total_balance
        self.spend_today = spend_today
        self.currency = currency

    def __eq__(self, other):
        return self.balance == other.balance and \
            self.total_balance == other.total_balance and \
            self.spend_today == other.spend_today and \
            self.currency == other.currency

    @staticmethod
    def from_json(response: Dict[str, Any]) -> 'Balance':

        return Balance(
            balance=response["balance"],
            total_balance=response["total_balance"],
            spend_today=response["spend_today"],
            currency=response["currency"]
        )


class Pot(MonzoType):
    """A Monzo pot"""

    identifier: bool
    name: str
    style: str
    balance: int
    currency: str
    round_up: bool
    created: datetime.datetime
    updated: datetime.datetime
    deleted: bool

    def __init__(
            self,
            *,
            identifier: bool,
            name: str,
            style: str,
            balance: int,
            currency: str,
            round_up: bool,
            created: datetime.datetime,
            updated: datetime.datetime,
            deleted: bool
    ) -> None:
        self.identifier = identifier
        self.name = name
        self.style = style
        self.balance = balance
        self.currency = currency
        self.round_up = round_up
        self.created = created
        self.updated = updated
        self.deleted = deleted

    def __eq__(self, other):
        return self.identifier == other.identifier

    @staticmethod
    def from_json(response: Dict[str, Any]) -> List['Pot']:
        # Make sure we are always dealing with a list rather than just one
        if response.get('pots') is None:
            pots = [response]
        else:
            pots = response['pots']

        results = []

        for pot in pots:
            created_datetime = _get_timestamp(pot["created"])
            updated_datetime = _get_timestamp(pot["updated"])
            results.append(Pot(
                identifier=pot["id"],
                name=pot["name"],
                style=pot["style"],
                balance=pot["balance"],
                currency=pot["currency"],
                round_up=pot["round_up"],
                created=created_datetime,
                updated=updated_datetime,
                deleted=pot["deleted"]
            ))

        return results


class Attachment(MonzoType):
    """A Monzo transaction attachment"""

    identifier: Optional[str]
    external_id: str
    file_type: str
    file_url: str
    user_id: str

    def __init__(
            self,
            *,
            identifier: Optional[str],
            external_id: str,
            file_type: str,
            file_url: str,
            user_id: str,
    ) -> None:
        self.identifier = identifier
        self.external_id = external_id
        self.file_type = file_type
        self.file_url = file_url
        self.user_id = user_id

    def __str__(self):
        return str({
            "identifier": self.identifier,
            "external_id": self.external_id,
            "file_type": self.file_type,
            "file_url": self.file_url,
            "user_id": self.user_id
        })

    @staticmethod
    def from_json(response: Dict[str, Any]) -> 'Attachment':
        return Attachment(
            identifier=response.get("id"),
            external_id=response["external_id"],
            file_type=response["file_type"],
            file_url=response["file_url"],
            user_id=response["user_id"]
        )


class Transaction(MonzoType):
    """A Monzo transaction.

    This type is incredibly complex and is changing all the time. Instead of
    trying, and failing, to keep this up to date, we just pull out a few key
    details and leave the rest as the raw_data dictionary.
    """

    identifier: str
    account_id: str
    user_id: str

    description: str

    amount: int
    currency: str
    local_amount: int
    local_currency: str
    account_balance: int

    created: datetime.datetime
    updated: datetime.datetime
    settled: Optional[datetime.datetime]

    attachments: List[Attachment]

    raw_data: Dict[str, Any]

    def __init__(
            self,
            *,
            identifier: str,
            account_id: str,
            user_id: str,
            description: str,
            amount: int,
            currency: str,
            local_amount: int,
            local_currency: str,
            account_balance: int,
            created: datetime.datetime,
            updated: datetime.datetime,
            settled: Optional[datetime.datetime],
            attachments: List[Attachment],
            raw_data: Dict[str, Any]
    ) -> None:
        self.identifier = identifier
        self.account_id = account_id
        self.user_id = user_id
        self.description = description
        self.amount = amount
        self.currency = currency
        self.local_amount = local_amount
        self.local_currency = local_currency
        self.account_balance = account_balance
        self.created = created
        self.updated = updated
        self.settled = settled
        self.attachments = attachments
        self.raw_data = raw_data

    def __eq__(self, other):
        return self.identifier == other.identifier

    @staticmethod
    def from_json(response: Dict[str, Any]) -> List['Transaction']:
        # Make sure we are always dealing with a list rather than just one
        if response.get('transactions') is not None:
            transactions = response['transactions']
        elif response.get('transaction') is not None:
            transactions = [response['transaction']]
        else:
            transactions = [response]

        results = []

        for transaction in transactions:
            created_datetime = _get_timestamp(transaction["created"])
            updated_datetime = _get_timestamp(transaction["updated"])
            settled_datetime = _get_timestamp(transaction["settled"])

            attachments_data = transaction["attachments"]
            if attachments_data is None:
                attachments_data = []

            attachments = [Attachment.from_json(attachment_data) for attachment_data in attachments_data]

            results.append(Transaction(
                identifier=transaction["id"],
                account_id=transaction["account_id"],
                user_id=transaction["user_id"],
                description=transaction["description"],
                amount=transaction["amount"],
                currency=transaction["currency"],
                local_amount=transaction["local_amount"],
                local_currency=transaction["local_currency"],
                account_balance=transaction["account_balance"],
                created=created_datetime,
                updated=updated_datetime,
                settled=settled_datetime,
                attachments=attachments,
                raw_data=transaction
            ))

        return results


class Webhook(MonzoType):
    """A Monzo webhook"""

    identifier: str
    account_id: str
    url: str

    def __init__(
            self,
            *,
            identifier: str,
            account_id: str,
            url: str
    ) -> None:
        self.identifier = identifier
        self.account_id = account_id
        self.url = url

    def __eq__(self, other):
        return self.identifier == other.identifier

    @staticmethod
    def from_json(response: Dict[str, Any]) -> List['Webhook']:

        # Make sure we are always dealing with a list rather than just one
        if response.get('webhooks') is not None:
            webhooks = response['webhooks']
        elif response.get('webhook') is not None:
            webhooks = [response['webhook']]
        else:
            webhooks = [response]

        results = []

        for webhook in webhooks:
            results.append(Webhook(
                identifier=webhook["id"],
                account_id=webhook["account_id"],
                url=webhook["url"]
            ))

        return results
