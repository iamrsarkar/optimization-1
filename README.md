# NexGen Logistics Warehouse Optimization Suite

A Streamlit-based analytics and optimization application built for **NexGen Logistics Pvt. Ltd.** to unlock inventory insights, rebalance stock intelligently, and control logistics cost.

## 🚀 Features
- Unified data ingestion of seven operational datasets with caching and cleaning.
- Business KPI cockpit with demand trends and moving-average demand forecasting.
- Inventory health analytics with understock/overstock detection, interactive visuals, and CSV exports.
- Transfer and reorder recommendations with optional PuLP-based optimization.
- Cost and sustainability dashboard including CO₂ intelligence and customer feedback snapshot.

## 📂 Project Structure
```
.
├── app.py                  # Streamlit application entry point
├── config.py               # Global configuration parameters
├── data_loader.py          # Data ingestion & preprocessing helpers
├── eda_utils.py            # KPI calculations, filtering, and forecasting
├── viz_utils.py            # Plotly visualization builders
├── warehouse_optimizer.py  # Transfer heuristics & linear programming model
├── requirements.txt        # Python dependencies
├── README.md               # Project overview & setup guide
└── innovation_brief.md     # Business impact summary
```

## 🛠️ Installation
1. Create and activate a virtual environment (optional but recommended).
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use .venv\Scripts\activate
   ```
2. Install dependencies.
   ```bash
   pip install -r requirements.txt
   ```

## ▶️ Usage
Run the Streamlit application from the project root:
```bash
streamlit run app.py
```
The dashboard automatically loads the CSV datasets bundled with the project.

## 📈 Data Sources
- `orders.csv`
- `delivery_performance.csv`
- `routes_distance.csv`
- `vehicle_fleet.csv`
- `warehouse_inventory.csv`
- `customer_feedback.csv`
- `cost_breakdown.csv`

## 🧠 Optimization Notes
- Heuristic transfer planning balances surplus and deficit warehouses per product using inter-city road distances.
- Optional PuLP optimization minimizes combined transfer and storage cost when PuLP is installed.

## 🤝 Contributions
Contributions and enhancements are welcome via pull requests. Please ensure code is well-documented and tested.

## 📄 License
This project is created for the NexGen Logistics case study scenario and is released without a formal license.
