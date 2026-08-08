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
# CSS
# ============================================================

st.markdown(
    """
    <style>

    /* ---------- Layout generale ---------- */

    .block-container {
        max-width: 1000px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    /* ---------- Header ---------- */

    .app-header {
        padding: 0.5rem 0 1.5rem 0;
    }

    .app-title {
        font-size: 2.2rem;
        font-weight: 800;
        margin-bottom: 0.15rem;
    }

    .app-subtitle {
        color: #6b7280;
        font-size: 1rem;
    }

    /* ---------- KPI ---------- */

    .kpi-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 1rem 1.1rem;
        min-height: 105px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
    }

    .kpi-label {
        color: #6b7280;
        font-size: 0.85rem;
        margin-bottom: 0.35rem;
    }

    .kpi-value {
        font-size: 1.55rem;
        font-weight: 800;
        color: #111827;
    }

    .kpi-description {
        color: #9ca3af;
        font-size: 0.75rem;
        margin-top: 0.25rem;
    }

    /* ---------- Conguagli ---------- */

    .settlement-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.7rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
    }

    .settlement-person {
        font-size: 1rem;
        font-weight: 700;
        color: #111827;
    }

    .settlement-arrow {
        color: #9ca3af;
        padding: 0 0.4rem;
    }

    .settlement-recipient {
        font-size: 1rem;
        font-weight: 700;
        color: #16a34a;
    }

    .settlement-amount {
        font-size: 1.25rem;
        font-weight: 800;
        color: #111827;
        margin-top: 0.35rem;
    }

    /* ---------- Saldi ---------- */

    .balance-positive {
        color: #16a34a;
        font-weight: 800;
    }

    .balance-negative {
        color: #dc2626;
        font-weight: 800;
    }

    .balance-zero {
        color: #6b7280;
        font-weight: 700;
    }

    /* ---------- Spese ---------- */

    .expense-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 1rem 1.1rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.025);
    }

    .expense-title {
        font-size: 1rem;
        font-weight: 750;
        color: #111827;
    }

    .expense-meta {
        color: #6b7280;
        font-size: 0.82rem;
        margin-top: 0.25rem;
    }

    .expense-amount {
        font-size: 1.15rem;
        font-weight: 800;
        text-align: right;
        color: #111827;
    }

    /* ---------- Empty state ---------- */

    .empty-state {
        text-align: center;
        padding: 3rem 1rem;
        color: #6b7280;
    }

    .empty-icon {
        font-size: 3rem;
        margin-bottom: 0.5rem;
    }

    .empty-title {
        font-size: 1.2rem;
        font-weight: 750;
        color: #111827;
    }

    /* ---------- Sidebar ---------- */

    [data-testid="stSidebar"] {
        border-right: 1px solid #e5e7eb;
    }

    /* ---------- Mobile ---------- */

    @media (max-width: 640px) {

        .block-container {
            padding-top: 1rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }

        .app-title {
            font-size: 1.8rem;
        }

        .kpi-card {
            min-height: 90px;
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
    """Formatta un importo in stile italiano."""
    try:
        value = float(amount)
    except (ValueError, TypeError):
        value = 0.0

    return f"{value:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def parse_amount(value):
    """Converte in modo robusto importi provenienti da Google Sheets."""
    if value is None or value == "":
        return 0.0

    if isinstance(value, (int, float)):
        return float(value)

    value = str(value).strip()
    value = value.replace("€", "").replace(" ", "")

    # Gestione sia di 12,50 che di 1.234,50
    if "," in value:
        value = value.replace(".", "").replace(",", ".")

    try:
        return float(value)
    except ValueError:
        return 0.0


def parse_date(value):
    """Converte una data proveniente da Google Sheets."""
    if not value:
        return None

    if isinstance(value, date):
        return value

    value = str(value).strip()

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    return None


def format_date(value):
    parsed = parse_date(value)

    if not parsed:
        return "Data non disponibile"

    return parsed.strftime("%d/%m/%Y")


def calculate_settlements(expenses):
    """
    Calcola i trasferimenti minimi necessari per pareggiare i conti.
    """

    balances = defaultdict(float)

    for member in MEMBERS:
        balances[member] = 0.0

    for exp in expenses:

        payer = exp["payer"]
        amount = exp["amount"]
        participants = exp["participants"]

        if not participants:
            continue

        split_amount = amount / len(participants)

        balances[payer] += amount

        for participant in participants:
            balances[participant] -= split_amount

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

    debtors.sort(key=lambda x: x[1], reverse=True)
    creditors.sort(key=lambda x: x[1], reverse=True)

    settlements = []

    i = 0
    j = 0

    while i < len(debtors) and j < len(creditors):

        amount = min(debtors[i][1], creditors[j][1])
        amount = round(amount, 2)

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
    """Calcola quanto ha effettivamente consumato ogni persona."""

    shares = defaultdict(float)

    for member in MEMBERS:
        shares[member] = 0.0

    for exp in expenses:

        participants = exp["participants"]
        amount = exp["amount"]

        if not participants:
            continue

        share = amount / len(participants)

        for participant in participants:
            shares[participant] += share

    return shares


def calculate_payer_totals(expenses):
    """Calcola quanto ha anticipato ogni persona."""

    totals = defaultdict(float)

    for member in MEMBERS:
        totals[member] = 0.0

    for exp in expenses:
        totals[exp["payer"]] += exp["amount"]

    return totals


# ============================================================
# GOOGLE SHEETS
# ============================================================

@st.cache_resource
def init_connection():

    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scope,
    )

    client = gspread.authorize(creds)

    return client


client = init_connection()
sheet = client.open(SHEET_NAME).sheet1


def ensure_headers():
    """
    Assicura che il foglio abbia le colonne aggiornate.

    Supporta anche il vecchio formato:
    Chi ha pagato | Cosa | Importo | Partecipanti
    """

    try:

        values = sheet.get_all_values()

        if not values:
            sheet.append_row(HEADERS)
            return

        current_headers = values[0]

        # Vecchio formato
        old_headers = [
            "Chi ha pagato",
            "Cosa",
            "Importo",
            "Partecipanti",
        ]

        if current_headers == old_headers:

            sheet.update(
                "A1:E1",
                [HEADERS],
            )

        elif current_headers != HEADERS:

            # Se il foglio è praticamente vuoto, inizializziamo.
            if len(values) <= 1:
                sheet.update(
                    "A1:E1",
                    [HEADERS],
                )

    except Exception as e:
        st.error(
            f"Impossibile inizializzare Google Sheets: {e}"
        )


ensure_headers()


@st.cache_data(ttl=10)
def load_expenses():

    try:

        records = sheet.get_all_records()

        expenses = []

        for idx, row in enumerate(records, start=2):

            raw_participants = str(
                row.get("Partecipanti", "")
            )

            participants = [
                p.strip()
                for p in raw_participants.split(",")
                if p.strip()
            ]

            amount = parse_amount(
                row.get("Importo", 0)
            )

            expenses.append(
                {
                    "row_idx": idx,
                    "date": parse_date(
                        row.get("Data", "")
                    ),
                    "payer": (
                        str(
                            row.get(
                                "Chi ha pagato",
                                "Sconosciuto",
                            )
                        ).strip()
                        or "Sconosciuto"
                    ),
                    "description": (
                        str(
                            row.get(
                                "Cosa",
                                "Spesa Generica",
                            )
                        ).strip()
                        or "Spesa Generica"
                    ),
                    "amount": amount,
                    "participants": participants,
                }
            )

        return expenses

    except Exception as e:

        st.error(
            f"Errore di lettura da Google Sheets: {e}"
        )

        return []


def save_expense_to_sheet(
    expense_date,
    payer,
    description,
    amount,
    participants,
):

    participants_str = ", ".join(participants)

    sheet.append_row(
        [
            expense_date.strftime("%Y-%m-%d"),
            payer,
            description,
            float(amount),
            participants_str,
        ]
    )

    st.cache_data.clear()


def delete_single_expense(row_idx):

    sheet.delete_rows(row_idx)

    st.cache_data.clear()


def clear_all_expenses():

    sheet.clear()

    sheet.append_row(HEADERS)

    st.cache_data.clear()


# ============================================================
# SESSION STATE
# ============================================================

if "is_admin" not in st.session_state:
    st.session_state.is_admin = False


# ============================================================
# DIALOG
# ============================================================

@st.dialog("Conferma eliminazione")
def confirm_delete_dialog(
    row_idx,
    description,
    amount,
):

    st.write(
        "Sei sicuro di voler eliminare questa spesa?"
    )

    st.markdown(
        f"**{description} · {euro(amount)}**"
    )

    st.caption(
        "Questa operazione non può essere annullata."
    )

    col_yes, col_no = st.columns(2)

    with col_yes:

        if st.button(
            "Elimina",
            type="primary",
            use_container_width=True,
        ):

            try:

                delete_single_expense(row_idx)

                st.success(
                    "Spesa eliminata."
                )

                st.rerun()

            except Exception as e:

                st.error(
                    f"Errore durante l'eliminazione: {e}"
                )

    with col_no:

        if st.button(
            "Annulla",
            use_container_width=True,
        ):
            st.rerun()


@st.dialog("⚠️ Svuota tutte le spese")
def confirm_clear_all_dialog(
    expense_count,
    total_amount,
):

    st.warning(
        "Questa operazione eliminerà definitivamente "
        "tutte le spese registrate."
    )

    st.markdown(
        f"""
        **{expense_count} spese**  
        Totale: **{euro(total_amount)}**
        """
    )

    st.caption(
        "L'operazione non può essere annullata."
    )

    col_yes, col_no = st.columns(2)

    with col_yes:

        if st.button(
            "Sì, cancella tutto",
            type="primary",
            use_container_width=True,
        ):

            try:

                clear_all_expenses()

                st.success(
                    "Tutte le spese sono state cancellate."
                )

                st.rerun()

            except Exception as e:

                st.error(
                    f"Errore durante la cancellazione: {e}"
                )

    with col_no:

        if st.button(
            "Annulla",
            use_container_width=True,
        ):
            st.rerun()


# ============================================================
# SIDEBAR / ADMIN
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
            "🔒 Esci dalla modalità admin",
            use_container_width=True,
        ):

            st.session_state.is_admin = False
            st.rerun()

    else:

        password = st.text_input(
            "Password admin",
            type="password",
            placeholder="Inserisci la password",
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

        st.caption(
            "La modalità normale permette solo di visualizzare le spese."
        )


# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
    <div class="app-header">
        <div class="app-title">💰 Spese di Gruppo</div>
        <div class="app-subtitle">
            Tieni traccia delle spese e scopri automaticamente chi deve pagare chi.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# LOAD DATA
# ============================================================

expenses = load_expenses()

total_amount = sum(
    exp["amount"]
    for exp in expenses
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
        "📊 Riepilogo",
        "🧾 Spese",
        "➕ Nuova spesa",
    ]
)


# ============================================================
# DASHBOARD
# ============================================================

with tab_dashboard:

    # --------------------------------------------------------
    # EMPTY STATE
    # --------------------------------------------------------

    if not expenses:

        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-icon">💸</div>
                <div class="empty-title">
                    Nessuna spesa ancora
                </div>
                <p>
                    Aggiungi la prima spesa per iniziare
                    a calcolare automaticamente i conguagli.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.session_state.is_admin:

            if st.button(
                "➕ Aggiungi la prima spesa",
                type="primary",
                use_container_width=True,
            ):

                st.session_state.go_to_add = True
                st.rerun()

    else:

        # ----------------------------------------------------
        # KPI
        # ----------------------------------------------------

        active_people = len(
            {
                participant
                for exp in expenses
                for participant in exp["participants"]
            }
        )

        col1, col2, col3, col4 = st.columns(4)

        with col1:

            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-label">Totale speso</div>
                    <div class="kpi-value">
                        {euro(total_amount)}
                    </div>
                    <div class="kpi-description">
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
                    <div class="kpi-label">Numero spese</div>
                    <div class="kpi-value">
                        {expense_count}
                    </div>
                    <div class="kpi-description">
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
                    <div class="kpi-label">Partecipanti</div>
                    <div class="kpi-value">
                        {active_people}
                    </div>
                    <div class="kpi-description">
                        Persone coinvolte
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col4:

            status_text = (
                "Tutto in pari 🎉"
                if not settlements
                else f"{len(settlements)} saldi"
            )

            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-label">Situazione</div>
                    <div class="kpi-value">
                        {len(settlements)}
                    </div>
                    <div class="kpi-description">
                        {status_text}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.write("")

        # ----------------------------------------------------
        # CONGUAGLI
        # ----------------------------------------------------

        st.subheader("💸 Conguagli")

        if not settlements:

            st.success(
                "🎉 Tutti i conti sono perfettamente in pari!"
            )

        else:

            st.caption(
                "Questi sono i trasferimenti necessari per pareggiare i conti."
            )

            for settlement in settlements:

                st.markdown(
                    f"""
                    <div class="settlement-card">
                        <div>
                            <span class="settlement-person">
                                {settlement["from"]}
                            </span>

                            <span class="settlement-arrow">
                                →
                            </span>

                            <span class="settlement-recipient">
                                {settlement["to"]}
                            </span>
                        </div>

                        <div class="settlement-amount">
                            {euro(settlement["amount"])}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.divider()

        # ----------------------------------------------------
        # SALDI PERSONALI
        # ----------------------------------------------------

        st.subheader("👥 Saldo per persona")

        st.caption(
            "Il saldo tiene conto di quanto ogni persona ha anticipato "
            "e di quanto ha effettivamente consumato."
        )

        sorted_balances = sorted(
            balances.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        for person, balance in sorted_balances:

            col_name, col_balance = st.columns(
                [3, 1]
            )

            with col_name:

                st.write(
                    f"**{person}**"
                )

                st.caption(
                    f"Anticipato {euro(payer_totals[person])} · "
                    f"Consumato {euro(personal_shares[person])}"
                )

            with col_balance:

                if balance > 0.009:

                    st.markdown(
                        f"""
                        <div class="balance-positive"
                             style="text-align:right">
                            +{euro(balance)}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                elif balance < -0.009:

                    st.markdown(
                        f"""
                        <div class="balance-negative"
                             style="text-align:right">
                            {euro(balance)}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                else:

                    st.markdown(
                        """
                        <div class="balance-zero"
                             style="text-align:right">
                            0,00 €
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        st.divider()

        # ----------------------------------------------------
        # QUOTA CONSUMATA
        # ----------------------------------------------------

        st.subheader("🛒 Quanto ha consumato ciascuno")

        sorted_shares = sorted(
            personal_shares.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        cols = st.columns(2)

        for index, (person, share) in enumerate(
            sorted_shares
        ):

            with cols[index % 2]:

                st.metric(
                    label=person,
                    value=euro(share),
                )

        st.divider()

        # ----------------------------------------------------
        # ANTICIPI
        # ----------------------------------------------------

        st.subheader("💳 Chi ha anticipato di più")

        sorted_payers = sorted(
            payer_totals.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        for person, total in sorted_payers:

            if total <= 0:
                continue

            person_expenses = [
                exp
                for exp in expenses
                if exp["payer"] == person
            ]

            with st.expander(
                f"👤 {person} · {euro(total)}"
            ):

                for exp in person_expenses:

                    participants_text = ", ".join(
                        exp["participants"]
                    )

                    st.markdown(
                        f"""
                        **{euro(exp["amount"])}** ·
                        {exp["description"]}

                        <small>
                        {format_date(exp["date"])} ·
                        Per {participants_text}
                        </small>
                        """,
                        unsafe_allow_html=True,
                    )

                    st.write("")


# ============================================================
# ELENCO SPESE
# ============================================================

with tab_expenses:

    if not expenses:

        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-icon">🧾</div>
                <div class="empty-title">
                    Nessuna spesa
                </div>
                <p>
                    Non ci sono ancora spese registrate.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    else:

        st.subheader(
            f"🧾 Spese · {expense_count}"
        )

        col_total, col_filter = st.columns(
            [1, 1]
        )

        with col_total:

            st.metric(
                "Totale",
                euro(total_amount),
            )

        with col_filter:

            payer_filter = st.selectbox(
                "Filtra per chi ha pagato",
                options=["Tutti"] + MEMBERS,
            )

        filtered_expenses = expenses

        if payer_filter != "Tutti":

            filtered_expenses = [
                exp
                for exp in expenses
                if exp["payer"] == payer_filter
            ]

        st.write("")

        # Più recenti prima
        filtered_expenses = sorted(
            filtered_expenses,
            key=lambda exp: (
                exp["date"] or date.min,
                exp["row_idx"],
            ),
            reverse=True,
        )

        for exp in filtered_expenses:

            col_info, col_amount, col_action = st.columns(
                [5, 2, 1]
            )

            with col_info:

                participants_text = ", ".join(
                    exp["participants"]
                )

                st.markdown(
                    f"""
                    <div class="expense-card">
                        <div class="expense-title">
                            {exp["description"]}
                        </div>

                        <div class="expense-meta">
                            👤 {exp["payer"]}
                            · 📅 {format_date(exp["date"])}
                        </div>

                        <div class="expense-meta">
                            👥 {participants_text}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with col_amount:

                st.markdown(
                    f"""
                    <div style="
                        padding-top: 1rem;
                        text-align: right;
                    ">
                        <div class="expense-amount">
                            {euro(exp["amount"])}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with col_action:

                if st.session_state.is_admin:

                    if st.button(
                        "🗑️",
                        key=f"delete_{exp['row_idx']}",
                        help="Elimina questa spesa",
                    ):

                        confirm_delete_dialog(
                            exp["row_idx"],
                            exp["description"],
                            exp["amount"],
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
                    "Le azioni qui sotto modificano definitivamente "
                    "i dati presenti nel foglio."
                )

                if st.button(
                    "🗑️ Svuota tutte le spese",
                    use_container_width=True,
                ):

                    confirm_clear_all_dialog(
                        expense_count,
                        total_amount,
                    )


# ============================================================
# AGGIUNGI SPESA
# ============================================================

with tab_add:

    if not st.session_state.is_admin:

        st.info(
            "🔐 Solo gli amministratori possono aggiungere o modificare le spese."
        )

        st.caption(
            "Inserisci la password nella sezione ⚙️ Impostazioni."
        )

    else:

        st.subheader("➕ Nuova spesa")

        st.caption(
            "Inserisci i dati della spesa. "
            "Il conguaglio verrà aggiornato automaticamente."
        )

        with st.form(
            "expense_form",
            clear_on_submit=True,
        ):

            expense_date = st.date_input(
                "📅 Data",
                value=date.today(),
            )

            payer = st.selectbox(
                "👤 Chi ha pagato?",
                options=MEMBERS,
            )

            description = st.text_input(
                "📝 Cosa?",
                placeholder="Es. Cena, benzina, spesa...",
            )

            amount = st.number_input(
                "💶 Importo",
                min_value=0.01,
                step=0.50,
                format="%.2f",
            )

            st.write(
                "**👥 Chi ha partecipato?**"
            )

            col_all, col_none = st.columns(2)

            with col_all:

                select_all = st.checkbox(
                    "Seleziona tutti",
                    value=True,
                )

            with col_none:

                deselect_all = st.checkbox(
                    "Nessuno",
                    value=False,
                )

            if deselect_all:

                default_participants = []

            elif select_all:

                default_participants = MEMBERS

            else:

                default_participants = []

            selected_participants = st.multiselect(
                "Partecipanti",
                options=MEMBERS,
                default=default_participants,
                label_visibility="collapsed",
            )

            st.divider()

            if selected_participants:

                share = (
                    amount
                    / len(selected_participants)
                )

                st.info(
                    f"💡 Quota per persona: "
                    f"**{euro(share)}** "
                    f"({len(selected_participants)} partecipanti)"
                )

            else:

                st.warning(
                    "Seleziona almeno un partecipante."
                )

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

                        save_expense_to_sheet(
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

                    except Exception as e:

                        st.error(
                            f"Errore durante il salvataggio: {e}"
                        )
