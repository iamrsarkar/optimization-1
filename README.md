# NexGen Logistics – Warehouse Optimization Tool

## Case Study Summary
NexGen Logistics Pvt. Ltd. operates a multi-warehouse distribution network across India with links to Singapore, Dubai, Hong Kong, and Bangkok. The business processes 200+ orders monthly across categories such as Electronics, Fashion, Food & Beverage, Healthcare, Industrial goods, Books, and Home Goods. Operations rely on five warehouses (Mumbai, Delhi, Bangalore, Chennai, Kolkata), a mixed fleet of 50 vehicles, and several carrier partners serving enterprise, SMB, and individual customers with Express, Standard, and Economy priorities.

## Problem Focus
This project delivers **Option 6 – Warehouse Optimization Tool**, enabling planners to rebalance inventory, monitor demand, and manage cost/service risks across the network. The Streamlit application combines all seven datasets to analyse demand, delivery performance, costs, inventory health, and customer sentiment.

## Application Pages
1. **Overview & KPIs** – Network-wide metrics, orders over time, origin/category mix, and on-time performance.
2. **Warehouse Inventory & Demand EDA** – Filterable warehouse/product analysis, heatmaps, demand vs stock charts, and top over/under-stocked combinations.
3. **Warehouse Optimization** – Configurable safety stock and demand window, heuristic/LP transfer planning, and reorder recommendations with downloads.
4. **Cost & Risk Insights** – Cost component decomposition and narrative guidance for balancing carrying cost and stock-out risk.
5. **Customer & Service View** – Customer feedback summary and rating vs delay correlations.

## Project Structure
```
app.py                     # Streamlit entry point
analysis_utils.py          # Shared filters and demand/inventory aggregation
config.py                  # Constants and model parameters
customer_feedback.csv      # Provided dataset
cost_breakdown.csv         # Provided dataset
data_loader.py             # Dataset loading/cleaning and master order creation
delivery_performance.csv   # Provided dataset
eda_utils.py               # Exploratory analysis helpers
innovation_brief.md        # Business brief summarising approach and impact
orders.csv                 # Provided dataset
routes_distance.csv        # Provided dataset
vehicle_fleet.csv          # Provided dataset
viz_utils.py               # Plotly visualisations
warehouse_inventory.csv    # Provided dataset
warehouse_optimizer.py     # Optimization logic and outputs
requirements.txt           # Python dependencies
analysis_report.md         # Detailed analytical findings
```

## Installation
```bash
pip install -r requirements.txt
```

## Running the App
```bash
streamlit run app.py
```

## Key Assumptions
- Distances between warehouses follow an approximate road-distance matrix encoded in `config.py`; a 1,500 km default is used when specific values are unavailable.
- Transfer cost is estimated as distance × 2.5 INR per unit. Shortage penalty in the LP model is set to 150 INR per unit to prioritise service.
- Demand is estimated from historical order counts (orders treated as single units due to missing quantity data) within a selectable lookback window. Safety stock defaults to 14 days of demand.
- Vehicle assignment per order is not available; fleet insights are descriptive only.

## Interpreting Optimization Outputs
- **Transfer Plan**: Recommended intra-network rebalancing moves with estimated logistics cost and expected holding-cost relief. Execute moves prioritising highest relief vs. cost ratios.
- **Reorder Recommendations**: When stock cover drops below reorder or safety thresholds, the tool estimates units required to reach the target stock level.
- **Metrics Bar**: Highlights surplus/deficit combinations, total transfer cost, and potential reduction in tied-up capital.

Use the filters to focus on specific warehouses or categories, iterate on safety stock assumptions, and export CSV plans for operational execution.
