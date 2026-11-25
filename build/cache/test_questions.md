# Test question answers (model gemini-2.5-flash, prompt agent-v4)

## Core 1: Should employee business travel be classified as Scope 1 or Scope 3? Explain the reasoning and describe how I can calculate my business travel emissions?

Employee business travel emissions should be classified as Scope 3 [1].

To calculate business travel emissions, you should:
1.  **Identify GHG emission sources:** This falls under mobile combustion [2].
2.  **Select a calculation approach:** The most common approach is to use emission factors [3].
3.  **Collect activity data and choose emission factors:** This will primarily involve activity data such as passenger miles and published or third-party emission factors [3]. For air travel, it is important to use the round trip distance [4].
4.  **Apply calculation tools:** The GHG Protocol provides cross-sector tools for mobile combustion that include calculations and emission factors for road, air, water, and rail transport [5].
5.  **Roll-up GHG emissions data to corporate level** [6].

It is important to note that while Scope 3 reporting is optional, it provides an opportunity to be innovative in GHG management and identify relevant GHG emissions along your value chain [1][2].

**Sources**
- [1] GHG Protocol Corporate Standard (2004), PDF page 31
- [2] GHG Protocol Corporate Standard (2004), PDF page 43
- [3] GHG Protocol Corporate Standard (2004), PDF page 44
- [4] GHG Protocol Corporate Standard (2004), PDF page 56
- [5] GHG Protocol Corporate Standard (2004), PDF page 46
- [6] GHG Protocol Corporate Standard (2004), PDF page 42

_tools: ['search_ghg_protocol']; 17998 in / 265 out tokens; $0.00606_

## Core 2: Are my scope 2 emissions calculation valid according to the Greenhouse Gas Protocol?

The validity of your Scope 2 emissions calculation cannot be fully determined from the provided information, but several areas require attention to align with the GHG Protocol Corporate Standard (2004).

**Not Valid (High Severity Findings):**

*   **Reporting Period:** Your Scope 2 emissions cover only 3 months [1].
    *   **Protocol requirement:** A public GHG report shall include the reporting period covered [2]. While the Protocol doesn't explicitly state a minimum duration, a 3-month period is unusually short for a comprehensive annual report.
*   **Steam Emission Factor:** Steam is the largest Scope 2 source (84.5% of emissions) and its emission factor has no stated source [1].
    *   **Protocol requirement:** The methodologies used to calculate or measure emissions, providing a reference or link to any calculation tools used, shall be included in a public GHG report [2].
    *   **Best practice:** Companies should use the most accurate calculation approach available to them and that is appropriate for their reporting context. If source- or facility-specific emission factors are available, they are preferable to more generic or general emission factors [3].
*   **Location-based vs. Market-based Reporting:** The report cannot assess location-based versus market-based reporting [1].
    *   **Protocol requirement:** The 2004 edition of the GHG Protocol Corporate Standard does not include guidance on market-based accounting for Scope 2 emissions. This was introduced in the 2015 Scope 2 Guidance. Therefore, this cannot be verified from the provided documents.

**Areas for Improvement (Medium Severity Findings):**

*   **Mixed Units and Scales:** Factor units are not stated, and two scales (0.001 and 1) are mixed for consumption units (kWh and MMBtu) [1].
    *   **Best practice:** Clear records of calculations undertaken to derive emissions data should be kept for any future internal or external verification [4]. This implies consistent and well-documented units and conversion factors.
*   **Renewable Energy Application:** Renewable percentages are listed but not applied to CO2e calculations [1].
    *   **Best practice:** While the 2004 Protocol does not explicitly detail how to apply renewable energy percentages to CO2e, transparent accounting of GHG emissions and reductions associated with opportunities like switching to less GHG-intensive electricity sources is encouraged [5].

**Valid (Low Severity Findings):**

*   **Arithmetic:** All 18 rows recompute within rounding [1].
    *   **Best practice:** This indicates good internal consistency in calculations.
*   **Electricity Grid Factors:** Electricity uses regional grid factors, which are a type of published factor [1].
    *   **Best practice:** Scope 2 GHG emissions will primarily be calculated from metered electricity consumption and supplier-specific, local grid, or other published emission factors [3].

To improve the validity of your Scope 2 emissions reporting, you should:
1.  Extend your reporting period to cover a full year.
2.  Provide the source and justification for the steam emission factor.
3.  Clearly state the units used for all factors and ensure consistent application of scales or provide clear conversion documentation.
4.  Explain how renewable energy percentages are considered in your emissions calculations, if at all.

**Sources**
- [1] Data-quality checks on scope2.csv
- [2] GHG Protocol Corporate Standard (2004), PDF page 65
- [3] GHG Protocol Corporate Standard (2004), PDF page 44
- [4] GHG Protocol Corporate Standard (2004), PDF page 49
- [5] GHG Protocol Corporate Standard (2004), PDF page 29

_tools: ['quality_report', 'search_ghg_protocol', 'claim_check']; 50287 in / 1501 out tokens; $0.01884_

## Core 3: How do my scope 1 & 2 emissions compare with other companies (refer to peer reports in the data sources) in my industry, and what insights can I derive from this comparison?

When comparing your company's Scope 1 and 2 emissions with other companies, it's crucial to consider the principles of GHG accounting and reporting to ensure meaningful comparisons. The GHG Protocol Corporate Standard emphasizes **Relevance, Completeness, Consistency, Transparency, and Accuracy** [1].

**Comparability Considerations:**

*   **Organizational and Operational Boundaries:** The choice of inventory boundary is dependent on the characteristics of the company, the intended purpose of information, and the needs of the users [2]. Companies must define their organizational boundaries (e.g., equity share or control approach) and then set operational boundaries by identifying direct (Scope 1) and indirect (Scope 2 and 3) emissions [3][4].
    *   **Insight:** Your company's industrial Scope 1 profile (coal, cement process emissions) is fundamentally different from the software/e-commerce peers (Docusign, Shopify). This difference in operational boundaries and activities is the primary reason for the higher absolute Scope 1 emissions (1692.47 tCO2e for 3 months, annualized to 6769.9 tCO2e if flat seasonality is assumed [5]) compared to Docusign (449 tCO2e [5]) and Shopify (360 tCO2e [5]).
*   **Scope 2 Reporting Method:** Scope 2 accounts for GHG emissions from the generation of purchased electricity consumed by the company [4]. The GHG Protocol is designed to prevent double counting of emissions within Scope 1 and 2, ensuring that only one company exercises ownership of these emissions [6].
    *   **Insight:** Docusign reports both market-based (3.1 tCO2e [5]) and location-based (8545 tCO2e [5]) Scope 2 emissions. The method used for your company's Scope 2 (2505.04 tCO2e for 3 months, annualized to 10020.2 tCO2e if flat seasonality is assumed [5]) is unknown. To ensure consistency and transparency, it is **recommended** to clarify the Scope 2 accounting method and consider dual reporting if relevant for your stakeholders [4][7].
*   **Reporting Periods and Consistency:** Consistent methodologies are essential for meaningful comparisons of emissions over time [1]. Companies should choose a base year for which verifiable emissions data are available and specify their reasons for choosing that year [8].
    *   **Insight:** Your company's Scope 1 and 2 data cover a 3-month period (2024-01-15 to 2024-03-15), while peers report for full fiscal or calendar years [5]. The annualized figures for your company (Scope 1: 6769.9 tCO2e; Scope 2: 10020.2 tCO2e [5]) are estimates assuming flat seasonality, which may not be accurate for an industrial operation. For future comparisons, it is **recommended** to report on a consistent annual basis and clearly state the reporting period and any assumptions made for annualization [8].
*   **Ratio Indicators:** Reporting absolute emissions is required, while reporting ratio indicators (e.g., emissions per unit of revenue) is optional but can improve comparability between different sizes of businesses [7].
    *   **Insight:** Without revenue data for your company, emissions intensity cannot be calculated to compare with Docusign's 45 tCO2e per $1M revenue [5]. Providing such a ratio would offer a more normalized comparison, especially given the significant differences in absolute emissions due to industry type. This is a **best practice** for enhancing comparability [7].

**Overall Insight:**

A direct "better or worse" comparison of absolute Scope 1 and 2 emissions is not appropriate due to the fundamental differences in industry, operational boundaries, and reporting periods. Your company's higher Scope 1 emissions are expected given its industrial nature. To improve future comparisons and transparency, it is **recommended** to:
*   Clearly define and disclose your organizational and operational boundaries.
*   Specify the Scope 2 accounting method (market-based or location-based).
*   Report on a consistent annual basis and clearly state any annualization assumptions.
*   Consider reporting emissions intensity ratios if revenue data becomes available.

**Sources**
- [1] GHG Protocol Corporate Standard (2004), PDF page 9
- [2] GHG Protocol Corporate Standard (2004), PDF page 10
- [3] GHG Protocol Corporate Standard (2004), PDF page 26
- [4] GHG Protocol Corporate Standard (2004), PDF page 27
- [5] Peer reports: Docusign FY25 Impact Report (pp.49-50) and Shopify 2024 Climate Report (pp.18-19)
- [6] GHG Protocol Corporate Standard (2004), PDF page 35
- [7] GHG Protocol Corporate Standard (2004), PDF page 67
- [8] GHG Protocol Corporate Standard (2004), PDF page 37

_tools: ['compare_with_peers', 'citation_guard', 'search_ghg_protocol']; 47176 in / 2154 out tokens; $0.01954_

## Bonus 1: What is our highest emitting Scope 3 category and what specific activities contribute to it?

Our highest emitting Scope 3 category is Category 3, with 31,794.33 tonnes CO2e [1]. The top activities contributing to this are Product Use Phase (4,982.78 tonnes CO2e), Business Travel - Air (4,874.98 tonnes CO2e), and Raw Materials - Steel (4,254.58 tonnes CO2e) [2].

Please note the following data caveats:
*   Categories and activities do not line up [1][2].
*   Every supplier supplies nearly every activity; supplier names do not match what they supply [1][2].
*   Only a minority of rows use primary data [1][2].

**Sources**
- [1] scope3.csv: top 1 Scope 3 groups by Category
- [2] scope3.csv: what drives Scope 3 Category 3

_tools: ['scope3_top', 'scope3_category_detail']; 4873 in / 210 out tokens; $0.00199_

## Bonus 2: Which suppliers should I prioritise to engage for emissions reduction efforts?

The top 5 suppliers by emissions are:

1.  **OfficeMax**: 50,966.25 tonnes CO2e [1], with Business Travel - Air as the top activity. 18% primary data [1].
2.  **Corporate Travel**: 50,296.34 tonnes CO2e [1], with Raw Materials - Steel as the top activity. 19.7% primary data [1].
3.  **WasteManagement Co**: 49,390.91 tonnes CO2e [1], with Packaging Materials as the top activity. 19.3% primary data [1].
4.  **MetalSupply Co**: 48,603.02 tonnes CO2e [1], with IT Hardware as the top activity. 17.6% primary data [1].
5.  **SteelCorp Inc**: 47,246.62 tonnes CO2e [1], with Manufacturing Equipment as the top activity. 17.2% primary data [1].

**Caveats**:
*   Suppliers are spread almost evenly, so ranking alone gives weak prioritization; combine with data quality and activity before engaging [1].
*   Categories and activities do not line up.
*   Every supplier supplies nearly every activity; supplier names do not match what they supply.
*   Only a minority of rows use primary data.

**Sources**
- [1] scope3.csv: suppliers ranked by emissions and data quality

_tools: ['supplier_priorities']; 3107 in / 357 out tokens; $0.00182_

## Bonus 3: Generate a summary report of our total emissions by scope with key insights

Total emissions are 378,683.02 tonnes CO2e [1].

**Key Insights:**

*   **Scope 3 Dominance:** Scope 3 accounts for the vast majority of emissions at 98.89% (374,485.51 tonnes CO2e) [1]. However, note that Scope 3 covers 12 months, while Scopes 1 and 2 cover only 3 months [1]. Also, Scope 3 categories and activities do not line up [1].
*   **Scope 1 Breakdown:** Stationary Combustion is the largest source within Scope 1, contributing 53.33% (902.57 tonnes CO2e) [2]. Scope 1 covers 3 months only [2].
*   **Scope 2 Breakdown:** Steam is the primary driver of Scope 2 emissions, representing 84.49% (2,116.4 tonnes CO2e) [3]. The factor for steam has no stated source [3]. Scope 2 covers 3 months only [3].
*   **Top Scope 3 Categories:** The top three Scope 3 categories are Category 3 (8.49%, 31,794.33 tonnes CO2e), Category 12 (8.32%, 31,169.22 tonnes CO2e), and Category 11 (7.66%, 28,700.5 tonnes CO2e) [4]. Categories and activities do not line up [4].

**Sources**
- [1] Total emissions per scope (scope1/2/3.csv)
- [2] scope1.csv: Scope 1 emissions grouped by Activity_Type
- [3] scope2.csv: Scope 2 emissions grouped by Energy_Type
- [4] scope3.csv: top 3 Scope 3 groups by Category

_tools: ['totals', 'scope1_breakdown', 'scope2_breakdown', 'scope3_top']; 4022 in / 415 out tokens; $0.00224_
