"""Functionality related to taxation."""


from decimal import Decimal
from unittest.loader import VALID_MODULE_NAME


def income_tax(taxable_income: Decimal, country: str) -> Decimal:
    """[summary]

    Args:
        taxable_income (Decimal): [description]
        country (str): [description]

    Returns:
        Decimal: [description]
    """
    if country == "Germany":
        return income_tax_germany(taxable_income)
    else:
        raise NotImplementedError(
            f"income tax formula for {country} not yet implemented"
        )


def income_tax_germany(taxable_income: Decimal) -> Decimal:
    """Income tax formula for Germany.

    Args:
        taxable_income (Decimal): [description]

    Returns:
        Decimal: [description]
    """
    ti = taxable_income
    if ti <= 9408:
        tax = 0
    elif 9408 < ti <= 14532:
        tax = (0.14 + (ti - 9408) * 972.87 * 1e-8) * (ti - 9408)
    elif 14532 < ti <= 57051:
        tax = (0.2397 + (ti - 14532) * 212.02 * 1e-8) * (ti - 14532) + 972.79
    elif 57051 < ti <= 270500:
        tax = (0.42 * ti) - 8963.74
    else:
        tax = 0.45 * ti - 17078.74
    tax = round(tax)
    return tax
