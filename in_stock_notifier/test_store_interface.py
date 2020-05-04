import os
from store_interface import WellCa

HTML_DIR = os.path.join(os.path.dirname(__file__), "test_html")


def test_well_ca_in_stock():
    with open(os.path.join(HTML_DIR, "well_ca_in_stock.html"), "r") as f:
        page_html = f.read()
        assert WellCa._is_in_stock(page_html)


def test_well_ca_out_of_stock():
    with open(os.path.join(HTML_DIR, "well_ca_out_of_stock.html"), "r") as f:
        page_html = f.read()
        assert not WellCa._is_in_stock(page_html)
