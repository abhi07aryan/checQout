import streamlit as st
import pandas as pd
import plotly.express as px
from modules.queue_model import mmc_metrics, candidate_table
from modules.optimization import optimize_counters
from modules.allocator import recommend_counter
from modules.simulation import simulate_checkout

st.set_page_config(page_title="checQout",page_icon="🛒",layout="wide")
st.title("🛒 checQout")
st.caption("Intelligent Retail Queue Management & Customer Allocation System")
st.info("Prototype note: the included demand profile is illustrative sample data, not measured supermarket data.")

@st.cache_data
def load_data():
    return pd.read_csv("data/sample_demand.csv")
data=load_data()

with st.sidebar:
    st.header("Store parameters")
    mu=st.number_input("Service rate per counter (customers/hour)",min_value=1.0,max_value=120.0,value=20.0,step=1.0)
    max_c=st.number_input("Maximum available counters",min_value=1,max_value=30,value=6,step=1)
    counter_cost=st.number_input("Cost per active counter per hour (₹)",min_value=0.0,value=150.0,step=10.0)
    wait_cost=st.number_input("Waiting cost (₹ per customer-hour)",min_value=0.0,value=30.0,step=5.0)
    max_wait=st.number_input("Maximum target queue wait (minutes)",min_value=0.0,value=8.0,step=1.0)

tabs=st.tabs(["Overview","Queue Analysis","Counter Optimization","Customer Allocation","Simulation","Data"])

with tabs[0]:
    st.subheader("Today's illustrative demand profile")
    c1,c2,c3=st.columns(3)
    c1.metric("Planning intervals",len(data))
    c2.metric("Peak arrival rate",f"{data.arrival_rate_per_hour.max():.0f} customers/hour")
    c3.metric("Mean arrival rate",f"{data.arrival_rate_per_hour.mean():.1f} customers/hour")
    fig=px.line(data,x="time_interval",y="arrival_rate_per_hour",markers=True,
                labels={"time_interval":"Time interval","arrival_rate_per_hour":"Arrivals/hour"},
                title="Estimated customer arrivals by interval")
    st.plotly_chart(fig,use_container_width=True)
    st.markdown("""
    **How checQout works**
    1. Estimate arrivals and service capacity.
    2. Use M/M/c to calculate expected queue performance.
    3. Use Integer Programming to select active counters.
    4. Route customers using estimated counter workload.
    5. Compare policies using simulation.
    """)

with tabs[1]:
    st.subheader("M/M/c queueing analysis")
    col1,col2=st.columns(2)
    lam=col1.number_input("Arrival rate λ (customers/hour)",min_value=0.0,value=48.0,step=1.0,key="q_lam")
    c=col2.number_input("Active counters c",min_value=1,max_value=int(max_c),value=min(3,int(max_c)),step=1,key="q_c")
    m=mmc_metrics(lam,mu,int(c))
    if not m["stable"]:
        st.error("Unstable configuration: arrival rate is at least the total service capacity (λ ≥ cμ).")
    else:
        a,b,d,e=st.columns(4)
        a.metric("Utilization",f"{m['rho']*100:.1f}%")
        b.metric("Expected queue wait",f"{m['wq_hours']*60:.2f} min")
        d.metric("Expected queue length",f"{m['lq']:.2f}")
        e.metric("Probability of waiting",f"{m['p_wait']*100:.1f}%")
        table=pd.DataFrame(candidate_table(lam,mu,int(max_c)))
        st.dataframe(table,use_container_width=True,hide_index=True)

with tabs[2]:
    st.subheader("Choose active counters")
    chosen_interval=st.selectbox("Select demand interval",data.time_interval.tolist(),index=8)
    lam=float(data.loc[data.time_interval==chosen_interval,"arrival_rate_per_hour"].iloc[0])
    st.write(f"Arrival rate for **{chosen_interval}**: **{lam:.1f} customers/hour**")
    result=optimize_counters(lam,mu,int(max_c),counter_cost,wait_cost,max_wait)
    if result["feasible"]:
        st.success(f"Recommended active counters: {result['recommended_c']}")
        mm=result["metrics"]
        a,b,d=st.columns(3)
        a.metric("Predicted queue wait",f"{mm['wq_hours']*60:.2f} min")
        b.metric("Utilization",f"{mm['rho']*100:.1f}%")
        d.metric("Modeled cost / hour",f"₹{result['objective_value']:.2f}")
        st.dataframe(pd.DataFrame(result["candidates"]),use_container_width=True,hide_index=True)
    else:
        st.warning(result["message"])
        if result["recommended_c"] is not None:
            st.write(f"Minimum-wait stable option within available counters: {result['recommended_c']} counters; predicted wait {result['minimum_wait_min']:.2f} minutes.")
        st.caption("Consider increasing counter availability, revising the service target, or validating the arrival/service assumptions.")


with tabs[3]:
    st.subheader("Customer-to-counter recommendation")

    st.write(
        "Enter the current queue and service status of each active "
        "counter. checQout will recommend the counter with the "
        "lowest estimated workload."
    )

    n = st.number_input(
        "Number of active counters",
        min_value=1,
        max_value=int(max_c),
        value=min(4, int(max_c)),
        step=1,
        key="a_n"
    )

    counter_cols = st.columns(int(n))

    queues = []
    remaining_times = []
    rates = [float(mu)] * int(n)

    for j, col in enumerate(counter_cols):

        with col:
            st.markdown(f"**Counter {j + 1}**")

            queue = st.number_input(
                "Customers waiting",
                min_value=0,
                max_value=100,
                value=[4, 2, 6, 1, 3, 5][j % 6],
                step=1,
                key=f"queue_{j}"
            )

            is_serving = st.checkbox(
                "Currently serving a customer",
                value=False,
                key=f"serving_{j}"
            )

            if is_serving:
                remaining_minutes = st.number_input(
                    "Remaining service time (minutes)",
                    min_value=0.0,
                    max_value=120.0,
                    value=2.0,
                    step=0.5,
                    key=f"remaining_{j}"
                )
            else:
                remaining_minutes = 0.0

            queues.append(int(queue))

            # Convert minutes into hours
            remaining_times.append(
                remaining_minutes / 60
            )

    # Calculate workload and recommend a counter
    allocation = recommend_counter(
        queues,
        rates,
        remaining_service=remaining_times
    )

    recommended = allocation["counter_index"] + 1

    st.success(
        f"Recommended counter: Counter {recommended}"
    )

    st.metric(
        "Estimated waiting workload",
        f"{allocation['estimated_wait_minutes']:.2f} minutes"
    )

    # Prepare workload comparison chart
    chart = pd.DataFrame({
        "Counter": [
            f"Counter {i + 1}" for i in range(int(n))
        ],
        "Estimated workload (minutes)": (
            allocation["workloads_minutes"]
        )
    })

    fig = px.bar(
        chart,
        x="Counter",
        y="Estimated workload (minutes)",
        title="Estimated workload at each checkout counter",
        text_auto=".2f"
    )

    st.plotly_chart(fig, width="stretch")

    st.caption(
        "Workload = remaining service time of the current customer "
        "+ expected service time of customers waiting in the queue. "
        "The estimate assumes a constant service rate at each counter."
    )


with tabs[4]:

    st.subheader("Discrete-event simulation")

    c1, c2, c3 = st.columns(3)

    sim_lam = c1.number_input(
        "Arrival rate",
        min_value=1.0,
        value=60.0,
        step=1.0,
        key="s_lam"
    )

    sim_c = c2.number_input(
        "Counters",
        min_value=1,
        max_value=int(max_c),
        value=min(4, int(max_c)),
        step=1,
        key="s_c"
    )

    duration = c3.number_input(
        "Simulation duration (hours)",
        min_value=1,
        max_value=24,
        value=3,
        step=1
    )

    routing = st.selectbox(
        "Customer routing policy",
        ["shortest", "round_robin"],
        format_func=lambda x:
            "Shortest estimated workload"
            if x == "shortest"
            else "Round robin"
    )

    if st.button("Run simulation", type="primary"):

        sim = simulate_checkout(
            sim_lam,
            mu,
            int(sim_c),
            duration_hours=float(duration),
            routing=routing
        )

        st.subheader("Simulation Results")

        # Performance metrics
        a, b, d, e = st.columns(4)

        a.metric(
            "Customers served",
            sim["customers"]
        )

        b.metric(
            "Average waiting time",
            f"{sim['avg_wait_min']:.2f} min"
        )

        d.metric(
            "Maximum waiting time",
            f"{sim['max_wait_min']:.2f} min"
        )

        efficiency = sim["allocation_efficiency"]

        e.metric(
            "Allocation efficiency",
            f"{efficiency:.2f}%"
            if efficiency is not None
            else "N/A"
        )

        # Waiting time distribution
        if sim["waits_min"]:

            st.plotly_chart(
                px.histogram(
                    pd.DataFrame({
                        "Waiting time (min)": sim["waits_min"]
                    }),
                    x="Waiting time (min)",
                    nbins=25,
                    title="Distribution of simulated waiting times"
                ),
                use_container_width=True
            )

        # Counter workload distribution
        st.subheader("Counter Workload Distribution")

        workload_data = pd.DataFrame({
            "Counter": [
                f"Counter {i + 1}"
                for i in range(int(sim_c))
            ],

            "Customers allocated": sim["counter_customers"],

            "Workload (minutes)": sim["counter_workloads_min"]
        })

        st.plotly_chart(
            px.bar(
                workload_data,
                x="Counter",
                y="Workload (minutes)",
                text_auto=".2f",
                title="Total service workload assigned to each counter"
            ),
            use_container_width=True
        )

        st.dataframe(
            workload_data,
            use_container_width=True,
            hide_index=True
        )

        st.caption(
            "Allocation efficiency is calculated using Jain's Fairness "
            "Index. A higher percentage indicates a more balanced "
            "distribution of service workload among active counters."
        )

        st.caption(
            "Simulation uses stochastic arrivals and service times. "
            "Repeat with several seeds and compare policies before "
            "drawing conclusions."
        )


with tabs[5]:
    st.subheader("Demand input data")
    st.dataframe(data,use_container_width=True,hide_index=True)
    st.download_button("Download sample demand CSV",data.to_csv(index=False),file_name="sample_demand.csv",mime="text/csv")
    uploaded=st.file_uploader("Upload your own demand CSV (columns: time_interval, arrival_rate_per_hour)",type=["csv"])
    if uploaded:
        user_data=pd.read_csv(uploaded)
        required={"time_interval","arrival_rate_per_hour"}
        if required.issubset(user_data.columns):
            st.success("File structure looks valid. This uploaded profile is previewed here; replace sample data in the project folder to use it across all modules.")
            st.dataframe(user_data,use_container_width=True)
        else:
            st.error("CSV must contain: time_interval, arrival_rate_per_hour.")
