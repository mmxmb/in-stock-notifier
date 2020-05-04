from urllib.parse import urlparse
from dataclasses import dataclass
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from aiohttp import ClientSession
from hashlib import md5


@dataclass
class Product:

    name: str
    url: str

    @property
    def hash(self) -> str:
        """ This is used as DynamoDB hash key in ProductNotificationTable.
        """
        return md5(bytes(self.url, encoding="utf8")).hexdigest()

    @property
    def fqdn(self) -> str:
        """ E.g. https://docs.python.org/3/library/urllib.parse.html => docs.python.org
        """
        return urlparse(self.url).netloc


class UnexpectedFQDN(Exception):
    pass


class StoreInterface(ABC):
    """ Every new store interface has to inherit from this class.
        A child class has to implement `fqdn` property and `_is_in_stock` class method.

        Finally, update `STORE_INTERFACE` dict at the bottom of this file so that the new
        interface can be exported and used by InStockNotifier instance.
    """

    @property
    def fqdn(self):
        """ Fully qualified domain name of the store.
        """
        raise NotImplementedError

    @classmethod
    async def is_in_stock(cls, product: Product, session: ClientSession) -> bool:
        """ Fetches product page and passes it to self._is_in_stock.
        """
        if not cls.is_expected_fqdn(product.fqdn):
            raise UnexpectedFQDN
        resp = await session.request(
            method="GET", url=product.url, raise_for_status=True
        )
        try:
            return cls._is_in_stock(await resp.text())
        except:
            raise  # re-raise exception to caller

    @classmethod
    def is_expected_fqdn(cls, fqdn: str):
        return fqdn == cls.fqdn

    @classmethod
    @abstractmethod
    def _is_in_stock(cls, resp_body: str) -> bool:
        """ Given a string with the product page HTML (`resp_body`), return whether
        the product is in stock.

        One way to implement this method is to use BeautifulSoup for finding elements 
        that indicate wheter the product is in stock.
        """
        raise NotImplementedError


class WellCa(StoreInterface):
    fqdn = "well.ca"

    @classmethod
    def _is_in_stock(cls, resp_body: str):
        soup = BeautifulSoup(resp_body, "html.parser")
        if soup.find(id="add_to_cart_button"):
            return True
        else:
            return False


STORE_INTERFACE = {WellCa.fqdn: WellCa}
