from collections import defaultdict
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st

st.set_page_config(
    page_title="Spese di Gruppo", page_icon="💰", layout="centered"
)


# --- Connessione a Google Sheets ---
@st.cache_resource
def init_connection():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scope
    )
    client = gspread.authorize(creds)
    return client


client = init_connection()

# SOSTITUISCI CON IL NOME ESATTO DEL TUO FOGLIO GOOGLE
SHEET_NAME = "SpeseGruppo"
sheet = client.open(SHEET_NAME).sheet1


def load_expenses():
    """Carica le spese dal Google Sheet."""
    try:
        records = sheet.get_all_records()
        expenses = []
        for row in records:
            participants = [
                p.strip() for p in str(row["Partecipanti"]).split(",")
            ]
            expenses.append(
                {
                    "payer": row["Chi ha pagato"],
                    "amount": float(row["Importo"]),
                    "participants": participants,
                }
            )
        return expenses
    except Exception:
        # Se il foglio è vuoto, inizializza le intestazioni
        sheet.append_row(["Chi ha pagato", "Importo", "Partecipanti"])
        return []


def save_expense_to_sheet(payer, amount, participants):
    """Aggiunge una riga nel Google Sheet."""
    participants_str = ", ".join(participants)
    sheet.append_row([payer, amount, participants_str])


# --- Gestione Password ---
st.sidebar.title("🔒 Autenticazione")
password = st.sidebar.text_input("Inserisci Password Admin", type="password")
is_admin = password == "zonozonozono"

if is_admin:
    st.sidebar.success("Modalità Modifica Attiva 🔓")
else:
    st.sidebar.info("Modalità Sola Lettura 👁️")

# --- Interfaccia Principale ---
st.title("💰 Spese di Gruppo")

# Carichiamo i dati dal foglio
expenses = load_expenses()

# --- MODULO AGGIUNTA (Solo se la password è corretta) ---
if is_admin:
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
                save_expense_to_sheet(payer.strip(), amount, parts)
                st.success("Spesa salvata su Google Sheets!")
                st.rerun()
            else:
                st.error("Compila tutti i campi.")
else:
    st.warning(
        "🔑 Inserisci la password nella barra laterale a sinistra per aggiungere o cancellare le spese."
    )

# --- VISUALIZZAZIONE E CONGUAGLI (Visibili a tutti) ---
if expenses:
    st.subheader(f"📋 Spese salvate ({len(expenses)})")
    for exp in expenses:
        st.write(
            f"• **{exp['payer']}**: {exp['amount']:.2f} € per *{', '.join(exp['participants'])}*"
        )

    # Il pulsante di svuotamento appare solo agli Admin
    if is_admin:
        st.write("---")
        if st.button("🗑️ Svuota tutto"):
            sheet.clear()
            sheet.append_row(["Chi ha pagato", "Importo", "Partecipanti"])
            st.rerun()

    # Calcolo Conguagli
    balances = defaultdict(float)
    for exp in expenses:
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
