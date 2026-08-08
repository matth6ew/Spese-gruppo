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
# STILE
# ============================================================

st.markdown(
    """
    <style>

    /* ========================================================
       GENERALE
       ======================================================== */

    .block-container {
        max-width: 1050px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    [data-testid="stAppViewContainer"] {
        background: #f7f8fa;
    }

    /* ========================================================
       HEADER
       ======================================================== */

    .app-title {
        font-size: 2.3rem;
        font-weight: 800;
        color: #111827;
        letter-spacing: -0.04em;
        margin-bottom: 0.15rem;
    }

    .app-subtitle {
        color: #6b7280;
        font-size: 1rem;
        margin-bottom: 1.5rem;
    }

    /* ========================================================
       KPI
       ======================================================== */

    .kpi-label {
        color: #6b7280;
        font-size: 0.82rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }

    .kpi-value {
        color: #111827;
        font-size: 1.65rem;
        font-weight: 800;
        margin-top: 0.35rem;
    }

    .kpi-help {
        color: #9ca3af;
        font-size: 0.78rem;
        margin-top: 0.15rem;
    }

    /* ========================================================
       SALDO POSITIVO / NEGATIVO
       ======================================================== */

    .positive {
        color: #16a34a;
        font-weight: 750;
    }

    .negative {
        color: #dc2626;
        font-weight: 750;
    }

    .neutral {
        color: #6b7280;
        font-weight: 700;
    }

    /* ========================================================
       MOBILE
       ======================================================== */

    @media (max-width: 700px) {

        .block-container {
            padding-top: 1rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }

        .app-title {
            font-size: 1.9rem;
        }

    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# UTILITY
# ============================================================

def euro(amount):
    """Formatta gli importi in formato italiano."""

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
    """Converte importi provenienti da Google Sheets."""

    if value is None or value == "":
        return 0.0

    if isinstance(value, (int, float)):
        return float(value)

    value = str(value).strip()
    value = value.replace("€", "").replace(" ", "")

    if "," in value:
        value = value.replace(".", "").replace(",", ".")

    try:
        return float(value)
    except ValueError:
        return 0.0


def parse_date(value):
    """Converte vari formati di data."""

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
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass

    return None


def format_date(value):
    parsed = parse_date(value)

    if not parsed:
        return "Data non disponibile"

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
# INIZIALIZZAZIONE / MIGRAZIONE FOGLIO
# ============================================================

def initialize_sheet():

    values = sheet.get_all_values()

    # Foglio completamente vuoto
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

    # --------------------------------------------------------
    # Vecchio formato:
    #
    # A = Chi ha pagato
    # B = Cosa
    # C = Importo
    # D = Partecipanti
    #
    # Nuovo formato:
    #
    # A = Data
    # B = Chi ha pagato
    # C = Cosa
    # D = Importo
    # E = Partecipanti
    # --------------------------------------------------------

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
            sheet.append_rows(migrated_rows)

        return

    # --------------------------------------------------------
    # Nuovo formato già presente
    # --------------------------------------------------------

    if current_headers == HEADERS:
        return

    # --------------------------------------------------------
    # Foglio con una sola riga / struttura non riconosciuta
    # --------------------------------------------------------

    if len(values) <= 1:

        sheet.update(
            "A1:E1",
            [HEADERS],
        )


initialize_sheet()


# ============================================================
# LETTURA SPESE
# ============================================================

@st.cache_data(ttl=10)
def load_expenses():

    try:

        records = sheet.get_all_records()

        expenses = []

        for row_idx, row in enumerate(records, start=2):

            raw_participants = str(
                row.get("Partecipanti", "")
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
                        row.get("Data", "")
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
                        row.get("Importo", 0)
                    ),
                    "participants": participants,
                }
            )

        return expenses

    except Exception as error:

        st.error(
            f"Errore durante la lettura delle spese: {error}"
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

        # Chi ha pagato ha anticipato l'intero importo
        balances[payer] += amount

        # Ogni partecipante deve la propria quota
        for participant in participants:
            balances[participant] -= share

    return balances


def calculate_settlements(expenses):

    balances = calculate_balances(expenses)

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
        key=lambda item: item[1],
        reverse=True,
    )

    creditors.sort(
        key=lambda item: item[1],
        reverse=True,
    )

    settlements = []

    debtor_index = 0
    creditor_index = 0

    while (
        debtor_index < len(debtors)
        and creditor_index < len(creditors)
    ):

        debtor = debtors[debtor_index]
        creditor = creditors[creditor_index]

        amount = min(
            debtor[1],
            creditor[1],
        )

        amount = round(amount, 2)

        if amount > 0:

            settlements.append(
                {
                    "from": debtor[0],
                    "to": creditor[0],
                    "amount": amount,
                }
            )

        debtor[1] -= amount
        creditor[1] -= amount

        if debtor[1] < 0.009:
            debtor_index += 1

        if creditor[1] < 0.009:
            creditor_index += 1

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

    st.write(
        "Vuoi davvero eliminare questa spesa?"
    )

    st.markdown(
        f"### {expense['description']}"
    )

    st.write(
        f"Pagata da **{expense['payer']}**"
    )

    st.write(
        f"Importo: **{euro(expense['amount'])}**"
    )

    st.caption(
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
                    f"Errore: {error}"
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
        f"Totale attuale: **{euro(total_amount)}**"
    )

    st.caption(
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
                    f"Errore: {error}"
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

    st.title("⚙️ Impostazioni")

    st.divider()

    st.subheader("🔐 Amministratore")

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
        "💡 In modalità normale puoi visualizzare "
        "tutte le spese. Solo l'admin può modificarle."
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
        Tieni sotto controllo le spese e scopri
        automaticamente come pareggiare i conti.
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# CARICAMENTO DATI
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
# NAVIGAZIONE
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

    # ========================================================
    # KPI
    # ========================================================

    col1, col2, col3 = st.columns(3)

    with col1:

        with st.container(border=True):

            st.markdown(
                '<div class="kpi-label">Totale speso</div>',
                unsafe_allow_html=True,
            )

            st.markdown(
                f'<div class="kpi-value">{euro(total_amount)}</div>',
                unsafe_allow_html=True,
            )

            st.markdown(
                '<div class="kpi-help">Tutte le spese</div>',
                unsafe_allow_html=True,
            )

    with col2:

        with st.container(border=True):

            st.markdown(
                '<div class="kpi-label">Spese</div>',
                unsafe_allow_html=True,
            )

            st.markdown(
                f'<div class="kpi-value">{expense_count}</div>',
                unsafe_allow_html=True,
            )

            st.markdown(
                '<div class="kpi-help">Registrate</div>',
                unsafe_allow_html=True,
            )

    with col3:

        with st.container(border=True):

            st.markdown(
                '<div class="kpi-label">Da saldare</div>',
                unsafe_allow_html=True,
            )

            st.markdown(
                f'<div class="kpi-value">{len(settlements)}</div>',
                unsafe_allow_html=True,
            )

            if settlements:

                st.markdown(
                    '<div class="kpi-help">Trasferimenti necessari</div>',
                    unsafe_allow_html=True,
                )

            else:

                st.markdown(
                    '<div class="kpi-help">Tutto in pari 🎉</div>',
                    unsafe_allow_html=True,
                )

    st.write("")


    # ========================================================
    # EMPTY STATE
    # ========================================================

    if not expenses:

        with st.container(border=True):

            st.markdown(
                """
                <div style="
                    text-align:center;
                    padding:2rem 1rem;
                ">

                    <div style="
                        font-size:3rem;
                        margin-bottom:0.5rem;
                    ">
                        💸
                    </div>

                    <div style="
                        font-size:1.25rem;
                        font-weight:750;
                        color:#111827;
                    ">
                        Nessuna spesa ancora
                    </div>

                    <div style="
                        color:#6b7280;
                        margin-top:0.4rem;
                    ">
                        Aggiungi la prima spesa per
                        iniziare a calcolare i conguagli.
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )

        if st.session_state.is_admin:

            st.info(
                "Vai alla tab **➕ Nuova spesa** per aggiungere la prima spesa."
            )


    # ========================================================
    # CONGUAGLI
    # ========================================================

    else:

        st.subheader("💸 Da saldare")

        if not settlements:

            st.success(
                "🎉 Tutti i conti sono perfettamente in pari!"
            )

        else:

            st.caption(
                "Il modo più semplice per pareggiare tutti i conti."
            )

            for settlement in settlements:

                payer = settlement["from"]
                recipient = settlement["to"]
                amount = settlement["amount"]

                with st.container(border=True):

                    col1, col2, col3 = st.columns(
                        [2.3, 0.8, 2.3]
                    )

                    with col1:

                        st.caption("DEVE PAGARE")

                        st.markdown(
                            f"### 🔴 {payer}"
                        )

                    with col2:

                        st.markdown(
                            """
                            <div style="
                                text-align:center;
                                padding-top:1.2rem;
                                font-size:1.7rem;
                                color:#9ca3af;
                            ">
                                →
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    with col3:

                        st.caption("RICEVE")

                        st.markdown(
                            f"### 🟢 {recipient}"
                        )

                    st.metric(
                        "Importo",
                        euro(amount),
                    )

        st.write("")


        # ====================================================
        # SALDI
        # ====================================================

        st.subheader("👥 Saldo del gruppo")

        st.caption(
            "Verde = deve ricevere · Rosso = deve pagare"
        )

        for person in MEMBERS:

            balance = balances[person]

            if (
                abs(balance) < 0.009
                and payer_totals[person] == 0
                and personal_shares[person] == 0
            ):
                continue

            with st.container(border=True):

                col1, col2, col3 = st.columns(
                    [2.5, 2, 1.5]
                )

                with col1:

                    st.markdown(
                        f"**{person}**"
                    )

                with col2:

                    st.caption(
                        f"Pagato {euro(payer_totals[person])}"
                    )

                    st.caption(
                        f"Consumato {euro(personal_shares[person])}"
                    )

                with col3:

                    if balance > 0.009:

                        st.markdown(
                            f"""
                            <div style="
                                text-align:right;
                                color:#16a34a;
                                font-size:1.05rem;
                                font-weight:800;
                            ">
                                +{euro(balance)}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    elif balance < -0.009:

                        st.markdown(
                            f"""
                            <div style="
                                text-align:right;
                                color:#dc2626;
                                font-size:1.05rem;
                                font-weight:800;
                            ">
                                {euro(balance)}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    else:

                        st.markdown(
                            """
                            <div style="
                                text-align:right;
                                color:#6b7280;
                                font-weight:700;
                            ">
                                0,00 €
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )


        # ====================================================
        # DETTAGLI
        # ====================================================

        st.write("")

        with st.expander(
            "📊 Vedi dettagli delle quote"
        ):

            sorted_people = sorted(
                personal_shares.items(),
                key=lambda item: item[1],
                reverse=True,
            )

            for person, share in sorted_people:

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

        st.subheader(
            f"🧾 Tutte le spese · {expense_count}"
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
                "Ordine",
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
                key=lambda expense: (
                    expense["date"] or date.min
                ),
                reverse=True,
            )

        elif sort_order == "Più vecchie":

            filtered_expenses.sort(
                key=lambda expense: (
                    expense["date"] or date.min
                )
            )

        elif sort_order == "Importo maggiore":

            filtered_expenses.sort(
                key=lambda expense: expense["amount"],
                reverse=True,
            )

        elif sort_order == "Importo minore":

            filtered_expenses.sort(
                key=lambda expense: expense["amount"]
            )

        st.write("")


        # ----------------------------------------------------
        # LISTA SPESE
        # ----------------------------------------------------

        for expense in filtered_expenses:

            with st.container(border=True):

                col_info, col_amount, col_action = st.columns(
                    [5, 1.5, 0.8]
                )

                with col_info:

                    st.markdown(
                        f"### {expense['description']}"
                    )

                    st.caption(
                        f"👤 {expense['payer']}  ·  "
                        f"📅 {format_date(expense['date'])}"
                    )

                    participants = expense[
                        "participants"
                    ]

                    if participants:

                        st.caption(
                            "👥 "
                            + ", ".join(participants)
                        )

                with col_amount:

                    st.markdown(
                        f"""
                        <div style="
                            text-align:right;
                            font-size:1.2rem;
                            font-weight:800;
                            padding-top:0.5rem;
                            color:#111827;
                        ">
                            {euro(expense["amount"])}
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
        # TOTAL FILTRATO
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

            st.write(
                f"**{len(filtered_expenses)}**"
            )

        with col2:

            st.caption(
                "Totale visualizzato"
            )

            st.write(
                f"**{euro(filtered_total)}**"
            )


        # ----------------------------------------------------
        # DANGER ZONE
        # ----------------------------------------------------

        if st.session_state.is_admin:

            st.divider()

            with st.expander(
                "⚠️ Gestione dati"
            ):

                st.warning(
                    "Queste operazioni modificano definitivamente "
                    "i dati nel Google Sheet."
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

        with st.container(border=True):

            st.markdown(
                "### 🔐 Accesso amministratore"
            )

            st.write(
                "Per aggiungere una spesa devi accedere "
                "come amministratore."
            )

            st.info(
                "Apri **⚙️ Impostazioni** e inserisci "
                "la password admin."
            )

    else:

        st.subheader("➕ Nuova spesa")

        st.caption(
            "Inserisci una spesa e scegli le persone che hanno partecipato."
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
                placeholder="Cena, benzina, spesa...",
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
                "**👥 Chi ha partecipato?**"
            )

            col_all, col_none = st.columns(2)

            with col_all:

                all_participants = st.checkbox(
                    "Tutti",
                    value=True,
                )

            with col_none:

                no_participants = st.checkbox(
                    "Nessuno",
                    value=False,
                )

            if no_participants:

                default_participants = []

            elif all_participants:

                default_participants = MEMBERS

            else:

                default_participants = []

            participants = st.multiselect(
                "Partecipanti",
                MEMBERS,
                default=default_participants,
                label_visibility="collapsed",
            )

            # ------------------------------------------------
            # PREVIEW
            # ------------------------------------------------

            if participants:

                per_person = (
                    amount / len(participants)
                )

                st.info(
                    f"💡 **{euro(per_person)}** "
                    f"per persona · "
                    f"{len(participants)} partecipanti"
                )

            else:

                st.warning(
                    "Seleziona almeno un partecipante."
                )

            st.write("")

            # ------------------------------------------------
            # SUBMIT
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

                elif not participants:

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
                            participants,
                        )

                        st.success(
                            f"Spesa di {euro(amount)} salvata! 🎉"
                        )

                        st.rerun()

                    except Exception as error:

                        st.error(
                            f"Errore durante il salvataggio: {error}"
                        )
