# NexGen Logistics – Warehouse Optimization Analysis Report

## 1. Data Overview
- **Orders (200 records):** INR 370,080.60 total value spanning seven product families. Orders originate mainly from Mumbai (45), Delhi (37), Bangalore (33), Kolkata (23), and Chennai (22) with remaining flows from partner hubs (e.g., Hyderabad, Pune, Ahmedabad).
- **Delivery Performance (150 records):** Contains promised/actual delivery days, carrier, cost, and customer rating data. 53% of fulfilled orders met the promised window with an average delay of 1.08 days.
- **Routes & Distance (150 records):** Average haul measures 2,003.7 km consuming 240.6 L of fuel, INR 478.5 in tolls, and 34 minutes of traffic delay per trip.
- **Vehicle Fleet (50 records):** Average vehicle age is 4.19 years with mean CO₂ emission intensity of 0.386 kg/km. Status mix: 28 available, 19 in transit, and 3 in maintenance.
- **Warehouse Inventory (35 records):** Tracks current stock, reorder threshold, and per-unit storage cost across the five Indian warehouses. Aggregate inventory carrying value is INR 2,072,180.57.
- **Customer Feedback (83 records):** Ratings by issue category—Timing (3.26), Service (4.00), Quality (4.00), Other (4.33), and None (3.39).
- **Cost Breakdown (150 records):** Average total fulfilment cost per order is INR 1,204.30 with fuel (INR 200.3) and labour (INR 172.9) as largest components.

## 2. Exploratory Findings
### Demand & Order Mix
- Product demand is broadly distributed: Fashion (34 orders), Books (31), Home Goods (30), Food & Beverage (29), Electronics (29), Industrial (27), Healthcare (20).
- Customer mix leans toward SMB (81 orders), followed by Enterprise (60) and Individual (59).
- Priority split: 46 Express, 84 Standard, 70 Economy. On-time rates are similar (Express 50%, Standard 54%, Economy 55%), indicating systemic process delays rather than priority-specific issues.

### Delivery & Service
- Correlation between customer ratings and delivery delay is **-0.74** (n=83), underscoring that each additional day late materially erodes service perception.
- Quality issues (damage/service) align with lower rating variance, suggesting that lateness—not product condition—is currently the dominant detractor.

### Routes & Fleet
- Long average haul distances and fuel draw emphasise the importance of reducing unnecessary inter-warehouse transfers and last-minute express moves.
- Available vehicles skew toward refrigerated and large trucks, leaving little slack for rapid redeployment if delays occur.

### Inventory Health
- Combined demand/inventory analysis across 35 warehouse-category pairs surfaces **27 surplus** and **7 deficit** combinations. Surpluses are concentrated in Mumbai, Bangalore, and Chennai across Books, Fashion, Food & Beverage, and Healthcare; deficits cluster in Kolkata and Delhi for Books, Electronics, and Industrial goods plus Mumbai Home Goods/Industrial.
- Example surpluses: Mumbai Books (+4,465 units above target), Bangalore Food & Beverage (+3,798), Chennai Fashion (+3,712).
- Example deficits: Kolkata Books (-791), Delhi Electronics (-659), Mumbai Home Goods (-235), Kolkata Industrial (-211).
- Stock cover for many surpluses exceeds 30,000 days because demand counts are low relative to stock, indicating significant carrying-cost opportunities.

### Cost & Risk Signals
- Average total cost per order ranges from INR 1,075 (Bangalore-origin) to INR 1,352 (Hyderabad-origin). Sites heavily dependent on partner hubs incur higher per-order spend.
- Fuel and labour represent 31% of total cost; combining storage and transfer optimisation can reduce repeat handling that inflates these components.

## 3. Optimization Results (90-day demand window, 14-day safety stock)
- **Transfer Plan:** 7 recommended rebalancing moves moving 2,046 units at an estimated transfer cost of INR 9.72M, releasing ~INR 56.8k in holding cost from origin warehouses. Largest moves: Mumbai→Kolkata Books (791 units), Bangalore→Kolkata Industrial (211 units), Mumbai→Delhi Food & Beverage (71 units).
- **Reorder Recommendations:** Total reorder requirement also equals 2,046 units, with focus on Kolkata Books (791), Delhi Electronics (659), Mumbai Home Goods (235), Kolkata Industrial (211), and Mumbai Industrial (74).
- **Classification Totals:** 27 surplus combinations, 7 deficit combinations; 1 combination balances near target.
- **Service Impact:** Executing transfers addresses all major stockouts except residual long-tail demand at Kolkata (post-transfer shortage close to zero). Reorders then rebuild safety stock to the 14-day target.

## 4. Interpretation & Recommendations
1. **Execute staged transfers** prioritising high-value stock relief vs. transfer cost (e.g., Books and Industrial categories). Consider consolidating loads to leverage low-cost Bangalore→Kolkata lanes before expensive Mumbai-origin runs.
2. **Trigger immediate replenishment** for deficit nodes even after transfers—especially Delhi Electronics and Kolkata Books—to prevent recurring express freight and poor customer ratings.
3. **Recalibrate reorder points** for chronic surpluses (e.g., Chennai Healthcare) by halving reorder thresholds or redirecting procurement to deficit nodes.
4. **Tackle systemic delay drivers** by coordinating carrier SLAs; despite priority differentiation, all priorities show ~50–55% on-time performance. Integrating inventory planning with carrier allocation could reduce negative customer sentiment.
5. **Leverage fleet availability**: With 28 vehicles idle, align transfer schedule to use available refrigerated/van capacity, avoiding incremental third-party spend.
6. **Monitor cost-to-serve**: Track the INR 1.2k average order cost at each warehouse and use the Streamlit dashboards to evaluate post-transfer improvements (fuel per km, toll savings, reduced urgent shipments).

## 5. Data & Model Caveats
- Order files lack quantity/weight information; demand estimation assumes one unit per order. Sensitivity analysis on safety-stock days is essential before execution.
- Delivery dataset omits 25% of orders (in-transit or missing); real-time integration would refine delay metrics.
- Transfer cost model is distance-based with static rates; incorporating actual lane rates and handling fees will refine ROI estimates.
- Linear programming option relies on PuLP; if unavailable, heuristic plan remains practical but may over-estimate long-haul transfers.
