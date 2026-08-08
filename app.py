from collections import defaultdict
from datetime import date, datetime

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials


# ============================================================
# CONFIGURAZIONE
# ============================================================

st.set_page_config(
    page_title="Spese di Gruppo",
    page_icon="💰",
    layout="centered",
    initial_sidebar_state="collapsed",
)

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
# CSS ADATTIVO AL TEMA STREAMLIT
# ============================================================

st.markdown(
    """
    <style>

    /* ========================================================
       LAYOUT GENERALE
       ======================================================== */

    .block-container {
        max-width: 1050px;
        padding-top: 1.5rem;
        padding-bottom: 4rem;
    }

    /* Usiamo le variabili di Streamlit.
       NON impostiamo colori fissi. */

    .app-title {
        color: var(--st-text-color);
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.04em;
        line-height: 1.1;
        margin-bottom: 0.3rem;
    }

    .app-subtitle {
        color: var(--st-gray-color);
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }


    /* ========================================================
       CARD KPI
       ======================================================== */

    .kpi-card {
        background: var(--st-secondary-background-color);
        border: 1px solid var(--st-border-color);
        border-radius: var(--st-base-radius);
        padding: 1.15rem 1.2rem;
        height: 100%;
        transition: border-color 0.15s ease;
    }

    .kpi-card:hover {
        border-color: var(--st-primary-color);
    }

    .kpi-label {
        color: var(--st-gray-text-color);
        font-size: 0.72rem;
        font-weight: 750;
        letter-spacing: 0.055em;
        text-transform: uppercase;
    }

    .kpi-value {
        color: var(--st-text-color);
        font-size: 1.65rem;
        font-weight: 800;
        letter-spacing: -0.025em;
        margin-top: 0.35rem;
    }

    .kpi-help {
        color: var(--st-gray-text-color);
        font-size: 0.76rem;
        margin-top: 0.2rem;
    }


    /* ========================================================
       SEZIONI
       ======================================================== */

    .section-title {
        color: var(--st-text-color);
        font-size: 1.35rem;
        font-weight: 800;
        margin-top: 1.5rem;
        margin-bottom: 0.2rem;
    }

    .section-description {
        color: var(--st-gray-text-color);
        font-size: 0.9rem;
        margin-bottom: 1rem;
    }


    /* ========================================================
       CONGUAGLI
       ======================================================== */

    .settlement-card {
        background: var(--st-secondary-background-color);
        border: 1px solid var(--st-border-color);
        border-radius: var(--st-base-radius);
        padding: 1.1rem 1.2rem;
        margin-bottom: 0.7rem;
    }

    .settlement-card:hover {
        border-color: var(--st-primary-color);
    }

    .settlement-label {
        color: var(--st-gray-text-color);
        font-size: 0.66rem;
        font-weight: 750;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin-bottom: 0.35rem;
    }

    .settlement-person {
        color: var(--st-text-color);
        font-size: 1.05rem;
        font-weight: 750;
    }

    .settlement-arrow {
        color: var(--st-gray-text-color);
        font-size: 1.35rem;
        text-align: center;
        padding-top: 0.65rem;
    }

    .settlement-amount {
        color: var(--st-text-color);
        font-size: 1.35rem;
        font-weight: 850;
        text-align: center;
        margin-top: 0.8rem;
    }

    .debtor {
        color: var(--st-red-text-color) !important;
    }

    .creditor {
        color: var(--st-green-text-color) !important;
    }


    /* ========================================================
       SALDI PERSONE
       ======================================================== */

    .person-card {
        background: var(--st-secondary-background-color);
        border: 1px solid var(--st-border-color);
        border-radius: var(--st-base-radius);
        padding: 0.9rem 1rem;
        margin-bottom: 0.55rem;
    }

    .person-name {
        color: var(--st-text-color);
        font-weight: 750;
    }

    .person-meta {
        color: var(--st-gray-text-color);
        font-size: 0.78rem;
    }

    .balance-positive {
        color: var(--st-green-text-color);
        font-weight: 800;
        text-align: right;
    }

    .balance-negative {
        color: var(--st-red-text-color);
        font-weight: 800;
        text-align: right;
    }

    .balance-neutral {
        color: var(--st-gray-text-color);
        font-weight: 700;
        text-align: right;
    }


    /* ========================================================
       SPESA
       ======================================================== */

    .expense-card {
        background: var(--st-secondary-background-color);
        border: 1px solid var(--st-border-color);
        border-radius: var(--st-base-radius);
        padding: 0.95rem 1rem;
        margin-bottom: 0.6rem;
    }

    .expense-title {
        color: var(--st-text-color);
        font-weight: 750;
        font-size: 0.98rem;
    }

    .expense-meta {
        color: var(--st-gray-text-color);
        font-size: 0.78rem;
        margin-top: 0.2rem;
    }

    .expense-amount {
        color: var(--st-text-color);
        font-weight: 800;
        font-size: 1rem;
        text-align: right;
    }


    /* ========================================================
       EMPTY STATE
       ======================================================== */

    .empty-state {
        background: var(--st-secondary-background-color);
        border: 1px solid var(--st-border-color);
        border-radius: var(--st-base-radius);
        text-align: center;
        padding: 2.5rem 1rem;
    }

    .empty-icon {
        font-size: 2.4rem;
        margin-bottom: 0.4rem;
    }

    .empty-title {
        color: var(--st-text-color);
        font-size: 1.1rem;
        font-weight: 750;
    }

    .empty-text {
        color: var(--st-gray-text-color);
        font-size: 0.9rem;
        margin-top: 0.3rem;
    }


    /* ========================================================
       MOBILE
       ======================================================== */

    @media (max-width: 700px) {

        .block-container {
            padding-left: 0.8rem;
            padding-right: 0.8rem;
            padding-top: 1rem;
        }

        .app-title {
            font-size: 1.85rem;
        }

        .kpi-value {
            font-size: 1.4rem;
        }

        .settlement-person {
            font-size: 0.95rem;
        }

    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# FUNZIONI UTILITY
# ============================================================

def euro(amount):
    """Formatta un numero in formato monetario italiano."""

    try:
        value = float(amount)
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
    """Converte un importo proveniente da Google Sheets."""

    if value is None or value == "":
        return 0.0

    if isinstance(value, (int, float)):
        return float(value)

    value = str(value).strip()
    value = value.replace("€", "").replace(" ", "")

    if "," in value:
        value = value.replace(".", "")
        value = value.replace(",", ".")

    try:
        return float(value)
    except ValueError:
        return 0.0


def parse_date(value):
    """Converte una data nei formati supportati."""

    if not value:
        return None

    if isinstance(value, date):
        return value

    value = str(value).strip()

    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
    ]

    for fmt in formats:

        try:
            return datetime.strptime(
                value,
                fmt,
            ).date()

        except ValueError:
            pass

    return None


def format_date(value):

    parsed = parse_date(value)

    if not parsed:
        return "—"

    return parsed.strftime("%d/%m/%Y")


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

    client = gspread.authorize(credentials)

    return client


client = init_connection()

sheet = client.open(SHEET_NAME).sheet1


# ============================================================
# INIZIALIZZAZIONE FOGLIO
# ============================================================

def initialize_sheet():

    values = sheet.get_all_values()

    if not values:

        sheet.append_row(HEADERS)

        return

    current_headers = values[0]

    old_headers = [
        "Chi ha pagato",
        "Cosa",
        "Importo",
        "Partecipanti",
    ]

    # Migrazione dal vecchio formato
    if current_headers == old_headers:

        old_rows = values[1:]

        migrated_rows = []

        for row in old_rows:

            row = row + [""] * (4 - len(row))

            migrated_rows.append(
                [
                    date.today().strftime("%Y-%m-%d"),
                    row[0],
                    row[1],
                    row[2],
                    row[3],
                ]
            )

        sheet.clear()

        sheet.append_row(HEADERS)

        if migrated_rows:

            sheet.append_rows(
                migrated_rows
            )

        return

    if current_headers == HEADERS:

        return


initialize_sheet()


# ============================================================
# LETTURA SPESE
# ============================================================

@st.cache_data(ttl=10)
def load_expenses():

    try:

        records = sheet.get_all_records()

        expenses = []

        for row_idx, row in enumerate(
            records,
            start=2,
        ):

            raw_participants = str(
                row.get(
                    "Partecipanti",
                    "",
                )
            )

            participants = [
                p.strip()
                for p in raw_participants.split(",")
                if p.strip()
            ]

            expenses.append(
                {
                    "row_idx": row_idx,

                    "date": parse_date(
                        row.get(
                            "Data",
                            "",
                        )
                    ),

                    "payer": str(
                        row.get(
                            "Chi ha pagato",
                            "Sconosciuto",
                        )
                    ).strip(),

                    "description": str(
                        row.get(
                            "Cosa",
                            "Spesa generica",
                        )
                    ).strip(),

                    "amount": parse_amount(
                        row.get(
                            "Importo",
                            0,
                        )
                    ),

                    "participants": participants,
                }
            )

        return expenses

    except Exception as error:

        st.error(
            f"Errore durante la lettura: {error}"
        )

        return []


# ============================================================
# SCRITTURA
# ============================================================

def save_expense(
    expense_date,
    payer,
    description,
    amount,
    participants,
):

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
# CALCOLO SALDI
# ============================================================

def calculate_balances(expenses):

    balances = defaultdict(float)

    for member in MEMBERS:

        balances[member] = 0.0

    for expense in expenses:

        payer = expense["payer"]
        amount = expense["amount"]
        participants = expense["participants"]

        if not participants:
            continue

        share = amount / len(participants)

        balances[payer] += amount

        for participant in participants:

            balances[participant] -= share

    return balances


def calculate_settlements(expenses):

    balances = calculate_balances(
        expenses
    )

    debtors = [
        [person, -balance]
        for person, balance in balances.items()
        if balance < -0.009
    ]

    creditors = [
        [person, balance]
        for person, balance in balances.items()
        if balance > 0.009
    ]

    debtors.sort(
        key=lambda x: x[1],
        reverse=True,
    )

    creditors.sort(
        key=lambda x: x[1],
        reverse=True,
    )

    settlements = []

    i = 0
    j = 0

    while (
        i < len(debtors)
        and j < len(creditors)
    ):

        amount = min(
            debtors[i][1],
            creditors[j][1],
        )

        amount = round(
            amount,
            2,
        )

        if amount > 0:

            settlements.append(
                {
                    "from": debtors[i][0],
                    "to": creditors[j][0],
                    "amount": amount,
                }
            )

        debtors[i][1] -= amount
        creditors[j][1] -= amount

        if debtors[i][1] < 0.009:

            i += 1

        if creditors[j][1] < 0.009:

            j += 1

    return settlements, balances


def calculate_personal_shares(expenses):

    shares = defaultdict(float)

    for member in MEMBERS:

        shares[member] = 0.0

    for expense in expenses:

        participants = expense["participants"]
        amount = expense["amount"]

        if not participants:
            continue

        share = amount / len(participants)

        for participant in participants:

            shares[participant] += share

    return shares


def calculate_payer_totals(expenses):

    totals = defaultdict(float)

    for member in MEMBERS:

        totals[member] = 0.0

    for expense in expenses:

        totals[expense["payer"]] += expense["amount"]

    return totals


# ============================================================
# SESSION STATE
# ============================================================

if "is_admin" not in st.session_state:

    st.session_state.is_admin = False


# ============================================================
# DIALOG ELIMINAZIONE
# ============================================================

@st.dialog("Elimina spesa")
def delete_dialog(expense):

    st.markdown(
        f"### {expense['description']}"
    )

    st.caption(
        f"{expense['payer']} · "
        f"{format_date(expense['date'])}"
    )

    st.markdown(
        f"## {euro(expense['amount'])}"
    )

    st.warning(
        "Questa operazione non può essere annullata."
    )

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "Elimina",
            type="primary",
            use_container_width=True,
        ):

            try:

                delete_expense(
                    expense["row_idx"]
                )

                st.rerun()

            except Exception as error:

                st.error(
                    str(error)
                )

    with col2:

        if st.button(
            "Annulla",
            use_container_width=True,
        ):

            st.rerun()


# ============================================================
# DIALOG SVUOTA TUTTO
# ============================================================

@st.dialog("⚠️ Svuota tutte le spese")
def clear_all_dialog(
    expense_count,
    total_amount,
):

    st.error(
        "Stai per eliminare tutte le spese."
    )

    st.write(
        f"**{expense_count} spese**"
    )

    st.write(
        f"Totale: **{euro(total_amount)}**"
    )

    st.warning(
        "Questa operazione non può essere annullata."
    )

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "Cancella tutto",
            type="primary",
            use_container_width=True,
        ):

            try:

                delete_all_expenses()

                st.rerun()

            except Exception as error:

                st.error(
                    str(error)
                )

    with col2:

        if st.button(
            "Annulla",
            use_container_width=True,
        ):

            st.rerun()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown("## ⚙️ Impostazioni")

    st.divider()

    st.markdown("### 🔐 Amministratore")

    if st.session_state.is_admin:

        st.success(
            "Modalità admin attiva"
        )

        if st.button(
            "Esci dalla modalità admin",
            use_container_width=True,
        ):

            st.session_state.is_admin = False

            st.rerun()

    else:

        password = st.text_input(
            "Password",
            type="password",
            placeholder="Password admin",
        )

        admin_password = st.secrets.get(
            "admin_password",
            "zono",
        )

        if password:

            if password == admin_password:

                st.session_state.is_admin = True

                st.rerun()

            else:

                st.error(
                    "Password non corretta."
                )

    st.divider()

    st.caption(
        "Gli utenti normali possono visualizzare "
        "le spese. Solo l'amministratore può modificarle."
    )


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="app-title">💰 Spese di Gruppo</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="app-subtitle">
        Gestisci le spese e scopri automaticamente
        come pareggiare i conti.
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DATI
# ============================================================

expenses = load_expenses()

total_amount = sum(
    expense["amount"]
    for expense in expenses
)

expense_count = len(expenses)

settlements, balances = calculate_settlements(
    expenses
)

personal_shares = calculate_personal_shares(
    expenses
)

payer_totals = calculate_payer_totals(
    expenses
)


# ============================================================
# TABS
# ============================================================

tab_dashboard, tab_expenses, tab_add = st.tabs(
    [
        "📊  Riepilogo",
        "🧾  Spese",
        "➕  Nuova spesa",
    ]
)


# ============================================================
# DASHBOARD
# ============================================================

with tab_dashboard:

    # --------------------------------------------------------
    # KPI
    # --------------------------------------------------------

    col1, col2, col3 = st.columns(3)

    with col1:

        st.markdown(
            f"""
            <div class="kpi-card">

                <div class="kpi-label">
                    Totale speso
                </div>

                <div class="kpi-value">
                    {euro(total_amount)}
                </div>

                <div class="kpi-help">
                    Tutte le spese
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:

        st.markdown(
            f"""
            <div class="kpi-card">

                <div class="kpi-label">
                    Spese
                </div>

                <div class="kpi-value">
                    {expense_count}
                </div>

                <div class="kpi-help">
                    Registrate
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:

        st.markdown(
            f"""
            <div class="kpi-card">

                <div class="kpi-label">
                    Da saldare
                </div>

                <div class="kpi-value">
                    {len(settlements)}
                </div>

                <div class="kpi-help">
                    Trasferimenti necessari
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )


    # --------------------------------------------------------
    # NESSUNA SPESA
    # --------------------------------------------------------

    if not expenses:

        st.write("")

        st.markdown(
            """
            <div class="empty-state">

                <div class="empty-icon">
                    💸
                </div>

                <div class="empty-title">
                    Nessuna spesa ancora
                </div>

                <div class="empty-text">
                    Aggiungi la prima spesa per iniziare.
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )


    # --------------------------------------------------------
    # CONGUAGLI
    # --------------------------------------------------------

    else:

        st.markdown(
            '<div class="section-title">💸 Da saldare</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="section-description">
                I trasferimenti minimi necessari per
                pareggiare i conti.
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not settlements:

            st.success(
                "🎉 Tutti i conti sono perfettamente in pari!"
            )

        else:

            for settlement in settlements:

                debtor = settlement["from"]
                creditor = settlement["to"]
                amount = settlement["amount"]

                st.markdown(
                    f"""
                    <div class="settlement-card">

                        <div style="
                            display:grid;
                            grid-template-columns:
                            1fr 60px 1fr;
                            align-items:center;
                        ">

                            <div>

                                <div class="
                                    settlement-label
                                ">
                                    Deve pagare
                                </div>

                                <div class="
                                    settlement-person
                                    debtor
                                ">
                                    🔴 {debtor}
                                </div>

                            </div>

                            <div class="
                                settlement-arrow
                            ">
                                →
                            </div>

                            <div>

                                <div class="
                                    settlement-label
                                ">
                                    Riceve
                                </div>

                                <div class="
                                    settlement-person
                                    creditor
                                ">
                                    🟢 {creditor}
                                </div>

                            </div>

                        </div>

                        <div class="
                            settlement-amount
                        ">
                            {euro(amount)}
                        </div>

                    </div>
                    """,
                    unsafe_allow_html=True,
                )


        # ----------------------------------------------------
        # SALDI
        # ----------------------------------------------------

        st.markdown(
            '<div class="section-title">👥 Saldi</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="section-description">
                Situazione individuale del gruppo.
            </div>
            """,
            unsafe_allow_html=True,
        )

        active_members = [
            member
            for member in MEMBERS
            if (
                abs(balances[member]) > 0.009
                or payer_totals[member] > 0
                or personal_shares[member] > 0
            )
        ]

        for person in active_members:

            balance = balances[person]

            if balance > 0.009:

                balance_html = f"""
                    <div class="balance-positive">
                        +{euro(balance)}
                    </div>
                """

            elif balance < -0.009:

                balance_html = f"""
                    <div class="balance-negative">
                        {euro(balance)}
                    </div>
                """

            else:

                balance_html = f"""
                    <div class="balance-neutral">
                        0,00 €
                    </div>
                """

            st.markdown(
                f"""
                <div class="person-card">

                    <div style="
                        display:grid;
                        grid-template-columns:
                        1.5fr 1.5fr 0.8fr;
                        align-items:center;
                    ">

                        <div>
                            <div class="person-name">
                                {person}
                            </div>
                        </div>

                        <div>
                            <div class="person-meta">
                                Pagato
                                {euro(payer_totals[person])}
                            </div>

                            <div class="person-meta">
                                Quota
                                {euro(personal_shares[person])}
                            </div>
                        </div>

                        <div>
                            {balance_html}
                        </div>

                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )


        # ----------------------------------------------------
        # DETTAGLIO QUOTE
        # ----------------------------------------------------

        with st.expander(
            "📊 Dettaglio quote personali"
        ):

            sorted_shares = sorted(
                personal_shares.items(),
                key=lambda item: item[1],
                reverse=True,
            )

            for person, share in sorted_shares:

                if share <= 0:
                    continue

                col1, col2 = st.columns(2)

                with col1:

                    st.write(
                        f"**{person}**"
                    )

                with col2:

                    st.write(
                        euro(share)
                    )


# ============================================================
# TAB SPESE
# ============================================================

with tab_expenses:

    if not expenses:

        st.info(
            "Non ci sono ancora spese registrate."
        )

    else:

        st.markdown(
            f"## 🧾 Spese · {expense_count}"
        )

        # ----------------------------------------------------
        # FILTRI
        # ----------------------------------------------------

        col1, col2 = st.columns(2)

        with col1:

            payer_filter = st.selectbox(
                "Chi ha pagato",
                ["Tutti"] + MEMBERS,
            )

        with col2:

            sort_order = st.selectbox(
                "Ordina",
                [
                    "Più recenti",
                    "Più vecchie",
                    "Importo maggiore",
                    "Importo minore",
                ],
            )

        filtered_expenses = expenses.copy()

        if payer_filter != "Tutti":

            filtered_expenses = [
                expense
                for expense in filtered_expenses
                if expense["payer"] == payer_filter
            ]

        if sort_order == "Più recenti":

            filtered_expenses.sort(
                key=lambda expense:
                    expense["date"] or date.min,
                reverse=True,
            )

        elif sort_order == "Più vecchie":

            filtered_expenses.sort(
                key=lambda expense:
                    expense["date"] or date.min,
            )

        elif sort_order == "Importo maggiore":

            filtered_expenses.sort(
                key=lambda expense:
                    expense["amount"],
                reverse=True,
            )

        elif sort_order == "Importo minore":

            filtered_expenses.sort(
                key=lambda expense:
                    expense["amount"],
            )


        # ----------------------------------------------------
        # LISTA SPESE
        # ----------------------------------------------------

        st.write("")

        for expense in filtered_expenses:

            col_info, col_amount, col_action = st.columns(
                [5, 1.5, 0.6]
            )

            with col_info:

                participants = ", ".join(
                    expense["participants"]
                )

                st.markdown(
                    f"""
                    <div class="expense-card">

                        <div class="
                            expense-title
                        ">
                            {expense["description"]}
                        </div>

                        <div class="
                            expense-meta
                        ">
                            👤 {expense["payer"]}
                            &nbsp; · &nbsp;
                            📅 {format_date(expense["date"])}
                        </div>

                        <div class="
                            expense-meta
                        ">
                            👥 {participants}
                        </div>

                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with col_amount:

                st.markdown(
                    f"""
                    <div style="
                        padding-top:1rem;
                        text-align:right;
                    ">

                        <div class="
                            expense-amount
                        ">
                            {euro(expense["amount"])}
                        </div>

                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with col_action:

                if st.session_state.is_admin:

                    if st.button(
                        "🗑️",
                        key=f"delete_{expense['row_idx']}",
                        help="Elimina",
                    ):

                        delete_dialog(
                            expense
                        )


        # ----------------------------------------------------
        # TOTALE FILTRATO
        # ----------------------------------------------------

        filtered_total = sum(
            expense["amount"]
            for expense in filtered_expenses
        )

        st.divider()

        col1, col2 = st.columns(2)

        with col1:

            st.caption(
                "Spese visualizzate"
            )

            st.markdown(
                f"**{len(filtered_expenses)}**"
            )

        with col2:

            st.caption(
                "Totale visualizzato"
            )

            st.markdown(
                f"**{euro(filtered_total)}**"
            )


        # ----------------------------------------------------
        # GESTIONE DATI
        # ----------------------------------------------------

        if st.session_state.is_admin:

            st.divider()

            with st.expander(
                "⚠️ Gestione dati"
            ):

                st.warning(
                    "Le operazioni qui sotto modificano "
                    "definitivamente il Google Sheet."
                )

                if st.button(
                    "🗑️ Svuota tutte le spese",
                    use_container_width=True,
                ):

                    clear_all_dialog(
                        expense_count,
                        total_amount,
                    )


# ============================================================
# TAB NUOVA SPESA
# ============================================================

with tab_add:

    if not st.session_state.is_admin:

        st.markdown(
            """
            <div class="empty-state">

                <div class="empty-icon">
                    🔐
                </div>

                <div class="empty-title">
                    Accesso amministratore richiesto
                </div>

                <div class="empty-text">
                    Accedi dalle impostazioni per
                    aggiungere o modificare le spese.
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    else:

        st.markdown(
            "## ➕ Nuova spesa"
        )

        st.caption(
            "Inserisci la spesa e seleziona le persone coinvolte."
        )

        with st.form(
            "new_expense_form",
            clear_on_submit=True,
        ):

            # ------------------------------------------------
            # DATA
            # ------------------------------------------------

            expense_date = st.date_input(
                "📅 Data",
                value=date.today(),
            )


            # ------------------------------------------------
            # PAGATORE
            # ------------------------------------------------

            payer = st.selectbox(
                "👤 Chi ha pagato?",
                MEMBERS,
            )


            # ------------------------------------------------
            # DESCRIZIONE
            # ------------------------------------------------

            description = st.text_input(
                "📝 Cosa?",
                placeholder="Cena, benzina, supermercato...",
            )


            # ------------------------------------------------
            # IMPORTO
            # ------------------------------------------------

            amount = st.number_input(
                "💶 Importo",
                min_value=0.01,
                value=10.00,
                step=0.50,
                format="%.2f",
            )


            st.write("")


            # ------------------------------------------------
            # PARTECIPANTI
            # ------------------------------------------------

            st.markdown(
                "**👥 Partecipanti**"
            )

            selection_mode = st.radio(
                "Chi deve dividere la spesa?",
                [
                    "Tutti",
                    "Seleziona manualmente",
                ],
                horizontal=True,
                label_visibility="collapsed",
            )

            if selection_mode == "Tutti":

                selected_participants = MEMBERS

            else:

                selected_participants = st.multiselect(
                    "Seleziona partecipanti",
                    MEMBERS,
                    placeholder="Scegli le persone...",
                )


            # ------------------------------------------------
            # PREVIEW
            # ------------------------------------------------

            if selected_participants:

                per_person = (
                    amount
                    / len(selected_participants)
                )

                st.info(
                    f"💡 {euro(per_person)} "
                    f"per persona · "
                    f"{len(selected_participants)} partecipanti"
                )

            else:

                st.warning(
                    "Seleziona almeno un partecipante."
                )


            st.write("")


            # ------------------------------------------------
            # SALVA
            # ------------------------------------------------

            submitted = st.form_submit_button(
                "💾 Salva spesa",
                type="primary",
                use_container_width=True,
            )

            if submitted:

                if not description.strip():

                    st.error(
                        "Inserisci una descrizione."
                    )

                elif amount <= 0:

                    st.error(
                        "L'importo deve essere maggiore di zero."
                    )

                elif not selected_participants:

                    st.error(
                        "Seleziona almeno un partecipante."
                    )

                else:

                    try:

                        save_expense(
                            expense_date,
                            payer,
                            description.strip(),
                            amount,
                            selected_participants,
                        )

                        st.success(
                            f"Spesa di {euro(amount)} salvata! 🎉"
                        )

                        st.rerun()

                    except Exception as error:

                        st.error(
                            f"Errore durante il salvataggio: {error}"
                        )
