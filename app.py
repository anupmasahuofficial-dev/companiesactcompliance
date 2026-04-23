import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import json
import plotly.express as px
import os

st.set_page_config(page_title="Corporate Compliance Intelligence", layout="wide", page_icon="🏢")

# --- UI/UX ANT DESIGN CSS ---
st.markdown("""
    <style>
        .stApp { background-color: #f0f2f5; }
        .ant-card {
            background: #fff;
            border-radius: 8px;
            box-shadow: 0 1px 2px 0 rgba(0,0,0,0.03);
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid #f0f0f0;
        }
        .ant-metric-value { font-size: 28px; font-weight: 600; color: #1890ff; }
        .ant-metric-title { font-size: 14px; color: #8c8c8c; margin-bottom: 8px; }
        div[data-testid="stMetricValue"] { font-size: 24px; color: #1f1f1f; }
    </style>
""", unsafe_allow_html=True)

# --- CORE FUNCTIONS ---

def generate_sample_tally_data():
    """Generates a sample JSON dataset representing Tally export data."""
    sample_data = {
        "company_name": "TechNova Solutions Pvt Ltd",
        "cin": "U72900KA2021PTC123456",
        "company_type": "Private",
        "financial_year": "2023-24",
        "incorporation_date": "2021-05-15",
        "turnover_in_cr": 12.5,
        "paid_up_capital_in_cr": 2.0,
        "agm_date": "2023-09-30", # Intentionally set in the past to show overdue penalties
        "board_meetings": ["2023-05-10", "2023-08-22", "2023-11-15", "2024-02-28"],
        "transactions": [
            {"date": "2023-06-15", "type": "Related Party Transaction", "amount": 500000},
            {"date": "2023-09-01", "type": "Director Loan", "amount": 1000000}
        ]
    }
    with open("sample_tally_data.json", "w") as f:
        json.dump(sample_data, f, indent=4)
    return sample_data

def tally_parser(uploaded_file):
    """Parses imported Tally JSON/Excel data."""
    if uploaded_file is not None:
        try:
            data = json.load(uploaded_file)
            return data
        except Exception as e:
            st.error(f"Error parsing Tally data: {e}")
            return None
    return None

def compliance_engine(company_data):
    """Determines section-wise applicability based on Companies Act, 2013."""
    compliances = []
    agm_date = datetime.strptime(company_data['agm_date'], "%Y-%m-%d").date()
    
    # Sec 137: Filing of Financial Statements (AOC-4) -> Due within 30 days of AGM
    aoc4_due_date = agm_date + timedelta(days=30)
    compliances.append({
        "Section": "Sec 137",
        "Form": "AOC-4",
        "Description": "Filing of Financial Statements",
        "Due Date": aoc4_due_date,
        "Status": "Upcoming" if aoc4_due_date >= date.today() else "Overdue",
        "Applicability": "All Companies"
    })

    # Sec 92: Annual Return (MGT-7/MGT-7A) -> Due within 60 days of AGM
    mgt7_due_date = agm_date + timedelta(days=60)
    compliances.append({
        "Section": "Sec 92",
        "Form": "MGT-7" if company_data['company_type'] != "OPC" else "MGT-7A",
        "Description": "Filing of Annual Return",
        "Due Date": mgt7_due_date,
        "Status": "Upcoming" if mgt7_due_date >= date.today() else "Overdue",
        "Applicability": "All Companies"
    })
    
    # Sec 173: Board Meetings -> Min 4 meetings, gap not > 120 days
    meetings = [datetime.strptime(d, "%Y-%m-%d").date() for d in company_data.get('board_meetings', [])]
    status = "Completed" if len(meetings) >= 4 else "Overdue"
    compliances.append({
        "Section": "Sec 173",
        "Form": "Board Minutes",
        "Description": f"Board Meetings (Held: {len(meetings)})",
        "Due Date": agm_date, # simplified representative date
        "Status": status,
        "Applicability": "All Companies"
    })
    
    return pd.DataFrame(compliances)

def penalty_calculator(section, due_date, actual_filing_date=None):
    """
    Calculates penalties for non-compliance based on Companies Act, 2013.
    Includes delay-based fee multipliers and daily penalties with max caps.
    """
    if actual_filing_date is None:
        actual_filing_date = date.today()
        
    delay_days = (actual_filing_date - due_date).days
    if delay_days <= 0:
        return 0, 0, 0
        
    penalty_company = 0
    penalty_officer = 0
    base_late_fee = 0
    
    if section in ["Sec 92", "Sec 137"]:
        # Late filing fees (Rs 100 per day) as per Companies (Registration Offices and Fees) Rules, 2014
        base_late_fee = 100 * delay_days
        
        # Sec 92(5): Company & Officer - Rs 10,000 + Rs 100/day (Max 2L company, 50k officer)
        # Sec 137(3): Company - Rs 10,000 + Rs 100/day (Max 2L) | Officer - Rs 10,000 + Rs 100/day (Max 50k)
        penalty_company = min(10000 + (100 * delay_days), 200000)
        penalty_officer = min(10000 + (100 * delay_days), 50000)
        
    return base_late_fee, penalty_company, penalty_officer

# --- APP LAYOUT ---

def main():
    # Initialize session state & sample data
    if 'company_data' not in st.session_state:
        st.session_state.company_data = generate_sample_tally_data()
        
    # Sidebar: Client Management System
    st.sidebar.title("🏢 Navigation")
    menu = st.sidebar.radio("Modules", [
        "Dashboard", 
        "Compliance Calendar", 
        "Penalty Engine", 
        "Tally Import", 
        "Document Checklist"
    ])
    
    st.sidebar.divider()
    st.sidebar.subheader("👤 Active Client")
    st.sidebar.info(f"**{st.session_state.company_data['company_name']}**\n\nCIN: {st.session_state.company_data['cin']}\n\nType: {st.session_state.company_data['company_type']}")
    
    df_comp = compliance_engine(st.session_state.company_data)
    
    if menu == "Dashboard":
        st.header("📊 Smart Compliance Dashboard")
        
        col1, col2, col3, col4 = st.columns(4)
        total = len(df_comp)
        completed = len(df_comp[df_comp['Status'] == 'Completed'])
        overdue = len(df_comp[df_comp['Status'] == 'Overdue'])
        upcoming = len(df_comp[df_comp['Status'] == 'Upcoming'])
        
        with col1:
            st.markdown(f'<div class="ant-card"><div class="ant-metric-title">Total Compliances</div><div class="ant-metric-value">{total}</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="ant-card"><div class="ant-metric-title">Completed</div><div class="ant-metric-value" style="color: #52c41a;">{completed}</div></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="ant-card"><div class="ant-metric-title">Overdue</div><div class="ant-metric-value" style="color: #f5222d;">{overdue}</div></div>', unsafe_allow_html=True)
        with col4:
            st.markdown(f'<div class="ant-card"><div class="ant-metric-title">Upcoming</div><div class="ant-metric-value" style="color: #faad14;">{upcoming}</div></div>', unsafe_allow_html=True)

        c1, c2 = st.columns([1, 1])
        with c1:
            st.subheader("Compliance Overview")
            fig = px.pie(names=['Completed', 'Overdue', 'Upcoming'], values=[completed, overdue, upcoming], 
                         color_discrete_sequence=['#52c41a', '#f5222d', '#faad14'], hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
            
        with c2:
            st.subheader("🔔 Alerts & Escalations")
            for _, row in df_comp[df_comp['Status'] == 'Overdue'].iterrows():
                delay = (date.today() - row['Due Date']).days
                st.error(f"**URGENT:** {row['Form']} ({row['Section']}) is overdue by {delay} days! Penalty compounding daily.")
            for _, row in df_comp[df_comp['Status'] == 'Upcoming'].iterrows():
                days_left = (row['Due Date'] - date.today()).days
                st.warning(f"**Reminder:** {row['Form']} due in {days_left} days ({row['Due Date'].strftime('%d %b %Y')}).")

    elif menu == "Compliance Calendar":
        st.header("📅 ROC Forms & Due Date Tracker")
        
        def color_status(val):
            color = '#52c41a' if val == 'Completed' else '#f5222d' if val == 'Overdue' else '#faad14'
            return f'color: {color}; font-weight: bold'
            
        st.dataframe(df_comp.style.map(color_status, subset=['Status']), use_container_width=True, hide_index=True)

    elif menu == "Penalty Engine":
        st.header("⚖️ Penalty Calculator (Sec 92 & 137)")
        overdue_forms = df_comp[df_comp['Status'] == 'Overdue']
        
        if overdue_forms.empty:
            st.success("✅ No overdue compliances! Zero penalties applicable.")
        else:
            total_late_fee, total_company_pen, total_officer_pen = 0, 0, 0
            penalties_data = []
            
            for _, row in overdue_forms.iterrows():
                late_fee, pen_comp, pen_off = penalty_calculator(row['Section'], row['Due Date'])
                total_late_fee += late_fee
                total_company_pen += pen_comp
                total_officer_pen += pen_off
                
                penalties_data.append({
                    "Form": row['Form'],
                    "Section Reference": row['Section'],
                    "Days Delayed": (date.today() - row['Due Date']).days,
                    "Additional Fee (₹)": f"₹ {late_fee:,}",
                    "Max Company Penalty (₹)": f"₹ {pen_comp:,}",
                    "Max Officer Penalty (₹)": f"₹ {pen_off:,}"
                })
                
            st.dataframe(pd.DataFrame(penalties_data), use_container_width=True, hide_index=True)
            
            st.subheader("Total Exposure Assessment")
            col1, col2, col3 = st.columns(3)
            col1.metric("Accrued Additional Fees", f"₹ {total_late_fee:,}")
            col2.metric("Company Penalty Exposure", f"₹ {total_company_pen:,}")
            col3.metric("Officer Penalty Exposure", f"₹ {total_officer_pen:,}")
            
            st.info("💡 **Legal Reference:** Penalties calculated as per Section 454 read with Section 92(5) and Section 137(3) of Companies Act, 2013.")

    elif menu == "Tally Import":
        st.header("🔗 Tally Data Import (JSON/Excel Simulation)")
        
        uploaded_file = st.file_uploader("Upload Tally JSON Export", type=['json'])
        if uploaded_file is not None:
            new_data = tally_parser(uploaded_file)
            if new_data:
                st.session_state.company_data = new_data
                st.success("Data imported and parsed successfully! Compliance engines synced.")
                st.json(new_data)
        
        st.divider()
        st.subheader("Sample Tally Dataset")
        st.write("Use this auto-generated file to test the import functionality.")
        with open("sample_tally_data.json", "r") as f:
            st.download_button("Download sample_tally_data.json", f, file_name="sample_tally_data.json", mime="application/json")

    elif menu == "Document Checklist":
        st.header("📑 Mandatory Document Checklist")
        st.markdown("Ensure these documents are prepared prior to ROC filings.")
        
        st.checkbox("Signed Financial Statements (Balance Sheet, P&L, Cash Flow) - Sec 134")
        st.checkbox("Board's Report & Annexures (MGT-9/AOC-2) - Sec 134")
        st.checkbox("Notice of AGM with Explanatory Statement - Sec 101 & 102")
        st.checkbox("Statutory Audit Report - Sec 143")
        st.checkbox("List of Shareholders/Debenture Holders as on AGM date - Sec 92")
        st.checkbox("Digital Signature Certificate (DSC) of Authorized Director - Valid & Registered")

if __name__ == "__main__":
    main()
