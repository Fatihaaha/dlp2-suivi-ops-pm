
# ==============================================
# DLP2 - APP STREAMLIT v5 - CORRIGÉE
# ==============================================
import streamlit as st
import pandas as pd
from datetime import datetime
import json
from utils import (
    envoyer_slack, get_route_type, get_top_reasons, count_reason,
    get_feedback_for_route, get_analyse_for_route, get_all_na_routes,
    get_all_manual_retours, afficher_tableau_avec_feedback,
    afficher_section_na, afficher_section_retours_manual,
    build_slack_message, generate_excel_summary
)

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
if 'routes_retours_manual' not in st.session_state:
    st.session_state.routes_retours_manual = {}

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

st.markdown("""
<div class="main-header">
    <h1>🚚 DLP2 - Suivi Ops Journalier</h1>
    <p>Analyse des routes BEHIND, AT_RISK, 10+ retours et NA par DSP</p>
</div>
""", unsafe_allow_html=True)

# SIDEBAR
st.sidebar.header("📁 Charger les extracts")
file_routes = st.sidebar.file_uploader("1. Extract ROUTES (CSV)", type=["csv"], key="routes")
file_packages = st.sidebar.file_uploader("2. Extract PACKAGES (CSV)", type=["csv"], key="packages")

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

# SAUVEGARDE / RESTAURATION FEEDBACKS
st.sidebar.markdown("---")
st.sidebar.header("💾 Feedbacks entre Flow Meetings")
if st.sidebar.button("💾 Sauvegarder les feedbacks", key="save_fb", type="primary"):
    save_data = {
        "feedbacks": dict(st.session_state.dsp_feedbacks),
        "analyses": dict(st.session_state.dsp_analyses),
        "routes_na": {k: v for k, v in st.session_state.routes_na.items()},
        "routes_retours_manual": {k: v for k, v in st.session_state.routes_retours_manual.items()},
        "sent_messages": dict(st.session_state.sent_messages),
        "saved_at": datetime.now().strftime("%d/%m/%Y %H:%M")
    }
    st.session_state.saved_feedbacks = save_data
    st.sidebar.success(f"✅ Sauvegardé à {save_data['saved_at']}")
if 'saved_feedbacks' in st.session_state:
    save_json = json.dumps(st.session_state.saved_feedbacks, ensure_ascii=False, indent=2)
    st.sidebar.download_button(
        label="📥 Télécharger sauvegarde (JSON)",
        data=save_json.encode('utf-8'),
        file_name=f"feedbacks_FM_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
        mime="application/json", key="dl_save"
    )
    st.sidebar.caption(f"💾 Dernière sauvegarde : {st.session_state.saved_feedbacks['saved_at']}")
uploaded_save = st.sidebar.file_uploader("📤 Restaurer feedbacks (JSON)", type=["json"], key="restore_fb")
if uploaded_save is not None:
    try:
        restored = json.loads(uploaded_save.read().decode('utf-8'))
        st.session_state.dsp_feedbacks.update(restored.get("feedbacks", {}))
        st.session_state.dsp_analyses.update(restored.get("analyses", {}))
        for k, v in restored.get("routes_na", {}).items():
            if k not in st.session_state.routes_na:
                st.session_state.routes_na[k] = v
        for k, v in restored.get("routes_retours_manual", {}).items():
            if k not in st.session_state.routes_retours_manual:
                st.session_state.routes_retours_manual[k] = v
        st.session_state.sent_messages.update(restored.get("sent_messages", {}))
        st.sidebar.success(f"✅ Restauré ! (du {restored.get('saved_at', '?')})")
    except Exception as e:
        st.sidebar.error(f"❌ Erreur : {e}")

if file_routes is None or file_packages is None:
    st.info("👈 Chargez vos fichiers CSV dans la barre latérale.")
    st.markdown("### 📋 Mode d'emploi")
    st.markdown("""
    1. **Glissez-déposez** vos fichiers CSV
    2. L'analyse se lance **automatiquement**
    3. Saisissez vos **💬 Feedbacks** et **🔍 Analyses**
    4. Ajoutez des **routes NA** et **10+ retours manuels**
    5. Cliquez **📥 Télécharger Excel** pour exporter
    """)
    st.stop()

# CHARGEMENT
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

# MÉTRIQUES
st.markdown(f"**Analyse du {now_str}**")
c1, c2, c3, c4, c5, c6 = st.columns(6)
with c1: st.metric("🔴 BEHIND", len(behind))
with c2: st.metric("🟠 AT_RISK", len(atrisk))
with c3: st.metric("📦 10+ Retours", len(retours10))
with c4: st.metric("⚪ Routes NA", len(get_all_na_routes()))
with c5: st.metric("📊 Total Routes", len(routes))
with c6: st.metric("🏢 DSP", len(dsps))


# ============================================
# ONGLETS
# ============================================
tab_names = ["📊 Résumé Global"] + [f"🏢 {d}" for d in dsps] + ["📝 Feedbacks"]
tabs = st.tabs(tab_names)

# RÉSUMÉ GLOBAL
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

    all_mr = get_all_manual_retours()
    if all_mr:
        st.markdown("---")
        st.markdown('<span class="retour-badge">ROUTES 10+ RETOURS (AJOUTÉES MANUELLEMENT)</span>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(all_mr), use_container_width=True, hide_index=True)

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

# ONGLETS DSP
for idx, dsp in enumerate(dsps):
    with tabs[idx + 1]:
        st.markdown(f"## 🏢 {dsp}")
        st.caption(f"Analyse du {now_str}")

        dsp_routes = routes[routes["DSP"] == dsp].copy()
        dsp_behind = dsp_routes[dsp_routes["Progression de la route"] == "BEHIND"]
        dsp_atrisk = dsp_routes[dsp_routes["Progression de la route"] == "AT_RISK"]
        dsp_ret10 = dsp_routes[dsp_routes["retours"] >= 10]
        all_na = get_all_na_routes()
        all_mr = get_all_manual_retours()
        dsp_na_list = [r for r in all_na if r.get("DSP", "") == dsp]
        dsp_mr_list = [r for r in all_mr if r.get("DSP", "") == dsp]

        m1, m2, m3, m4, m5 = st.columns(5)
        with m1: st.metric("🔴 BEHIND", len(dsp_behind))
        with m2: st.metric("🟠 AT_RISK", len(dsp_atrisk))
        with m3: st.metric("📦 10+ Ret.", len(dsp_ret10))
        with m4: st.metric("⚪ NA", len(dsp_na_list))
        with m5: st.metric("📊 Total Ret.", int(dsp_routes["retours"].sum()))

        st.markdown('<span class="behind-badge">BEHIND</span>', unsafe_allow_html=True)
        if not dsp_behind.empty:
            
            dfb = dsp_behind[["Code de la route", "Type", "Tous les arrêts", "Arrêts effectués", "arrêts non démarrés", "livraisons au total", "retours"]].copy()
            dfb.columns = ["Route", "Type", "Arrêts", "Effectués", "Restants", "Livraisons", "Retours"]
            afficher_tableau_avec_feedback(dfb, f"dsp_behind_{dsp}")
        else:
            st.success("✅ Aucune route BEHIND")

        st.markdown("---")
        st.markdown('<span class="atrisk-badge">AT_RISK</span>', unsafe_allow_html=True)
        if not dsp_atrisk.empty:
            dfa = dsp_atrisk[["Code de la route", "Type", "Tous les arrêts", "Arrêts effectués", "arrêts non démarrés", "livraisons au total", "retours"]].copy()
            dfa.columns = ["Route", "Type", "Arrêts", "Effectués", "Restants", "Livraisons", "Retours"]
            afficher_tableau_avec_feedback(dfa, f"dsp_atrisk_{dsp}")
        else:
            st.success("✅ Aucune route AT_RISK")

        st.markdown("---")
        st.markdown('<span class="retour-badge">10+ RETOURS</span>', unsafe_allow_html=True)
        if not dsp_ret10.empty:
            dfr = dsp_ret10[["Code de la route", "Type", "Progression de la route", "retours"]].copy()
            dfr.columns = ["Route", "Type", "Progression", "Retours"]
            afficher_tableau_avec_feedback(dfr, f"dsp_ret10_{dsp}")
        else:
            st.success("✅ Aucune route avec 10+ retours")

        # AJOUT MANUEL 10+ RETOURS
        st.markdown("---")
        st.markdown('<span class="retour-badge">➕ AJOUTER DES ROUTES 10+ RETOURS</span>', unsafe_allow_html=True)
        st.markdown("")
        afficher_section_retours_manual(f"ret_{dsp}", dsp_name=dsp)

        st.markdown("---")
        st.markdown('<span class="na-badge">ROUTES NA</span>', unsafe_allow_html=True)
        st.markdown("")
        afficher_section_na(f"na_{dsp}", dsp_name=dsp)

        # DÉTAIL DES RETOURS PAR ROUTE
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

        # BAD WEATHER & UNSAFE DUE TO DOG
        if not dsp_pkg.empty:
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

        # MESSAGE SLACK
        st.markdown("---")
        st.markdown("### 💬 Message Slack")
        slack_msg = build_slack_message(dsp, dsp_behind, dsp_atrisk, dsp_ret10, packages, drt, all_na, all_mr)
        st.markdown(f'<div class="slack-box">{slack_msg}</div>', unsafe_allow_html=True)

        msg_key = f"sent_{dsp}"
        if msg_key in st.session_state.sent_messages:
            st.markdown(f'<div class="sent-ok">✅ Message envoyé à {st.session_state.sent_messages[msg_key]}</div>', unsafe_allow_html=True)

        sc1, sc2 = st.columns(2)
        with sc1:
            if st.button(f"📋 Copier le message", key=f"copy_{dsp}"):
                st.code(slack_msg, language=None)
        with sc2:
            webhook_url = all_webhooks.get(dsp, "")
            if webhook_url:
                if st.button(f"📤 Envoyer sur Slack", key=f"send_{dsp}", type="primary"):
                    if envoyer_slack(webhook_url, slack_msg):
                        st.session_state.sent_messages[msg_key] = datetime.now().strftime("%H:%M")
                        st.success("✅ Envoyé !")
                        st.rerun()
                    else:
                        st.error("❌ Échec de l'envoi")
            else:
                st.info("💡 Configurez le webhook Slack pour ce DSP dans la sidebar")

# ONGLET FEEDBACKS
with tabs[-1]:
    st.markdown("## 📝 Tous les Feedbacks")
    all_fb = []
    for fb_key, fb_text in st.session_state.dsp_feedbacks.items():
        if fb_text and str(fb_text).strip() and fb_key.startswith("route_"):
            route_id = fb_key.replace("route_", "")
            analyse = get_analyse_for_route(route_id)
            all_fb.append({
                "Route": route_id,
                "💬 Feedback DSP": str(fb_text).strip(),
                "🔍 Analyse": analyse
            })
    if all_fb:
        st.dataframe(pd.DataFrame(all_fb), use_container_width=True, hide_index=True)
    else:
        st.info("Aucun feedback saisi.")

# FOOTER
st.markdown("---")
st.markdown(
    "<center><small>DLP2 - Suivi Ops Journalier | "
    "Développé pour l'équipe PM DLP2</small></center>",
    unsafe_allow_html=True
)


