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
# CSS MINIMALE
#
# NIENTE colori fissi.
# NIENTE background nero/bianco.
#
# Il tema viene lasciato a Streamlit.
# ============================================================

st.markdown(
    """
    <style>

    /* Layout */

    .block-container {
        max-width: 1050px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    /* Titolo */

    .app-subtitle {
        opacity: 0.65;
        margin-top: -0.5rem;
        margin-bottom: 1.5rem;
    }

    /* Spaziatura */

    .section-space {
        height: 0.7rem;
    }

    /* Conguagli */

    .settlement-amount {
        font-size: 1.45rem;
        font-weight: 800;
        text-align: center;
        margin-top: 0.5rem;
    }

    .debtor {
        color: var(--red-text-color);
        font-weight: 700;
    }

    .creditor {
        color: var(--green-text-color);
        font-weight: 700;
    }

    .arrow {
        text-align: center;
        font-size: 1.5rem;
        opacity: 0.55;
        padding-top: 0.7rem;
    }

    /* Testo secondario */

    .muted {
        opacity: 0.65;
    }

    /* Mobile */

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
    """
    Formatta un numero in formato italiano.

    Esempio:
    2730.24 -> 2.730,24 €
    """

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
    """
    Converte un valore proveniente da Google Sheets
    in float.
    """

    if value is None or value == "":
        return 0.0

    if isinstance(value, (int, float)):
        return float(value)

    value = str(value).strip()
    value = value.replace("€", "").replace(" ", "")

    # Gestione formato italiano:
    # 1.234,56 -> 1234.56
    if "," in value:
        value = value.replace(".", "")
        value = value.replace(",", ".")

    try:
        return float(value)
    except ValueError:
        return 0.0


def parse_date(value):
    """
    Converte una data proveniente da Google Sheets.
    """

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
    """
    Formatta una data in formato italiano.
    """

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
# INIZIALIZZAZIONE / MIGRAZIONE GOOGLE SHEET
# ============================================================

def initialize_sheet():

    values = sheet.get_all_values()

    # Foglio completamente vuoto
    if not values:
        sheet.append_row(HEADERS)
        return

    current_headers = values[0]

    # --------------------------------------------------------
    # Vecchio formato:
    #
    # Chi ha pagato
    # Cosa
    # Importo
    # Partecipanti
    # --------------------------------------------------------

    old_headers = [
        "Chi ha pagato",
        "Cosa",
        "Importo",
        "Partecipanti",
    ]

    if current_headers == old_headers:

        old_rows = values[1:]

        migrated_rows = []

        for row in old_rows:

            row = row + [""] * (
                4 - len(row)
            )

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

    # Nuovo formato
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
                participant.strip()
                for participant in raw_participants.split(",")
                if participant.strip()
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
            f"Errore durante la lettura del Google Sheet: {error}"
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

    # Inizializza tutti i membri
    for member in MEMBERS:
        balances[member] = 0.0

    for expense in expenses:

        payer = expense["payer"]
        amount = expense["amount"]
        participants = expense["participants"]

        if not participants:
            continue

        share = amount / len(participants)

        # Chi ha pagato ha anticipato tutto
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

        amount = round(
            amount,
            2,
        )

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
# DIALOG: ELIMINA SPESA
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

    st.metric(
        "Importo",
        euro(expense["amount"]),
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
                    f"Errore: {error}"
                )

    with col2:

        if st.button(
            "Annulla",
            use_container_width=True,
        ):

            st.rerun()


# ============================================================
# DIALOG: ELIMINA TUTTO
# ============================================================

@st.dialog("⚠️ Svuota tutte le spese")
def clear_all_dialog(
    expense_count,
    total_amount,
):

    st.error(
        "Stai per eliminare tutte le spese."
    )

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "Spese",
            expense_count,
        )

    with col2:

        st.metric(
            "Totale",
            euro(total_amount),
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

    st.header("⚙️ Impostazioni")

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
            "Password admin",
            type="password",
            placeholder="Inserisci password",
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

    if st.session_state.is_admin:

        st.caption(
            "🔓 Puoi aggiungere, eliminare e gestire le spese."
        )

    else:

        st.caption(
            "👁️ Modalità sola lettura."
        )


# ============================================================
# HEADER
# ============================================================

st.title("💰 Spese di Gruppo")

st.markdown(
    '<div class="app-subtitle">'
    "Gestisci le spese e scopri automaticamente "
    "come pareggiare i conti."
    "</div>",
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
# TABS PRINCIPALI
# ============================================================

tab_dashboard, tab_expenses, tab_new = st.tabs(
    [
        "📊 Riepilogo",
        "🧾 Spese",
        "➕ Nuova spesa",
    ]
)


# ============================================================
# TAB 1 — RIEPILOGO
# ============================================================

with tab_dashboard:

    # --------------------------------------------------------
    # KPI
    # --------------------------------------------------------

    col1, col2, col3 = st.columns(3)

    with col1:

        with st.container(border=True):

            st.metric(
                "Totale speso",
                euro(total_amount),
            )

            st.caption(
                "Tutte le spese registrate"
            )

    with col2:

        with st.container(border=True):

            st.metric(
                "Spese",
                expense_count,
            )

            st.caption(
                "Spese registrate"
            )

    with col3:

        with st.container(border=True):

            st.metric(
                "Da saldare",
                len(settlements),
            )

            st.caption(
                "Trasferimenti necessari"
            )


    st.markdown(
        '<div class="section-space"></div>',
        unsafe_allow_html=True,
    )


    # --------------------------------------------------------
    # NESSUNA SPESA
    # --------------------------------------------------------

    if not expenses:

        st.info(
            "💸 Non ci sono ancora spese. "
            "Aggiungi la prima dalla scheda «Nuova spesa»."
        )


    else:

        # ====================================================
        # CONGUAGLI
        # ====================================================

        st.header("💸 Da saldare")

        st.caption(
            "I trasferimenti minimi necessari per pareggiare i conti."
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

                with st.container(border=True):

                    col1, col2, col3 = st.columns(
                        [2, 0.6, 2]
                    )

                    with col1:

                        st.caption(
                            "DEVE PAGARE"
                        )

                        st.markdown(
                            f'<div class="debtor">'
                            f"🔴 {debtor}"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

                    with col2:

                        st.markdown(
                            '<div class="arrow">→</div>',
                            unsafe_allow_html=True,
                        )

                    with col3:

                        st.caption(
                            "RICEVE"
                        )

                        st.markdown(
                            f'<div class="creditor">'
                            f"🟢 {creditor}"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

                    st.markdown(
                        f'<div class="settlement-amount">'
                        f"{euro(amount)}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )


        # ====================================================
        # SALDI
        # ====================================================

        st.header("👥 Situazione")

        st.caption(
            "Quanto ha anticipato e quanto dovrebbe aver sostenuto ogni persona."
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

        if not active_members:

            st.info(
                "Nessuna situazione da mostrare."
            )

        else:

            for person in active_members:

                balance = balances[person]

                if balance > 0.009:

                    status = "🟢 Riceve"
                    status_value = f"+{euro(balance)}"

                elif balance < -0.009:

                    status = "🔴 Deve"
                    status_value = euro(balance)

                else:

                    status = "⚪ In pari"
                    status_value = "0,00 €"

                with st.container(border=True):

                    col1, col2, col3 = st.columns(
                        [1.5, 1.5, 1]
                    )

                    with col1:

                        st.markdown(
                            f"### {person}"
                        )

                    with col2:

                        st.caption(
                            f"Pagato: {euro(payer_totals[person])}"
                        )

                        st.caption(
                            f"Quota: {euro(personal_shares[person])}"
                        )

                    with col3:

                        st.caption(
                            status
                        )

                        st.markdown(
                            f"**{status_value}**"
                        )


        # ====================================================
        # DETTAGLIO
        # ====================================================

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
                    st.write(person)

                with col2:
                    st.write(
                        euro(share)
                    )


        # ====================================================
        # TOTALE ANTICIPATO
        # ====================================================

        with st.expander(
            "💳 Totale anticipato da ogni persona"
        ):

            sorted_payers = sorted(
                payer_totals.items(),
                key=lambda item: item[1],
                reverse=True,
            )

            for person, total in sorted_payers:

                if total <= 0:
                    continue

                col1, col2 = st.columns(2)

                with col1:
                    st.write(person)

                with col2:
                    st.write(
                        euro(total)
                    )


# ============================================================
# TAB 2 — ELENCO SPESE
# ============================================================

with tab_expenses:

    st.header("🧾 Spese")

    if not expenses:

        st.info(
            "Non ci sono ancora spese registrate."
        )

    else:

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
                "Ordina per",
                [
                    "Più recenti",
                    "Più vecchie",
                    "Importo maggiore",
                    "Importo minore",
                ],
            )


        filtered_expenses = expenses.copy()


        # ----------------------------------------------------
        # FILTRO PAGATORE
        # ----------------------------------------------------

        if payer_filter != "Tutti":

            filtered_expenses = [
                expense
                for expense in filtered_expenses
                if expense["payer"] == payer_filter
            ]


        # ----------------------------------------------------
        # ORDINAMENTO
        # ----------------------------------------------------

        if sort_order == "Più recenti":

            filtered_expenses.sort(
                key=lambda expense:
                    expense["date"] or date.min,
                reverse=True,
            )

        elif sort_order == "Più vecchie":

            filtered_expenses.sort(
                key=lambda expense:
                    expense["date"] or date.min
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
                    expense["amount"]
            )


        # ----------------------------------------------------
        # RISULTATO FILTRO
        # ----------------------------------------------------

        st.caption(
            f"{len(filtered_expenses)} "
            f"spese visualizzate"
        )


        # ----------------------------------------------------
        # LISTA
        # ----------------------------------------------------

        for expense in filtered_expenses:

            with st.container(border=True):

                col1, col2, col3 = st.columns(
                    [4, 1.3, 0.6]
                )

                with col1:

                    st.markdown(
                        f"**{expense['description']}**"
                    )

                    participants = ", ".join(
                        expense["participants"]
                    )

                    st.caption(
                        f"👤 {expense['payer']} · "
                        f"📅 {format_date(expense['date'])}"
                    )

                    st.caption(
                        f"👥 {participants}"
                    )

                with col2:

                    st.markdown(
                        f"**{euro(expense['amount'])}**"
                    )

                with col3:

                    if st.session_state.is_admin:

                        if st.button(
                            "🗑️",
                            key=f"delete_{expense['row_idx']}",
                            help="Elimina spesa",
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

            st.metric(
                "Numero",
                len(filtered_expenses),
            )

        with col2:

            st.caption(
                "Totale visualizzato"
            )

            st.metric(
                "Totale",
                euro(filtered_total),
            )


        # ----------------------------------------------------
        # GESTIONE ADMIN
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
# TAB 3 — NUOVA SPESA
# ============================================================

with tab_new:

    if not st.session_state.is_admin:

        st.header("🔐 Nuova spesa")

        st.info(
            "Accedi come amministratore dalla sidebar "
            "per poter aggiungere una spesa."
        )

    else:

        st.header("➕ Nuova spesa")

        st.caption(
            "Inserisci i dettagli della spesa."
        )

        # ----------------------------------------------------
        # FORM
        # ----------------------------------------------------

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
                placeholder=(
                    "Cena, benzina, supermercato..."
                ),
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


            st.divider()


            # ------------------------------------------------
            # PARTECIPANTI
            # ------------------------------------------------

            st.subheader(
                "👥 Chi partecipa?"
            )

            selection_mode = st.radio(
                "Modalità",
                [
                    "Tutti",
                    "Seleziona manualmente",
                ],
                horizontal=True,
                label_visibility="collapsed",
            )


            if selection_mode == "Tutti":

                selected_participants = MEMBERS.copy()

            else:

                selected_participants = st.multiselect(
                    "Partecipanti",
                    MEMBERS,
                    placeholder=(
                        "Seleziona le persone coinvolte..."
                    ),
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
                    f"{len(selected_participants)} "
                    f"partecipanti"
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


        # ----------------------------------------------------
        # GESTIONE SUBMIT
        # ----------------------------------------------------

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
                        expense_date=expense_date,
                        payer=payer,
                        description=description.strip(),
                        amount=amount,
                        participants=selected_participants,
                    )

                    st.success(
                        f"Spesa di {euro(amount)} salvata! 🎉"
                    )

                    st.rerun()

                except Exception as error:

                    st.error(
                        f"Errore durante il salvataggio: {error}"
                    )
