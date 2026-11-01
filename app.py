
# ==============================================
# DLP2 - APPLICATION WEB STREAMLIT
# ==============================================
# Installation : pip install streamlit pandas requests
# Lancement   : streamlit run app.py
# ==============================================

import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime

# ============================================
# CONFIG PAGE
# ============================================
st.set_page_config(
    page_title="DLP2 - Suivi Ops",
    page_icon="🚚",
    layout="wide"
)

# ============================================
# WEBHOOKS SLACK PAR DSP
# ============================================
# 👇 REMPLACE les URLs par tes vrais webhooks Slack
# Pour créer un webhook :
#   1. Va sur https://api.slack.com/apps
#   2. Crée une app → Incoming Webhooks → Activate
#   3. Add New Webhook to Workspace → choisis le canal du DSP
#   4. Copie l'URL et colle-la ici

SLACK_WEBHOOKS = {
    # "Nom du DSP": "https://hooks.slack.com/services/T.../B.../xxx",
    # Exemples :
    # "TMFOP": "https://hooks.slack.com/services/T123/B456/abcdef",
    # "PRIME": "https://hooks.slack.com/services/T123/B789/ghijkl",
    # Ajoute une ligne par DSP ↓
}

def envoyer_slack(webhook_url, message):
    """Envoie un message via webhook Slack."""
    try:
        payload = {"text": message}
        response = requests.post(
            webhook_url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        st.error(f"Erreur d'envoi : {e}")
        return False


# ============================================
# INITIALISER LE STOCKAGE DES FEEDBACKS
# ============================================
if 'feedbacks' not in st.session_state:
    st.session_state.feedbacks = {}
if 'sent_messages' not in st.session_state:
    st.session_state.sent_messages = {}

# ============================================
# FONCTIONS UTILITAIRES
# ============================================
def get_route_type(svc):
    if pd.isna(svc):
        return "-"
    s = str(svc).lower()
    if "nursery route level 1" in s:
        return "Nursery 1"
    elif "nursery route level 2" in s:
        return "Nursery 2"
    elif "nursery route level 3" in s:
        return "Nursery 3"
    elif "nursery route level 4" in s:
        return "Nursery 4"
    elif "cargo electric bicycle" in s:
        return "Cargo Bike"
    elif "park and walk" in s:
        return "Park & Walk"
    elif "standard parcel" in s:
        return "Standard"
    else:
        return "-"


def get_top_reasons(packages_df, route_code):
    subset = packages_df[
        packages_df["RouteCode"] == route_code
    ]
    if subset.empty:
        return "-"
    counts = subset["ReasonCode"].value_counts()
    parts = []
    for reason, count in counts.items():
        parts.append(f"{reason}: {count}")
    return " | ".join(parts)


def count_reason(packages_df, route_code, reason):
    subset = packages_df[
        (packages_df["RouteCode"] == route_code)
        & (packages_df["ReasonCode"] == reason)
    ]
    return len(subset)


def afficher_tableau_avec_feedback(df, section_key):
    """
    Affiche un tableau éditable avec colonne Feedback DSP.
    """
    df = df.copy()
    df["💬 Feedback DSP"] = ""

    for idx, row in df.iterrows():
        route_id = str(row.get("Route", idx))
        fb_key = f"{section_key}_{route_id}"
        if fb_key in st.session_state.feedbacks:
            df.at[idx, "💬 Feedback DSP"] = (
                st.session_state.feedbacks[fb_key]
            )

    edited = st.data_editor(
        df,
        column_config={
            "💬 Feedback DSP": st.column_config.TextColumn(
                "💬 Feedback DSP",
                help="Saisir le feedback envoyé au DSP sur Slack",
                max_chars=500,
                width="large",
            ),
        },
        disabled=[
            col for col in df.columns
            if col != "💬 Feedback DSP"
        ],
        hide_index=True,
        width='stretch',
        key=f"editor_{section_key}"
    )

    for idx, row in edited.iterrows():
        route_id = str(row.get("Route", idx))
        fb_key = f"{section_key}_{route_id}"
        feedback = row.get("💬 Feedback DSP", "")
        if feedback and str(feedback).strip():
            st.session_state.feedbacks[fb_key] = (
                str(feedback).strip()
            )

    return edited


def build_slack_message(dsp_name, behind_df,
                        atrisk_df, retours_df,
                        packages_df, drt):
    now = datetime.now().strftime("%d/%m/%Y")
    msg = (
        f"*DLP2 - {now}* - DSP : *{dsp_name}*\n\n"
    )

    if not behind_df.empty:
        msg += "*BEHIND :*\n"
        for _, r in behind_df.iterrows():
            rc = r["Code de la route"]
            rt = drt.get(rc, "")
            left = r.get("arrêts non démarrés", "?")
            nb = r.get("retours", 0)
            line = f"  - {rc} [{rt}] : {left} restants"
            if nb > 0:
                line += f" | {nb} retour(s)"
            msg += line + "\n"
        msg += "\n"
    else:
        msg += "Aucune BEHIND\n\n"

    if not atrisk_df.empty:
        msg += "*AT_RISK :*\n"
        for _, r in atrisk_df.iterrows():
            rc = r["Code de la route"]
            rt = drt.get(rc, "")
            left = r.get("arrêts non démarrés", "?")
            nb = r.get("retours", 0)
            line = f"  - {rc} [{rt}] : {left} restants"
            if nb > 0:
                line += f" | {nb} retour(s)"
            msg += line + "\n"
        msg += "\n"
    else:
        msg += "Aucune AT_RISK\n\n"

    if not retours_df.empty:
        msg += "*10+ retours :*\n"
        for _, r in retours_df.iterrows():
            rc = r["Code de la route"]
            rt = drt.get(rc, "")
            nb = r.get("retours", 0)
            msg += f"  - {rc} [{rt}] : *{nb} retours*\n"
    else:
        msg += "Aucune 10+ retours"

    return msg


# ============================================
# STYLE CSS
# ============================================
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg,
            #003366, #004080);
        color: white;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 20px;
    }
    .metric-card {
        background: white;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    .behind-badge {
        background-color: #C00000;
        color: white;
        padding: 3px 10px;
        border-radius: 5px;
        font-weight: bold;
    }
    .atrisk-badge {
        background-color: #FF8C00;
        color: white;
        padding: 3px 10px;
        border-radius: 5px;
        font-weight: bold;
    }
    .retour-badge {
        background-color: #C05000;
        color: white;
        padding: 3px 10px;
        border-radius: 5px;
        font-weight: bold;
    }
    .slack-box {
        background-color: #F2EDF6;
        border: 1px solid #8B008B;
        border-radius: 10px;
        padding: 15px;
        font-family: monospace;
        white-space: pre-wrap;
    }
    .sent-ok {
        background-color: #E8F5E9;
        border: 2px solid #4CAF50;
        border-radius: 10px;
        padding: 10px;
        text-align: center;
        font-weight: bold;
        color: #2E7D32;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 14px;
        font-weight: bold;
    }
    .feedback-summary {
        background-color: #E8F5E9;
        border: 1px solid #4CAF50;
        border-radius: 10px;
        padding: 15px;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)


# ============================================
# HEADER
# ============================================
st.markdown("""
<div class="main-header">
    <h1>🚚 DLP2 - Suivi Ops Journalier</h1>
    <p>Analyse des routes BEHIND, AT_RISK
    et 10+ retours par DSP</p>
</div>
""", unsafe_allow_html=True)


# ============================================
# SIDEBAR : UPLOAD + CONFIG WEBHOOKS
# ============================================
st.sidebar.header("📁 Charger les extracts")

file_routes = st.sidebar.file_uploader(
    "1. Extract ROUTES (CSV)",
    type=["csv"],
    key="routes"
)
file_packages = st.sidebar.file_uploader(
    "2. Extract PACKAGES (CSV)",
    type=["csv"],
    key="packages"
)
file_itin = st.sidebar.file_uploader(
    "3. Extract ITINÉRAIRES (CSV) - optionnel",
    type=["csv"],
    key="itin"
)

# Section config webhooks dans la sidebar
st.sidebar.markdown("---")
st.sidebar.header("⚙️ Config Slack")
st.sidebar.caption(
    "Colle les webhooks Slack de chaque DSP "
    "pour activer l'envoi automatique."
)

# Permettre d'ajouter des webhooks dynamiquement
if 'custom_webhooks' not in st.session_state:
    st.session_state.custom_webhooks = {}

with st.sidebar.expander("➕ Ajouter un webhook DSP"):
    new_dsp = st.text_input(
        "Nom du DSP",
        key="new_dsp_name"
    )
    new_webhook = st.text_input(
        "URL Webhook Slack",
        key="new_webhook_url",
        type="password"
    )
    if st.button("✅ Enregistrer", key="save_webhook"):
        if new_dsp and new_webhook:
            st.session_state.custom_webhooks[
                new_dsp.strip()
            ] = new_webhook.strip()
            st.success(f"Webhook {new_dsp} enregistré !")
        else:
            st.warning("Remplis les 2 champs")

# Fusionner webhooks codés en dur + dynamiques
all_webhooks = {**SLACK_WEBHOOKS}
all_webhooks.update(st.session_state.custom_webhooks)

if all_webhooks:
    st.sidebar.markdown("**Webhooks configurés :**")
    for dsp_name in all_webhooks:
        st.sidebar.markdown(f"  ✅ {dsp_name}")
else:
    st.sidebar.info(
        "Aucun webhook configuré. "
        "L'envoi Slack sera désactivé."
    )


if file_routes is None or file_packages is None:
    st.info(
        "👈 Chargez vos fichiers CSV dans la "
        "barre latérale pour lancer l'analyse."
    )
    st.markdown("### 📋 Mode d'emploi")
    st.markdown("""
    1. **Glissez-déposez** vos 3 fichiers CSV
    2. L'analyse se lance **automatiquement**
    3. Naviguez entre les onglets par DSP
    4. **Saisissez vos feedbacks** dans la colonne 💬
    5. Cliquez **📤 Envoyer sur Slack** pour envoyer
       le message directement au canal du DSP
    6. **Exportez** les feedbacks en CSV
    """)

    st.markdown("### ⚙️ Configuration Slack")
    st.markdown("""
    Pour activer l'envoi automatique :
    1. Va sur **api.slack.com/apps** → **Create New App**
    2. Choisis **From scratch** → nomme-la "DLP2 Bot"
    3. Va dans **Incoming Webhooks** → **Activate**
    4. Clique **Add New Webhook to Workspace**
    5. Choisis le **canal du DSP** → **Autoriser**
    6. Copie l'**URL du webhook**
    7. Colle-la dans la barre latérale ⚙️ Config Slack
    8. **Répète** pour chaque canal DSP
    """)
    st.stop()


# ============================================
# CHARGEMENT DES DONNÉES
# ============================================
try:
    routes = pd.read_csv(file_routes, encoding="latin-1")
except Exception:
    routes = pd.read_csv(file_routes, encoding="utf-8")

try:
    packages = pd.read_csv(file_packages, encoding="latin-1")
except Exception:
    packages = pd.read_csv(file_packages, encoding="utf-8")

routes.columns = routes.columns.str.strip()
packages.columns = packages.columns.str.strip()

routes["Type"] = routes[
    "Type de service de livraison"
].apply(get_route_type)

drt = dict(zip(
    routes["Code de la route"],
    routes["Type"]
))

retours_count = packages.groupby(
    "RouteCode"
).size().reset_index(name="retours")

routes = routes.merge(
    retours_count,
    left_on="Code de la route",
    right_on="RouteCode",
    how="left"
)
routes["retours"] = routes["retours"].fillna(0).astype(int)

behind = routes[
    routes["Progression de la route"] == "BEHIND"
].copy()
atrisk = routes[
    routes["Progression de la route"] == "AT_RISK"
].copy()
retours10 = routes[routes["retours"] >= 10].copy()

dsps = sorted(routes["DSP"].unique())
now_str = datetime.now().strftime("%d/%m/%Y %H:%M")


# ============================================
# MÉTRIQUES GLOBALES
# ============================================
st.markdown(f"**Analyse du {now_str}**")

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("🔴 BEHIND", len(behind))
with col2:
    st.metric("🟠 AT_RISK", len(atrisk))
with col3:
    st.metric("📦 10+ Retours", len(retours10))
with col4:
    st.metric("📊 Total Routes", len(routes))
with col5:
    st.metric("🏢 DSP", len(dsps))


# ============================================
# ONGLETS
# ============================================
tab_names = (
    ["📊 Résumé Global"]
    + [f"🏢 {d}" for d in dsps]
    + ["📝 Tous les Feedbacks"]
)
tabs = st.tabs(tab_names)


# ============================================
# ONGLET RÉSUMÉ GLOBAL
# ============================================
with tabs[0]:
    st.markdown("## 📊 Résumé Global")

    # BEHIND
    st.markdown(
        '<span class="behind-badge">'
        'ROUTES EN RETARD (BEHIND)</span>',
        unsafe_allow_html=True
    )
    if not behind.empty:
        display_behind = behind[[
            "Code de la route", "DSP", "Type",
            "Tous les arrêts", "Arrêts effectués",
            "arrêts non démarrés",
            "livraisons au total", "retours"
        ]].copy()
        display_behind.columns = [
            "Route", "DSP", "Type", "Arrêts",
            "Effectués", "Restants",
            "Livraisons", "Retours"
        ]
        afficher_tableau_avec_feedback(
            display_behind, "global_behind"
        )
    else:
        st.success("✅ Aucune route en retard")

    st.markdown("---")

    # AT_RISK
    st.markdown(
        '<span class="atrisk-badge">'
        'ROUTES A RISQUE (AT_RISK)</span>',
        unsafe_allow_html=True
    )
    if not atrisk.empty:
        display_atrisk = atrisk[[
            "Code de la route", "DSP", "Type",
            "Tous les arrêts", "Arrêts effectués",
            "arrêts non démarrés",
            "livraisons au total", "retours"
        ]].copy()
        display_atrisk.columns = [
            "Route", "DSP", "Type", "Arrêts",
            "Effectués", "Restants",
            "Livraisons", "Retours"
        ]
        afficher_tableau_avec_feedback(
            display_atrisk, "global_atrisk"
        )
    else:
        st.success("✅ Aucune route à risque")

    st.markdown("---")

    # 10+ RETOURS
    st.markdown(
        '<span class="retour-badge">'
        'ROUTES AVEC 10+ RETOURS</span>',
        unsafe_allow_html=True
    )
    if not retours10.empty:
        reasons_list = [
            "CUSTOMER UNAVAILABLE",
            "BUSINESS CLOSED",
            "ADDRESS NOT FOUND",
            "INACCESSIBLE DELIVERY LOCATION",
            "RESCHEDULED BY CUSTOMER",
            "LOCKER ISSUE"
        ]
        rows = []
        for _, r in retours10.iterrows():
            rc = r["Code de la route"]
            row = {
                "Route": rc,
                "DSP": r["DSP"],
                "Type": r["Type"],
                "Progression": r[
                    "Progression de la route"],
                "Retours": r["retours"]
            }
            total_known = 0
            for reason in reasons_list:
                c = count_reason(packages, rc, reason)
                short = reason.split()[0][:8]
                row[short] = c
                total_known += c
            row["Autres"] = r["retours"] - total_known
            rows.append(row)
        afficher_tableau_avec_feedback(
            pd.DataFrame(rows), "global_retours"
        )
    else:
        st.success("✅ Aucune route avec 10+ retours")

    # Bilan par DSP
    st.markdown("---")
    st.markdown("### 📋 Bilan par DSP")
    bilan_rows = []
    for dsp in dsps:
        dsp_routes = routes[routes["DSP"] == dsp]
        nb_behind = len(dsp_routes[
            dsp_routes[
                "Progression de la route"
            ] == "BEHIND"
        ])
        nb_atrisk = len(dsp_routes[
            dsp_routes[
                "Progression de la route"
            ] == "AT_RISK"
        ])
        nb_ret10 = len(dsp_routes[
            dsp_routes["retours"] >= 10
        ])
        total_ret = dsp_routes["retours"].sum()
        bilan_rows.append({
            "DSP": dsp,
            "BEHIND": nb_behind,
            "AT_RISK": nb_atrisk,
            "10+ Retours": nb_ret10,
            "Total Retours": int(total_ret)
        })
    st.dataframe(
        pd.DataFrame(bilan_rows),
        width='stretch',
        hide_index=True
    )

    # BOUTON ENVOI GLOBAL
    st.markdown("---")
    st.markdown("### 📤 Envoi groupé Slack")
    if all_webhooks:
        if st.button(
            "📤 Envoyer à TOUS les DSP",
            key="send_all",
            type="primary"
        ):
            sent = 0
            failed = 0
            for dsp in dsps:
                if dsp in all_webhooks:
                    dsp_r = routes[routes["DSP"] == dsp]
                    dsp_b = dsp_r[
                        dsp_r["Progression de la route"]
                        == "BEHIND"
                    ]
                    dsp_a = dsp_r[
                        dsp_r["Progression de la route"]
                        == "AT_RISK"
                    ]
                    dsp_10 = dsp_r[dsp_r["retours"] >= 10]

                    if (dsp_b.empty and dsp_a.empty
                            and dsp_10.empty):
                        continue

                    msg = build_slack_message(
                        dsp, dsp_b, dsp_a,
                        dsp_10, packages, drt
                    )
                    ok = envoyer_slack(
                        all_webhooks[dsp], msg
                    )
                    if ok:
                        sent += 1
                    else:
                        failed += 1

            if sent > 0:
                st.success(
                    f"✅ {sent} message(s) envoyé(s) !"
                )
            if failed > 0:
                st.error(
                    f"❌ {failed} échec(s) d'envoi"
                )
    else:
        st.warning(
            "⚙️ Configure les webhooks Slack dans "
            "la barre latérale pour activer l'envoi."
        )


# ============================================
# ONGLETS PAR DSP
# ============================================
for idx, dsp in enumerate(dsps):
    with tabs[idx + 1]:
        st.markdown(f"## 🏢 {dsp}")
        st.caption(f"Analyse du {now_str}")

        dsp_routes = routes[
            routes["DSP"] == dsp
        ].copy()
        dsp_behind = dsp_routes[
            dsp_routes[
                "Progression de la route"
            ] == "BEHIND"
        ]
        dsp_atrisk = dsp_routes[
            dsp_routes[
                "Progression de la route"
            ] == "AT_RISK"
        ]
        dsp_ret10 = dsp_routes[
            dsp_routes["retours"] >= 10
        ]

        # Métriques DSP
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("🔴 BEHIND", len(dsp_behind))
        with c2:
            st.metric("🟠 AT_RISK", len(dsp_atrisk))
        with c3:
            st.metric("📦 10+ Ret.", len(dsp_ret10))
        with c4:
            st.metric(
                "📊 Total Ret.",
                int(dsp_routes["retours"].sum())
            )

        # BEHIND
        st.markdown(
            '<span class="behind-badge">'
            'ROUTES EN RETARD (BEHIND)</span>',
            unsafe_allow_html=True
        )
        if not dsp_behind.empty:
            df_b = dsp_behind[[
                "Code de la route", "Type",
                "Tous les arrêts",
                "Arrêts effectués",
                "arrêts non démarrés",
                "livraisons au total", "retours"
            ]].copy()
            df_b.columns = [
                "Route", "Type", "Arrêts",
                "Effectués", "Restants",
                "Livraisons", "Retours"
            ]
            afficher_tableau_avec_feedback(
                df_b, f"dsp_{dsp}_behind"
            )
        else:
            st.success("✅ Aucune route en retard")

        # AT_RISK
        st.markdown(
            '<span class="atrisk-badge">'
            'ROUTES A RISQUE (AT_RISK)</span>',
            unsafe_allow_html=True
        )
        if not dsp_atrisk.empty:
            df_a = dsp_atrisk[[
                "Code de la route", "Type",
                "Tous les arrêts",
                "Arrêts effectués",
                "arrêts non démarrés",
                "livraisons au total", "retours"
            ]].copy()
            df_a.columns = [
                "Route", "Type", "Arrêts",
                "Effectués", "Restants",
                "Livraisons", "Retours"
            ]
            afficher_tableau_avec_feedback(
                df_a, f"dsp_{dsp}_atrisk"
            )
        else:
            st.success("✅ Aucune route à risque")

        # 10+ RETOURS
        st.markdown(
            '<span class="retour-badge">'
            'ROUTES AVEC 10+ RETOURS</span>',
            unsafe_allow_html=True
        )
        if not dsp_ret10.empty:
            rows_r = []
            for _, r in dsp_ret10.iterrows():
                rc = r["Code de la route"]
                rows_r.append({
                    "Route": rc,
                    "Type": r["Type"],
                    "Progression": r[
                        "Progression de la route"],
                    "Retours": r["retours"],
                    "Raisons": get_top_reasons(
                        packages, rc)
                })
            afficher_tableau_avec_feedback(
                pd.DataFrame(rows_r),
                f"dsp_{dsp}_retours"
            )
        else:
            st.success(
                "✅ Aucune route avec 10+ retours"
            )

        # DETAIL RETOURS
        st.markdown("---")
        st.markdown("### 📋 Détail des retours")
        dsp_route_codes = dsp_routes[
            "Code de la route"
        ].unique()
        dsp_packages = packages[
            packages["RouteCode"].isin(
                dsp_route_codes)
        ]
        if not dsp_packages.empty:
            prog_map = dict(zip(
                dsp_routes["Code de la route"],
                dsp_routes[
                    "Progression de la route"]
            ))
            df_det = dsp_packages[[
                "RouteCode", "ScannableId",
                "Address", "ReasonCode"
            ]].copy()
            df_det.insert(
                1, "Type",
                df_det["RouteCode"].map(drt)
            )
            df_det.insert(
                2, "Progression",
                df_det["RouteCode"].map(prog_map)
            )
            df_det.columns = [
                "Route", "Type", "Progression",
                "Scannable ID", "Adresse", "Raison"
            ]
            st.dataframe(
                df_det,
                width='stretch',
                hide_index=True
            )
        else:
            st.info("Aucun retour pour ce DSP")

        # MESSAGE SLACK + BOUTON ENVOI
        st.markdown("---")
        st.markdown(
            "### 💬 Message Slack"
        )
        slack_msg = build_slack_message(
            dsp, dsp_behind, dsp_atrisk,
            dsp_ret10, packages, drt
        )

        # Aperçu du message
        st.markdown(
            f'<div class="slack-box">'
            f'{slack_msg}</div>',
            unsafe_allow_html=True
        )

        # Boutons côte à côte
        btn_col1, btn_col2 = st.columns(2)

        with btn_col1:
            st.code(slack_msg, language=None)

        with btn_col2:
            # Vérifier si webhook existe pour ce DSP
            dsp_has_webhook = dsp in all_webhooks
            already_sent = dsp in (
                st.session_state.sent_messages
            )

            if dsp_has_webhook:
                if already_sent:
                    st.markdown(
                        '<div class="sent-ok">'
                        '✅ Message envoyé à '
                        f'{st.session_state.sent_messages[dsp]}'
                        '</div>',
                        unsafe_allow_html=True
                    )
                    # Bouton pour renvoyer
                    if st.button(
                        "🔄 Renvoyer",
                        key=f"resend_{dsp}"
                    ):
                        ok = envoyer_slack(
                            all_webhooks[dsp],
                            slack_msg
                        )
                        if ok:
                            st.session_state.sent_messages[
                                dsp
                            ] = datetime.now().strftime(
                                "%H:%M"
                            )
                            st.success("✅ Renvoyé !")
                            st.rerun()
                else:
                    if st.button(
                        f"📤 Envoyer sur Slack → #{dsp}",
                        key=f"send_{dsp}",
                        type="primary"
                    ):
                        ok = envoyer_slack(
                            all_webhooks[dsp],
                            slack_msg
                        )
                        if ok:
                            st.session_state.sent_messages[
                                dsp
                            ] = datetime.now().strftime(
                                "%H:%M"
                            )
                            st.success(
                                f"✅ Message envoyé "
                                f"sur #{dsp} !"
                            )
                            st.rerun()
                        else:
                            st.error(
                                "❌ Échec de l'envoi. "
                                "Vérifie le webhook."
                            )
            else:
                st.warning(
                    f"⚙️ Pas de webhook pour {dsp}. "
                    f"Configure-le dans la barre "
                    f"latérale."
                )


# ============================================
# ONGLET TOUS LES FEEDBACKS
# ============================================
with tabs[-1]:
    st.markdown("## 📝 Tous les Feedbacks DSP")

    if st.session_state.feedbacks:
        fb_rows = []
        for fb_key, fb_text in (
            st.session_state.feedbacks.items()
        ):
            parts = fb_key.split("_", 2)
            if len(parts) >= 3:
                section = parts[1]
                route = parts[2]
            else:
                section = "-"
                route = fb_key
            fb_rows.append({
                "Route": route,
                "Section": section,
                "Feedback DSP": fb_text,
                "Date": datetime.now().strftime(
                    "%d/%m/%Y"
                )
            })

        fb_df = pd.DataFrame(fb_rows)

        c1, c2 = st.columns(2)
        c1.metric("💬 Total feedbacks", len(fb_df))
        c2.metric(
            "🏢 DSP concernés",
            fb_df["Section"].nunique()
        )

        st.dataframe(
            fb_df,
            width='stretch',
            hide_index=True
        )

        csv = fb_df.to_csv(
            index=False, sep=';'
        ).encode('utf-8-sig')
        st.download_button(
            label="📥 Exporter tous les feedbacks (CSV)",
            data=csv,
            file_name=(
                f"feedbacks_dsp_"
                f"{datetime.now().strftime('%Y%m%d')}"
                f".csv"
            ),
            mime="text/csv"
        )
    else:
        st.info(
            "Aucun feedback saisi pour le moment. "
            "Saisissez vos feedbacks dans la colonne "
            "💬 des tableaux de routes."
        )

    # Historique des envois Slack
    if st.session_state.sent_messages:
        st.markdown("---")
        st.markdown("### 📤 Historique des envois Slack")
        for dsp_name, heure in (
            st.session_state.sent_messages.items()
        ):
            st.markdown(
                f"  ✅ **{dsp_name}** — envoyé à {heure}"
            )


# ============================================
# FOOTER
# ============================================
st.markdown("---")
st.markdown(
    "<center><small>"
    "DLP2 - Suivi Ops Journalier | "
    "Développé pour l'équipe Dispatch"
    "</small></center>",
    unsafe_allow_html=True
)

