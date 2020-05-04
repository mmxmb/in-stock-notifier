import argparse
import urllib.request
import os

parser = argparse.ArgumentParser(
    description="Saves two HTTP GET response HTML files in the current directory."
)
parser.add_argument(
    "in_stock_url",
    metavar="in_stock_url",
    type=str,
    help="a product page URL with the product in stock",
)
parser.add_argument(
    "out_of_stock_url",
    metavar="out_of_stock_url",
    type=str,
    help="a product page URL with the product out of stock",
)
args = parser.parse_args()

with open(os.path.join(os.getcwd(), "in_stock.html"), "w") as f:
    with urllib.request.urlopen(args.in_stock_url) as r:
        f.write(r.read().decode("utf-8"))

with open(os.path.join(os.getcwd(), "out_of_stock.html"), "w") as f:
    with urllib.request.urlopen(args.out_of_stock_url) as r:
        f.write(r.read().decode("utf-8"))
