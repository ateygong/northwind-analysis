"""Run all three analyses and regenerate every figure and table."""

import q1_suppliers
import q2_products
import q3_customers

if __name__ == "__main__":
    for module in (q1_suppliers, q2_products, q3_customers):
        module.run()
        print("\n" + "=" * 70 + "\n")
