
# ==============================================
# DLP2 - APPLICATION WEB STREAMLIT v3
# ==============================================
# Nouveautés v3 :
#   - Colonne "Analyse de la route" à côté de Feedback DSP
#   - Section "Routes NA" (non tentés) dans chaque onglet
#   - Synchronisation auto vers Résumé Global
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
SLACK_WEBHOOKS = {}

def envoyer_slack(webhook_url, message):
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
# INITIALISER LE STOCKAGE
# ============================================
if 'feedbacks' not in st.session_state:
    st.session_state.feedbacks = {}
if 'sent_messages' not in st.session_state:
    st.session_state.sent_messages = {}
if 'dsp_feedbacks' not in st.session_state:
    st.session_state.dsp_feedbacks = {}
if 'dsp_analyses' not in st.session_state:
    st.session_state.dsp_analyses = {}
if 'routes_na' not in st.session_state:
    st.session_state.routes_na = {}

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
    subset = packages_df[packages_df["RouteCode"] == route_code]
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


def get_feedback_for_route(route_code):
    for fb_key, fb_text in st.session_state.dsp_feedbacks.items():
        if route_code in fb_key and fb_text:
            return fb_text
    return ""


def get_analyse_for_route(route_code):
    for a_key, a_text in st.session_state.dsp_analyses.items():
        if route_code in a_key and a_text:
            return a_text
    return ""


def afficher_tableau_avec_feedback(df, section_key, sync_to_global=False):
    df = df.copy()
    df["💬 Feedback DSP"] = ""
    df["🔍 Analyse de la route"] = ""

    for idx, row in df.iterrows():
        route_id = str(row.get("Route", idx))
        fb_key = f"{section_key}_{route_id}"

        # Charger feedback existant
        if fb_key in st.session_state.dsp_feedbacks:
            df.at[idx, "💬 Feedback DSP"] = st.session_state.dsp_feedbacks[fb_key]
        elif sync_to_global:
            fb = get_feedback_for_route(route_id)
            if fb:
                df.at[idx, "💬 Feedback DSP"] = fb

        # Charger analyse existante
        if fb_key in st.session_state.dsp_analyses:
            df.at[idx, "🔍 Analyse de la route"] = st.session_state.dsp_analyses[fb_key]
        elif sync_to_global:
            an = get_analyse_for_route(route_id)
            if an:
                df.at[idx, "🔍 Analyse de la route"] = an

    edited = st.data_editor(
        df,
        column_config={
            "💬 Feedback DSP": st.column_config.TextColumn(
                "💬 Feedback DSP",
                help="Feedback envoyé au DSP sur Slack",
                max_chars=500,
                width="large",
            ),
            "🔍 Analyse de la route": st.column_config.TextColumn(
                "🔍 Analyse de la route",
                help="Notre analyse interne de la route",
                max_chars=500,
                width="large",
            ),
        },
        disabled=[
            col for col in df.columns
            if col not in ["💬 Feedback DSP", "🔍 Analyse de la route"]
        ],
        hide_index=True,
        use_container_width=True,
        key=f"editor_{section_key}"
    )

    # Sauvegarder feedbacks et analyses
    for idx, row in edited.iterrows():
        route_id = str(row.get("Route", idx))
        fb_key = f"{section_key}_{route_id}"

        feedback = row.get("💬 Feedback DSP", "")
        if feedback and str(feedback).strip():
            st.session_state.dsp_feedbacks[fb_key] = str(feedback).strip()
            st.session_state.dsp_feedbacks[f"route_{route_id}"] = str(feedback).strip()

        analyse = row.get("🔍 Analyse de la route", "")
        if analyse and str(analyse).strip():
            st.session_state.dsp_analyses[fb_key] = str(analyse).strip()
            st.session_state.dsp_analyses[f"route_{route_id}"] = str(analyse).strip()

    return edited


def afficher_section_na(section_key, dsp_name=""):
    """Section Routes NA - routes avec non tentés."""
    st.markdown("#### ➕ Ajouter une route NA")

    na_key = f"na_{section_key}"

    col1, col2, col3, col4 = st.columns([2, 1, 3, 3])
    with col1:
        na_route = st.text_input("Code route", key=f"na_route_{section_key}")
    with col2:
        na_nb = st.number_input("Nb non tentés", min_value=0, value=0, key=f"na_nb_{section_key}")
    with col3:
        na_feedback = st.text_input("💬 Feedback DSP", key=f"na_fb_{section_key}")
    with col4:
        na_analyse = st.text_input("🔍 Analyse de la route", key=f"na_an_{section_key}")

    if st.button("➕ Ajouter", key=f"add_na_{section_key}"):
        if na_route.strip():
            if na_key not in st.session_state.routes_na:
                st.session_state.routes_na[na_key] = []
            st.session_state.routes_na[na_key].append({
                "Route": na_route.strip(),
                "DSP": dsp_name,
                "Nb non tentés": na_nb,
                "💬 Feedback DSP": na_feedback,
                "🔍 Analyse de la route": na_analyse,
            })
            # Synchroniser feedback et analyse
            if na_feedback.strip():
                st.session_state.dsp_feedbacks[f"route_{na_route.strip()}"] = na_feedback.strip()
            if na_analyse.strip():
                st.session_state.dsp_analyses[f"route_{na_route.strip()}"] = na_analyse.strip()
            st.success(f"✅ Route {na_route} ajoutée !")
            st.rerun()
        else:
            st.warning("Saisis un code route")

    # Afficher les routes NA existantes
    if na_key in st.session_state.routes_na and st.session_state.routes_na[na_key]:
        na_df = pd.DataFrame(st.session_state.routes_na[na_key])

        edited_na = st.data_editor(
            na_df,
            column_config={
                "💬 Feedback DSP": st.column_config.TextColumn(
                    "💬 Feedback DSP",
                    help="Feedback envoyé au DSP",
                    max_chars=500,
                    width="large",
                ),
                "🔍 Analyse de la route": st.column_config.TextColumn(
                    "🔍 Analyse de la route",
                    help="Notre analyse interne",
                    max_chars=500,
                    width="large",
                ),
            },
            disabled=["Route", "DSP"],
            hide_index=True,
            use_container_width=True,
            key=f"editor_na_{section_key}"
        )

        # Sauvegarder les modifications
        st.session_state.routes_na[na_key] = edited_na.to_dict('records')
        for _, row in edited_na.iterrows():
            route_id = str(row.get("Route", ""))
            fb = row.get("💬 Feedback DSP", "")
            an = row.get("🔍 Analyse de la route", "")
            if fb and str(fb).strip():
                st.session_state.dsp_feedbacks[f"route_{route_id}"] = str(fb).strip()
            if an and str(an).strip():
                st.session_state.dsp_analyses[f"route_{route_id}"] = str(an).strip()

        if st.button("🗑️ Vider les routes NA", key=f"clear_na_{section_key}"):
            st.session_state.routes_na[na_key] = []
            st.rerun()
    else:
        st.info("Aucune route NA saisie pour le moment.")


def get_all_na_routes():
    """Récupère toutes les routes NA de tous les onglets."""
    all_na = []
    for na_key, na_list in st.session_state.routes_na.items():
        for item in na_list:
            all_na.append(item)
    return all_na


def build_slack_message(dsp_name, behind_df, atrisk_df, retours_df, packages_df, drt, na_routes=None):
    now = datetime.now().strftime("%d/%m/%Y")
    msg = f"*DLP2 - {now}* - DSP : *{dsp_name}*\n\n"

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
        msg += "\n"
    else:
        msg += "Aucune 10+ retours\n\n"

    # Routes NA
    if na_routes:
        dsp_na = [r for r in na_routes if r.get("DSP", "") == dsp_name]
        if dsp_na:
            msg += "*Routes NA (non tentés) :*\n"
            for r in dsp_na:
                msg += f"  - {r['Route']} : *{r['Nb non tentés']} non tentés*\n"

    return msg


def build_sharepoint_summary(routes, behind, atrisk, retours10, packages, drt, dsps):
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    all_na = get_all_na_routes()

    html = f"""<h2>📊 DLP2 - Résumé Ops du {now}</h2>
<table border="1" cellpadding="5" cellspacing="0" style="border-collapse:collapse; font-family:Calibri; font-size:11pt;">
<tr style="background-color:#003366; color:white;">
<th>DSP</th><th>🔴 BEHIND</th><th>🟠 AT_RISK</th>
<th>📦 10+ Retours</th><th>⚪ NA</th><th>Total Retours</th>
</tr>"""

    for dsp in dsps:
        dsp_r = routes[routes["DSP"] == dsp]
        nb_b = len(dsp_r[dsp_r["Progression de la route"] == "BEHIND"])
        nb_a = len(dsp_r[dsp_r["Progression de la route"] == "AT_RISK"])
        nb_10 = len(dsp_r[dsp_r["retours"] >= 10])
        nb_na = len([r for r in all_na if r.get("DSP", "") == dsp])
        tot = int(dsp_r["retours"].sum())

        bg = ""
        if nb_b > 0:
            bg = ' style="background-color:#FFE0E0;"'
        elif nb_a > 0:
            bg = ' style="background-color:#FFF3E0;"'

        html += f"""<tr{bg}>
<td><b>{dsp}</b></td><td align="center">{nb_b}</td>
<td align="center">{nb_a}</td><td align="center">{nb_10}</td>
<td align="center">{nb_na}</td><td align="center">{tot}</td>
</tr>"""

    html += "</table>"

    # BEHIND détaillé
    if not behind.empty:
        html += """<br><h3 style="color:#C00000;">🔴 Routes en retard (BEHIND)</h3>
<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse; font-family:Calibri; font-size:10pt;">
<tr style="background-color:#C00000; color:white;">
<th>Route</th><th>DSP</th><th>Type</th><th>Restants</th><th>Retours</th>
<th>💬 Feedback DSP</th><th>🔍 Analyse</th></tr>"""
        for _, r in behind.iterrows():
            rc = r["Code de la route"]
            fb = get_feedback_for_route(rc)
            an = get_analyse_for_route(rc)
            html += f"""<tr><td>{rc}</td><td>{r['DSP']}</td><td>{drt.get(rc, '-')}</td>
<td align="center">{r.get('arrêts non démarrés', '?')}</td>
<td align="center">{r.get('retours', 0)}</td><td>{fb}</td><td>{an}</td></tr>"""
        html += "</table>"

    # AT_RISK détaillé
    if not atrisk.empty:
        html += """<br><h3 style="color:#FF8C00;">🟠 Routes à risque (AT_RISK)</h3>
<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse; font-family:Calibri; font-size:10pt;">
<tr style="background-color:#FF8C00; color:white;">
<th>Route</th><th>DSP</th><th>Type</th><th>Restants</th><th>Retours</th>
<th>💬 Feedback DSP</th><th>🔍 Analyse</th></tr>"""
        for _, r in atrisk.iterrows():
            rc = r["Code de la route"]
            fb = get_feedback_for_route(rc)
            an = get_analyse_for_route(rc)
            html += f"""<tr><td>{rc}</td><td>{r['DSP']}</td><td>{drt.get(rc, '-')}</td>
<td align="center">{r.get('arrêts non démarrés', '?')}</td>
<td align="center">{r.get('retours', 0)}</td><td>{fb}</td><td>{an}</td></tr>"""
        html += "</table>"

    # 10+ retours détaillé
    if not retours10.empty:
        html += """<br><h3 style="color:#C05000;">📦 Routes avec 10+ retours</h3>
<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse; font-family:Calibri; font-size:10pt;">
<tr style="background-color:#C05000; color:white;">
<th>Route</th><th>DSP</th><th>Type</th><th>Progression</th><th>Retours</th>
<th>💬 Feedback DSP</th><th>🔍 Analyse</th></tr>"""
        for _, r in retours10.iterrows():
            rc = r["Code de la route"]
            fb = get_feedback_for_route(rc)
            an = get_analyse_for_route(rc)
            html += f"""<tr><td>{rc}</td><td>{r['DSP']}</td><td>{drt.get(rc, '-')}</td>
<td>{r.get('Progression de la route', '-')}</td>
<td align="center">{r.get('retours', 0)}</td><td>{fb}</td><td>{an}</td></tr>"""
        html += "</table>"

    # Routes NA
    if all_na:
        html += """<br><h3 style="color:#607D8B;">⚪ Routes NA (non tentés)</h3>
<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse; font-family:Calibri; font-size:10pt;">
<tr style="background-color:#607D8B; color:white;">
<th>Route</th><th>DSP</th><th>Nb non tentés</th>
<th>💬 Feedback DSP</th><th>🔍 Analyse</th></tr>"""
        for r in all_na:
            html += f"""<tr><td>{r['Route']}</td><td>{r.get('DSP', '-')}</td>
<td align="center">{r.get('Nb non tentés', 0)}</td>
<td>{r.get('💬 Feedback DSP', '')}</td>
<td>{r.get('🔍 Analyse de la route', '')}</td></tr>"""
        html += "</table>"

    html += f"""<br><p style="color:gray; font-size:9pt;">
Généré automatiquement - DLP2 Suivi Ops - {now}</p>"""

    return html


# ============================================
# STYLE CSS
# ============================================
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #003366, #004080);
        color: white; padding: 20px; border-radius: 10px;
        text-align: center; margin-bottom: 20px;
    }
    .behind-badge {
        background-color: #C00000; color: white;
        padding: 3px 10px; border-radius: 5px; font-weight: bold;
    }
    .atrisk-badge {
        background-color: #FF8C00; color: white;
        padding: 3px 10px; border-radius: 5px; font-weight: bold;
    }
    .retour-badge {
        background-color: #C05000; color: white;
        padding: 3px 10px; border-radius: 5px; font-weight: bold;
    }
    .na-badge {
        background-color: #607D8B; color: white;
        padding: 3px 10px; border-radius: 5px; font-weight: bold;
    }
    .slack-box {
        background-color: #F2EDF6; border: 1px solid #8B008B;
        border-radius: 10px; padding: 15px;
        font-family: monospace; white-space: pre-wrap;
    }
    .sent-ok {
        background-color: #E8F5E9; border: 2px solid #4CAF50;
        border-radius: 10px; padding: 10px;
        text-align: center; font-weight: bold; color: #2E7D32;
    }
    .sharepoint-box {
        background-color: #E3F2FD; border: 2px solid #1565C0;
        border-radius: 10px; padding: 15px; margin: 10px 0;
    }
    .sync-info {
        background-color: #FFF8E1; border: 1px solid #FFC107;
        border-radius: 8px; padding: 10px; font-size: 0.9em;
    }
</style>
""", unsafe_allow_html=True)


# ============================================
# HEADER
# ============================================
st.markdown("""
<div class="main-header">
    <h1>🚚 DLP2 - Suivi Ops Journalier</h1>
    <p>Analyse des routes BEHIND, AT_RISK, 10+ retours et NA par DSP</p>
</div>
""", unsafe_allow_html=True)


# ============================================
# SIDEBAR
# ============================================
st.sidebar.header("📁 Charger les extracts")

file_routes = st.sidebar.file_uploader("1. Extract ROUTES (CSV)", type=["csv"], key="routes")
file_packages = st.sidebar.file_uploader("2. Extract PACKAGES (CSV)", type=["csv"], key="packages")
file_itin = st.sidebar.file_uploader("3. Extract ITINÉRAIRES (CSV) - optionnel", type=["csv"], key="itin")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Config Slack")
st.sidebar.caption("Colle les webhooks Slack de chaque DSP pour activer l'envoi automatique.")

if 'custom_webhooks' not in st.session_state:
    st.session_state.custom_webhooks = {}

with st.sidebar.expander("➕ Ajouter un webhook DSP"):
    new_dsp = st.text_input("Nom du DSP", key="new_dsp_name")
    new_webhook = st.text_input("URL Webhook Slack", key="new_webhook_url", type="password")
    if st.button("✅ Enregistrer", key="save_webhook"):
        if new_dsp and new_webhook:
            st.session_state.custom_webhooks[new_dsp.strip()] = new_webhook.strip()
            st.success(f"Webhook {new_dsp} enregistré !")
        else:
            st.warning("Remplis les 2 champs")

all_webhooks = {**SLACK_WEBHOOKS}
all_webhooks.update(st.session_state.custom_webhooks)

if all_webhooks:
    st.sidebar.markdown("**Webhooks configurés :**")
    for dsp_name in all_webhooks:
        st.sidebar.markdown(f"  ✅ {dsp_name}")
else:
    st.sidebar.info("Aucun webhook configuré.")


if file_routes is None or file_packages is None:
    st.info("👈 Chargez vos fichiers CSV dans la barre latérale pour lancer l'analyse.")
    st.markdown("### 📋 Mode d'emploi")
    st.markdown("""
    1. **Glissez-déposez** vos 3 fichiers CSV
    2. L'analyse se lance **automatiquement**
    3. Naviguez entre les onglets par DSP
    4. **Saisissez vos feedbacks** 💬 et **analyses** 🔍 → synchronisation auto vers le Résumé Global
    5. **Ajoutez des routes NA** (non tentés) dans chaque onglet DSP
    6. Cliquez **📋 Copier pour SharePoint** pour exporter le résumé complet
    7. Cliquez **📤 Envoyer sur Slack** pour envoyer le message au DSP
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

routes["Type"] = routes["Type de service de livraison"].apply(get_route_type)
drt = dict(zip(routes["Code de la route"], routes["Type"]))

retours_count = packages.groupby("RouteCode").size().reset_index(name="retours")
routes = routes.merge(retours_count, left_on="Code de la route", right_on="RouteCode", how="left")
routes["retours"] = routes["retours"].fillna(0).astype(int)

behind = routes[routes["Progression de la route"] == "BEHIND"].copy()
atrisk = routes[routes["Progression de la route"] == "AT_RISK"].copy()
retours10 = routes[routes["retours"] >= 10].copy()

dsps = sorted(routes["DSP"].unique())
now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
all_na = get_all_na_routes()


# ============================================
# MÉTRIQUES GLOBALES
# ============================================
st.markdown(f"**Analyse du {now_str}**")

col1, col2, col3, col4, col5, col6 = st.columns(6)
with col1:
    st.metric("🔴 BEHIND", len(behind))
with col2:
    st.metric("🟠 AT_RISK", len(atrisk))
with col3:
    st.metric("📦 10+ Retours", len(retours10))
with col4:
    st.metric("⚪ Routes NA", len(all_na))
with col5:
    st.metric("📊 Total Routes", len(routes))
with col6:
    st.metric("🏢 DSP", len(dsps))


# ============================================
# ONGLETS
# ============================================
tab_names = ["📊 Résumé Global"] + [f"🏢 {d}" for d in dsps] + ["📝 Tous les Feedbacks"]
tabs = st.tabs(tab_names)


# ============================================
# ONGLET RÉSUMÉ GLOBAL
# ============================================
with tabs[0]:
    st.markdown("## 📊 Résumé Global")

    st.markdown(
        '<div class="sync-info">'
        '🔄 Les feedbacks et analyses saisis dans les onglets DSP '
        'apparaissent automatiquement ici.</div>',
        unsafe_allow_html=True
    )
    st.markdown("")

    # BEHIND
    st.markdown('<span class="behind-badge">ROUTES EN RETARD (BEHIND)</span>', unsafe_allow_html=True)
    if not behind.empty:
        display_behind = behind[["Code de la route", "DSP", "Type", "Tous les arrêts",
            "Arrêts effectués", "arrêts non démarrés", "livraisons au total", "retours"]].copy()
        display_behind.columns = ["Route", "DSP", "Type", "Arrêts", "Effectués", "Restants", "Livraisons", "Retours"]
        afficher_tableau_avec_feedback(display_behind, "global_behind", sync_to_global=True)
    else:
        st.success("✅ Aucune route en retard")

    st.markdown("---")

    # AT_RISK
    st.markdown('<span class="atrisk-badge">ROUTES A RISQUE (AT_RISK)</span>', unsafe_allow_html=True)
    if not atrisk.empty:
        display_atrisk = atrisk[["Code de la route", "DSP", "Type", "Tous les arrêts",
            "Arrêts effectués", "arrêts non démarrés", "livraisons au total", "retours"]].copy()
        display_atrisk.columns = ["Route", "DSP", "Type", "Arrêts", "Effectués", "Restants", "Livraisons", "Retours"]
        afficher_tableau_avec_feedback(display_atrisk, "global_atrisk", sync_to_global=True)
    else:
        st.success("✅ Aucune route à risque")

    st.markdown("---")

    # 10+ RETOURS
    st.markdown('<span class="retour-badge">ROUTES AVEC 10+ RETOURS</span>', unsafe_allow_html=True)
    if not retours10.empty:
        reasons_list = ["CUSTOMER UNAVAILABLE", "BUSINESS CLOSED", "ADDRESS NOT FOUND",
            "INACCESSIBLE DELIVERY LOCATION", "RESCHEDULED BY CUSTOMER", "LOCKER ISSUE"]
        rows = []
        for _, r in retours10.iterrows():
            rc = r["Code de la route"]
            row = {"Route": rc, "DSP": r["DSP"], "Type": r["Type"],
                   "Progression": r["Progression de la route"], "Retours": r["retours"]}
            total_known = 0
            for reason in reasons_list:
                c = count_reason(packages, rc, reason)
                short = reason.split()[0][:8]
                row[short] = c
                total_known += c
            row["Autres"] = r["retours"] - total_known
            rows.append(row)
        afficher_tableau_avec_feedback(pd.DataFrame(rows), "global_retours", sync_to_global=True)
    else:
        st.success("✅ Aucune route avec 10+ retours")

    st.markdown("---")

    # ROUTES NA - RÉSUMÉ GLOBAL
    st.markdown('<span class="na-badge">ROUTES NA (NON TENTÉS)</span>', unsafe_allow_html=True)
    if all_na:
        na_df = pd.DataFrame(all_na)
        st.dataframe(na_df, use_container_width=True, hide_index=True)
    else:
        st.info("⚪ Aucune route NA saisie. Ajoutez-les dans les onglets DSP.")

    # Bilan par DSP
    st.markdown("---")
    st.markdown("### 📋 Bilan par DSP")
    bilan_rows = []
    for dsp in dsps:
        dsp_routes = routes[routes["DSP"] == dsp]
        nb_behind = len(dsp_routes[dsp_routes["Progression de la route"] == "BEHIND"])
        nb_atrisk = len(dsp_routes[dsp_routes["Progression de la route"] == "AT_RISK"])
        nb_ret10 = len(dsp_routes[dsp_routes["retours"] >= 10])
        nb_na = len([r for r in all_na if r.get("DSP", "") == dsp])
        total_ret = dsp_routes["retours"].sum()
        bilan_rows.append({
            "DSP": dsp, "BEHIND": nb_behind, "AT_RISK": nb_atrisk,
            "10+ Retours": nb_ret10, "NA": nb_na, "Total Retours": int(total_ret)
        })
    st.dataframe(pd.DataFrame(bilan_rows), use_container_width=True, hide_index=True)

    # SHAREPOINT
    st.markdown("---")
    st.markdown("### 📋 Exporter pour SharePoint")
    st.markdown(
        '<div class="sharepoint-box">'
        '<b>📋 Résumé formaté pour SharePoint</b><br>'
        'Inclut les feedbacks, analyses et routes NA.</div>',
        unsafe_allow_html=True
    )

    if st.button("📋 Générer le résumé SharePoint", key="gen_sharepoint", type="primary"):
        sharepoint_html = build_sharepoint_summary(routes, behind, atrisk, retours10, packages, drt, dsps)
        st.session_state.sharepoint_html = sharepoint_html

    if 'sharepoint_html' in st.session_state:
        st.markdown("**Aperçu :**")
        st.markdown(st.session_state.sharepoint_html, unsafe_allow_html=True)

        st.download_button(
            label="📥 Télécharger le résumé (HTML)",
            data=st.session_state.sharepoint_html,
            file_name=f"resume_dlp2_{datetime.now().strftime('%Y%m%d_%H%M')}.html",
            mime="text/html", key="dl_sharepoint"
        )

        st.info(
            "💡 **Comment coller dans SharePoint :**\n"
            "1. Téléchargez le fichier HTML\n"
            "2. Ouvrez-le dans votre navigateur\n"
            "3. Sélectionnez tout (Ctrl+A) → Copiez (Ctrl+C)\n"
            "4. Dans SharePoint, collez (Ctrl+V)"
        )


# ============================================
# ONGLETS PAR DSP
# ============================================
for idx, dsp in enumerate(dsps):
    with tabs[idx + 1]:
        st.markdown(f"## 🏢 {dsp}")
        st.caption(f"Analyse du {now_str}")

        st.markdown(
            '<div class="sync-info">'
            '🔄 Feedbacks et analyses se synchronisent automatiquement dans le Résumé Global.</div>',
            unsafe_allow_html=True
        )
        st.markdown("")

        dsp_routes = routes[routes["DSP"] == dsp].copy()
        dsp_behind = dsp_routes[dsp_routes["Progression de la route"] == "BEHIND"]
        dsp_atrisk = dsp_routes[dsp_routes["Progression de la route"] == "AT_RISK"]
        dsp_ret10 = dsp_routes[dsp_routes["retours"] >= 10]
        dsp_na = [r for r in all_na if r.get("DSP", "") == dsp]

        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.metric("🔴 BEHIND", len(dsp_behind))
        with c2:
            st.metric("🟠 AT_RISK", len(dsp_atrisk))
        with c3:
            st.metric("📦 10+ Ret.", len(dsp_ret10))
        with c4:
            st.metric("⚪ NA", len(dsp_na))
        with c5:
            st.metric("📊 Total Ret.", int(dsp_routes["retours"].sum()))

        # BEHIND
        st.markdown('<span class="behind-badge">ROUTES EN RETARD (BEHIND)</span>', unsafe_allow_html=True)
        if not dsp_behind.empty:
            df_b = dsp_behind[["Code de la route", "Type", "Tous les arrêts",
                "Arrêts effectués", "arrêts non démarrés", "livraisons au total", "retours"]].copy()
            df_b.columns = ["Route", "Type", "Arrêts", "Effectués", "Restants", "Livraisons", "Retours"]
            afficher_tableau_avec_feedback(df_b, f"dsp_{dsp}_behind")
        else:
            st.success("✅ Aucune route en retard")

        # AT_RISK
        st.markdown('<span class="atrisk-badge">ROUTES A RISQUE (AT_RISK)</span>', unsafe_allow_html=True)
        if not dsp_atrisk.empty:
            df_a = dsp_atrisk[["Code de la route", "Type", "Tous les arrêts",
                "Arrêts effectués", "arrêts non démarrés", "livraisons au total", "retours"]].copy()
            df_a.columns = ["Route", "Type", "Arrêts", "Effectués", "Restants", "Livraisons", "Retours"]
            afficher_tableau_avec_feedback(df_a, f"dsp_{dsp}_atrisk")
        else:
            st.success("✅ Aucune route à risque")

        # 10+ RETOURS
        st.markdown('<span class="retour-badge">ROUTES AVEC 10+ RETOURS</span>', unsafe_allow_html=True)
        if not dsp_ret10.empty:
            rows_r = []
            for _, r in dsp_ret10.iterrows():
                rc = r["Code de la route"]
                rows_r.append({
                    "Route": rc, "Type": r["Type"],
                    "Progression": r["Progression de la route"],
                    "Retours": r["retours"],
                    "Raisons": get_top_reasons(packages, rc)
                })
            afficher_tableau_avec_feedback(pd.DataFrame(rows_r), f"dsp_{dsp}_retours")
        else:
            st.success("✅ Aucune route avec 10+ retours")

        # ROUTES NA
        st.markdown("---")
        st.markdown('<span class="na-badge">ROUTES NA (NON TENTÉS)</span>', unsafe_allow_html=True)
        st.markdown("")
        afficher_section_na(f"na_{dsp}", dsp_name=dsp)

        # DETAIL RETOURS
        st.markdown("---")
        st.markdown("### 📋 Détail des retours")
        dsp_route_codes = dsp_routes["Code de la route"].unique()
        dsp_packages = packages[packages["RouteCode"].isin(dsp_route_codes)]
        if not dsp_packages.empty:
            prog_map = dict(zip(dsp_routes["Code de la route"], dsp_routes["Progression de la route"]))
            df_det = dsp_packages[["RouteCode", "ScannableId", "Address", "ReasonCode"]].copy()
            df_det.insert(1, "Type", df_det["RouteCode"].map(drt))
            df_det.insert(2, "Progression", df_det["RouteCode"].map(prog_map))
            df_det.columns = ["Route", "Type", "Progression", "Scannable ID", "Adresse", "Raison"]
            st.dataframe(df_det, use_container_width=True, hide_index=True)
        else:
            st.info("Aucun retour pour ce DSP")

        # MESSAGE SLACK
        st.markdown("---")
        st.markdown("### 💬 Message Slack")
        slack_msg = build_slack_message(dsp, dsp_behind, dsp_atrisk, dsp_ret10, packages, drt, all_na)

        st.markdown(f'<div class="slack-box">{slack_msg}</div>', unsafe_allow_html=True)

        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            st.code(slack_msg, language=None)
        with btn_col2:
            dsp_has_webhook = dsp in all_webhooks
            already_sent = dsp in st.session_state.sent_messages

            if dsp_has_webhook:
                if already_sent:
                    st.markdown(
                        f'<div class="sent-ok">✅ Message envoyé à {st.session_state.sent_messages[dsp]}</div>',
                        unsafe_allow_html=True
                    )
                    if st.button("🔄 Renvoyer", key=f"resend_{dsp}"):
                        ok = envoyer_slack(all_webhooks[dsp], slack_msg)
                        if ok:
                            st.session_state.sent_messages[dsp] = datetime.now().strftime("%H:%M")
                            st.rerun()
                else:
                    if st.button(f"📤 Envoyer sur Slack → #{dsp}", key=f"send_{dsp}", type="primary"):
                        ok = envoyer_slack(all_webhooks[dsp], slack_msg)
                        if ok:
                            st.session_state.sent_messages[dsp] = datetime.now().strftime("%H:%M")
                            st.success(f"✅ Message envoyé sur #{dsp} !")
                            st.rerun()
                        else:
                            st.error("❌ Échec de l'envoi.")
            else:
                st.warning(f"⚙️ Pas de webhook pour {dsp}.")


# ============================================
# ONGLET TOUS LES FEEDBACKS
# ============================================
with tabs[-1]:
    st.markdown("## 📝 Tous les Feedbacks & Analyses")

    has_feedbacks = bool(st.session_state.dsp_feedbacks)
    has_analyses = bool(st.session_state.dsp_analyses)

    if has_feedbacks or has_analyses:
        fb_rows = []
        seen_routes = set()

        all_route_keys = set()
        for fb_key in st.session_state.dsp_feedbacks:
            if fb_key.startswith("route_"):
                all_route_keys.add(fb_key.replace("route_", ""))
        for a_key in st.session_state.dsp_analyses:
            if a_key.startswith("route_"):
                all_route_keys.add(a_key.replace("route_", ""))

        for route_id in all_route_keys:
            fb = st.session_state.dsp_feedbacks.get(f"route_{route_id}", "")
            an = st.session_state.dsp_analyses.get(f"route_{route_id}", "")
            if fb or an:
                fb_rows.append({
                    "Route": route_id,
                    "💬 Feedback DSP": fb,
                    "🔍 Analyse de la route": an,
                    "Date": datetime.now().strftime("%d/%m/%Y")
                })

        if fb_rows:
            fb_df = pd.DataFrame(fb_rows)

            c1, c2 = st.columns(2)
            c1.metric("💬 Total feedbacks", len([r for r in fb_rows if r["💬 Feedback DSP"]]))
            c2.metric("🔍 Total analyses", len([r for r in fb_rows if r["🔍 Analyse de la route"]]))

            st.dataframe(fb_df, use_container_width=True, hide_index=True)

            csv = fb_df.to_csv(index=False, sep=';').encode('utf-8-sig')
            st.download_button(
                label="📥 Exporter feedbacks & analyses (CSV)",
                data=csv,
                file_name=f"feedbacks_analyses_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("Aucun feedback ou analyse saisi pour le moment.")
    else:
        st.info("Aucun feedback ou analyse saisi pour le moment.")

    if st.session_state.sent_messages:
        st.markdown("---")
        st.markdown("### 📤 Historique des envois Slack")
        for dsp_name, heure in st.session_state.sent_messages.items():
            st.markdown(f"  ✅ **{dsp_name}** — envoyé à {heure}")


# ============================================
# FOOTER
# ============================================
st.markdown("---")
st.markdown(
    "<center><small>DLP2 - Suivi Ops Journalier | Développé pour l'équipe Dispatch</small></center>",
    unsafe_allow_html=True
)

