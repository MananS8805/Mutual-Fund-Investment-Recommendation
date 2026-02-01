Here is the logical framework you can use to estimate the **Total Expense Ratio (TER)**. You can implement this using `IF/ELSE` statements in Excel, Python, or SQL.

This logic is based on **SEBI's regulatory limits** (which cap the maximum fees) and **market standards** (where larger funds charge less).

---

### **Step 1: Assign a "Base" Expense Ratio (Regular Plan)**

First, determine the starting expense ratio based on the **Scheme Category**. This assumes the fund is a "Regular Plan" (which includes distributor commissions).

| **Category Group** | **Specific Keywords to Look For** | **Base TER (Regular)** |
| --- | --- | --- |
| **Passives (Cheapest)** | `ETF`, `Exchange Traded Fund` | **0.10%** |
|  | `Index Fund` | **0.80%** |
| **Liquid / Overnight** | `Liquid`, `Overnight` | **0.25%** |
| **Short-Term Debt** | `Ultra Short`, `Low Duration`, `Money Market` | **0.80%** |
| **Long-Term Debt** | `Corporate Bond`, `Banking & PSU`, `Gilt`, `Dynamic Bond` | **1.20%** |
| **Arbitrage** | `Arbitrage` | **1.00%** |
| **Equity & Others** | `Equity`, `Large Cap`, `Mid Cap`, `Small Cap`, `Flexi Cap`, `ELSS`, `Hybrid` | **2.10%** |
| **Fund of Funds** | `FoF`, `Fund of Fund` | **0.50%** |

---

### **Step 2: Apply "Direct Plan" Discount**

If the scheme is a **Direct Plan** (look for "Direct" in the scheme name or plan column), you must subtract the distributor commission.

* **Logic:** The higher the Base TER, the higher the commission you remove.

| **Base TER (from Step 1)** | **Direct Plan Discount** | **Logic** |
| --- | --- | --- |
| **> 1.80%** (Equity/Hybrid) | **Subtract 1.10%** | High commissions in equity. |
| **1.00% - 1.80%** (L-T Debt) | **Subtract 0.60%** | Moderate commissions. |
| **0.50% - 1.00%** (S-T Debt/Index) | **Subtract 0.40%** | Low commissions. |
| **< 0.50%** (Liquid/ETF) | **Subtract 0.05%** | Minimal difference. |

---

### **Step 3: Apply AUM (Size) Adjustment**

Funds with huge Assets Under Management (AUM) benefit from "Economies of Scale" and are mandated by SEBI to charge less.

* **If AUM > ₹50,000 Cr:** Subtract **0.30%**
* **If AUM > ₹20,000 Cr:** Subtract **0.20%**
* **If AUM > ₹5,000 Cr:** Subtract **0.10%**
* **If AUM < ₹50 Cr:** Add **0.10%** *(Small funds often have higher fixed operational costs)*

---

### **Step 4: Set Safety Limits (Caps)**

Finally, ensure your calculation doesn't produce unrealistic numbers (like negative fees).

* **Minimum Limit:** `0.05%` (No fund is free)
* **Maximum Limit:** `2.25%` (SEBI's regulatory cap for most equity funds)

---

### **Example Calculations**

**Scenario A: HDFC Mid-Cap Opportunities (Equity, Huge Size)**

1. **Category:** Equity → Base: **2.10%**
2. **Plan:** Regular → Discount: **0%**
3. **AUM:** ₹60,000 Cr → Discount: **-0.30%**
4. **Final Estimate:** `2.10 - 0.30 =` **1.80%**

**Scenario B: SBI Liquid Fund (Liquid, Direct)**

1. **Category:** Liquid → Base: **0.25%**
2. **Plan:** Direct → Discount: **-0.05%**
3. **AUM:** ₹70,000 Cr → Discount: **-0.05%** (Liquid funds hit a floor, usually don't drop below 0.15%)
4. **Final Estimate:** `0.25 - 0.05 - 0.05 =` **0.15%**

**Scenario C: Small Cap Index Fund (Index, Direct, Small Size)**

1. **Category:** Index → Base: **0.80%**
2. **Plan:** Direct → Discount: **-0.40%**
3. **AUM:** ₹20 Cr (Small) → Add: **+0.10%**
4. **Final Estimate:** `0.80 - 0.40 + 0.10 =` **0.50%**