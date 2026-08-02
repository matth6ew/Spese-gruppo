from collections import defaultdict
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st

st.set_page_config(
    page_title="Spese di Gruppo", page_icon="💰", layout="centered"
)

# --- CONFIGURAZIONE PARTECIPANTI FISSI ---
MEMBERS = [
    "Serena",
    "Matteo",
    "Donghui",
    "Kevin",
    "Samantha",
    "Nixia",
    "Alessia",
    "Lorenzo",
    "Giulia",
    "Johnny",
]

SHEET_NAME = "SpeseGruppo"


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
sheet = client.open(SHEET_NAME).sheet1


def load_expenses():
    """Carica le spese dal Google Sheet proponendo fallback se vuoto."""
    try:
        records = sheet.get_all_records()
        expenses = []
        for idx, row in enumerate(records, start=2):  # start=2 per tracciare la riga reale (1-indexed + header)
            # Gestione sicura nel caso 'Partecipanti' non sia popolato correttamente
            raw_participants = str(row.get("Partecipanti", ""))
            participants = (
                [p.strip() for p in raw_participants.split(",") if p.strip()]
                if raw_participants
                else []
            )

            expenses.append(
                {
                    "row_idx": idx,
                    "payer": row.get("Chi ha pagato", "Sconosciuto"),
                    "description": row.get("Cosa", "Spesa Generica"),
                    "amount": float(row.get("Importo", 0.0)),
                    "participants": participants,
                }
            )
        return expenses
    except Exception:
        # Se il foglio è vuoto o corrotto, reinizializza le intestazioni
        sheet.clear()
        sheet.append_row(["Chi ha pagato", "Cosa", "Importo", "Partecipanti"])
        return []


def save_expense_to_sheet(payer, description, amount, participants):
    """Aggiunge una riga nel Google Sheet."""
    participants_str = ", ".join(participants)
    sheet.append_row([payer, description, amount, participants_str])


def delete_single_expense(row_idx):
    """Elimina una riga specifica dal Google Sheet."""
    sheet.delete_rows(row_idx)


# --- Gestione Autenticazione ---
st.sidebar.title("🔒 Autenticazione")
password = st.sidebar.text_input("Inserisci Password Admin", type="password")

# Consiglio: definisci 'admin_password' nei tuoi secrets (`.streamlit/secrets.toml`)
admin_password = st.secrets.get("admin_password", "zono") 
is_admin = password == admin_password

if is_admin:
    st.sidebar.success("Modalità Modifica Attiva 🔓")
else:
    st.sidebar.info("Modalità Sola Lettura 👁️")

# --- Interfaccia Principale ---
st.title("💰 Spese di Gruppo")

expenses = load_expenses()

# --- MODULO AGGIUNTA (Solo Admin) ---
if is_admin:
    with st.form("expense_form", clear_on_submit=True):
        st.subheader("➕ Aggiungi spesa")

        payer = st.selectbox("Chi ha pagato?", options=MEMBERS)
        description = st.text_input("Cosa ha pagato? (es. Cena, Benzina)")
        amount = st.number_input(
            "Importo (€)", min_value=0.01, step=0.50, format="%.2f"
        )
        selected_participants = st.multiselect(
            "Per chi? (rimuovi chi non partecipa alla spesa)",
            options=MEMBERS,
            default=MEMBERS,
        )

        if st.form_submit_button("Aggiungi"):
            if payer and description.strip() and amount > 0 and selected_participants:
                save_expense_to_sheet(
                    payer, description.strip(), amount, selected_participants
                )
                st.success("Spesa salvata su Google Sheets!")
                st.rerun()
            else:
                st.error("Compila tutti i campi e seleziona almeno un partecipante.")
else:
    st.info(
        "🔑 Inserisci la password nella barra laterale per aggiungere o gestire le spese."
    )

# --- VISUALIZZAZIONE E CONGUAGLI ---
if expenses:
    st.subheader(f"📋 Spese salvate ({len(expenses)})")
    
    for exp in expenses:
        col_txt, col_act = st.columns([5, 1])
        with col_txt:
            st.write(
                f"• **{exp['payer']}** ha pagato **{exp['amount']:.2f} €** per *{exp['description']}* (per {', '.join(exp['participants'])})"
            )
        with col_act:
            if is_admin:
                if st.button("❌", key=f"del_{exp['row_idx']}", help="Elimina questa spesa"):
                    delete_single_expense(exp["row_idx"])
                    st.rerun()

    # Opzioni di Cancellazione Totale (Solo Admin)
    if is_admin:
        st.write("---")

        if "confirm_delete" not in st.session_state:
            st.session_state.confirm_delete = False

        if not st.session_state.confirm_delete:
            if st.button("🗑️ Svuota tutto"):
                st.session_state.confirm_delete = True
                st.rerun()

        if st.session_state.confirm_delete:
            st.warning("⚠️ Sei sicuro di voler cancellare TUTTE le spese salvate?")
            col_conf1, col_conf2 = st.columns([1, 1])

            with col_conf1:
                if st.button("🔴 Sì, cancella tutto", type="primary"):
                    sheet.clear()
                    sheet.append_row(["Chi ha pagato", "Cosa", "Importo", "Partecipanti"])
                    st.session_state.confirm_delete = False
                    st.success("Tutte le spese sono state cancellate!")
                    st.rerun()

            with col_conf2:
                if st.button("Annulla"):
                    st.session_state.confirm_delete = False
                    st.rerun()

    # --- CALCOLO CONGUAGLI ---
    balances = defaultdict(float)
    for exp in expenses:
        if exp["participants"]:
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
else:
    st.write(" Nessuna spesa ancora registrata.")
    
