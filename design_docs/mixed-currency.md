# Mixed-currency support

Discussion: [#401](https://github.com/tuttle-dev/tuttle/discussions/401). Related: #396, #400.

## The problem

Tuttle assumes a freelancer invoices in the currency of the country they are taxed
in. The common real case breaks that assumption: taxed in Germany (EUR), invoicing
US clients in USD.

Today this does not merely lack support — it produces two contradictory wrong
answers at the same time:

- **Revenue KPIs mix currencies.** `compute_kpis` (`tuttle/kpi.py:84`) sums
  `inv.total` over all invoices with no currency check. `KPISummary.to_dict`
  (`tuttle/kpi.py:39`) then formats that sum with `tax_currency`. A $10,000 USD
  invoice is displayed as €10,000.
- **Tax and salary KPIs silently drop them.** `compute_vat_reserves` and
  `compute_spendable_income` (`tuttle/tax_reserves.py:136`, `:263`) and
  `monthly_spendable_breakdown` (`tuttle/kpi.py:254`) skip every invoice whose
  contract currency differs from the tax system's currency.

So foreign revenue inflates the dashboard and vanishes from spendable income
simultaneously. This is the salary confusion reported in #396/#400.

A third, separate defect: `einvoice.py:187` sets the document currency from the
contract but never emits BT-6 (tax currency code) or BT-111 (VAT amount in
accounting currency). EN16931 requires both when the invoice currency differs from
the VAT currency, so a foreign-currency invoice currently produces non-conformant XML.

## Scope decision: no VAT on foreign-currency invoices

The model already distinguishes this case. `TaxCategory.outside_scope` (`model.py:431`)
exists for exactly it: B2B services to a non-EU recipient, where the place of supply
is the recipient's country under § 3a Abs. 2 UStG. Such a supply is not taxable in
Germany, so a USD invoice to a US business **carries no German VAT at all**.

| Case | VAT on the foreign-currency invoice | What conversion must do |
| --- | --- | --- |
| B2B, non-EU client — `outside_scope` | none | Convert totals for revenue, income tax, dashboard. VAT reserve is zero before and after conversion. |
| B2B, EU client — reverse charge, `zero_rated` | 0% | Same. (ZM / UStVA reporting is a separate feature, unrelated to currency.) |
| Place of supply is Germany (B2C etc.) | domestic VAT, e.g. 19% | Real VAT-in-two-currencies: convert the VAT amount, resolve rounding, emit a nonzero BT-111. |

**Only the third row needs VAT conversion machinery, and it is out of scope.** For the
first two — which is what freelance B2B work actually looks like — converted VAT is
arithmetic on zeros. This is what makes the whole feature small: the fix in
`tax_reserves.py` is not "convert VAT reserves", it is "stop skipping foreign
invoices". They contribute converted revenue to the income-tax base and nothing to the
VAT reserve.

Rather than build for the third row, **guard against it**: a contract with a nonzero
`VAT_rate` *and* a currency other than the tax currency would produce quietly wrong
numbers. Detect that combination and warn instead of guessing. If someone hits the
warning, we will know the case is real before spending a week on it.

## Design

**Invoices stay in their contract currency. Only aggregates convert.**

The invoice is a legal document stating what the client owes; it is USD and remains
USD in the PDF, the e-invoice, the invoice list, and the timeline. Conversion to the
user's primary currency happens exclusively where values from multiple invoices are
summed: dashboard KPIs, tax reserves, spendable income, forecasting.

### The rate is a function, not a column

The **ECB monthly average for the month of the invoice date**. Under § 16 Abs. 6
UStG the binding rate is the monthly *Umsatzsteuer-Umrechnungskurs* published by the
BMF, which is derived from ECB reference rates — so the legally required rate and the
sensible default coincide.

A closed month's average never changes, so `rate(currency, month)` is already
deterministic: last year's tax figures cannot move under us. That means **no
`Invoice.fx_rate` column, no migration, and no backfill** — converting on read is
just as stable as freezing a value, and is a function instead of a schema.

Source: `frankfurter.dev` (free, no API key, ECB data, supports date-range averages).
Fetched rates are cached in the existing `app_db` key/value store, which is what makes
the app work offline for months it has already seen. A month with no cached rate and
no network stays unconverted and is flagged — it does not silently count as zero.

Pinning to the *invoice date* means VAT (supply date) and income tax (Zufluss /
payment date) use the same rate. Deliberate simplification; revisit only if the drift
is shown to matter.

**When the column earns its place:** the first time someone must override a rate (a
tax advisor insists on a different one), or wants to see on the invoice which rate was
applied. Add `Invoice.fx_rate` then, nullable, falling back to the function. Not
before.

### Conversion fee: salary only, never tax

The ~1% bank/Wise spread proposed in #401 must **not** reduce taxable revenue — the
taxable amount is the ECB-converted figure. But it does reduce what actually lands in
the account, so it belongs in the "what can I spend" estimate. Applied in
`compute_spendable_income` only. This is the tax-precision vs. salary-estimate
distinction raised in the discussion.

### Settings: a new "Currency conversion" section

Both keys live in the existing `app_db` key/value store via `SettingsIntent` — no
schema change — and get their own fieldset in
`ui/src/components/settings/SettingsView.tsx`, sibling to **Tax & Legal**:

| Key | Default | Meaning |
| --- | --- | --- |
| `currency.primary` | `get_tax_system(operating_country).currency` | Currency for dashboard, tax, and salary figures. EUR, GBP, USD for now. |
| `currency.fx_haircut` | `1.0` (%) | Bank/exchange spread deducted from the salary estimate only. |

Defaulting `currency.primary` from the operating country's tax system means
preselection by country is free and needs no country→currency table.

The section carries a short explainer, because for most users it is inert:

> These settings only matter if you invoice in a currency other than the one you are
> taxed in — for example a USD invoice to a US client while being taxed in Germany.
> Invoices always stay in their own currency; this is how those amounts are converted
> for your dashboard, tax reserves, and salary.
>
> The exchange rate is the ECB monthly average for the invoice's month, which is the
> rate German tax law requires (§ 16 Abs. 6 UStG). The conversion fee is subtracted
> from the salary estimate only — it never reduces your taxable revenue.

If `currency.primary` equals every contract currency in use, the whole section is a
no-op and the numbers are identical to today's.

### Display

Invoice amounts always render in their native currency — in the list, the timeline,
the PDF, and the e-invoice. Converted aggregates are prefixed with `≈`, because they
are approximate.

The **invoice detail view** is the one place both currencies appear together. When the
invoice currency differs from `currency.primary`, show three extra rows:

| Row | Example |
| --- | --- |
| Invoice currency | `USD` |
| Exchange rate | `1 USD = 0.9174 EUR` (ECB monthly average, Mar 2026) |
| Amount in primary currency | `≈ €9,174.00` |

Hidden entirely when the two currencies match, so single-currency users never see them.

This is the "which rate was applied?" question, and it does **not** bring back
`Invoice.fx_rate`: the detail view calls `rate(currency, invoice_month)` like every
other consumer and gets the same deterministic answer. Showing the rate is a read, not
a reason to store it.

## Plan

1. **E-invoice conformance** (independent, ships alone). Emit BT-6 and BT-111 in
   `einvoice.py` when contract currency ≠ tax currency. With a zero-VAT category the
   accounting-currency VAT amount is `0.00`, so this is small — but it is a
   conformance bug today, regardless of the dashboard work.
2. **Settings.** New "Currency conversion" fieldset with `currency.primary` (defaulted
   from the operating country's tax system) and `currency.fx_haircut`, plus the
   explainer.
3. **FX rate module.** `rate(currency, month)` against frankfurter.dev, cached in
   `app_db`. One small module, no schema change, no new heavy dependency.
4. **Convert the aggregates.** Delete the skip branches in `tuttle/kpi.py` and
   `tuttle/tax_reserves.py`; convert invoice totals through `rate()` instead.
   Converted VAT is zero for every in-scope case, so no VAT rounding rules are needed.
   Same call adds the currency / rate / converted-amount rows to the invoice detail
   view.
5. **Salary haircut.** `currency.fx_haircut` applied in `compute_spendable_income`.
6. **Guard the unsupported cases.** Warn on a contract with nonzero `VAT_rate` and a
   currency other than the tax currency, and on a month whose rate could not be
   resolved.

## Out of scope

- **Domestic VAT on a foreign-currency invoice** (third row above) — converted VAT
  amounts, VAT rounding rules, nonzero BT-111. Guarded with a warning instead.
- **Per-invoice stored rate and manual override** (`Invoice.fx_rate`) — the monthly
  average is deterministic, so nothing needs freezing until someone must override it.
- Currencies beyond EUR, GBP, USD.
- Per-client or per-project currency defaults.
- Rate pinned to payment date as well as invoice date.
