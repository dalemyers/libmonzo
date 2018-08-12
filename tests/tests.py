#!/usr/bin/env python3

"""Tests for the package."""

#pylint: disable=line-too-long

import filecmp
import json
import os
import random
import sys
import tempfile
from typing import ClassVar, Dict
import unittest
import uuid

import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.abspath(__file__), "..", "..")))

#pylint: disable=wrong-import-position
import libmonzo
#pylint: enable=wrong-import-position


class LibMonzoTests(unittest.TestCase):
    """Test the library."""

    config: ClassVar[Dict[str, str]]
    client: ClassVar[libmonzo.MonzoClient]

    @classmethod
    def setUpClass(cls):
        cls.config = LibMonzoTests.load_configuration()
        cls.client = libmonzo.MonzoClient(cls.config["client_id"], cls.config["owner_id"], cls.config["client_secret"])
        #cls.client.authenticate()
        #print(cls.client.access_token)
        cls.client.access_token = cls.config["access_token"]

    @staticmethod
    def load_configuration() -> Dict[str, str]:
        """Load the configuration."""
        config_path = os.path.expanduser("~/.libmonzo")
        with open(config_path, 'r') as config_file:
            return json.load(config_file)

    def test_who_am_i(self):
        """Test whoami."""

        whoami = LibMonzoTests.client.whoami()

        self.assertTrue(isinstance(whoami, libmonzo.types.WhoAmI))
        self.assertTrue(whoami.authenticated)
        self.assertEqual(LibMonzoTests.config["user_id"], whoami.user_id)
        self.assertEqual(LibMonzoTests.config["client_id"], whoami.client_id)

    def test_accounts(self):
        """Test accounts."""

        accounts = LibMonzoTests.client.accounts()

        expected_accounts = LibMonzoTests.config["accounts"]

        self.assertTrue(len(accounts) == len(expected_accounts))

        for account in accounts:
            matching_account_dict = None
            matching_account = None

            for expected_account in expected_accounts:
                if account.identifier == expected_account["id"]:
                    matching_account_dict = expected_account
                    break

            self.assertIsNotNone(matching_account_dict, f"Failed to find matching account for ID: {account.identifier}")

            matching_account = libmonzo.types.Account.from_json(matching_account_dict)[0]

            self.assertEqual(account.identifier, matching_account.identifier)
            self.assertEqual(account.description, matching_account.description)
            self.assertEqual(account.created, matching_account.created)
            self.assertEqual(account.is_closed, matching_account.is_closed)
            self.assertEqual(account.account_type, matching_account.account_type)
            self.assertEqual(account.owners, matching_account.owners)
            self.assertEqual(account.account_number, matching_account.account_number)
            self.assertEqual(account.sort_code, matching_account.sort_code)
            self.assertEqual(account, matching_account)

    def test_balances(self):
        """Test balances."""

        accounts = LibMonzoTests.client.accounts()

        for account in accounts:
            balance = LibMonzoTests.client.balance(account_id=account.identifier)
            self.assertIsNotNone(balance)
            self.assertTrue(balance.currency == "GBP")

    def test_pots(self):
        """Test pots."""

        pots = LibMonzoTests.client.pots()
        expected_pots = LibMonzoTests.config["pots"]

        self.assertTrue(len(pots) == len(expected_pots))

        for pot in pots:
            matching_pot_dict = None
            matching_pot = None

            for expected_pot in expected_pots:
                if pot.identifier == expected_pot["id"]:
                    matching_pot_dict = expected_pot
                    break

            self.assertIsNotNone(matching_pot_dict, f"Failed to find matching pot for ID: {pot.identifier}")

            matching_pot = libmonzo.types.Pot.from_json(matching_pot_dict)[0]

            self.assertEqual(pot.identifier, matching_pot.identifier)
            self.assertEqual(pot.name, matching_pot.name)
            self.assertEqual(pot.style, matching_pot.style)
            self.assertEqual(pot.currency, matching_pot.currency)
            self.assertEqual(pot.round_up, matching_pot.round_up)
            self.assertEqual(pot.created, matching_pot.created)
            self.assertEqual(pot.deleted, matching_pot.deleted)

    def test_pot_deposit(self):
        """Test pot depositing/withdrawing."""

        account_id = LibMonzoTests.config["test_account_id"]
        pot_id = LibMonzoTests.config["pot_deposit_pot_id"]
        perform_disruptive_tests = LibMonzoTests.config["perform_disruptive_tests"]

        if not perform_disruptive_tests:
            return

        initial_pot = [pot for pot in LibMonzoTests.client.pots() if pot.identifier == pot_id][0]
        initial_account = [account for account in LibMonzoTests.client.accounts() if account.identifier == account_id][0]
        initial_account_balance = LibMonzoTests.client.balance(account_id=initial_account.identifier)

        # Perform the deposit (1 penny)
        LibMonzoTests.client.deposit_into_pot(pot_id=initial_pot.identifier, source_account_id=initial_account.identifier, amount=1)

        # Get the pot and account again
        mid_pot = [pot for pot in LibMonzoTests.client.pots() if pot.identifier == pot_id][0]
        mid_account = [account for account in LibMonzoTests.client.accounts() if account.identifier == account_id][0]
        mid_account_balance = LibMonzoTests.client.balance(account_id=mid_account.identifier)

        # Check the values
        self.assertTrue(mid_pot.balance == initial_pot.balance + 1)
        self.assertTrue(mid_account_balance.balance == initial_account_balance.balance - 1)
        self.assertTrue(mid_account_balance.total_balance == initial_account_balance.total_balance)

        # Now do the transfer the other way
        LibMonzoTests.client.withdraw_from_pot(pot_id=initial_pot.identifier, destination_account_id=initial_account.identifier, amount=1)

        # Get the pot and account again
        post_pot = [pot for pot in LibMonzoTests.client.pots() if pot.identifier == pot_id][0]
        post_account = [account for account in LibMonzoTests.client.accounts() if account.identifier == account_id][0]
        post_account_balance = LibMonzoTests.client.balance(account_id=post_account.identifier)

        # Check the values
        self.assertTrue(post_pot.balance == mid_pot.balance - 1)
        self.assertTrue(post_pot.balance == initial_pot.balance)
        self.assertTrue(post_account_balance.balance == mid_account_balance.balance + 1)
        self.assertTrue(post_account_balance.balance == initial_account_balance.balance)

    def test_transactions(self):
        """Test transactions."""

        accounts = LibMonzoTests.client.accounts()

        for account in accounts:
            transactions = LibMonzoTests.client.transactions(account_id=account.identifier)
            self.assertIsNotNone(transactions)
            transaction = random.choice(transactions)
            detailed_transaction = LibMonzoTests.client.transaction(identifier=transaction.identifier)
            self.assertEqual(detailed_transaction.identifier, transaction.identifier)

    def test_annotations(self):
        """Test annotating transactions."""

        perform_annotations_test = LibMonzoTests.config["perform_annotations_test"]

        if not perform_annotations_test:
            return

        account_id = LibMonzoTests.config["test_account_id"]

        transactions = LibMonzoTests.client.transactions(account_id=account_id)
        transaction = random.choice(transactions)
        annotation_key = "libmonzo_annotation_test"
        annotation_value = "1"

        # Add an annotation to the transaction
        LibMonzoTests.client.annotate_transaction(
            identifier=transaction.identifier,
            key=annotation_key,
            value=annotation_value
        )

        # Read it back to confirm it worked
        annotated_transaction = LibMonzoTests.client.transaction(identifier=transaction.identifier)
        metadata = annotated_transaction.raw_data.get("metadata")
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata.get(annotation_key), annotation_value)

        # Remove the annotation
        LibMonzoTests.client.remove_transaction_annotation(
            identifier=transaction.identifier,
            key=annotation_key
        )

        # Read it back to confirm it worked
        cleared_transaction = LibMonzoTests.client.transaction(identifier=transaction.identifier)
        with self.assertRaises(ValueError):
            _ = cleared_transaction.raw_data["metadata"][annotation_key]

    def test_add_feed_item(self):
        """Test adding a feed item."""

        perform_disruptive_tests = LibMonzoTests.config["perform_disruptive_tests"]

        if not perform_disruptive_tests:
            return

        account_id = LibMonzoTests.config["test_account_id"]

        try:
            LibMonzoTests.client.create_feed_item(
                account_id=account_id,
                title="Hello world",
                image_url="http://via.placeholder.com/64x64?text=X",
                background_color=libmonzo.types.Color(hex_code="#000088"),
                title_color=libmonzo.types.Color(hex_code="#FFFFFF"),
                body_color=libmonzo.types.Color(hex_code="#AAAAAA"),
                body="This is a feed test",
                url="https://google.com"
            )
        except libmonzo.exceptions.MonzoAPIError as ex:
            self.fail(f"Exception was raised: {ex}")

    def test_attachment_registration(self):
        """Test adding an attachment"""

        identifier = LibMonzoTests.config["attachment_transaction_id"]

        # Get the transaction
        transaction = LibMonzoTests.client.transaction(identifier=identifier)

        try:

            # Confirm there are no attachments:
            self.assertEqual(0, len(transaction.attachments))

            # Register the attachment
            LibMonzoTests.client.register_attachment(
                transaction_id=transaction.identifier,
                url="http://via.placeholder.com/400x400?text=Transaction%20Sample%20Attachment",
                mime_type="image/png"
            )

            # Confirm there is 1 attachment:
            transaction = LibMonzoTests.client.transaction(identifier=identifier)
            self.assertEqual(1, len(transaction.attachments))

        finally:

            # Unregister the attachments
            for attachment in transaction.attachments:
                LibMonzoTests.client.unregister_attachment(attachment_id=attachment.identifier)

            # Confirm there are no attachments:
            transaction = LibMonzoTests.client.transaction(identifier=identifier)
            self.assertEqual(0, len(transaction.attachments))


    def test_upload_attachment(self):
        """Test uploading an attachment"""

        perform_attachment_upload_test = LibMonzoTests.config["perform_attachment_upload_test"]

        if not perform_attachment_upload_test:
            return

        file_path = os.path.realpath(__file__)
        folder_path = os.path.dirname(file_path)
        image_path = os.path.join(folder_path, "upload_sample.png")

        attachment_url = LibMonzoTests.client.upload_attachment(file_path=image_path, mime_type="image/png")

        temp_name = str(uuid.uuid4()) + ".png"
        temp_location = os.path.join(tempfile.gettempdir(), temp_name)

        response = requests.get(attachment_url)

        with open(temp_location, 'wb') as temp_file:
            temp_file.write(response.content)

        try:
            self.assertTrue(filecmp.cmp(temp_location, image_path))
        finally:
            os.remove(temp_location)


    def test_webhooks(self):
        """Test webhooks."""

        account_id = LibMonzoTests.config["test_account_id"]

        # Get the current hooks
        current_hooks = LibMonzoTests.client.list_webhooks(account_id=account_id)

        # Register a new hook
        created_hook = LibMonzoTests.client.register_webhook(account_id=account_id, url="https://example.com")

        # Get the latest hooks
        new_hooks = LibMonzoTests.client.list_webhooks(account_id=account_id)

        # Confirm that the old ones are there
        for old_hook in current_hooks:

            # Try and find the old hook in the new ones
            found_previous = False
            for new_hook in new_hooks:
                if new_hook.identifier == old_hook.identifier:
                    found_previous = True
                    break

            self.assertTrue(found_previous, "Failed to find previous hook")

        # Confirm that the new one is there
        found_new_hook = False
        for hook in new_hooks:
            if hook.identifier == created_hook.identifier:
                found_new_hook = True
                break

        self.assertTrue(found_new_hook, "Failed to find new hook")

        # Finally we can delete it
        LibMonzoTests.client.delete_webhook(webhook_id=created_hook.identifier)

        final_hooks = LibMonzoTests.client.list_webhooks(account_id=account_id)

        # Confirm that our old ones are still there
        for old_hook in current_hooks:

            # Try and find the old hook in the new ones
            found_previous = False
            for final_hook in final_hooks:
                if final_hook.identifier == old_hook.identifier:
                    found_previous = True
                    break

            self.assertTrue(found_previous, "Failed to find previous hook")

        # Confirm that the new one is NOT there
        found_new_hook = False
        for hook in final_hooks:
            if hook.identifier == created_hook.identifier:
                found_new_hook = True
                break

        self.assertFalse(found_new_hook, "Found new hook after deletion")



if __name__ == "__main__":
    unittest.main(verbosity=2)
