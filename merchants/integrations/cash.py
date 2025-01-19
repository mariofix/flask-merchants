from ..core import CoreProvider


class CashProvider(CoreProvider):
    name = "cash-provider"

    def create():
        return {"url": "url", "transaction": "tr_1234"}
