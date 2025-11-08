# NexGen Logistics – Warehouse Optimization & Inventory Rebalancing Tool

## Context
NexGen Logistics runs a five-warehouse Indian distribution network supporting 200+ monthly orders across electronics, fashion, food & beverage, healthcare, industrial goods, books, and home goods. Operations span domestic depots (Mumbai, Delhi, Bangalore, Chennai, Kolkata) and international gateway partners. Rising inventory carrying cost (INR 2.07M tied up) and volatile delivery performance (only 53% on-time, 1.08-day average delay) motivate a smarter planning layer that aligns stock placement with demand while safeguarding customer experience.

## Problem Statement
Stock imbalances drive both overstock (capital drag, high storage cost) and stockouts (express shipping, service degradation). Without a holistic view of demand, warehouse inventory levels, and delivery outcomes, planners struggle to decide when to transfer, reorder, or hold. NexGen requires a decision cockpit that minimises total storage plus transfer cost and protects service levels across segments and priorities.

## Approach
- **Data Integration:** Consolidated seven CSV datasets covering orders, delivery performance, routes, fleet, inventory, cost, and customer feedback. Built a master orders table with derived metrics (delay days, total fulfilment cost, cost per km).
- **Exploratory Analytics:** Generated KPIs on revenue, demand mix, on-time rate, route efficiency, fleet utilisation, and customer sentiment. Identified 27 surplus vs. 7 deficit warehouse-product combinations.
- **Optimization Engine:** Implemented configurable safety stock and lookback windows, a heuristic transfer matcher (with optional PuLP-based LP), and reorder sizing logic. Transfer cost uses an estimated lane-distance matrix (2.5 INR per unit-km) with a 150 INR/unit shortage penalty.
- **Streamlit Experience:** Five-page app with interactive filters, Plotly visuals (line, stacked bar, heatmap, histogram, scatter), and downloadable transfer/reorder plans.

## Key Insights
- Mumbai, Bangalore, and Chennai hold deep surpluses—e.g., Mumbai Books +4.5k units over target—while Kolkata and Delhi face critical deficits (Books -791, Electronics -659).
- Average total fulfilment cost is INR 1.2k/order; fuel and labour consume 31% of spend, magnified when emergency shipments cover stockouts.
- Customer ratings correlate strongly (r = -0.74) with delivery delay, highlighting the customer-impact of poor inventory positioning.
- Fleet status reveals 28 idle assets, signalling opportunity to redeploy company-owned capacity for inter-warehouse transfers.

## Proposed Solution
Deploy the Streamlit Warehouse Optimization app for daily/weekly planning. Analysts can:
- Monitor KPIs and visualise order mix, on-time performance, and cost-to-serve.
- Diagnose imbalances via inventory-demand heatmaps and stock-cover histograms.
- Run optimisation scenarios adjusting lookback window and safety stock to generate transfer and reorder plans.
- Export actionable CSVs for operations execution and collaborate with procurement, transportation, and customer service teams.

## Business Impact
- **Inventory efficiency:** Suggested 7 transfers move 2,046 units, releasing ~INR 56.8k in holding cost and reducing excess cover by >80% in focus categories.
- **Service protection:** Reordering the same 2,046 units mitigates stockout risk in Kolkata/Delhi, supporting a projected uplift in on-time performance (target +10 ppts) and reducing negative feedback.
- **Cost reduction:** Rebalancing curbs express shipments and optimises lane usage, with potential to cut fulfilment cost by 5–8% through fuel and labour savings.
- **Sustainability:** Better placement shortens routes for last-mile replenishment, trimming CO₂ exposure (fleet average 0.386 kg/km) and utilising idle assets before outsourcing.

## Future Extensions
- Demand forecasting using machine learning with seasonality, promotions, and external signals.
- Integration with WMS/TMS for near real-time stock and transit visibility.
- End-to-end optimisation blending inventory rebalancing with routing, carrier selection, and vehicle assignment.
- Supplier lead-time modelling and dynamic safety stock tuning using probabilistic service levels.
