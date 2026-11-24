"""Shared data loading, revenue calculation and output helpers."""

from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
WORKBOOK = ROOT / "Northwind Database.xlsx"
FIG_DIR = ROOT / "outputs" / "figures"
TABLE_DIR = ROOT / "outputs" / "tables"

# Chart colors (validated categorical slots from the dataviz reference palette).
BLUE = "#2a78d6"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
GRAY = "#a3a29b"
INK = "#0b0b0b"
INK_2 = "#52514e"


def load_tables(path=WORKBOOK):
    """Load the Northwind sheets used in the analysis.

    Args:
        path (pathlib.Path | str): Northwind Excel workbook.

    Returns:
        dict[str, pandas.DataFrame]: Tables keyed by "orders",
            "details", "products", "suppliers", "customers",
            "employees" and "categories". OrderDate is parsed as a
            datetime and products keep only the original columns.
    """
    sheets = pd.read_excel(path, sheet_name=None)
    tables = {
        "orders": sheets["Orders"],
        "details": sheets["Orders Details"],
        "products": sheets["Product"],
        "suppliers": sheets["Suppliers"],
        "customers": sheets["Customers"],
        "employees": sheets["Employees"],
        "categories": sheets["Categories"],
    }
    tables["orders"]["OrderDate"] = pd.to_datetime(tables["orders"]["OrderDate"])
    # Keep only the original Northwind product columns; the sheet also holds
    # leftover helper columns (Cheap, NewPrice, IsCheap, ...) from earlier work.
    tables["products"] = tables["products"][
        ["ProductID", "ProductName", "SupplierID", "CategoryID", "Price",
         "UnitsInStock", "UnitsOnOrder", "ReorderLevel", "Discontinued"]
    ]
    return tables


def order_lines(tables):
    """Build one row per order line with revenue and order details.

    Revenue is UnitPrice * Quantity * (1 - Discount).

    Args:
        tables (dict[str, pandas.DataFrame]): Output of load_tables.

    Returns:
        pandas.DataFrame: Order Details rows with Revenue, OrderDate,
            CustomerID, EmployeeID and Year added.
    """
    lines = tables["details"].copy()
    lines["Revenue"] = lines["UnitPrice"] * lines["Quantity"] * (1 - lines["Discount"])
    lines = lines.merge(
        tables["orders"][["OrderID", "OrderDate", "CustomerID", "EmployeeID"]],
        on="OrderID", how="left",
    )
    lines["Year"] = lines["OrderDate"].dt.year
    return lines


def style_axes(ax):
    """Apply the shared chart style to a set of axes.

    Hides the top and right spines and sets gray axis and label colors.

    Args:
        ax (matplotlib.axes.Axes): Axes to style in place.

    Returns:
        None.
    """
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRAY)
    ax.tick_params(colors=INK_2, labelsize=9)
    ax.yaxis.label.set_color(INK_2)
    ax.xaxis.label.set_color(INK_2)
    ax.title.set_color(INK)


def save_figure(fig, name):
    """Save a figure as a PNG in outputs/figures and close it.

    Args:
        fig (matplotlib.figure.Figure): Figure to save.
        name (str): File name, e.g. "q1_supplier_reliance.png".

    Returns:
        None. Writes the file at 200 dpi on a white background.
    """
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_DIR / name, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def save_table(df, name, index=True):
    """Save a table as a CSV in outputs/tables.

    Args:
        df (pandas.DataFrame): Table to save.
        name (str): File name, e.g. "q1_suppliers.csv".
        index (bool): Whether to write the row index as a column.

    Returns:
        None.
    """
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(TABLE_DIR / name, index=index)
