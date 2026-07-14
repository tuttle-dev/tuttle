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
the VAT currency, so a USD invoice carrying German VAT currently produces
non-conformant XML.

## Design

**Invoices stay in their contract currency. Only aggregates convert.**

The invoice is a legal document stating what the client owes; it is USD and remains
USD in the PDF, the e-invoice, the invoice list, and the timeline. Conversion to the
user's primary currency happens exclusively where values from multiple invoices are
summed: dashboard KPIs, tax reserves, spendable income, forecasting.

### Freeze the rate on the invoice

Add a nullable `Invoice.fx_rate` (Numeric) column, populated once when the invoice
is created and never recomputed. The alternative — converting on the fly from a live
rate table — would make last year's tax figures change every time the app is opened,
which is unusable for anything that gets filed. This is the only schema migration
the feature needs.

### Which rate

The **ECB monthly average for the month of the invoice date**. Under § 16 Abs. 6
UStG the binding rate is the monthly *Umsatzsteuer-Umrechnungskurs* published by the
BMF, which is derived from ECB reference rates — so the legally required rate and the
sensible default coincide.

Source: `frankfurter.dev` (free, no API key, ECB data, supports date-range averages).
Cached in the existing `app_db` key/value settings store. On fetch failure or
offline, fall back to a manual rate field on the invoice, prefilled where a cached
value exists.

Pinning to the *invoice date* means VAT (supply date) and income tax (Zufluss /
payment date) use the same rate. This is a deliberate simplification: one rate per
invoice, one column. Revisit only if the drift is shown to matter.

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

Individual invoices always render in their native currency. Converted aggregates are
marked as approximate (`≈` or a footnote), because they are.

## Plan

1. **E-invoice conformance** (independent, ships alone). Emit BT-6 and BT-111 in
   `einvoice.py` when contract currency ≠ tax currency. This is a correctness bug
   today, regardless of the dashboard work.
2. **Settings.** New "Currency conversion" fieldset with `currency.primary` (defaulted
   from the operating country's tax system) and `currency.fx_haircut`, plus the
   explainer.
3. **FX rate module.** Fetch the ECB monthly average, cache it, expose a manual
   override. One small module, no new heavy dependency.
4. **Migration + capture.** `Invoice.fx_rate`, populated at invoice creation;
   backfill existing invoices lazily on first read rather than in a batch job.
5. **Convert the aggregates.** Replace the currency filters in `tuttle/kpi.py` and
   `tuttle/tax_reserves.py` with conversion via `fx_rate`. Delete the skip branches.
6. **Salary haircut.** `currency.fx_haircut` applied in `compute_spendable_income`.

### Check before building step 5

For a German freelancer with US B2B clients, the place of supply is the US: no German
VAT, reverse charge, 0% rate. If that is the setup, the VAT-reserve path is mostly
inert and the work collapses to income tax plus dashboard display. Confirm before
building VAT-in-two-currencies machinery that never runs.

## Out of scope

- Currencies beyond EUR, GBP, USD.
- Batch backfill of historical rates (lazy on first view instead).
- Per-client or per-project currency defaults.
- Rate pinned to payment date as well as invoice date.
