"""Question 3: sales staff coverage of the most valuable markets."""

import matplotlib.pyplot as plt

from data import (BLUE, INK, ORANGE, load_tables, order_lines,
                  save_figure, save_table, style_axes)

NORTH_AMERICA = {"USA", "Canada", "Mexico"}
SOUTH_AMERICA = {"Brazil", "Argentina", "Venezuela"}


def region_of(country):
    """Map a customer country to its region.

    Args:
        country (str): Customer country name.

    Returns:
        str: "North America", "South America", or "Europe" for any
            other country.
    """
    if country in NORTH_AMERICA:
        return "North America"
    if country in SOUTH_AMERICA:
        return "South America"
    return "Europe"


def country_summary(tables, lines):
    """Summarize customers and revenue by country with a median split.

    A country is flagged FewButHighValue if it has fewer ordering
    customers than the median country and above-median revenue per
    customer.

    Args:
        tables (dict[str, pandas.DataFrame]): Output of load_tables.
        lines (pandas.DataFrame): Order lines from order_lines.

    Returns:
        tuple[pandas.DataFrame, float, float]: One row per country,
            sorted by revenue per customer; the median customer count;
            and the median revenue per customer.
    """
    lines = lines.merge(tables["customers"][["CustomerID", "Country"]], on="CustomerID")
    summary = lines.groupby("Country").agg(
        Customers=("CustomerID", "nunique"),  # customers who placed at least one order
        Orders=("OrderID", "nunique"),
        Revenue=("Revenue", "sum"),
    )
    summary["RevenuePerCustomer"] = summary["Revenue"] / summary["Customers"]
    summary["RevenueSharePct"] = 100 * summary["Revenue"] / summary["Revenue"].sum()

    med_customers = summary["Customers"].median()
    med_rpc = summary["RevenuePerCustomer"].median()
    # Plain median split: fewer customers than the median country AND
    # above-median revenue per customer.
    summary["FewButHighValue"] = (summary["Customers"] < med_customers) & (
        summary["RevenuePerCustomer"] > med_rpc
    )
    return summary.sort_values("RevenuePerCustomer", ascending=False), med_customers, med_rpc


def top_customer_dependence(tables, lines, countries):
    """Break down revenue by customer within the given countries.

    Args:
        tables (dict[str, pandas.DataFrame]): Output of load_tables.
        lines (pandas.DataFrame): Order lines from order_lines.
        countries (list[str]): Countries to include.

    Returns:
        pandas.DataFrame: One row per country and customer with orders,
            revenue and share of the country's revenue in percent.
    """
    lines = lines.merge(tables["customers"][["CustomerID", "CompanyName", "Country"]], on="CustomerID")
    lines = lines[lines["Country"].isin(countries)]
    by_cust = lines.groupby(["Country", "CompanyName"]).agg(
        Orders=("OrderID", "nunique"), Revenue=("Revenue", "sum")
    ).reset_index()
    by_cust["ShareOfCountryPct"] = 100 * by_cust["Revenue"] / by_cust.groupby("Country")["Revenue"].transform("sum")
    return by_cust.sort_values(["Country", "Revenue"], ascending=[True, False])


def rep_summary(tables, lines):
    """Summarize orders, revenue and reach for each employee.

    Args:
        tables (dict[str, pandas.DataFrame]): Output of load_tables.
        lines (pandas.DataFrame): Order lines from order_lines.

    Returns:
        pandas.DataFrame: One row per employee with title, office,
            orders, revenue, customers, countries served, revenue share
            and revenue per order; sorted by revenue descending.
    """
    lines = lines.merge(tables["customers"][["CustomerID", "Country"]], on="CustomerID")
    reps = lines.groupby("EmployeeID").agg(
        Orders=("OrderID", "nunique"),
        Revenue=("Revenue", "sum"),
        Customers=("CustomerID", "nunique"),
        Countries=("Country", "nunique"),
    )
    reps["RevenueSharePct"] = 100 * reps["Revenue"] / reps["Revenue"].sum()
    reps["RevenuePerOrder"] = reps["Revenue"] / reps["Orders"]
    emp = tables["employees"].set_index("EmployeeID")
    reps = emp[["FirstName", "LastName", "Title", "Country"]].rename(
        columns={"Country": "BasedIn"}).join(reps)
    reps["Name"] = reps["FirstName"] + " " + reps["LastName"]
    return reps.drop(columns=["FirstName", "LastName"]).sort_values("Revenue", ascending=False)


def region_by_office(tables, lines):
    """Split each region's revenue by the handling employee's office.

    Args:
        tables (dict[str, pandas.DataFrame]): Output of load_tables.
        lines (pandas.DataFrame): Order lines from order_lines.

    Returns:
        pandas.DataFrame: One row per region with UK and USA revenue,
            the total, the region's share of all revenue and each
            office's share within the region, in percent.
    """
    # Revenue from each customer region, split by the office of the employee
    # who handled the order.
    lines = lines.merge(tables["customers"][["CustomerID", "Country"]], on="CustomerID").merge(
        tables["employees"][["EmployeeID", "Country"]].rename(columns={"Country": "Office"}),
        on="EmployeeID")
    lines["Region"] = lines["Country"].map(region_of)
    table = lines.pivot_table(index="Region", columns="Office", values="Revenue", aggfunc="sum")
    table["Total"] = table.sum(axis=1)
    table["RegionSharePct"] = 100 * table["Total"] / table["Total"].sum()
    table["USStaffPct"] = 100 * table["USA"] / table["Total"]
    table["UKStaffPct"] = 100 * table["UK"] / table["Total"]
    return table.sort_values("Total", ascending=False)


def plot_region_staff(regions):
    """Plot revenue by region, split by US and UK-based staff.

    Args:
        regions (pandas.DataFrame): Output of region_by_office.

    Returns:
        None. Saves q3_region_staff.png.
    """
    data = regions.iloc[::-1]  # largest region on top
    fig, ax = plt.subplots(figsize=(9, 3.8))
    us, uk = data["USA"] / 1000, data["UK"] / 1000
    ax.barh(data.index, us, color=BLUE, height=0.6, label="Handled by US-based staff")
    ax.barh(data.index, uk, left=us, color=ORANGE, height=0.6, label="Handled by UK-based staff")
    for i, (region, r) in enumerate(data.iterrows()):
        ax.text(r["USA"] / 2000, i, f"{r['USStaffPct']:.0f}%", ha="center", va="center",
                color="white", fontsize=9.5, fontweight="bold")
        ax.text(r["USA"] / 1000 + r["UK"] / 2000, i, f"{r['UKStaffPct']:.0f}%", ha="center",
                va="center", color="white", fontsize=9.5, fontweight="bold")
    ax.set_xlim(0, data["Total"].max() / 1000 * 1.05)
    ax.set_xlabel("Revenue, Jul 1996 – May 1998 ($K)")
    ax.tick_params(axis="y", labelsize=10.5)
    europe = regions.loc["Europe"]
    ax.set_title(f"Europe is our biggest market, but our UK-based staff\n"
                 f"handle only {europe['UKStaffPct']:.0f}% of it", loc="left", fontsize=12.5)
    ax.legend(frameon=False, loc="lower right", fontsize=9)
    style_axes(ax)
    save_figure(fig, "q3_region_staff.png")


def run():
    """Run the Question 3 analysis.

    Args:
        None.

    Returns:
        None. Saves the Q3 tables and chart and prints a summary.
    """
    tables = load_tables()
    lines = order_lines(tables)
    summary, med_customers, med_rpc = country_summary(tables, lines)
    targets = summary.index[summary["FewButHighValue"]].tolist()
    dependence = top_customer_dependence(tables, lines, targets)
    reps = rep_summary(tables, lines)

    save_table(summary.round(2), "q3_customer_countries.csv")
    save_table(dependence.round(2), "q3_target_country_customers.csv", index=False)
    save_table(reps.round(2), "q3_reps.csv")
    regions = region_by_office(tables, lines)
    save_table(regions.round(2), "q3_region_by_office.csv")
    plot_region_staff(regions)

    print(f"Q3 - medians: {med_customers} customers, ${med_rpc:,.0f} per customer")
    print("Q3 - countries\n", summary.round(0).to_string())
    print("\nQ3 - target-country customers\n", dependence.round(1).to_string(index=False))
    print("\nQ3 - reps\n", reps.round(0).to_string())
    print("\nQ3 - region by office\n", regions.round(1).to_string())


if __name__ == "__main__":
    run()
