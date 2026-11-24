"""Question 1: how reliant Northwind is on individual suppliers."""

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Patch

from data import (BLUE, INK, ORANGE, load_tables, order_lines,
                  save_figure, save_table, style_axes)

OVER_RELIANT_MULTIPLE = 2.0      # revenue share >= 2x an equal ("fair") share
LOW_CONTRIBUTION_MULTIPLE = 0.5  # revenue share <= 0.5x an equal share
LIGHT_GRAY = "#d9d8d2"
SHORT_NAMES = {"Plutzer Lebensmittelgroßmärkte AG": "Plutzer"}


def hhi(shares_pct):
    """Compute the Herfindahl-Hirschman Index of shares.

    Args:
        shares_pct (pandas.Series): Shares in percent (0-100).

    Returns:
        float: Sum of squared shares, from near 0 up to 10,000.
    """
    return float((shares_pct ** 2).sum())


def supplier_lines(tables, lines):
    """Attach product and supplier details to each order line.

    Args:
        tables (dict[str, pandas.DataFrame]): Output of load_tables.
        lines (pandas.DataFrame): Order lines from order_lines.

    Returns:
        pandas.DataFrame: ``lines`` with ProductName, Discontinued,
            SupplierID, CompanyName and Country added.
    """
    products = tables["products"].merge(
        tables["suppliers"][["SupplierID", "CompanyName", "Country"]], on="SupplierID"
    )
    return lines.merge(
        products[["ProductID", "ProductName", "Discontinued", "SupplierID", "CompanyName", "Country"]],
        on="ProductID",
    )


def supplier_summary(tables, lines):
    """Summarize revenue by supplier and flag reliance levels.

    A supplier is "Over-reliant" at 2x or more of an equal share of
    revenue, "Low contribution" at 0.5x or less, otherwise "Typical".

    Args:
        tables (dict[str, pandas.DataFrame]): Output of load_tables.
        lines (pandas.DataFrame): Order lines from supplier_lines.

    Returns:
        tuple[pandas.DataFrame, float]: One row per supplier, sorted by
            revenue, with share, reliance and top-product columns; and
            the equal ("fair") share in percent.
    """
    by_product = (
        lines.groupby(["SupplierID", "ProductName", "Discontinued"])["Revenue"].sum()
        .reset_index().sort_values("Revenue", ascending=False)
    )
    top_product = by_product.groupby("SupplierID").head(1).set_index("SupplierID")

    summary = lines.groupby("SupplierID").agg(
        Supplier=("CompanyName", "first"),
        Country=("Country", "first"),
        Revenue=("Revenue", "sum"),
        Orders=("OrderID", "nunique"),
    )
    summary["Products"] = tables["products"].groupby("SupplierID").size()
    summary["DiscontinuedProducts"] = tables["products"].groupby("SupplierID")["Discontinued"].sum()
    summary["RevenueSharePct"] = 100 * summary["Revenue"] / summary["Revenue"].sum()

    fair_share = 100 / len(summary)
    summary["xFairShare"] = summary["RevenueSharePct"] / fair_share
    summary["Reliance"] = "Typical"
    summary.loc[summary["xFairShare"] >= OVER_RELIANT_MULTIPLE, "Reliance"] = "Over-reliant"
    summary.loc[summary["xFairShare"] <= LOW_CONTRIBUTION_MULTIPLE, "Reliance"] = "Low contribution"

    summary["TopProduct"] = top_product["ProductName"]
    summary["TopProductDiscontinued"] = top_product["Discontinued"]
    summary["TopProductPctOfSupplier"] = 100 * top_product["Revenue"] / summary["Revenue"]
    summary["TopProductPctOfTotal"] = 100 * top_product["Revenue"] / summary["Revenue"].sum()
    return summary.sort_values("Revenue", ascending=False), fair_share


def concentration_metrics(summary):
    """Compute supplier concentration measures.

    Args:
        summary (pandas.DataFrame): Output of supplier_summary, sorted
            by revenue descending.

    Returns:
        dict[str, float | int]: Supplier count, fair share, HHI, top
            1/2/5 shares, and the count and share of each reliance
            group. Shares are in percent.
    """
    shares = summary["RevenueSharePct"]
    return {
        "Suppliers": len(summary),
        "FairSharePct": 100 / len(summary),
        "SupplierHHI": hhi(shares),
        "Top1SharePct": shares.iloc[0],
        "Top2SharePct": shares.iloc[:2].sum(),
        "Top5SharePct": shares.iloc[:5].sum(),
        "OverReliantCount": int((summary["Reliance"] == "Over-reliant").sum()),
        "OverReliantSharePct": shares[summary["Reliance"] == "Over-reliant"].sum(),
        "LowContributionCount": int((summary["Reliance"] == "Low contribution").sum()),
        "LowContributionSharePct": shares[summary["Reliance"] == "Low contribution"].sum(),
        "OtherSuppliersAvgSharePct": shares[summary["Reliance"] != "Over-reliant"].mean(),
    }


def country_context(summary):
    """Total suppliers and revenue share by supplier country.

    Args:
        summary (pandas.DataFrame): Output of supplier_summary.

    Returns:
        pandas.DataFrame: Suppliers and RevenueSharePct per country,
            largest share first.
    """
    by_country = summary.groupby("Country").agg(
        Suppliers=("Supplier", "count"), RevenueSharePct=("RevenueSharePct", "sum")
    )
    return by_country.sort_values("RevenueSharePct", ascending=False)


def plot_supplier_shares(summary, fair_share):
    """Plot revenue share of the top, middle and bottom suppliers.

    Over-reliant and low-contribution suppliers get their own bars;
    typical suppliers are shown as one average bar.

    Args:
        summary (pandas.DataFrame): Output of supplier_summary.
        fair_share (float): Equal share in percent. Not used in the
            current chart.

    Returns:
        None. Saves q1_supplier_reliance.png.
    """
    data = summary.sort_values("RevenueSharePct", ascending=False)
    top = data[data["Reliance"] == "Over-reliant"]
    low = data[data["Reliance"] == "Low contribution"]
    middle = data[data["Reliance"] == "Typical"]

    # Name the top and bottom suppliers; the middle group is shown as one average bar.
    labels = ([SHORT_NAMES.get(n, n) for n in top["Supplier"]]
              + [f"{len(middle)} remaining suppliers (average)"]
              + [SHORT_NAMES.get(n, n) for n in low["Supplier"]])
    values = list(top["RevenueSharePct"]) + [middle["RevenueSharePct"].mean()] + list(low["RevenueSharePct"])
    colors = [ORANGE] * len(top) + [LIGHT_GRAY] + [BLUE] * len(low)

    fig, ax = plt.subplots(figsize=(8.5, 5.6))
    ax.barh(labels[::-1], values[::-1], color=colors[::-1], height=0.65)
    for i, v in enumerate(values[::-1]):
        ax.text(v + 0.15, i, f"{v:.1f}%", va="center", fontsize=9, color=INK)
    ax.set_xlabel("Share of total revenue (%)")
    ax.set_xlim(0, max(values) * 1.15)
    ax.tick_params(axis="y", labelsize=9.5)
    ax.set_title(f"Our top {len(top)} suppliers bring in {top['RevenueSharePct'].sum():.0f}% "
                 f"of our total revenue,\nwhile our bottom {len(low)} bring in just "
                 f"{low['RevenueSharePct'].sum():.0f}% of revenue", loc="left", fontsize=12.5)
    ax.legend(handles=[
        Patch(color=ORANGE, label=f"Top {len(top)} suppliers ({top['RevenueSharePct'].sum():.0f}% of revenue)"),
        Patch(color=LIGHT_GRAY, label=f"{len(middle)} remaining suppliers ({middle['RevenueSharePct'].sum():.0f}%)"),
        Patch(color=BLUE, label=f"{len(low)} smallest suppliers ({low['RevenueSharePct'].sum():.0f}%)"),
    ], frameon=False, loc="lower right", fontsize=9)
    style_axes(ax)
    save_figure(fig, "q1_supplier_reliance.png")


def run():
    """Run the Question 1 analysis.

    Args:
        None.

    Returns:
        None. Saves the Q1 tables and chart and prints a summary.
    """
    tables = load_tables()
    lines = supplier_lines(tables, order_lines(tables))
    summary, fair_share = supplier_summary(tables, lines)
    metrics = concentration_metrics(summary)
    over = summary[summary["Reliance"] == "Over-reliant"][
        ["Supplier", "Country", "RevenueSharePct", "xFairShare", "TopProduct",
         "TopProductPctOfSupplier", "TopProductPctOfTotal", "TopProductDiscontinued"]
    ]
    low = summary[summary["Reliance"] == "Low contribution"][
        ["Supplier", "Country", "Products", "DiscontinuedProducts", "RevenueSharePct", "xFairShare"]
    ]

    save_table(summary.round(2), "q1_suppliers.csv")
    save_table(over.round(2), "q1_over_reliant_suppliers.csv")
    save_table(low.round(2), "q1_low_contribution_suppliers.csv")
    save_table(country_context(summary).round(2), "q1_country_context.csv")
    metrics_table = pd.Series(metrics).round(2).to_frame("Value")
    save_table(metrics_table, "q1_concentration_metrics.csv")
    plot_supplier_shares(summary, fair_share)

    print("Q1 - concentration metrics\n", metrics_table.to_string())
    print("\nQ1 - over-reliant suppliers\n", over.round(1).to_string())
    print("\nQ1 - low-contribution suppliers\n", low.round(2).to_string())
    print("\nQ1 - country context\n", country_context(summary).round(1).head(4).to_string())


if __name__ == "__main__":
    run()
