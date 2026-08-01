import json
import os
from collections import defaultdict
import streamlit as st

DB_FILE = "spese_gruppo.json"

st.set_page_config(
    page_title="Spese di Gruppo", page_icon="💰", layout="centered"
)


def load_expenses():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_expenses(expenses):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(expenses, f, ensure_ascii=False, indent=4)


if "expenses" not in st.session_state:
    st.session_state.expenses = load_expenses()

st.title("💰 Spese di Gruppo")

# Form di inserimento
with st.form("expense_form", clear_on_submit=True):
    st.subheader("➕ Aggiungi spesa")
    payer = st.text_input("Chi ha pagato?")
    amount = st.number_input(
        "Importo (€)", min_value=0.01, step=0.50, format="%.2f"
    )
    participants_raw = st.text_input("Per chi? (nomi separati da virgola)")

    if st.form_submit_button("Aggiungi"):
        if payer and amount > 0 and participants_raw:
            parts = [
                p.strip() for p in participants_raw.split(",") if p.strip()
            ]
            st.session_state.expenses.append(
                {"payer": payer.strip(), "amount": amount, "participants": parts}
            )
            save_expenses(st.session_state.expenses)
            st.success("Spesa salvata!")
            st.rerun()
        else:
            st.error("Compila tutti i campi.")

# Visualizzazione e Conguagli
if st.session_state.expenses:
    st.subheader(f"📋 Spese salvate ({len(st.session_state.expenses)})")
    for exp in st.session_state.expenses:
        st.write(
            f"• **{exp['payer']}**: {exp['amount']:.2f} € per *{', '.join(exp['participants'])}*"
        )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Svuota tutto"):
            st.session_state.expenses = []
            if os.path.exists(DB_FILE):
                os.remove(DB_FILE)
            st.rerun()

    balances = defaultdict(float)
    for exp in st.session_state.expenses:
        split_amount = exp["amount"] / len(exp["participants"])
        balances[exp["payer"]] += exp["amount"]
        for p in exp["participants"]:
            balances[p] -= split_amount

    debtors = [[p, -b] for p, b in balances.items() if b < -0.01]
    creditors = [[p, b] for p, b in balances.items() if b > 0.01]

    st.subheader("💸 Conguagli")
    i, j = 0, 0
    while i < len(debtors) and j < len(creditors):
        settled = min(debtors[i][1], creditors[j][1])
        st.info(
            f"**{debtors[i][0]}** deve dare **{settled:.2f} €** a **{creditors[j][0]}**"
        )
        debtors[i][1] -= settled
        creditors[j][1] -= settled
        if debtors[i][1] < 0.01:
            i += 1
        if creditors[j][1] < 0.01:
            j += 1