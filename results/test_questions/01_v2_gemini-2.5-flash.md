# Test question answers (model gemini-2.5-flash, prompt agent-v2)

## Core 1: Should employee business travel be classified as Scope 1 or Scope 3? Explain the reasoning and describe how I can calculate my business travel emissions?

Employee business travel should be classified as Scope 3 emissions [1][2].

**Protocol requirement:**
*   Direct GHG emissions are from sources owned or controlled by the company, such as company-owned vehicles [3][4].
*   Indirect GHG emissions are a consequence of the company's activities but occur at sources owned or controlled by another company [3].
*   Scope 3 is an optional reporting category for all other indirect emissions [3]. Employee business travel is explicitly listed as a Scope 3 activity [2].

To calculate your business travel emissions, you would need to gather data on the distance traveled and the mode of transport (e.g., air, rail, car). You can then multiply this activity data by relevant emission factors for each mode of transport. The GHG Protocol suggests that while data accuracy may be lower for Scope 3, estimates are acceptable as long as the estimation approach is transparent and the data is adequate for the inventory's objectives [5].

**Sources**
- [1] GHG Protocol Corporate Standard (2004), PDF page 28
- [2] GHG Protocol Corporate Standard (2004), PDF page 31
- [3] GHG Protocol Corporate Standard (2004), PDF page 27
- [4] GHG Protocol Corporate Standard (2004), PDF page 29
- [5] GHG Protocol Corporate Standard (2004), PDF page 33

_tools: ['search_ghg_protocol']; 10597 in / 252 out tokens; $0.00381_

## Core 2: Are my scope 2 emissions calculation valid according to the Greenhouse Gas Protocol?

Here's an assessment of your Scope 2 emissions calculation based on the GHG Protocol Corporate Standard (2004 edition) [1]:

**Protocol requirements:**

*   **Reporting Period:** Your report covers only 3 months (2024-01-15 to 2024-03-15) [1]. A public GHG emissions report shall include the reporting period covered [2].
*   **Steam Emission Factor:** Steam is a significant source of Scope 2 emissions (84.5% or 2116.4 tonnes CO2e) [1]. The emission factor used for steam has no stated source [1]. The GHG Protocol recommends obtaining source/supplier-specific emission factors for purchased electricity, and if not available, regional or grid emission factors should be used [3]. For other energy types like steam, if source- or facility-specific emission factors are available, they are preferable to more generic ones [4].
*   **Units and Conversions:** Factor units are not stated, and two different scales (0.001 and 1) are mixed for electricity (kWh) and steam (MMBtu) [1]. The Protocol requires checking that emission units, parameters, and conversion factors are appropriately labeled and correctly carried through calculations [5].
*   **Location-based vs. Market-based Reporting:** The assessment of location-based versus market-based reporting cannot be made [1]. The 2004 edition of the GHG Protocol Corporate Standard does not include guidance on the market-based method for Scope 2 emissions. This was introduced in the 2015 Scope 2 Guidance.

**Best practices:**

*   **Renewable Energy:** Renewable percentage is listed but not applied to CO2e, with an illustrative difference of 19.3% (388.64 tonnes vs. 313.52 tonnes) if all were backed by qualifying contracts [1]. The Protocol states that companies can reduce electricity use by investing in energy-efficient technologies and that emerging green power markets provide opportunities to switch to less GHG-intensive sources [6]. While the 2004 standard mentions renewable energy certificates (RECs) as a way to offset emissions [7], it does not explicitly detail how to apply renewable percentages to CO2e calculations within Scope 2.
*   **Arithmetic Accuracy:** All 18 rows recompute within rounding [1]. This indicates good arithmetic accuracy, which is a key aspect of inventory quality [8].
*   **Electricity Grid Factors:** Electricity uses regional grid factors (CAISO, ERCOT, NEISO, PJM) [1]. The GHG Protocol recommends using source/supplier-specific emission factors for purchased electricity, and if these are not available, regional or grid emission factors should be used [3].

**Recommendations:**

*   **Extend Reporting Period:** Ensure your reporting period covers a full year for comprehensive reporting, as required by the Protocol [2].
*   **Document Steam Emission Factor:** Clearly state the source of the emission factor used for steam and justify its appropriateness. Prioritize supplier-specific or regional factors if available [3][4].
*   **Clarify Units and Conversions:** Document all units and conversion factors used in your calculations to ensure transparency and accuracy [5].
*   **Consider Market-Based Reporting (Future Guidance):** While not in the 2004 standard, be aware that later guidance (2015 Scope 2 Guidance) introduced market-based reporting for Scope 2.
*   **Apply Renewable Energy Impact:** If the renewable energy percentages are backed by verifiable contracts, ensure they are appropriately reflected in your CO2e calculations.

**Sources**
- [1] Data-quality checks on scope2.csv
- [2] GHG Protocol Corporate Standard (2004), PDF page 65
- [3] GHG Protocol Corporate Standard (2004), PDF page 89
- [4] GHG Protocol Corporate Standard (2004), PDF page 44
- [5] GHG Protocol Corporate Standard (2004), PDF page 53
- [6] GHG Protocol Corporate Standard (2004), PDF page 29
- [7] GHG Protocol Corporate Standard (2004), PDF page 63
- [8] GHG Protocol Corporate Standard (2004), PDF page 52

_tools: ['quality_report', 'search_ghg_protocol', 'search_ghg_protocol', 'search_ghg_protocol', 'search_ghg_protocol', 'search_ghg_protocol']; 69268 in / 986 out tokens; $0.02325_

## Core 3: How do my scope 1 & 2 emissions compare with other companies (refer to peer reports in the data sources) in my industry, and what insights can I derive from this comparison?

When comparing your company's Scope 1 and 2 emissions with Docusign and Shopify, several caveats must be considered [1]:

*   **Different Boundaries**: Shopify reports operational emissions only (Scope 1, 2, 3.6, 3.7) [1]. Docusign reports Scope 1, 2, and specified Scope 3 categories [1]. Your company's Scope 3 spans many more categories.
*   **Scope 2 Method**: Docusign's Scope 2 is shown as both market-based (3.1 tCO2e) [1] and location-based (8,545 tCO2e) [1]. Your company's Scope 2 method is unknown, and dual reporting has not been verified.
*   **Reporting Periods**: Your company's Scope 1 and 2 data cover 3 months (2024-01-15 to 2024-03-15) [1]. The "annualised_tonnes_if_flat" (Scope 1: 6769.9 tCO2e; Scope 2: 10020.2 tCO2e) [1] is a rough guide that assumes flat seasonality. Docusign's period is FY25 (Feb 2024 - Jan 2025) [1], and Shopify's is Calendar Year 2024 [1].
*   **No Revenue Data**: Emissions intensity (tCO2e per $1M) cannot be computed for your company to compare with Docusign's 45 tCO2e per $1M revenue [1].
*   **Industry Comparison**: The two peers are software/e-commerce companies. Your company's Scope 1 profile (coal, cement process emissions) is industrial, suggesting that direct size comparisons may not reflect like-for-like performance gaps.
*   **Shopify Data Source**: Shopify figures were read from a chart on p.19 [1], not a table.

**Comparison Insights (with caveats):**

*   **Scope 1 Emissions**: Your company's annualized Scope 1 emissions are approximately 6,769.9 tCO2e [1]. This is significantly higher than Docusign's 449 tCO2e [1] and Shopify's 360 tCO2e [1]. This difference is likely due to your company's industrial activities (coal, cement process emissions) compared to the software/e-commerce nature of the peers.
*   **Scope 2 Emissions**: Your company's annualized Scope 2 emissions are approximately 10,020.2 tCO2e [1]. This is higher than Docusign's market-based 3.1 tCO2e [1] but comparable to Docusign's location-based 8,545 tCO2e [1]. Shopify's Scope 2 is 319 tCO2e [1]. The difference in Scope 2 figures, especially with Docusign, highlights the importance of understanding the accounting method (market-based vs. location-based).
*   **Renewable Electricity**: Docusign reports 100% renewable electricity share [1], which contributes to their very low market-based Scope 2 emissions. This could be an area for your company to explore for Scope 2 reduction.

Given the significant differences in industry and operational profiles, a direct quantitative comparison of total emissions may not be the most insightful. Instead, focus on understanding the drivers of emissions within each scope for your company and identifying best practices from peers, such as Docusign's renewable electricity procurement, that could be adapted to your context.

**Sources**
- [1] Peer reports: Docusign FY25 Impact Report (pp.49-50) and Shopify 2024 Climate Report (pp.18-19)

_tools: ['compare_with_peers']; 6072 in / 890 out tokens; $0.00405_

## Bonus 1: What is our highest emitting Scope 3 category and what specific activities contribute to it?

Our highest emitting Scope 3 category is Category 3, accounting for 31794.33 tonnes CO2e [1]. The top activities contributing to this category are:

*   Product Use Phase: 4982.78 tonnes CO2e [2]
*   Business Travel - Air: 4874.98 tonnes CO2e [2]
*   Raw Materials - Steel: 4254.58 tonnes CO2e [2]

**Sources**
- [1] scope3.csv: top 1 Scope 3 groups by Category
- [2] scope3.csv: what drives Scope 3 Category 3

_tools: ['scope3_top', 'scope3_category_detail']; 3994 in / 157 out tokens; $0.00159_

## Bonus 2: Which suppliers should I prioritise to engage for emissions reduction efforts?

The top 8 suppliers by emissions are:

1.  **OfficeMax**: 50,966.25 tonnes CO2e [1] (13.61% share [1]), with 18% primary data [1]. Top activity: Business Travel - Air.
2.  **Corporate Travel**: 50,296.34 tonnes CO2e [1] (13.43% share [1]), with 19.7% primary data [1]. Top activity: Raw Materials - Steel.
3.  **WasteManagement Co**: 49,390.91 tonnes CO2e [1] (13.19% share [1]), with 19.3% primary data [1]. Top activity: Packaging Materials.
4.  **MetalSupply Co**: 48,603.02 tonnes CO2e [1] (12.98% share [1]), with 17.6% primary data [1]. Top activity: IT Hardware.
5.  **SteelCorp Inc**: 47,246.62 tonnes CO2e [1] (12.62% share [1]), with 17.2% primary data [1]. Top activity: Manufacturing Equipment.
6.  **TechEquip Corp**: 44,445.1 tonnes CO2e [1] (11.87% share [1]), with 18.9% primary data [1]. Top activity: Business Travel - Air.
7.  **PackagePro Ltd**: 43,184.66 tonnes CO2e [1] (11.53% share [1]), with 27% primary data [1]. Top activity: Business Travel - Air.
8.  **LogisticsPro**: 40,352.61 tonnes CO2e [1] (10.78% share [1]), with 18.4% primary data [1]. Top activity: Office Supplies.

The suppliers are spread almost evenly, so ranking alone gives weak prioritization. It is recommended to combine this ranking with data quality and activity type before engaging [1].

**Sources**
- [1] scope3.csv: suppliers ranked by emissions and data quality

_tools: ['supplier_priorities']; 2819 in / 526 out tokens; $0.00216_

## Bonus 3: Generate a summary report of our total emissions by scope with key insights

Our total emissions are 378,683.02 tonnes CO2e [1].

**Scope 1 Emissions:** 1,692.47 tonnes CO2e [1] (0.45% of total [1])
*   **Key Insight:** Stationary Combustion is the largest source (53.33%, 902.57 tonnes CO2e [2]), followed by Process Emissions (41.48%, 702 tonnes CO2e [2]).

**Scope 2 Emissions:** 2,505.04 tonnes CO2e [1] (0.66% of total [1])
*   **Key Insight:** Steam accounts for the majority of Scope 2 emissions (84.49%, 2116.4 tonnes CO2e [3]), with Electricity making up the rest (15.51%, 388.64 tonnes CO2e [3]).

**Scope 3 Emissions:** 374,485.51 tonnes CO2e [1] (98.89% of total [1])
*   **Key Insight:** Scope 3 is by far the largest contributor to our overall emissions. The top three categories are Category 3 (8.49%, 31794.33 tonnes CO2e [4]), Category 12 (8.32%, 31169.22 tonnes CO2e [4]), and Category 11 (7.66%, 28700.5 tonnes CO2e [4]).

**Reporting Period Caveat:** The reporting periods for Scope 1 and 2 cover 3 months (2024-01-15 to 2024-03-15), while Scope 3 covers 12 months (2024-01-15 to 2024-12-15) [1]. Therefore, the shares are not directly comparable [1].

**Sources**
- [1] Total emissions per scope (scope1/2/3.csv)
- [2] scope1.csv: Scope 1 emissions grouped by Activity_Type
- [3] scope2.csv: Scope 2 emissions grouped by Energy_Type
- [4] scope3.csv: top 3 Scope 3 groups by Category

_tools: ['totals', 'scope1_breakdown', 'scope2_breakdown', 'scope3_top']; 2965 in / 521 out tokens; $0.00219_
