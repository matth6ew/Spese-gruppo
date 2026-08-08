from collections import defaultdict
from datetime import date, datetime

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials


# ============================================================
# CONFIGURAZIONE PAGINA
# ============================================================

st.set_page_config(
    page_title="Spese di Gruppo",
    page_icon="💰",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# ============================================================
# CONFIGURAZIONE APP
# ============================================================

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

HEADERS = [
    "Data",
    "Chi ha pagato",
    "Cosa",
    "Importo",
    "Partecipanti",
]


# ============================================================
# CSS UI/UX AGGIORNATO
# ============================================================

st.markdown(
    """
    <style>
    .block-container {
        max-width: 1000px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    .app-subtitle {
        opacity: 0.65;
        margin-top: -0.5rem;
        margin-bottom: 1.5rem;
        font-size: 1.05rem;
    }

    .section-space {
        height: 1rem;
    }

    .settlement-card {
        padding: 1.2rem;
        border-radius: 12px;
        border: 1px solid rgba(150, 150, 150, 0.2);
        margin-bottom: 0.8rem;
    }

    .settlement-amount {
        font-size: 1.35rem;
        font-weight: 800;
        text-align: center;
        margin-top: 0.8rem;
    }

    .debtor {
        color: #ff4b4b;
        font-weight: 700;
    }

    .creditor {
        color: #09ab3b;
        font-weight: 700;
    }

    .arrow {
        text-align: center;
        font-size: 1.4rem;
        opacity: 0.5;
        padding-top: 0.5rem;
    }

    @media (max-width: 700px) {
        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
            padding-top: 1rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# UTILITY
# ============================================================

def euro(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = 0.0

    return (
        f"{value:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
        + " €"
    )


def parse_amount(value):
    if value is None or value == "":
        return 0.0

    if isinstance(value, (int, float)):
        return float(value)

    value = str(value).strip().replace("€", "").replace(" ", "")

    if "," in value:
        value = value.replace(".", "").replace(",", ".")

    try:
        return float(value)
    except ValueError:
        return 0.0


def parse_date(value):
    if not value:
        return None

    if isinstance(value, date):
        return value

    value = str(value).strip()
    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass

    return None


def format_date(value):
    parsed = parse_date(value)
    return parsed.strftime("%d/%m/%Y") if parsed else "—"


# ============================================================
# GOOGLE SHEETS
# ============================================================

@st.cache_resource
def init_connection():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scope,
    )
    return gspread.authorize(credentials)


client = init_connection()
sheet = client.open(SHEET_NAME).sheet1


def initialize_sheet():
    values = sheet.get_all_values()
    if not values:
        sheet.append_row(HEADERS)
        return

    current_headers = values[0]
    old_headers = ["Chi ha pagato", "Cosa", "Importo", "Partecipanti"]

    if current_headers == old_headers:
        migrated_rows = [
            [date.today().strftime("%Y-%m-%d"), row[0], row[1], row[2], row[3]]
            for row in values[1:]
        ]
        sheet.clear()
        sheet.append_row(HEADERS)
        if migrated_rows:
            sheet.append_rows(migrated_rows)


initialize_sheet()


# ============================================================
# LETTURA E SCRITTURA DATI
# ============================================================

@st.cache_data(ttl=10)
def load_expenses():
    try:
        records = sheet.get_all_records()
        expenses = []
        for row_idx, row in enumerate(records, start=2):
            raw_participants = str(row.get("Partecipanti", ""))
            participants = [p.strip() for p in raw_participants.split(",") if p.strip()]
            expenses.append(
                {
                    "row_idx": row_idx,
                    "date": parse_date(row.get("Data", "")),
                    "payer": str(row.get("Chi ha pagato", "Sconosciuto")).strip(),
                    "description": str(row.get("Cosa", "Spesa generica")).strip(),
                    "amount": parse_amount(row.get("Importo", 0)),
                    "participants": participants,
                }
            )
        return expenses
    except Exception as error:
        st.error(f"Errore durante la lettura del Google Sheet: {error}")
        return []


def save_expense(expense_date, payer, description, amount, participants):
    sheet.append_row(
        [
            expense_date.strftime("%Y-%m-%d"),
            payer,
            description,
            float(amount),
            ", ".join(participants),
        ]
    )
    st.cache_data.clear()


def delete_expense(row_idx):
    sheet.delete_rows(row_idx)
    st.cache_data.clear()


def delete_all_expenses():
    sheet.clear()
    sheet.append_row(HEADERS)
    st.cache_data.clear()


# ============================================================
# CALCOLI FINANZIARI
# ============================================================

def calculate_balances(expenses):
    balances = defaultdict(float, {m: 0.0 for m in MEMBERS})
    for expense in expenses:
        payer, amount, participants = expense["payer"], expense["amount"], expense["participants"]
        if not participants:
            continue
        share = amount / len(participants)
        balances[payer] += amount
        for participant in participants:
            balances[participant] -= share
    return balances


def calculate_settlements(expenses):
    balances = calculate_balances(expenses)
    debtors = [[p, -b] for p, b in balances.items() if b < -0.009]
    creditors = [[p, b] for p, b in balances.items() if b > 0.009]

    debtors.sort(key=lambda x: x[1], reverse=True)
    creditors.sort(key=lambda x: x[1], reverse=True)

    settlements = []
    d_idx, c_idx = 0, 0

    while d_idx < len(debtors) and c_idx < len(creditors):
        debtor, creditor = debtors[d_idx], creditors[c_idx]
        amount = round(min(debtor[1], creditor[1]), 2)

        if amount > 0:
            settlements.append({"from": debtor[0], "to": creditor[0], "amount": amount})

        debtor[1] -= amount
        creditor[1] -= amount

        if debtor[1] < 0.009:
            d_idx += 1
        if creditor[1] < 0.009:
            c_idx += 1

    return settlements, balances


def calculate_personal_shares(expenses):
    shares = defaultdict(float, {m: 0.0 for m in MEMBERS})
    for expense in expenses:
        participants, amount = expense["participants"], expense["amount"]
        if participants:
            share = amount / len(participants)
            for p in participants:
                shares[p] += share
    return shares


def calculate_payer_totals(expenses):
    totals = defaultdict(float, {m: 0.0 for m in MEMBERS})
    for expense in expenses:
        totals[expense["payer"]] += expense["amount"]
    return totals


# ============================================================
# SESSION STATE
# ============================================================

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False


# ============================================================
# DIALOGS
# ============================================================

@st.dialog("Elimina spesa")
def delete_dialog(expense):
    st.markdown(f"### {expense['description']}")
    st.caption(f"{expense['payer']} · {format_date(expense['date'])}")
    st.metric("Importo", euro(expense["amount"]))
    st.warning("Questa operazione non può essere annullata.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Elimina", type="primary", use_container_width=True):
            try:
                delete_expense(expense["row_idx"])
                st.rerun()
            except Exception as e:
                st.error(f"Errore: {e}")
    with col2:
        if st.button("Annulla", use_container_width=True):
            st.rerun()


@st.dialog("⚠️ Svuota tutte le spese")
def clear_all_dialog(expense_count, total_amount):
    st.error("Stai per eliminare tutte le spese registrate.")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Spese", expense_count)
    with col2:
        st.metric("Totale", euro(total_amount))
    
    st.warning("Questa operazione non può essere annullata.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Cancella tutto", type="primary", use_container_width=True):
            try:
                delete_all_expenses()
                st.rerun()
            except Exception as e:
                st.error(f"Errore: {e}")
    with col2:
        if st.button("Annulla", use_container_width=True):
            st.rerun()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.header("⚙️ Impostazioni")
    st.divider()
    st.subheader("🔐 Amministratore")

    if st.session_state.is_admin:
        st.success("Modalità admin attiva")
        if st.button("Esci dalla modalità admin", use_container_width=True):
            st.session_state.is_admin = False
            st.rerun()
    else:
        password = st.text_input("Password admin", type="password", placeholder="Inserisci password")
        admin_password = st.secrets.get("admin_password", "zono")

        if password:
            if password == admin_password:
                st.session_state.is_admin = True
                st.rerun()
            else:
                st.error("Password non corretta.")

    st.divider()
    st.caption("🔓 Puoi gestire le spese." if st.session_state.is_admin else "👁️ Modalità sola lettura.")


# ============================================================
# HEADER PRINCIPALE
# ============================================================

st.title("💰 Spese di Gruppo")
st.markdown(
    '<div class="app-subtitle">Gestisci le spese condivise e scopri automaticamente come pareggiare i conti in modo equo.</div>',
    unsafe_allow_html=True,
)


# ============================================================
# CARICAMENTO DATI
# ============================================================

expenses = load_expenses()
total_amount = sum(e["amount"] for e in expenses)
expense_count = len(expenses)
settlements, balances = calculate_settlements(expenses)
personal_shares = calculate_personal_shares(expenses)
payer_totals = calculate_payer_totals(expenses)


# ============================================================
# TABS PRINCIPALI
# ============================================================

tab_dashboard, tab_expenses, tab_new = st.tabs(["📊 Riepilogo", "🧾 Spese", "➕ Nuova spesa"])


# ============================================================
# TAB 1 — RIEPILOGO
# ============================================================

with tab_dashboard:
    col1, col2, col3 = st.columns(3)
    with col1:
        with st.container(border=True):
            st.metric("Totale speso", euro(total_amount))
            st.caption("Tutte le spese registrate")
    with col2:
        with st.container(border=True):
            st.metric("Spese", expense_count)
            st.caption("Transazioni totali")
    with col3:
        with st.container(border=True):
            st.metric("Da saldare", len(settlements))
            st.caption("Bonifici necessari")

    st.markdown('<div class="section-space"></div>', unsafe_allow_html=True)

    if not expenses:
        st.info("💸 Non ci sono ancora spese. Aggiungi la prima dalla scheda «Nuova spesa».")
    else:
        st.header("💸 Da saldare")
        st.caption("I trasferimenti minimi necessari per azzerare i debiti.")

        if not settlements:
            st.success("🎉 Tutti i conti sono perfettamente in pari!")
        else:
            for s in settlements:
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2, 0.6, 2])
                    with c1:
                        st.caption("DEVE PAGARE")
                        st.markdown(f'<div class="debtor">🔴 {s["from"]}</div>', unsafe_allow_html=True)
                    with c2:
                        st.markdown('<div class="arrow">→</div>', unsafe_allow_html=True)
                    with c3:
                        st.caption("RICEVE")
                        st.markdown(f'<div class="creditor">🟢 {s["to"]}</div>', unsafe_allow_html=True)
                    
                    st.markdown(f'<div class="settlement-amount">{euro(s["amount"])}</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-space"></div>', unsafe_allow_html=True)
        st.header("👥 Situazione Personale")
        st.caption("Anticipi effettuati vs quote di spesa effettive.")

        active_members = [m for m in MEMBERS if abs(balances[m]) > 0.009 or payer_totals[m] > 0 or personal_shares[m] > 0]

        if not active_members:
            st.info("Nessuna situazione da mostrare.")
        else:
            for person in active_members:
                balance = balances[person]
                if balance > 0.009:
                    status, status_val = "🟢 Riceve", f"+{euro(balance)}"
                elif balance < -0.009:
                    status, status_val = "🔴 Deve", euro(balance)
                else:
                    status, status_val = "⚪ In pari", "0,00 €"

                with st.container(border=True):
                    c1, c2, c3 = st.columns([1.5, 1.5, 1])
                    with c1:
                        st.markdown(f"### {person}")
                    with c2:
                        st.caption(f"Pagato: {euro(payer_totals[person])}")
                        st.caption(f"Quota: {euro(personal_shares[person])}")
                    with c3:
                        st.caption(status)
                        st.markdown(f"**{status_val}**")


# ============================================================
# TAB 2 — ELENCO SPESE
# ============================================================

with tab_expenses:
    st.header("🧾 Elenco Spese")

    if not expenses:
        st.info("Non ci sono ancora spese registrate.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            payer_filter = st.selectbox("Filtra per pagatore", ["Tutti"] + MEMBERS)
        with col2:
            sort_order = st.selectbox("Ordina per", ["Più recenti", "Più vecchie", "Importo maggiore", "Importo minore"])

        filtered = expenses.copy()
        if payer_filter != "Tutti":
            filtered = [e for e in filtered if e["payer"] == payer_filter]

        if sort_order == "Più recenti":
            filtered.sort(key=lambda x: x["date"] or date.min, reverse=True)
        elif sort_order == "Più vecchie":
            filtered.sort(key=lambda x: x["date"] or date.min)
        elif sort_order == "Importo maggiore":
            filtered.sort(key=lambda x: x["amount"], reverse=True)
        elif sort_order == "Importo minore":
            filtered.sort(key=lambda x: x["amount"])

        st.caption(f"Visualizzazione di {len(filtered)} spese")

        for expense in filtered:
            with st.container(border=True):
                c1, c2, c3 = st.columns([4, 1.3, 0.6])
                with c1:
                    st.markdown(f"**{expense['description']}**")
                    st.caption(f"👤 {expense['payer']} · 📅 {format_date(expense['date'])}")
                    st.caption(f"👥 {', '.join(expense['participants'])}")
                with c2:
                    st.markdown(f"**{euro(expense['amount'])}**")
                with c3:
                    if st.session_state.is_admin:
                        if st.button("🗑️", key=f"del_{expense['row_idx']}", help="Elimina spesa"):
                            delete_dialog(expense)

        filtered_total = sum(e["amount"] for e in filtered)
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Spese filtrate", len(filtered))
        with c2:
            st.metric("Totale filtrato", euro(filtered_total))

        if st.session_state.is_admin:
            st.divider()
            with st.expander("⚠️ Gestione dati avanzata"):
                if st.button("🗑️ Svuota tutte le spese", use_container_width=True):
                    clear_all_dialog(expense_count, total_amount)


# ============================================================
# TAB 3 — NUOVA SPESA
# ============================================================

with tab_new:
    if not st.session_state.is_admin:
        st.header("🔐 Nuova spesa")
        st.info("Accedi come amministratore dalla sidebar per poter aggiungere una spesa.")
    else:
        st.header("➕ Nuova spesa")
        st.caption("Inserisci i dettagli della spesa da condividere.")

        with st.form("new_expense_form", clear_on_submit=True):
            expense_date = st.date_input("📅 Data", value=date.today())
            payer = st.selectbox("👤 Chi ha pagato?", MEMBERS)
            description = st.text_input("📝 Descrizione", placeholder="Cena, benzina, spesa...")
            amount = st.number_input("💶 Importo", min_value=0.01, value=10.00, step=0.50, format="%.2f")

            st.divider()
            st.subheader("👥 Partecipanti")
            
            selection_mode = st.radio(
                "Modalità",
                ["Tutti", "Seleziona manualmente"],
                horizontal=True,
                label_visibility="collapsed",
            )

            if selection_mode == "Tutti":
                selected_participants = MEMBERS.copy()
            else:
                selected_participants = st.multiselect(
                    "Seleziona le persone coinvolte",
                    MEMBERS,
                    default=MEMBERS,
                )

            if selected_participants:
                per_person = amount / len(selected_participants)
                st.info(f"💡 Circa **{euro(per_person)}** a testa per {len(selected_participants)} partecipanti.")
            else:
                st.warning("⚠️ Seleziona almeno un partecipante.")

            submitted = st.form_submit_button("💾 Salva spesa", type="primary", use_container_width=True)

        if submitted:
            if not description.strip():
                st.error("Inserisci una descrizione valida.")
            elif amount <= 0:
                st.error("L'importo deve essere maggiore di zero.")
            elif not selected_participants:
                st.error("Seleziona almeno un partecipante.")
            else:
                try:
                    save_expense(
                        expense_date=expense_date,
                        payer=payer,
                        description=description.strip(),
                        amount=amount,
                        participants=selected_participants,
                    )
                    st.success("Spesa salvata con successo! 🎉")
                    st.rerun()
                except Exception as error:
                    st.error(f"Errore durante il salvataggio: {error}")
