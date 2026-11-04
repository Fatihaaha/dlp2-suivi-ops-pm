
# ==============================================
# DLP2 - APP STREAMLIT v4 - INTERFACE
# ==============================================
# Installation : pip install streamlit pandas requests openpyxl
# Lancement   : streamlit run app.py
# ==============================================

import streamlit as st
import pandas as pd
from datetime import datetime
from utils import (
    envoyer_slack, get_route_type, get_top_reasons, count_reason,
    get_feedback_for_route, get_analyse_for_route, get_all_na_routes,
    afficher_tableau_avec_feedback, afficher_section_na,
    build_slack_message, generate_excel_summary
)

# ============================================
# CONFIG
# ============================================
st.set_page_config(page_title="DLP2 - Suivi Ops", page_icon="🚚", layout="wide")

SLACK_WEBHOOKS = {}

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
# CSS
# ============================================
st.markdown("""
<style>
    .main-header { background: linear-gradient(135deg, #003366, #004080); color: white; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
    .behind-badge { background-color: #C00000; color: white; padding: 3px 10px; border-radius: 5px; font-weight: bold; }
    .atrisk-badge { background-color: #FF8C00; color: white; padding: 3px 10px; border-radius: 5px; font-weight: bold; }
    .retour-badge { background-color: #C05000; color: white; padding: 3px 10px; border-radius: 5px; font-weight: bold; }
    .na-badge { background-color: #607D8B; color: white; padding: 3px 10px; border-radius: 5px; font-weight: bold; }
    .slack-box { background-color: #F2EDF6; border: 1px solid #8B008B; border-radius: 10px; padding: 15px; font-family: monospace; white-space: pre-wrap; }
    .sent-ok { background-color: #E8F5E9; border: 2px solid #4CAF50; border-radius: 10px; padding: 10px; text-align: center; font-weight: bold; color: #2E7D32; }
    .sync-info { background-color: #FFF8E1; border: 1px solid #FFC107; border-radius: 8px; padding: 10px; font-size: 0.9em; }
    .excel-box { background-color: #E8F5E9; border: 2px solid #4CAF50; border-radius: 10px; padding: 15px; margin: 10px 0; }
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
if 'custom_webhooks' not in st.session_state:
    st.session_state.custom_webhooks = {}

with st.sidebar.expander("➕ Ajouter un webhook DSP"):
    new_dsp = st.text_input("Nom du DSP", key="new_dsp_name")
    new_webhook = st.text_input("URL Webhook Slack", key="new_webhook_url", type="password")
    if st.button("✅ Enregistrer", key="save_webhook"):
        if new_dsp and new_webhook:
            st.session_state.custom_webhooks[new_dsp.strip()] = new_webhook.strip()
            st.success(f"Webhook {new_dsp} enregistré !")

all_webhooks = {**SLACK_WEBHOOKS}
all_webhooks.update(st.session_state.custom_webhooks)
if all_webhooks:
    st.sidebar.markdown("**Webhooks configurés :**")
    for dn in all_webhooks:
        st.sidebar.markdown(f"  ✅ {dn}")

# ============================================
# SAUVEGARDE / RESTAURATION FEEDBACKS
# ============================================
st.sidebar.markdown("---")
st.sidebar.header("💾 Feedbacks entre Flow Meetings")

# SAUVEGARDER
if st.sidebar.button("💾 Sauvegarder les feedbacks", key="save_fb", type="primary"):
    save_data = {
        "feedbacks": dict(st.session_state.dsp_feedbacks),
        "analyses": dict(st.session_state.dsp_analyses),
        "routes_na": dict(st.session_state.routes_na),
        "sent_messages": dict(st.session_state.sent_messages),
        "saved_at": datetime.now().strftime("%d/%m/%Y %H:%M")
    }
    st.session_state.saved_feedbacks = save_data
    st.sidebar.success(f"✅ Feedbacks sauvegardés à {save_data['saved_at']}")

# Bouton télécharger la sauvegarde
if 'saved_feedbacks' in st.session_state:
    import json as json_mod
    save_json = json_mod.dumps(st.session_state.saved_feedbacks, ensure_ascii=False, indent=2)
    st.sidebar.download_button(
        label="📥 Télécharger sauvegarde (JSON)",
        data=save_json.encode('utf-8'),
        file_name=f"feedbacks_FM1_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
        mime="application/json",
        key="dl_save"
    )
    st.sidebar.caption(f"💾 Dernière sauvegarde : {st.session_state.saved_feedbacks['saved_at']}")

# RESTAURER
uploaded_save = st.sidebar.file_uploader("📤 Restaurer feedbacks (JSON)", type=["json"], key="restore_fb")
if uploaded_save is not None:
    import json as json_mod
    try:
        restored = json_mod.loads(uploaded_save.read().decode('utf-8'))
        st.session_state.dsp_feedbacks.update(restored.get("feedbacks", {}))
        st.session_state.dsp_analyses.update(restored.get("analyses", {}))
        st.session_state.routes_na.update(restored.get("routes_na", {}))
        st.session_state.sent_messages.update(restored.get("sent_messages", {}))
        st.sidebar.success(f"✅ Feedbacks restaurés ! (sauvegarde du {restored.get('saved_at', '?')})")
    except Exception as e:
        st.sidebar.error(f"❌ Erreur : {e}")


if file_routes is None or file_packages is None:
    st.info("👈 Chargez vos fichiers CSV dans la barre latérale pour lancer l'analyse.")
    st.markdown("### 📋 Mode d'emploi")
    st.markdown("""
    1. **Glissez-déposez** vos fichiers CSV
    2. L'analyse se lance **automatiquement**
    3. Saisissez vos **💬 Feedbacks** et **🔍 Analyses** → synchronisation auto
    4. Ajoutez des **routes NA** (non tentés)
    5. Cliquez **📥 Télécharger Excel** pour exporter le résumé formaté
    """)
    st.stop()

# ============================================
# CHARGEMENT
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
# MÉTRIQUES
# ============================================
st.markdown(f"**Analyse du {now_str}**")
c1, c2, c3, c4, c5, c6 = st.columns(6)
with c1: st.metric("🔴 BEHIND", len(behind))
with c2: st.metric("🟠 AT_RISK", len(atrisk))
with c3: st.metric("📦 10+ Retours", len(retours10))
with c4: st.metric("⚪ Routes NA", len(all_na))
with c5: st.metric("📊 Total Routes", len(routes))
with c6: st.metric("🏢 DSP", len(dsps))

# ============================================
# ONGLETS
# ============================================
tab_names = ["📊 Résumé Global"] + [f"🏢 {d}" for d in dsps] + ["📝 Feedbacks"]
tabs = st.tabs(tab_names)

# ============================================
# RÉSUMÉ GLOBAL
# ============================================
with tabs[0]:
    st.markdown("## 📊 Résumé Global")
    st.markdown('<div class="sync-info">🔄 Feedbacks et analyses se synchronisent automatiquement.</div>', unsafe_allow_html=True)
    st.markdown("")

    st.markdown('<span class="behind-badge">ROUTES EN RETARD (BEHIND)</span>', unsafe_allow_html=True)
    if not behind.empty:
        db = behind[["Code de la route", "DSP", "Type", "Tous les arrêts", "Arrêts effectués", "arrêts non démarrés", "livraisons au total", "retours"]].copy()
        db.columns = ["Route", "DSP", "Type", "Arrêts", "Effectués", "Restants", "Livraisons", "Retours"]
        afficher_tableau_avec_feedback(db, "global_behind", sync_to_global=True)
    else:
        st.success("✅ Aucune route en retard")

    st.markdown("---")
    st.markdown('<span class="atrisk-badge">ROUTES A RISQUE (AT_RISK)</span>', unsafe_allow_html=True)
    if not atrisk.empty:
        da = atrisk[["Code de la route", "DSP", "Type", "Tous les arrêts", "Arrêts effectués", "arrêts non démarrés", "livraisons au total", "retours"]].copy()
        da.columns = ["Route", "DSP", "Type", "Arrêts", "Effectués", "Restants", "Livraisons", "Retours"]
        afficher_tableau_avec_feedback(da, "global_atrisk", sync_to_global=True)
    else:
        st.success("✅ Aucune route à risque")

    st.markdown("---")
    st.markdown('<span class="retour-badge">ROUTES AVEC 10+ RETOURS</span>', unsafe_allow_html=True)
    if not retours10.empty:
        reasons_list = ["CUSTOMER UNAVAILABLE", "BUSINESS CLOSED", "ADDRESS NOT FOUND",
            "INACCESSIBLE DELIVERY LOCATION", "RESCHEDULED BY CUSTOMER", "LOCKER ISSUE"]
        rows = []
        for _, r in retours10.iterrows():
            rc = r["Code de la route"]
            rd = {"Route": rc, "DSP": r["DSP"], "Type": r["Type"],
                  "Progression": r["Progression de la route"], "Retours": r["retours"]}
            tk = 0
            for reason in reasons_list:
                cnt = count_reason(packages, rc, reason)
                rd[reason.split()[0][:8]] = cnt
                tk += cnt
            rd["Autres"] = r["retours"] - tk
            rows.append(rd)
        afficher_tableau_avec_feedback(pd.DataFrame(rows), "global_retours", sync_to_global=True)
    else:
        st.success("✅ Aucune route avec 10+ retours")

    st.markdown("---")
    st.markdown('<span class="na-badge">ROUTES NA (NON TENTÉS)</span>', unsafe_allow_html=True)
    all_na = get_all_na_routes()
    if all_na:
        st.dataframe(pd.DataFrame(all_na), use_container_width=True, hide_index=True)
    else:
        st.info("⚪ Aucune route NA. Ajoutez-les dans les onglets DSP.")

    st.markdown("---")
    st.markdown("### 📋 Bilan par DSP")
    bilan = []
    for dsp in dsps:
        dr = routes[routes["DSP"] == dsp]
        bilan.append({"DSP": dsp,
            "BEHIND": len(dr[dr["Progression de la route"] == "BEHIND"]),
            "AT_RISK": len(dr[dr["Progression de la route"] == "AT_RISK"]),
            "10+ Ret": len(dr[dr["retours"] >= 10]),
            "NA": len([r for r in all_na if r.get("DSP", "") == dsp]),
            "Total Ret": int(dr["retours"].sum())})
    st.dataframe(pd.DataFrame(bilan), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### 📥 Exporter pour SharePoint")
    st.markdown('<div class="excel-box"><b>📥 Résumé Excel formaté</b> avec codes couleurs pour SharePoint</div>', unsafe_allow_html=True)

    if st.button("📥 Générer le fichier Excel", key="gen_excel", type="primary"):
        with st.spinner("Génération..."):
            excel_data = generate_excel_summary(routes, behind, atrisk, retours10, packages, drt, dsps)
            st.session_state.excel_data = excel_data.getvalue()
        st.success("✅ Fichier Excel généré !")

    if 'excel_data' in st.session_state:
        st.download_button(
            label="📥 Télécharger le résumé Excel",
            data=st.session_state.excel_data,
            file_name=f"DLP2_Resume_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_excel"
        )

# ============================================
# ONGLETS DSP
# ============================================
for idx, dsp in enumerate(dsps):
    with tabs[idx + 1]:
        st.markdown(f"## 🏢 {dsp}")
        st.caption(f"Analyse du {now_str}")
        st.markdown('<div class="sync-info">🔄 Synchronisation auto vers Résumé Global</div>', unsafe_allow_html=True)
        st.markdown("")

        dsp_routes = routes[routes["DSP"] == dsp].copy()
        dsp_behind = dsp_routes[dsp_routes["Progression de la route"] == "BEHIND"]
        dsp_atrisk = dsp_routes[dsp_routes["Progression de la route"] == "AT_RISK"]
        dsp_ret10 = dsp_routes[dsp_routes["retours"] >= 10]
        dsp_na_list = [r for r in all_na if r.get("DSP", "") == dsp]

        m1, m2, m3, m4, m5 = st.columns(5)
        with m1: st.metric("🔴 BEHIND", len(dsp_behind))
        with m2: st.metric("🟠 AT_RISK", len(dsp_atrisk))
        with m3: st.metric("📦 10+ Ret.", len(dsp_ret10))
        with m4: st.metric("⚪ NA", len(dsp_na_list))
        with m5: st.metric("📊 Total Ret.", int(dsp_routes["retours"].sum()))

        st.markdown('<span class="behind-badge">BEHIND</span>', unsafe_allow_html=True)
        if not dsp_behind.empty:
            df_b = dsp_behind[["Code de la route", "Type", "Tous les arrêts", "Arrêts effectués", "arrêts non démarrés", "livraisons au total", "retours"]].copy()
            df_b.columns = ["Route", "Type", "Arrêts", "Effectués", "Restants", "Livraisons", "Retours"]
            afficher_tableau_avec_feedback(df_b, f"dsp_{dsp}_behind")
        else:
            st.success("✅ Aucune")

        st.markdown('<span class="atrisk-badge">AT_RISK</span>', unsafe_allow_html=True)
        if not dsp_atrisk.empty:
            df_a = dsp_atrisk[["Code de la route", "Type", "Tous les arrêts", "Arrêts effectués", "arrêts non démarrés", "livraisons au total", "retours"]].copy()
            df_a.columns = ["Route", "Type", "Arrêts", "Effectués", "Restants", "Livraisons", "Retours"]
            afficher_tableau_avec_feedback(df_a, f"dsp_{dsp}_atrisk")
        else:
            st.success("✅ Aucune")

        st.markdown('<span class="retour-badge">10+ RETOURS</span>', unsafe_allow_html=True)
        if not dsp_ret10.empty:
            rr = []
            for _, r in dsp_ret10.iterrows():
                rc = r["Code de la route"]
                rr.append({"Route": rc, "Type": r["Type"], "Progression": r["Progression de la route"],
                    "Retours": r["retours"], "Raisons": get_top_reasons(packages, rc)})
            afficher_tableau_avec_feedback(pd.DataFrame(rr), f"dsp_{dsp}_retours")
        else:
            st.success("✅ Aucune")

        st.markdown("---")
        st.markdown('<span class="na-badge">ROUTES NA</span>', unsafe_allow_html=True)
        st.markdown("")
        afficher_section_na(f"na_{dsp}", dsp_name=dsp)

        st.markdown("---")
               st.markdown("### 📋 Détail des retours par route")
        dsp_codes = dsp_routes["Code de la route"].unique()
        dsp_pkg = packages[packages["RouteCode"].isin(dsp_codes)]
        if not dsp_pkg.empty:
            reasons_list = [
                "CUSTOMER UNAVAILABLE", "BUSINESS CLOSED", "ADDRESS NOT FOUND",
                "INACCESSIBLE DELIVERY LOCATION", "RESCHEDULED BY CUSTOMER", "LOCKER ISSUE"
            ]
            detail_rows = []
            for rc in dsp_codes:
                route_pkg = dsp_pkg[dsp_pkg["RouteCode"] == rc]
                if route_pkg.empty:
                    continue
                row_data = {
                    "Route": rc,
                    "Type": drt.get(rc, "-"),
                    "Progression": dsp_routes[dsp_routes["Code de la route"] == rc]["Progression de la route"].values if len(dsp_routes[dsp_routes["Code de la route"] == rc]) > 0 else "-",
                }
                total_known = 0
                for reason in reasons_list:
                    cnt = len(route_pkg[route_pkg["ReasonCode"] == reason])
                    short_name = reason.replace("CUSTOMER ", "").replace("DELIVERY ", "").replace("BY CUSTOMER", "").replace("ISSUE", "").strip()[:12]
                    row_data[short_name] = cnt
                    total_known += cnt
                row_data["Autres"] = len(route_pkg) - total_known
                row_data["Total"] = len(route_pkg)
                detail_rows.append(row_data)

            if detail_rows:
                detail_df = pd.DataFrame(detail_rows)
                detail_df = detail_df.sort_values("Total", ascending=False)
                st.dataframe(detail_df, use_container_width=True, hide_index=True)
            else:
                st.info("Aucun retour")
        else:
            st.info("Aucun retour")
        # ============================================
        # BAD WEATHER & UNSAFE DUE TO DOG
        # ============================================
        dsp_codes = dsp_routes["Code de la route"].unique()
        dsp_pkg = packages[packages["RouteCode"].isin(dsp_codes)]

        if not dsp_pkg.empty:
            # BAD WEATHER
            bad_weather = dsp_pkg[dsp_pkg["ReasonCode"].str.lower().str.contains("bad weather", na=False)]
            st.markdown("---")
            st.markdown("### ⛈️ Bad Weather")
            if not bad_weather.empty:
                st.markdown(f'<span style="background-color:#1565C0;color:white;padding:3px 10px;border-radius:5px;font-weight:bold;">⛈️ {len(bad_weather)} colis — {bad_weather["RouteCode"].nunique()} routes</span>', unsafe_allow_html=True)
                bw_detail = bad_weather[["RouteCode", "ScannableId", "Address", "ReasonCode"]].copy()
                bw_detail.insert(1, "Type", bw_detail["RouteCode"].map(drt))
                bw_detail.columns = ["Route", "Type", "Tracking", "Adresse", "Raison"]
                st.dataframe(bw_detail, use_container_width=True, hide_index=True)
            else:
                st.success("✅ Aucun retour Bad Weather")

            # UNSAFE DUE TO DOG
            unsafe_dog = dsp_pkg[dsp_pkg["ReasonCode"].str.lower().str.contains("unsafe due to dog", na=False)]
            st.markdown("---")
            st.markdown("### 🐕 Unsafe due to Dog")
            if not unsafe_dog.empty:
                st.markdown(f'<span style="background-color:#C62828;color:white;padding:3px 10px;border-radius:5px;font-weight:bold;">🐕 {len(unsafe_dog)} colis — {unsafe_dog["RouteCode"].nunique()} routes</span>', unsafe_allow_html=True)
                dog_detail = unsafe_dog[["RouteCode", "ScannableId", "Address", "ReasonCode"]].copy()
                dog_detail.insert(1, "Type", dog_detail["RouteCode"].map(drt))
                dog_detail.columns = ["Route", "Type", "Tracking", "Adresse", "Raison"]
                st.dataframe(dog_detail, use_container_width=True, hide_index=True)
            else:
                st.success("✅ Aucun retour Unsafe due to Dog")

        st.markdown("---")
        st.markdown("### 💬 Message Slack")
        slack_msg = build_slack_message(dsp, dsp_behind, dsp_atrisk, dsp_ret10, packages, drt, all_na)
        st.markdown(f'<div class="slack-box">{slack_msg}</div>', unsafe_allow_html=True)

        bc1, bc2 = st.columns(2)
        with bc1:
            st.code(slack_msg, language=None)
        with bc2:
            if dsp in all_webhooks:
                if dsp in st.session_state.sent_messages:
                    st.markdown(f'<div class="sent-ok">✅ Envoyé à {st.session_state.sent_messages[dsp]}</div>', unsafe_allow_html=True)
                    if st.button("🔄 Renvoyer", key=f"resend_{dsp}"):
                        if envoyer_slack(all_webhooks[dsp], slack_msg):
                            st.session_state.sent_messages[dsp] = datetime.now().strftime("%H:%M")
                            st.rerun()
                else:
                    if st.button(f"📤 Envoyer → #{dsp}", key=f"send_{dsp}", type="primary"):
                        if envoyer_slack(all_webhooks[dsp], slack_msg):
                            st.session_state.sent_messages[dsp] = datetime.now().strftime("%H:%M")
                            st.rerun()
            else:
                st.warning(f"⚙️ Pas de webhook pour {dsp}.")

# ============================================
# ONGLET FEEDBACKS
# ============================================
with tabs[-1]:
    st.markdown("## 📝 Tous les Feedbacks & Analyses")

    all_route_keys = set()
    for fb_key in st.session_state.dsp_feedbacks:
        if fb_key.startswith("route_"):
            all_route_keys.add(fb_key.replace("route_", ""))
    for a_key in st.session_state.dsp_analyses:
        if a_key.startswith("route_"):
            all_route_keys.add(a_key.replace("route_", ""))

    if all_route_keys:
        fb_rows = []
        for route_id in all_route_keys:
            fb = st.session_state.dsp_feedbacks.get(f"route_{route_id}", "")
            an = st.session_state.dsp_analyses.get(f"route_{route_id}", "")
            if fb or an:
                fb_rows.append({
                    "Route": route_id,
                    "💬 Feedback DSP": fb,
                    "🔍 Analyse": an,
                    "Date": datetime.now().strftime("%d/%m/%Y")
                })
        if fb_rows:
            fb_df = pd.DataFrame(fb_rows)
            fc1, fc2 = st.columns(2)
            fc1.metric("💬 Feedbacks", len([r for r in fb_rows if r["💬 Feedback DSP"]]))
            fc2.metric("🔍 Analyses", len([r for r in fb_rows if r["🔍 Analyse"]]))
            st.dataframe(fb_df, use_container_width=True, hide_index=True)
            csv = fb_df.to_csv(index=False, sep=';').encode('utf-8-sig')
            st.download_button("📥 Exporter (CSV)", data=csv,
                file_name=f"feedbacks_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")
        else:
            st.info("Aucun feedback ou analyse saisi.")
    else:
        st.info("Aucun feedback ou analyse saisi.")

    if st.session_state.sent_messages:
        st.markdown("---")
        st.markdown("### 📤 Historique Slack")
        for dn, hr in st.session_state.sent_messages.items():
            st.markdown(f"  ✅ **{dn}** — envoyé à {hr}")

# ============================================
# FOOTER
# ============================================
st.markdown("---")
st.markdown("<center><small>DLP2 - Suivi Ops Journalier | Équipe Dispatch</small></center>", unsafe_allow_html=True)

