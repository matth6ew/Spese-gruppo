from collections import defaultdict
from datetime import date, datetime
from html import escape

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
# CSS RESPONSIVE AVANZATO (MOBILE & DESKTOP)
# ============================================================

st.markdown(
    """
    <style>
    .block-container {
        max-width: 1120px;
        padding-top: 2.2rem;
        padding-bottom: 5rem;
        padding-left: 1.2rem;
        padding-right: 1.2rem;
    }

    [data-testid="stHeader"] {
        background: transparent;
    }

    .app-hero {
        margin: 0 0 2rem;
    }

    .app-hero-kicker {
        display: inline-flex;
        align-items: center;
        gap: .45rem;
        padding: .38rem .72rem;
        border: 1px solid rgba(255,255,255,.10);
        border-radius: 999px;
        background: rgba(255,255,255,.035);
        color: #a7adb7;
        font-size: .78rem;
        font-weight: 700;
        letter-spacing: .03em;
        text-transform: uppercase;
    }

    .app-hero h1 {
        margin: .75rem 0 .35rem;
        font-size: clamp(2rem, 4vw, 2.9rem);
        line-height: 1.05;
        letter-spacing: -.045em;
        color: #f4f5f7;
    }

    .app-hero p {
        margin: 0;
        max-width: 680px;
        color: #8f96a1;
        font-size: 1rem;
        line-height: 1.55;
    }

    .summary-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: .9rem;
        margin-bottom: 2rem;
    }

    .summary-card {
        min-height: 112px;
        padding: 1.15rem 1.2rem;
        border: 1px solid rgba(255,255,255,.09);
        border-radius: 18px;
        background: linear-gradient(145deg, rgba(255,255,255,.055), rgba(255,255,255,.018));
        box-shadow: 0 10px 30px rgba(0,0,0,.12);
    }

    .summary-label {
        color: #8e95a0;
        font-size: .78rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: .055em;
    }

    .summary-value {
        margin-top: .35rem;
        color: #f3f4f6;
        font-size: 1.65rem;
        line-height: 1.15;
        font-weight: 800;
        letter-spacing: -.03em;
    }

    .summary-help {
        margin-top: .28rem;
        color: #6f7783;
        font-size: .78rem;
    }

    .section-heading {
        margin: 2.1rem 0 .95rem;
    }

    .section-heading h2 {
        margin: 0;
        color: #f1f2f4;
        font-size: 1.35rem;
        letter-spacing: -.025em;
    }

    .section-heading p {
        margin: .25rem 0 0;
        color: #7f8793;
        font-size: .9rem;
    }

    /* Stili moderni per le card di trasferimento */
    .settlement-list {
        display: grid;
        gap: .8rem;
    }

    .settlement-card {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 1.15rem 1.25rem;
        border: 1px solid rgba(255,255,255,.085);
        border-radius: 16px;
        background: rgba(255,255,255,.025);
        gap: 1rem;
    }

    .settlement-info {
        display: flex;
        align-items: center;
        gap: 1.2rem;
        flex-wrap: wrap;
    }

    .settlement-person-block {
        display: flex;
        flex-direction: column;
    }

    .settlement-label {
        margin-bottom: .2rem;
        color: #737b87;
        font-size: .67rem;
        font-weight: 800;
        letter-spacing: .075em;
        text-transform: uppercase;
    }

    .person-name {
        color: #f1f3f5;
        font-size: 1rem;
        font-weight: 750;
    }

    .person-name.debtor::before,
    .person-name.creditor::before {
        content: "";
        display: inline-block;
        width: .55rem;
        height: .55rem;
        margin-right: .45rem;
        border-radius: 50%;
        vertical-align: middle;
    }

    .person-name.debtor::before {
        background: #ff4b4b;
        box-shadow: 0 0 0 3px rgba(255,75,75,.12);
    }

    .person-name.creditor::before {
        background: #7bc043;
        box-shadow: 0 0 0 3px rgba(123,192,67,.12);
    }

    .settlement-arrow {
        color: #6f7783;
        font-size: 1.1rem;
        font-weight: bold;
    }

    .settlement-amount {
        color: #f7f8fa;
        font-size: 1.25rem;
        font-weight: 850;
        white-space: nowrap;
    }

    .empty-success {
        padding: 1rem 1.15rem;
        border: 1px solid rgba(123,192,67,.18);
        border-radius: 15px;
        background: rgba(123,192,67,.055);
        color: #a9d982;
        font-weight: 650;
    }

    /* Adattamento fluido per schermi mobili */
    @media (max-width: 640px) {
        .summary-grid {
            grid-template-columns: 1fr;
        }
        .block-container {
            padding-left: 0.85rem;
            padding-right: 0.85rem;
            padding-top: 1.2rem;
        }
        .settlement-card {
            flex-direction: column;
            align-items: flex-start;
            gap: 0.8rem;
            padding: 1rem;
        }
        .settlement-info {
            width: 100%;
            justify-content: space-between;
            gap: 0.5rem;
        }
        .settlement-arrow {
            display: none;
        }
        .settlement-amount {
            align-self: flex-end;
            font-size: 1.35rem;
            border-top: 1px solid rgba(255,255,255,.06);
            width: 100%;
            padding-top: 0.6rem;
            text-align: right;
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


def update_expense(row_idx, expense_date, payer, description, amount, participants):
    sheet.update(
        range_name=f"A{row_idx}:E{row_idx}",
        values=[
            [
                expense_date.strftime("%Y-%m-%d"),
                payer,
                description,
                float(amount),
                ", ".join(participants),
            ]
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

@st.dialog("Modifica spesa")
def edit_dialog(expense):
    st.subheader(f"Modifica: {expense['description']}")

    with st.form(f"edit_form_{expense['row_idx']}"):
        default_date = expense["date"] if expense["date"] else date.today()
        new_date = st.date_input("📅 Data", value=default_date)

        default_payer_idx = MEMBERS.index(expense["payer"]) if expense["payer"] in MEMBERS else 0
        new_payer = st.selectbox("👤 Chi ha pagato?", MEMBERS, index=default_payer_idx)

        new_desc = st.text_input("📝 Descrizione", value=expense["description"])
        new_amount = st.number_input("💶 Importo", min_value=0.01, value=float(expense["amount"]), step=0.50, format="%.2f")

        valid_default_parts = [p for p in expense["participants"] if p in MEMBERS]
        new_participants = st.multiselect("👥 Partecipanti", MEMBERS, default=valid_default_parts)

        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("Salva modifiche", type="primary", use_container_width=True)
        with col2:
            cancelled = st.form_submit_button("Annulla", use_container_width=True)

        if submitted:
            if not new_desc.strip():
                st.error("Inserisci una descrizione.")
            elif new_amount <= 0:
                st.error("L'importo deve essere maggiore di zero.")
            elif not new_participants:
                st.error("Seleziona almeno un partecipante.")
            else:
                try:
                    update_expense(
                        row_idx=expense["row_idx"],
                        expense_date=new_date,
                        payer=new_payer,
                        description=new_desc.strip(),
                        amount=new_amount,
                        participants=new_participants,
                    )
                    st.success("Spesa aggiornata con successo! 🎉")
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore durante l'aggiornamento: {e}")

        if cancelled:
            st.rerun()


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

st.markdown(
    """
    <div class="app-hero">
        <div class="app-hero-kicker">💰 Spese condivise</div>
        <h1>Spese di Gruppo</h1>
        <p>Registra le spese, controlla chi ha anticipato e scopri in un attimo i trasferimenti minimi per chiudere i conti.</p>
    </div>
    """,
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
    st.markdown(
        f"""
        <div class="summary-grid">
            <div class="summary-card">
                <div class="summary-label">Totale speso</div>
                <div class="summary-value">{escape(euro(total_amount))}</div>
            </div>
            <div class="summary-card">
                <div class="summary-label">Spese</div>
                <div class="summary-value">{expense_count}</div>
            </div>
            <div class="summary-card">
                <div class="summary-label">Da saldare</div>
                <div class="summary-value">{len(settlements)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not expenses:
        st.info("💸 Non ci sono ancora spese. Aggiungi la prima dalla scheda «Nuova spesa».")
    else:
        st.markdown(
            """
            <div class="section-heading">
                <h2>Da saldare</h2>
                <p>Il percorso più semplice per pareggiare i conti con il minor numero di trasferimenti.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not settlements:
            st.markdown(
                '<div class="empty-success">✓ Tutti i conti sono perfettamente in pari.</div>',
                unsafe_allow_html=True,
            )
        else:
            settlement_html = ['<div class="settlement-list">']
            for s in settlements:
                settlement_html.append(
                    f"""
                    <div class="settlement-card">
                        <div class="settlement-info">
                            <div class="settlement-person-block">
                                <div class="settlement-label">Deve pagare</div>
                                <div class="person-name debtor">{escape(s["from"])}</div>
                            </div>
                            <div class="settlement-arrow">→</div>
                            <div class="settlement-person-block">
                                <div class="settlement-label">Riceve</div>
                                <div class="person-name creditor">{escape(s["to"])}</div>
                            </div>
                        </div>
                        <div class="settlement-amount">{escape(euro(s["amount"]))}</div>
                    </div>
                    """
                )
            settlement_html.append("</div>")
            st.markdown("".join(settlement_html), unsafe_allow_html=True)

        st.markdown(
            """
            <div class="section-heading">
                <h2>Situazione</h2>
                <p>Quanto ha anticipato e qual è il saldo netto di ogni persona.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        active_members = [
            m for m in MEMBERS
            if abs(balances[m]) > 0.009 or payer_totals[m] > 0 or personal_shares[m] > 0
        ]

        if not active_members:
            st.info("Nessuna situazione da mostrare.")
        else:
            for person in active_members:
                balance = balances[person]
                if balance > 0.009:
                    status = "Riceve"
                    status_val = f"+{euro(balance)}"
                    value_color = "color: #83cf4d;"
                elif balance < -0.009:
                    status = "Deve"
                    status_val = euro(balance)
                    value_color = "color: #ff6666;"
                else:
                    status = "In pari"
                    status_val = "0,00 €"
                    value_color = "color: #b2b7bf;"

                with st.container(border=True):
                    cols = st.columns([2, 1])
                    with cols[0]:
                        st.markdown(f"**{person}**")
                        st.caption(f"Pagato {euro(payer_totals[person])} · Quota {euro(personal_shares[person])}")
                    with cols[1]:
                        st.markdown(f"<div style='text-align: right; font-size: 0.7rem; font-weight: 700; color: #8f97a2;'>{status}</div>", unsafe_allow_html=True)
                        st.markdown(f"<div style='text-align: right; font-size: 0.95rem; font-weight: 800; {value_color}'>{status_val}</div>", unsafe_allow_html=True)


# ============================================================
# TAB 2 — ELENCO SPESE
# ============================================================

with tab_expenses:
    st.header("🧾 Spese")

    if not expenses:
        st.info("Non ci sono ancora spese registrate.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            payer_filter = st.selectbox("Chi ha pagato", ["Tutti"] + MEMBERS)
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

        st.caption(f"{len(filtered)} spese visualizzate")

        for expense in filtered:
            with st.container(border=True):
                cols_layout = [4, 1.3, 0.5, 0.5] if st.session_state.is_admin else [4, 1.3]
                cols = st.columns(cols_layout)

                with cols[0]:
                    st.markdown(f"**{expense['description']}**")
                    participants = ", ".join(expense["participants"])
                    st.caption(f"👤 {expense['payer']} · 📅 {format_date(expense['date'])}")
                    st.caption(f"👥 {participants}")

                with cols[1]:
                    st.markdown(f"**{euro(expense['amount'])}**")

                if st.session_state.is_admin:
                    with cols[2]:
                        if st.button("✏️", key=f"edit_{expense['row_idx']}", help="Modifica spesa"):
                            edit_dialog(expense)
                    with cols[3]:
                        if st.button("🗑️", key=f"delete_{expense['row_idx']}", help="Elimina spesa"):
                            delete_dialog(expense)

        filtered_total = sum(e["amount"] for e in filtered)
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.caption("Spese visualizzate")
            st.metric("Numero", len(filtered))
        with col2:
            st.caption("Totale visualizzato")
            st.metric("Totale", euro(filtered_total))

        if st.session_state.is_admin:
            st.divider()
            with st.expander("⚠️ Gestione dati"):
                st.warning("Le operazioni qui sotto modificano definitivamente il Google Sheet.")
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
        st.caption("Inserisci i dettagli della spesa.")

        with st.form("new_expense_form", clear_on_submit=True):
            expense_date = st.date_input("📅 Data", value=date.today())
            payer = st.selectbox("👤 Chi ha pagato?", MEMBERS)
            description = st.text_input("📝 Cosa?", placeholder="Cena, benzina, supermercato...")
            amount = st.number_input("💶 Importo", min_value=0.01, value=10.00, step=0.50, format="%.2f")

            st.divider()
            st.subheader("👥 Chi partecipa?")
            
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
                    "Partecipanti",
                    MEMBERS,
                    placeholder="Seleziona le persone coinvolte...",
                )

            if selected_participants:
                per_person = amount / len(selected_participants)
                st.info(f"💡 {euro(per_person)} per persona · {len(selected_participants)} partecipanti")
            else:
                st.warning("Seleziona almeno un partecipante.")

            st.write("")
            submitted = st.form_submit_button("💾 Salva spesa", type="primary", use_container_width=True)

        if submitted:
            if not description.strip():
                st.error("Inserisci una descrizione.")
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
                    st.success(f"Spesa di {euro(amount)} salvata! 🎉")
                    st.rerun()
                except Exception as error:
                    st.error(f"Errore durante il salvataggio: {error}")
