# checQout

Intelligent Retail Queue Management & Customer Allocation System.

## MVP features
- M/M/c queueing analysis using Erlang C.
- Integer-programming selection of active checkout counters.
- Workload-based customer-to-counter recommendation.
- Discrete-event simulation using SimPy.
- Streamlit dashboard with clearly labelled illustrative sample data.

## Run locally
1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Create and activate a virtual environment (recommended).
4. Install dependencies:
   `pip install -r requirements.txt`
5. Start the dashboard:
   `streamlit run app.py`

## Data note
`data/sample_demand.csv` contains illustrative hourly demand assumptions, not observed supermarket data. Replace these values with measured arrivals and service times before drawing real-world conclusions.

## Model assumptions
The analytical model assumes Poisson arrivals, exponential service times, identical parallel counters and a common queue. The simulation uses stochastic arrivals and service times and a shortest-estimated-workload routing policy.
