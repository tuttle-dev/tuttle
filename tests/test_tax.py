from tuttle import tax


def test_income_tax():
    taxable_income = 42000
    income_tax = tax.income_tax_germany(taxable_income)
