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
    """Carica le spese dal Google Sheet gestendo in sicurezza i fallback."""
    try:
        all_values = sheet.get_all_values()
        if not all_values:
            sheet.append_row(["Chi ha pagato", "Cosa", "Importo", "Partecipanti"])
            return []

        records = sheet.get_all_records()
        expenses = []
        for idx, row in enumerate(records, start=2):
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
    except Exception as e:
        st.error(f"Errore di lettura da Google Sheets: {e}")
        return []


def save_expense_to_sheet(payer, description, amount, participants):
    """Aggiunge una riga nel Google Sheet."""
    participants_str = ", ".join(participants)
    sheet.append_row([payer, description, amount, participants_str])


def delete_single_expense(row_idx):
    """Elimina una riga specifica dal Google Sheet."""
    sheet.delete_rows(row_idx)


# --- Dialogo Modale per Conferma Cancellazione Singola ---
@st.dialog("Conferma eliminazione")
def confirm_delete_dialog(row_idx, description):
    st.write(f"Sei sicuro di voler eliminare la spesa: *{description}*?")
    col_yes, col_no = st.columns(2)
    with col_yes:
        if st.button("Sì, elimina", type="primary", use_container_width=True):
            delete_single_expense(row_idx)
            st.success("Spesa eliminata!")
            st.rerun()
    with col_no:
        if st.button("Annulla", use_container_width=True):
            st.rerun()


# --- Dialogo Modale per Svuotare Tutto ---
@st.dialog("⚠️ Svuota tutte le spese")
def confirm_clear_all_dialog():
    st.warning("Questa azione eliminerà DEFINITIVAMENTE tutte le spese registrate.")
    col_yes, col_no = st.columns(2)
    with col_yes:
        if st.button("Sì, cancella tutto", type="primary", use_container_width=True):
            sheet.clear()
            sheet.append_row(["Chi ha pagato", "Cosa", "Importo", "Partecipanti"])
            st.success("Tutte le spese sono state cancellate!")
            st.rerun()
    with col_no:
        if st.button("Annulla", use_container_width=True):
            st.rerun()


# --- Gestione Autenticazione ---
st.sidebar.title("🔒 Autenticazione")
password = st.sidebar.text_input("Inserisci Password Admin", type="password")

admin_password = st.secrets.get("admin_password", "zono")
is_admin = password == admin_password

if is_admin:
    st.sidebar.success("Modalità Modifica Attiva 🔓")
else:
    st.sidebar.info("Modalità Sola Lettura 👁️")

# --- Interfaccia Principale ---
st.title("💰 Spese di Gruppo")

expenses = load_expenses()

# Creazione delle schede (Tabs) per unire ordine visivo e UX moderna
tab_dash, tab_list, tab_add = st.tabs(
    ["📊 Dashboard & Conguagli", "📋 Elenco Spese", "➕ Aggiungi Spesa"]
)

with tab_dash:
    if expenses:
        # 1. --- CALCOLO E VISUALIZZAZIONE CONGUAGLI ---
        balances = defaultdict(float)

        for exp in expenses:
            participants = exp["participants"]
            amount = exp["amount"]
            payer = exp["payer"]

            if participants:
                split_amount = amount / len(participants)
                balances[payer] += amount
                for p in participants:
                    balances[p] -= split_amount

        debtors = [[p, -b] for p, b in balances.items() if b < -0.009]
        creditors = [[p, b] for p, b in balances.items() if b > 0.009]
        debtors.sort(key=lambda x: x[1], reverse=True)
        creditors.sort(key=lambda x: x[1], reverse=True)

        st.subheader("💸 Conguagli consigliati")

        if not debtors and not creditors:
            st.success("Tutti i conti sono perfettamente in pari! 🎉")
        else:
            i, j = 0, 0
            while i < len(debtors) and j < len(creditors):
                settled = min(debtors[i][1], creditors[j][1])
                settled_rounded = round(settled, 2)

                if settled_rounded > 0:
                    st.info(
                        f"**{debtors[i][0]}** deve dare **{settled_rounded:.2f} €** a **{creditors[j][0]}**"
                    )

                debtors[i][1] -= settled
                creditors[j][1] -= settled

                if debtors[i][1] < 0.009:
                    i += 1
                if j < len(creditors) and creditors[j][1] < 0.009:
                    j += 1

        st.write("---")

        # 2. --- QUOTA EFFETTIVA CONSUMATA PER PERSONA ---
        st.subheader("🛒 Quota effettiva di spesa per persona")
        personal_shares = defaultdict(float)

        for exp in expenses:
            participants = exp["participants"]
            amount = exp["amount"]
            if participants:
                split_amount = amount / len(participants)
                for p in participants:
                    personal_shares[p] += split_amount

        if personal_shares:
            sorted_shares = sorted(personal_shares.items(), key=lambda x: x[1], reverse=True)
            cols = st.columns(2)
            for idx, (person, share) in enumerate(sorted_shares):
                with cols[idx % 2]:
                    st.metric(label=person, value=f"{share:.2f} €")

        st.write("---")

        # 3. --- RIEPILOGO PER PERSONA ---
        st.subheader("📊 Totale anticipato per persona")
        payer_summary = defaultdict(list)
        payer_totals = defaultdict(float)

        for exp in expenses:
            payer = exp["payer"]
            payer_summary[payer].append(exp)
            payer_totals[payer] += exp["amount"]

        for payer, total in sorted(payer_totals.items(), key=lambda x: x[1], reverse=True):
            with st.expander(f"👤 **{payer}** ha anticipato un totale di **{total:.2f} €**"):
                for exp in payer_summary[payer]:
                    participants_list = ", ".join(exp['participants'])
                    st.write(f"- **{exp['amount']:.2f} €** per *{exp['description']}* (per {participants_list})")
    else:
        st.info("Nessuna spesa ancora registrata.")

with tab_list:
    if expenses:
        st.subheader(f"📋 Elenco di tutte le spese ({len(expenses)})")

        for exp in expenses:
            col_txt, col_act = st.columns([5, 1])
            with col_txt:
                st.write(
                    f"• **{exp['payer']}** ha pagato **{exp['amount']:.2f} €** per *{exp['description']}* (per {', '.join(exp['participants'])})"
                )
            with col_act:
                if is_admin:
                    if st.button("❌", key=f"del_{exp['row_idx']}", help="Elimina spesa"):
                        confirm_delete_dialog(exp["row_idx"], exp["description"])

        if is_admin:
            st.write("---")
            if st.button("🗑️ Svuota tutto", use_container_width=True):
                confirm_clear_all_dialog()
    else:
        st.info("Nessuna spesa da mostrare.")

with tab_add:
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

            if st.form_submit_button("Aggiungi spesa", use_container_width=True):
                if payer and description.strip() and amount > 0 and selected_participants:
                    save_expense_to_sheet(
                        payer, description.strip(), amount, selected_participants
                    )
                    st.success("Spesa salvata su Google Sheets!")
                    st.rerun()
                else:
                    st.error("Compila tutti i campi e seleziona almeno un partecipante.")
    else:
        st.info("🔑 Inserisci la password nella barra laterale per aggiungere o gestire le spese.")
