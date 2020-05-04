from in_stock_notifier import InStockNotifier
import asyncio


def run_notifier(event, context):
    """ This is the entry point.
    """
    notifier = InStockNotifier()
    asyncio.run(notifier.check_stocks())
