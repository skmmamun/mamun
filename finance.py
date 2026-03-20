import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime

# --- 1. DATABASE SYSTEM ---
def init_db():
    conn = sqlite3.connect('finance_flow_v6.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY, name TEXT UNIQUE)')
    c.execute('CREATE TABLE IF NOT EXISTS subcategories (id INTEGER PRIMARY KEY, cat_id INTEGER, name TEXT)')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions 
                 (id INTEGER PRIMARY KEY, date TEXT, type TEXT, 
                  category TEXT, subcategory TEXT, amount REAL, 
                  quantity REAL, unit TEXT, notes TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- 2. NAVIGATION ---
st.set_page_config(page_title="Rooppur Taka Ledger", layout="wide")
st.sidebar.title("৳ Navigation")
menu = st.sidebar.radio("Select Task", [
    "Financial Dashboard", 
    "Record Income", 
    "Record Expenditure", 
    "Manage Lists & Deletion"
])

# --- 3. RECORD INCOME (SIMPLE) ---
if menu == "Record Income":
    st.header("💰 Record New Income")
    conn = sqlite3.connect('finance_flow_v6.db')
    cat_list = pd.read_sql("SELECT name FROM categories", conn)['name'].tolist()
    
    with st.form("income_form"):
        col1, col2 = st.columns(2)
        with col1:
            t_date = st.date_input("Date", datetime.now())
            source = st.selectbox("Source (Category)", cat_list if cat_list else ["Add a category first"])
        with col2:
            amount = st.number_input("Income Amount (৳)", min_value=0.0, step=500.0)
        
        note = st.text_area("Notes / Details")
        
        if st.form_submit_button("Save Income"):
            if not cat_list:
                st.error("Please add a category in 'Manage Lists' first.")
            else:
                conn.execute('''INSERT INTO transactions 
                                (date, type, category, subcategory, amount, quantity, unit, notes) 
                                VALUES (?,?,?,?,?,?,?,?)''',
                             (t_date.strftime("%Y-%m-%d"), "Income", source, "Income Entry", amount, 1.0, "N/A", note))
                conn.commit()
                st.success(f"Income of ৳{amount} recorded.")
    conn.close()

# --- 4. RECORD EXPENDITURE (FIXED DYNAMIC DROPDOWNS) ---
elif menu == "Record Expenditure":
    st.header("🛒 Record New Expenditure")
    conn = sqlite3.connect('finance_flow_v6.db')
    
    # 1. Fetch Main Categories
    cat_df = pd.read_sql("SELECT name FROM categories", conn)
    cat_list = cat_df['name'].tolist()
    
    if not cat_list:
        st.warning("⚠️ Setup categories first in 'Manage Lists'.")
    else:
        # --- MOVE SELECTORS OUTSIDE THE FORM FOR AUTO-UPDATE ---
        col_cat, col_sub = st.columns(2)
        
        with col_cat:
            main_cat = st.selectbox("Main Category", cat_list)
        
        # 2. Fetch Sub-items IMMEDIATELY based on main_cat
        c = conn.cursor()
        c.execute("SELECT name FROM subcategories WHERE cat_id = (SELECT id FROM categories WHERE name = ?)", (main_cat,))
        sub_list = [r[0] for r in c.fetchall()]
        
        with col_sub:
            # This will now refresh instantly when main_cat changes
            item = st.selectbox("Specific Item (Subcategory)", sub_list if sub_list else ["General"])

        # --- START FORM FOR THE REMAINING DATA ---
        with st.form("exp_details_form"):
            t_date = st.date_input("Date", datetime.now())
            
            col_q, col_u, col_a = st.columns([1, 1, 2])
            with col_q:
                qty = st.number_input("Quantity", min_value=0.1, step=0.1, value=1.0)
            with col_u:
                unit = st.selectbox("Unit", ["kg", "gram", "ltr", "pcs", "box", "month", "N/A"])
            with col_a:
                amount = st.number_input("Total Amount (৳)", min_value=0.0, step=100.0)
            
            note = st.text_area("Note / Details")
            
            submit = st.form_submit_button("Save Expenditure")
            
            if submit:
                conn.execute('''INSERT INTO transactions 
                                (date, type, category, subcategory, amount, quantity, unit, notes) 
                                VALUES (?,?,?,?,?,?,?,?)''',
                             (t_date.strftime("%Y-%m-%d"), "Expenditure", main_cat, item, amount, qty, unit, note))
                conn.commit()
                st.success(f"✅ Saved: ৳{amount} for {item}")
                # Optional: st.rerun() to clear the form
    conn.close()

# --- 5. MANAGE LISTS & DELETION ---
elif menu == "Manage Lists & Deletion":
    st.header("📋 Setup & Cleanup")
    col_add, col_del = st.columns(2)
    with col_add:
        st.subheader("➕ Add New")
        mode = st.radio("Target", ["Main Category", "Sub-item"])
        n_input = st.text_input("Name")
        if mode == "Sub-item":
            conn = sqlite3.connect('finance_flow_v6.db')
            cats = pd.read_sql("SELECT name FROM categories", conn)['name'].tolist()
            target = st.selectbox("Parent Category", cats)
            conn.close()
            
        if st.button("Save"):
            conn = sqlite3.connect('finance_flow_v6.db')
            if mode == "Main Category":
                try:
                    conn.execute("INSERT INTO categories (name) VALUES (?)", (n_input,))
                    conn.commit()
                    st.success("Added Category.")
                    st.rerun()
                except: st.error("Already exists.")
            else:
                c = conn.cursor()
                c.execute("SELECT id FROM categories WHERE name = ?", (target,))
                conn.execute("INSERT INTO subcategories (cat_id, name) VALUES (?, ?)", (c.fetchone()[0], n_input))
                conn.commit()
                st.success("Added Sub-item.")
                st.rerun()
            conn.close()
            
    with col_del:
        st.subheader("🗑️ Delete Sub-item")
        conn = sqlite3.connect('finance_flow_v6.db')
        all_cats = pd.read_sql("SELECT name FROM categories", conn)['name'].tolist()
        if all_cats:
            v_cat = st.selectbox("View Items in", all_cats)
            c = conn.cursor()
            c.execute("SELECT name FROM subcategories WHERE cat_id = (SELECT id FROM categories WHERE name = ?)", (v_cat,))
            subs = [r[0] for r in c.fetchall()]
            t_del = st.selectbox("Item to Remove", ["-- Select --"] + subs)
            if t_del != "-- Select --":
                confirm = st.checkbox("Confirm Deletion")
                if st.button("Delete") and confirm:
                    conn.execute("DELETE FROM subcategories WHERE name = ? AND cat_id = (SELECT id FROM categories WHERE name = ?)", (t_del, v_cat))
                    conn.commit()
                    st.rerun()
        conn.close()

# --- 6. DASHBOARD WITH SEARCH ---
else:
    st.header("📊 Financial Summary")
    conn = sqlite3.connect('finance_flow_v6.db')
    df = pd.read_sql("SELECT * FROM transactions", conn)
    conn.close()

    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df['month_year'] = df['date'].dt.strftime('%B %Y')
        selected_month = st.sidebar.selectbox("Select Month", df['month_year'].unique())
        
        # 1. APPLY MONTH FILTER
        f_df = df[df['month_year'] == selected_month]
        
        # 2. SEARCH BAR
        search_query = st.text_input("🔍 Search History (Type Category, Item, or Note keyword)", "")
        if search_query:
            # Filters the current view based on keywords in Category, Subcategory, or Notes
            f_df = f_df[
                f_df['category'].str.contains(search_query, case=False) | 
                f_df['subcategory'].str.contains(search_query, case=False) |
                f_df['notes'].str.contains(search_query, case=False)
            ]

        inc = f_df[f_df['type'] == "Income"]['amount'].sum()
        exp = f_df[f_df['type'] == "Expenditure"]['amount'].sum()
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Income", f"৳{inc:,.0f}")
        k2.metric("Expenditure", f"৳{exp:,.0f}", delta=f"-৳{exp:,.0f}", delta_color="inverse")
        k3.metric("Net Balance", f"৳{inc-exp:,.0f}")

        st.divider()
        st.subheader(f"Records: {selected_month}")
        st.dataframe(f_df.sort_values('date', ascending=False), use_container_width=True)
        
        csv = f_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export Current View", data=csv, file_name=f"taka_report_{selected_month}.csv")
    else:
        st.info("No records yet.")