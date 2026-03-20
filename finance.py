import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- 1. DATABASE & SETTINGS SYSTEM ---
def init_db():
    conn = sqlite3.connect('finance_final.db', check_same_thread=False)
    c = conn.cursor()
    # Core Data Tables
    c.execute('CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY, name TEXT UNIQUE)')
    c.execute('CREATE TABLE IF NOT EXISTS subcategories (id INTEGER PRIMARY KEY, cat_id INTEGER, name TEXT)')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions 
                 (id INTEGER PRIMARY KEY, date TEXT, type TEXT, 
                  category TEXT, subcategory TEXT, amount REAL, 
                  quantity REAL, unit TEXT, notes TEXT)''')
    
    # Table for Permanent Settings (Password)
    c.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
    
    # Set default password to admin123 if the table is new
    c.execute("SELECT value FROM settings WHERE key = 'admin_password'")
    if c.fetchone() is None:
        c.execute("INSERT INTO settings (key, value) VALUES ('admin_password', 'admin123')")
    
    conn.commit()
    conn.close()

def get_stored_password():
    conn = sqlite3.connect('finance_final.db')
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = 'admin_password'")
    res = c.fetchone()
    conn.close()
    return res[0] if res else "admin123"

def update_stored_password(new_pw):
    conn = sqlite3.connect('finance_final.db')
    c = conn.cursor()
    c.execute("UPDATE settings SET value = ? WHERE key = 'admin_password'", (new_pw,))
    conn.commit()
    conn.close()

init_db()

# --- 2. LOGIN SYSTEM ---
def check_password():
    def password_entered():
        stored_pw = get_stored_password()
        if st.session_state["username"] == "admin" and st.session_state["password"] == stored_pw:
            st.session_state["password_correct"] = True
            del st.session_state["password"] 
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("৳ Rooppur Ledger Login")
        st.text_input("Username", on_change=password_entered, key="username")
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Username", on_change=password_entered, key="username")
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        st.error("😕 Username or password incorrect")
        return False
    return True

# --- 3. MAIN APP ---
if check_password():
    st.sidebar.title("৳ Navigation")
    menu = st.sidebar.radio("Select Task", [
        "Financial Dashboard", 
        "Record Income", 
        "Record Expenditure", 
        "Manage Lists & Deletion",
        "Security Settings"
    ])

    # --- SECURITY SETTINGS ---
    if menu == "Security Settings":
        st.header("🔐 Security Settings")
        st.subheader("Change Login Password Permanently")
        with st.form("change_pw_form"):
            current_pw_db = get_stored_password()
            old_pw = st.text_input("Current Password", type="password")
            new_pw = st.text_input("New Password", type="password")
            confirm_pw = st.text_input("Confirm New Password", type="password")
            if st.form_submit_button("Update Password"):
                if old_pw != current_pw_db:
                    st.error("❌ Current password incorrect.")
                elif new_pw != confirm_pw:
                    st.error("❌ New passwords do not match.")
                elif len(new_pw) < 4:
                    st.error("❌ Min 4 characters required.")
                else:
                    update_stored_password(new_pw)
                    st.success("✅ Password updated permanently!")

    # --- RECORD INCOME ---
    elif menu == "Record Income":
        st.header("💰 Record New Income")
        conn = sqlite3.connect('finance_final.db')
        cat_list = pd.read_sql("SELECT name FROM categories", conn)['name'].tolist()
        with st.form("income_form"):
            t_date = st.date_input("Date", datetime.now())
            source = st.selectbox("Source (Category)", cat_list if cat_list else ["Setup Category First"])
            amount = st.number_input("Amount (৳)", min_value=0.0, step=500.0)
            note = st.text_area("Note")
            if st.form_submit_button("Save Income"):
                if not cat_list: st.error("Add a category first!")
                else:
                    conn.execute("INSERT INTO transactions (date, type, category, subcategory, amount, quantity, unit, notes) VALUES (?,?,?,?,?,?,?,?)",
                                 (t_date.strftime("%Y-%m-%d"), "Income", source, "Income Entry", amount, 1.0, "N/A", note))
                    conn.commit()
                    st.success("Income Logged.")
        conn.close()

    # --- RECORD EXPENDITURE ---
    elif menu == "Record Expenditure":
        st.header("🛒 Record Expenditure")
        conn = sqlite3.connect('finance_final.db')
        cat_list = pd.read_sql("SELECT name FROM categories", conn)['name'].tolist()
        if not cat_list:
            st.warning("⚠️ No categories found.")
        else:
            col_a, col_b = st.columns(2)
            with col_a: main_cat = st.selectbox("Category", cat_list)
            c = conn.cursor()
            c.execute("SELECT name FROM subcategories WHERE cat_id = (SELECT id FROM categories WHERE name = ?)", (main_cat,))
            sub_list = [r[0] for r in c.fetchall()]
            with col_b: item = st.selectbox("Item", sub_list if sub_list else ["General"])
            
            with st.form("exp_form"):
                t_date = st.date_input("Date", datetime.now())
                q, u, a = st.columns([1,1,2])
                with q: qty = st.number_input("Qty", min_value=0.1, value=1.0)
                with u: unit = st.selectbox("Unit", ["kg", "gram", "ltr", "pcs", "month", "N/A"])
                with a: amt = st.number_input("Total (৳)", min_value=0.0, step=100.0)
                note = st.text_area("Note")
                if st.form_submit_button("Save"):
                    conn.execute("INSERT INTO transactions (date, type, category, subcategory, amount, quantity, unit, notes) VALUES (?,?,?,?,?,?,?,?)",
                                 (t_date.strftime("%Y-%m-%d"), "Expenditure", main_cat, item, amt, qty, unit, note))
                    conn.commit()
                    st.success("Saved.")
        conn.close()

    # --- MANAGE LISTS (RESTORED) ---
    elif menu == "Manage Lists & Deletion":
        st.header("📋 Manage Categories & Sub-items")
        col_add, col_del = st.columns(2)
        
        with col_add:
            st.subheader("➕ Add New")
            mode = st.radio("Type", ["Main Category", "Sub-item"])
            name_input = st.text_input("Name")
            if mode == "Sub-item":
                conn = sqlite3.connect('finance_final.db')
                all_c = pd.read_sql("SELECT name FROM categories", conn)['name'].tolist()
                target_c = st.selectbox("Parent Category", all_c)
                conn.close()
            
            if st.button("Save New Item"):
                conn = sqlite3.connect('finance_final.db')
                if mode == "Main Category":
                    try:
                        conn.execute("INSERT INTO categories (name) VALUES (?)", (name_input,))
                        conn.commit()
                        st.success(f"Category '{name_input}' added!")
                        st.rerun()
                    except: st.error("Already exists.")
                else:
                    c = conn.cursor()
                    c.execute("SELECT id FROM categories WHERE name = ?", (target_c,))
                    conn.execute("INSERT INTO subcategories (cat_id, name) VALUES (?, ?)", (c.fetchone()[0], name_input))
                    conn.commit()
                    st.success(f"Added {name_input} to {target_c}")
                    st.rerun()
                conn.close()

        with col_del:
            st.subheader("🗑️ Delete Items")
            conn = sqlite3.connect('finance_final.db')
            cats = pd.read_sql("SELECT name FROM categories", conn)['name'].tolist()
            if cats:
                v_cat = st.selectbox("View Items In", cats)
                c = conn.cursor()
                c.execute("SELECT name FROM subcategories WHERE cat_id = (SELECT id FROM categories WHERE name = ?)", (v_cat,))
                subs = [r[0] for r in c.fetchall()]
                to_del = st.selectbox("Select to Remove", ["-- Select --"] + subs)
                if to_del != "-- Select --":
                    if st.button("Confirm Delete"):
                        conn.execute("DELETE FROM subcategories WHERE name = ? AND cat_id = (SELECT id FROM categories WHERE name = ?)", (to_del, v_cat))
                        conn.commit()
                        st.success("Deleted.")
                        st.rerun()
            conn.close()

    # --- DASHBOARD ---
    else:
        st.header("📊 Financial Dashboard")
        conn = sqlite3.connect('finance_final.db')
        df = pd.read_sql("SELECT * FROM transactions", conn)
        conn.close()
        if not df.empty:
            df
