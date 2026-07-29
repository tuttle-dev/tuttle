import datetime
import enum


class ContractType(enum.Enum):
    """How a contract is priced. The single discriminator that decides
    whether a contract is time-based (a ``rate`` per unit) or fixed-price
    (a single ``fixed_price``). A contract is always exactly one of these.
    """

    time_based = "time_based"
    fixed_price = "fixed_price"

    def __str__(self):
        return str(self.value)


class ChargeBasis(enum.Enum):
    """How an additional contract charge is quantified on an invoice.

    ``per_unit`` charges scale with the billed time quantity — three billed
    days of work carry three daily fees. The other two are flat: one is
    repeated on every invoice, the other is billed a single time over the
    whole life of the contract.
    """

    per_unit = "per_unit"
    per_invoice = "per_invoice"
    once = "once"

    def __str__(self):
        return str(self.value)


class Cycle(enum.Enum):
    hourly = "hourly"
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    quarterly = "quarterly"
    yearly = "yearly"

    def __str__(self):
        return str(self.value)


class TimeUnit(enum.Enum):
    # minute = "minute"
    hour = "hour"
    day = "day"

    def to_timedelta(self):
        if self == TimeUnit.hour:
            return datetime.timedelta(hours=1)
        elif self == TimeUnit.day:
            return datetime.timedelta(days=1)

    @property
    def abbrev(self) -> str:
        """Short display label, e.g. 'h' or 'd'."""
        _abbrevs = {TimeUnit.hour: "h", TimeUnit.day: "d"}
        return _abbrevs.get(self, self.value)

    def __str__(self):
        return str(self.value)
