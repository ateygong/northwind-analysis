"""Question 2: demand over time and the bottom 10% of products."""

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from data import (BLUE, GRAY, INK, INK_2, ORANGE, load_tables, order_lines,
                  save_figure, save_table, style_axes)
from q1_suppliers import supplier_lines, supplier_summary

BOTTOM_SHARE = 0.10   # bottom 10% of active products by total units, whole period
FADING_RATIO = 0.5    # 1998 monthly units < 50% of 1997 -> fading
RISING_RATIO = 1.5    # 1998 monthly units > 150% of 1997 -> picking up


def full_months(lines):
    """Drop order lines from the final, partly covered month.

    The data ends on 6 May 1998, so May 1998 would understate any
    per-month average or monthly total.

    Args:
        lines (pandas.DataFrame): Order lines with OrderDate.

    Returns:
        pandas.DataFrame: ``lines`` without the last calendar month.
    """
    last_full = lines["OrderDate"].max().to_period("M") - 1
    return lines[lines["OrderDate"].dt.to_period("M") <= last_full]


def months_per_year(lines):
    """Count the months with orders in each year.

    Args:
        lines (pandas.DataFrame): Order lines with OrderDate and Year.

    Returns:
        pandas.Series: Number of distinct order months, by year.
    """
    return lines.groupby("Year")["OrderDate"].apply(lambda s: s.dt.to_period("M").nunique())


def product_year_table(tables, lines, months):
    """Build a per-product table of units and revenue by year.

    Yearly and overall totals use every order line. Per-month
    averages use full months only (see full_months).

    Args:
        tables (dict[str, pandas.DataFrame]): Output of load_tables.
        lines (pandas.DataFrame): Order lines from order_lines.
        months (pandas.Series): Full months with orders per year, from
            months_per_year applied to full_months(lines).

    Returns:
        pandas.DataFrame: One row per product, indexed by ProductID,
            with yearly units and revenue, per-month averages, totals,
            category and supplier; sorted by total units descending.
    """
    yearly = lines.pivot_table(index="ProductID", columns="Year",
                               values=["Quantity", "Revenue"], aggfunc="sum", fill_value=0)
    units, revenue = yearly["Quantity"], yearly["Revenue"]
    full = full_months(lines).pivot_table(index="ProductID", columns="Year",
                                          values=["Quantity", "Revenue"], aggfunc="sum")
    full = full.reindex(units.index).fillna(0)
    per_month = full["Quantity"].div(months, axis=1)
    revenue_per_month = full["Revenue"].div(months, axis=1)

    table = tables["products"].set_index("ProductID")[
        ["ProductName", "SupplierID", "CategoryID", "Price", "Discontinued"]]
    table = table.join(units.add_prefix("Units_")).join(revenue.round(2).add_prefix("Revenue_"))
    table = table.join(per_month.round(1).add_prefix("UnitsPerMonth_"))
    table = table.join(revenue_per_month.round(2).add_prefix("RevenuePerMonth_"))
    table["TotalUnits"] = units.sum(axis=1)
    table["TotalRevenue"] = revenue.sum(axis=1).round(2)
    table = table.reset_index().merge(
        tables["categories"][["CategoryID", "CategoryName"]], on="CategoryID"
    ).merge(
        tables["suppliers"][["SupplierID", "CompanyName"]].rename(columns={"CompanyName": "Supplier"}),
        on="SupplierID",
    ).set_index("ProductID")
    return table.sort_values("TotalUnits", ascending=False)


def category_per_month(lines, tables, months):
    """Compute average units per month by category and year.

    Args:
        lines (pandas.DataFrame): Full-month order lines, from
            full_months.
        tables (dict[str, pandas.DataFrame]): Output of load_tables.
        months (pandas.Series): Months with orders per year, from
            months_per_year.

    Returns:
        pandas.DataFrame: Categories by year, sorted by the latest year
            descending.
    """
    lines = lines.merge(tables["products"][["ProductID", "CategoryID"]], on="ProductID").merge(
        tables["categories"][["CategoryID", "CategoryName"]], on="CategoryID")
    units = lines.pivot_table(index="CategoryName", columns="Year", values="Quantity", aggfunc="sum")
    per_month = units.div(months, axis=1)
    return per_month.sort_values(per_month.columns[-1], ascending=False)


def classify_trend(units_1997, units_1998):
    """Label a product's demand trend from 1997 to 1998.

    Args:
        units_1997 (float): Average units per month in 1997.
        units_1998 (float): Average units per month in 1998.

    Returns:
        str: "Fading" if 1998 is below 0.5x of 1997, "Picking up" if
            above 1.5x, otherwise "Steady". With no 1997 units, any
            1998 units count as "Picking up".
    """
    if units_1997 == 0:
        return "Picking up" if units_1998 > 0 else "Steady"
    ratio = units_1998 / units_1997
    if ratio < FADING_RATIO:
        return "Fading"
    if ratio > RISING_RATIO:
        return "Picking up"
    return "Steady"


def bottom_products(product_table):
    """Select the bottom 10% of active products by total units.

    Discontinued products are excluded before ranking.

    Args:
        product_table (pandas.DataFrame): Output of product_year_table.

    Returns:
        tuple[pandas.DataFrame, int, int]: The bottom products with a
            Trend column; the number selected; and the number of
            active products.
    """
    # Discontinued products are excluded: the decision to drop them is already made.
    active = product_table[~product_table["Discontinued"]]
    n = int(round(len(active) * BOTTOM_SHARE))
    bottom = active.nsmallest(n, "TotalUnits").copy()
    bottom["Trend"] = [classify_trend(a, b) for a, b in
                       zip(bottom["UnitsPerMonth_1997"], bottom["UnitsPerMonth_1998"])]
    cols = ["ProductName", "CategoryName", "Supplier", "Price", "TotalUnits", "TotalRevenue",
            "UnitsPerMonth_1996", "UnitsPerMonth_1997", "UnitsPerMonth_1998",
            "RevenuePerMonth_1997", "RevenuePerMonth_1998", "Trend", "SupplierID"]
    return bottom[cols], n, len(active)


def summary_metrics(tables, lines, product_table, bottom):
    """Summarize the bottom products and link them to Question 1.

    Args:
        tables (dict[str, pandas.DataFrame]): Output of load_tables.
        lines (pandas.DataFrame): Order lines from order_lines.
        product_table (pandas.DataFrame): Output of product_year_table.
        bottom (pandas.DataFrame): Output of bottom_products.

    Returns:
        pandas.Series: Count, unit and revenue shares in percent, trend
            counts, and how many come from low-contribution suppliers.
    """
    suppliers, _ = supplier_summary(tables, supplier_lines(tables, lines))
    low_suppliers = set(suppliers.index[suppliers["Reliance"] == "Low contribution"])
    from_low = bottom[bottom["SupplierID"].isin(low_suppliers)]
    return pd.Series({
        "BottomProducts": len(bottom),
        "BottomUnitsSharePct": 100 * bottom["TotalUnits"].sum() / product_table["TotalUnits"].sum(),
        "BottomRevenueSharePct": 100 * bottom["TotalRevenue"].sum() / product_table["TotalRevenue"].sum(),
        "Fading": int((bottom["Trend"] == "Fading").sum()),
        "PickingUp": int((bottom["Trend"] == "Picking up").sum()),
        "Steady": int((bottom["Trend"] == "Steady").sum()),
        "FromLowContributionSuppliers": len(from_low),
        "LowContributionSuppliersInvolved": "; ".join(sorted(from_low["Supplier"].unique())),
    })


def monthly_units(lines, bottom_ids):
    """Total units ordered per month, overall and for bottom products.

    The last month is dropped because the data covers only part of it.

    Args:
        lines (pandas.DataFrame): Order lines from order_lines.
        bottom_ids (pandas.Index): ProductIDs of the bottom products.

    Returns:
        pandas.DataFrame: AllProducts and Bottom10 units, indexed by
            monthly period.
    """
    # The data ends on a partial month (orders stop early in May 1998), so the
    # last month is dropped to avoid a misleading drop at the end of the line.
    last_full = lines["OrderDate"].max().to_period("M") - 1
    period = lines["OrderDate"].dt.to_period("M")
    keep = period <= last_full
    total = lines[keep].groupby(period[keep])["Quantity"].sum()
    is_bottom = keep & lines["ProductID"].isin(bottom_ids)
    bottom = lines[is_bottom].groupby(period[is_bottom])["Quantity"].sum().reindex(total.index, fill_value=0)
    return pd.DataFrame({"AllProducts": total, "Bottom10": bottom})


def bottom_table(bottom):
    """Format the bottom products for the output table.

    Adds the 1997-to-1998 change in units and revenue per month.

    Args:
        bottom (pandas.DataFrame): Output of bottom_products.

    Returns:
        pandas.DataFrame: Product, category, supplier, price, total
            revenue, per-month units, changes and trend.
    """
    bottom = bottom.assign(
        ChangeUnitsPerMonth=bottom["UnitsPerMonth_1998"] - bottom["UnitsPerMonth_1997"],
        ChangeRevenuePerMonth=bottom["RevenuePerMonth_1998"] - bottom["RevenuePerMonth_1997"])
    return bottom.rename(columns={
        "ProductName": "Product", "CategoryName": "Category",
        "UnitsPerMonth_1997": "UnitsPerMonth1997", "UnitsPerMonth_1998": "UnitsPerMonth1998",
    })[["Product", "Category", "Supplier", "Price", "TotalRevenue", "UnitsPerMonth1997", "UnitsPerMonth1998", "ChangeUnitsPerMonth", "ChangeRevenuePerMonth", "Trend"]]


def plot_monthly(monthly, n_bottom):
    """Plot monthly units for all products and the bottom 10%.

    Args:
        monthly (pandas.DataFrame): Output of monthly_units.
        n_bottom (int): Number of bottom products, for the legend.

    Returns:
        None. Saves q2_monthly_orders.png.
    """
    x = monthly.index.to_timestamp()
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.fill_between(x, 0, monthly["AllProducts"], color="#a9c8ee", alpha=0.6, linewidth=0)
    ax.plot(x, monthly["AllProducts"], color=BLUE, linewidth=2, label="All products")
    ax.plot(x, monthly["Bottom10"], color=ORANGE, linewidth=2, label=f"Bottom 10% ({n_bottom} products)")
    for col in ("AllProducts", "Bottom10"):
        ax.text(x[-1], monthly[col].iloc[-1], f" {monthly[col].iloc[-1]:,}", va="center", fontsize=9, color=INK)
    ax.set_ylabel("Units ordered per month")
    ax.set_ylim(0)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    first, last = monthly.index[0].strftime("%b %Y"), monthly.index[-1].strftime("%b %Y")
    ax.set_title("Total demand keeps climbing, while the bottom 10% hold stagnant",
                 loc="left", fontsize=12.5, pad=24)
    ax.text(0, 1.03, f"Monthly orders, {first} – {last}", transform=ax.transAxes,
            fontsize=10, color=INK_2)
    ax.legend(frameon=False, loc="upper left")
    ax.grid(axis="y", color=GRAY, alpha=0.3)
    style_axes(ax)
    save_figure(fig, "q2_monthly_orders.png")


def run():
    """Run the Question 2 analysis.

    Args:
        None.

    Returns:
        None. Saves the Q2 tables and chart and prints a summary.
    """
    tables = load_tables()
    lines = order_lines(tables)
    full = full_months(lines)
    months = months_per_year(full)
    product_table = product_year_table(tables, lines, months)
    categories = category_per_month(full, tables, months)
    bottom, n, n_active = bottom_products(product_table)
    metrics = summary_metrics(tables, lines, product_table, bottom)
    company = full.groupby("Year")[["Quantity", "Revenue"]].sum().div(months, axis=0)
    monthly = monthly_units(lines, bottom.index)
    table = bottom_table(bottom)

    save_table(product_table, "q2_product_by_year.csv")
    save_table(categories.round(1), "q2_category_units_per_month.csv")
    save_table(company.round(1).rename(columns={"Quantity": "UnitsPerMonth", "Revenue": "RevenuePerMonth"}),
               "q2_company_per_month.csv")
    save_table(monthly, "q2_monthly_units.csv")
    save_table(table.round(2), "q2_bottom10_products.csv")
    save_table(metrics.to_frame("Value"), "q2_summary_metrics.csv")
    plot_monthly(monthly, n)

    print("Q2 - company per month by year\n", company.round(0).to_string())
    print("\nQ2 - monthly units\n", monthly.to_string())
    print(f"\nQ2 - bottom {n} of {n_active} active products\n", table.round(1).to_string())
    print("\nQ2 - summary\n", metrics.to_string())


if __name__ == "__main__":
    run()
