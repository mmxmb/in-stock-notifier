from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, BooleanAttribute
import os


class ProductNotificationTable(Model):
    """ DynamoDB table storing information about whether
        notification for an in-stock product has already
        been sent out.
    """

    class Meta:
        table_name = "in-stock-notifications"
        region = "us-east-1"
        if os.environ.get("DEV") and os.environ.get("DEV").lower() == "true":
            host = "http://host.docker.internal:8000"

    # name and url are not used anywhere but make debugging easier
    product_id = UnicodeAttribute(hash_key=True, attr_name="product_id")
    product_name = UnicodeAttribute(attr_name="product_name")
    url = UnicodeAttribute(attr_name="url")
    is_sent = BooleanAttribute(default=False, attr_name="is_sent")
