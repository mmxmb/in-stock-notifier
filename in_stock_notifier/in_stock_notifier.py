from typing import List, Any, Hashable
import boto3
import logging
import os
from product_notification_table import ProductNotificationTable
from store_interface import Product, UnexpectedFQDN, STORE_INTERFACE
from urllib.parse import urlparse
from aiohttp import ClientSession, ClientResponseError
import csv
import asyncio


class InStockNotifier:
    def __init__(self) -> None:
        """ Initializes self.products, logging and creates notification table.
        """
        self.import_products_csv()
        if not ProductNotificationTable.exists():
            ProductNotificationTable.create_table(
                wait=True, billing_mode="PAY_PER_REQUEST"
            )

        self.ses = None  # initialize the client later only when it's actually needed

        fmt = "%(asctime)s %(message)s"
        logging.basicConfig(format=fmt)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    def import_products_csv(self):
        """ Loads Product objects from products.csv in project root dir.
        """
        self.products = []
        with open(
            os.path.join(os.path.dirname(os.path.realpath(__file__)), "products.csv"),
            newline="",
        ) as f:
            csv_reader = csv.reader(f)
            next(csv_reader)  # skip column names
            for product_name, url in csv_reader:
                self.products.append(Product(product_name, url))

    def send_notification(self, product: Product) -> bool:
        """ Sends notification about a product in stock from EMAIL_FROM
            to EMAIL_TO. Returns True if the message is sent successfully
            and False otherwise.
        """
        if not os.environ.get("EMAIL_FROM"):
            self.logger.error("EMAIL_FROM environment varialbe is not specified")
            return False
        email_from = os.environ.get("EMAIL_FROM")
        if not os.environ.get("EMAIL_TO"):
            self.logger.error("EMAIL_TO environment varialbe is not specified")
            return False
        email_to = os.environ.get("EMAIL_TO")
        if os.environ.get("DEV") and os.environ.get("DEV").lower() == "true":
            self.logger.info(
                "Not sending email via SES "
                f"for {product.name} in {product.fqdn} since DEV=true"
            )
            return True
        if not self.ses:
            self.ses = boto3.client("ses")
        resp = self.ses.send_templated_email(
            Source=email_from,
            Destination={"ToAddresses": [email_to]},
            Template="in-stock-notification",
            TemplateData=f'{{ "product_name": "{product.name}",'
            f'"store_name": "{product.fqdn}", '
            f'"url": "{product.url}" }}',
        )
        if safeget(resp, "ResponseMetadata", "HTTPStatusCode") == 200:
            self.logger.info(
                "Successfully sent email notification "
                f"for {product.name} at {product.fqdn}"
            )
            return True
        else:
            self.logger.error(
                f"Failed to send notification for {product.name} in "
                f"{product.fqdn}. Response from ses.send_templated_email: {resp}"
            )
            return False

    def has_already_notified(self, product: Product) -> bool:
        """ Checks if an in-stock notification has already been sent
            for this product.

            Since boto3 is used here, this method is blocking.
        """
        try:
            notification = ProductNotificationTable.get(product.hash)
            return notification.is_sent
        except ProductNotificationTable.DoesNotExist:
            # this product has not been yet added to the table
            notification_item = ProductNotificationTable(
                product.hash, product_name=product.name, url=product.url
            )
            notification_item.save()
            return False

    async def check_stock_and_notify(
        self, product: Product, session: ClientSession
    ) -> None:
        """ Checks if a product is in stock. If it is, checks if an email notification
            about this has already been sent. If not, send it, then update the table to
            reflect that the notification has been sent.

            Note: sending an email and updating the table are both blocking.
        """
        fqdn = urlparse(product.url).netloc
        if fqdn not in STORE_INTERFACE:
            self.logger.warning(
                f"Store interface is not implemented for {fqdn}. Skipping this product."
            )
            return
        store_interface = STORE_INTERFACE[fqdn]
        try:
            in_stock = await store_interface.is_in_stock(product, session)
            self.logger.info(f"Product {product.name} is in stock: {in_stock}")
        except UnexpectedFQDN:
            self.logger.warning(
                f"Store interface is not implemented for {fqdn}."
                "This exception should have not happened. Skipping this product."
            )
            return
        except ClientResponseError:
            self.logger.warning(
                f"Couldn't successfully load {product.url}. Skipping this product."
            )
            return
        if in_stock:
            if not self.has_already_notified(product):
                result = self.send_notification(product)
                if not result:  # failed to send email; something wrong with SES config
                    return
                self.update_notification_table(product)

    def update_notification_table(self, product: Product) -> None:
        """ Checks notification table to find out if a notification email 
            has already been sent about this product.

            Since pynamodb is used, this method is blocking.
        """
        notification_item = ProductNotificationTable.get(product.hash)
        notification_item.update(actions=[ProductNotificationTable.is_sent.set(True)])
        notification_item.save()

    async def check_stocks(self) -> None:
        """ Checks if products that the notifier tracks are in stock.
            Sends out notifications if products are in stock.
        """
        self.logger.info("Started execution")
        async with ClientSession() as session:
            tasks = []
            for product in self.products:
                tasks.append(self.check_stock_and_notify(product, session))
            await asyncio.gather(*tasks)
        self.logger.info("Finished execution")


def safeget(dct: dict, *keys: Hashable) -> Any:
    """ Safely get value from a nested dict; like Hash#dig in Ruby.
        See: https://stackoverflow.com/questions/25833613/python-safe-method-to-get-value-of-nested-dictionary
    """
    if type(dct) is not dict:
        return None
    for key in keys:
        try:
            dct = dct[key]
        except KeyError:
            return None
    return dct
