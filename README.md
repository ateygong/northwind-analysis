# Northwind Traders: Suppliers, Products and Markets

Analysis of the Northwind Database that answers three business questions:

1. **Supplier reliance:** How reliant are we on individual suppliers, in both directions?
2. **Products:** How much of each product is ordered per year, and which products should we re-evaluate selling?
3. **Markets and sales staff:** Are our sales staff focused on our most valuable markets?

The results are presented on the webpage `index.html`. Every number, chart and table on the page comes from the Python code in `src/`.

## Repository layout

```
Northwind Database.xlsx   Source data (one sheet per table)
requirements.txt          Pinned Python packages
src/
  data.py                 Loads the workbook, calculates revenue, shared chart and save helpers
  q1_suppliers.py         Question 1: supplier revenue shares, reliance flags, HHI
  q2_products.py          Question 2: monthly demand and the bottom 10% of products
  q3_customers.py         Question 3: revenue by region and by staff office, country median split
  run_analysis.py         Runs all three questions
outputs/
  figures/                Charts used on the webpage (PNG)
  tables/                 Tables behind every number on the webpage (CSV)
index.html                The webpage
```

## How to reproduce

Requires Python 3.9 or newer.

1. Clone the repository and move into it:

   ```bash
   git clone <repository-url>
   cd <repository-folder>
   ```

2. Create a virtual environment and install the packages:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Run the full analysis:

   ```bash
   python src/run_analysis.py
   ```

   This reads `Northwind Database.xlsx`, rewrites every file in `outputs/figures/` and `outputs/tables/`, and prints a summary of each question to the terminal. Each question can also be run on its own, for example `python src/q1_suppliers.py`.

4. View the webpage by opening `index.html` in a browser, or serve the folder locally so the charts load:

   ```bash
   python3 -m http.server 8000
   ```

   Then go to http://localhost:8000.

## Where each result comes from

| Webpage element | Produced by | Output file(s) |
|---|---|---|
| Key metrics (revenue, orders, products, suppliers, customers) | `q1_suppliers.py`, `q2_products.py`, `q3_customers.py` | Revenue, orders and customers: column totals of `q3_customer_countries.csv`. Suppliers: rows of `q1_suppliers.csv`. Products: rows of `q2_product_by_year.csv` |
| Q1 chart: top 4 vs bottom 8 suppliers | `q1_suppliers.py` | `figures/q1_supplier_reliance.png` |
| Q1 numbers: shares, HHI, top product per supplier | `q1_suppliers.py` | `q1_concentration_metrics.csv`, `q1_over_reliant_suppliers.csv`, `q1_low_contribution_suppliers.csv`, `q1_suppliers.csv` |
| Q2 chart: monthly units, all products vs bottom 10% | `q2_products.py` | `figures/q2_monthly_orders.png`, `q2_monthly_units.csv` |
| Q2 table: bottom-10% products and their 1997 to 1998 change | `q2_products.py` | `q2_bottom10_products.csv` |
| Q2 numbers: units and revenue per month by year, shares | `q2_products.py` | `q2_company_per_month.csv`, `q2_summary_metrics.csv`, `q2_product_by_year.csv` |
| Q3 chart: revenue by region, split by staff office | `q3_customers.py` | `figures/q3_region_staff.png`, `q3_region_by_office.csv` |
| Q3 numbers: six "few customers, high value" countries and their largest customers | `q3_customers.py` | `q3_customer_countries.csv`, `q3_target_country_customers.csv` |
| Q3 numbers: countries served per employee | `q3_customers.py` | `q3_reps.csv` |

## Method notes

- **Revenue** = UnitPrice × Quantity × (1 − Discount), calculated from the Order Details sheet.
- **Partial years:** the data runs from July 1996 to early May 1998, so comparisons between years use averages per month, not yearly totals. Monthly line charts leave out May 1998 because it is only partly covered.
- **Q1:** a supplier is *over-reliant* if its revenue share is at least 2× an equal share (1/29 = 3.45%), and *low contribution* if it is at most 0.5×. Concentration is measured with the Herfindahl-Hirschman Index (HHI) of supplier revenue shares.
- **Q2:** the bottom 10% is taken from the 69 active products (the 8 discontinued products are left out), ranked by total units over the whole period. A product is *fading* if its 1998 units per month are below half of 1997, and *picking up* if above 1.5×.
- **Q3:** countries are grouped into Europe, North America (USA, Canada, Mexico) and South America (Brazil, Argentina, Venezuela). Each order is linked to the office of the employee who handled it (5 in the US, 4 in the UK). "Few customers, high value" countries are found with a median split on number of customers and revenue per customer.
- The Product sheet contains some leftover helper columns (Cheap, NewPrice, IsCheap) that are not part of the original Northwind data; the code ignores them.

## Code documentation

All modules and functions in `src/` have PEP 257 docstrings (Google style), written with the course's `python-docstrings` skill, included in this repository as `SKILL.md`.
