
# ==============================================
# DLP2 - APPLICATION WEB STREAMLIT v4
# ==============================================
# Fonctionnalités :
#   - Analyse routes BEHIND, AT_RISK, 10+ retours, NA
#   - Colonne Feedback DSP + Analyse de la route
#   - Synchronisation auto vers Résumé Global
#   - Export Excel formaté avec codes couleurs pour SharePoint
#   - Envoi Slack par DSP
# ==============================================
# Installation : pip install streamlit pandas requests openpyxl
# Lancement   : streamlit run app.py
# ==============================================

import streamlit as st
import pandas as pd
import requests
import json
import io
from datetime import datetime
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

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
    parts = [f"{reason}: {count}" for reason, count in counts.items()]
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


def get_all_na_routes():
    all_na = []
    for na_key, na_list in st.session_state.routes_na.items():
        for item in na_list:
            all_na.append(item)
    return all_na


def afficher_tableau_avec_feedback(df, section_key, sync_to_global=False):
    df = df.copy()
    df["💬 Feedback DSP"] = ""
    df["🔍 Analyse de la route"] = ""

    for idx, row in df.iterrows():
        route_id = str(row.get("Route", idx))
        fb_key = f"{section_key}_{route_id}"

        if fb_key in st.session_state.dsp_feedbacks:
            df.at[idx, "💬 Feedback DSP"] = st.session_state.dsp_feedbacks[fb_key]
        elif sync_to_global:
            fb = get_feedback_for_route(route_id)
            if fb:
                df.at[idx, "💬 Feedback DSP"] = fb

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
            if na_feedback.strip():
                st.session_state.dsp_feedbacks[f"route_{na_route.strip()}"] = na_feedback.strip()
            if na_analyse.strip():
                st.session_state.dsp_analyses[f"route_{na_route.strip()}"] = na_analyse.strip()
            st.success(f"✅ Route {na_route} ajoutée !")
            st.rerun()
        else:
            st.warning("Saisis un code route")

    if na_key in st.session_state.routes_na and st.session_state.routes_na[na_key]:
        na_df = pd.DataFrame(st.session_state.routes_na[na_key])
        edited_na = st.data_editor(
            na_df,
            column_config={
                "💬 Feedback DSP": st.column_config.TextColumn(
                    "💬 Feedback DSP", max_chars=500, width="large"
                ),
                "🔍 Analyse de la route": st.column_config.TextColumn(
                    "🔍 Analyse", max_chars=500, width="large"
                ),
            },
            disabled=["Route", "DSP"],
            hide_index=True,
            use_container_width=True,
            key=f"editor_na_{section_key}"
        )
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


# ============================================
# GÉNÉRATION EXCEL FORMATÉ
# ============================================
def generate_excel_summary(routes, behind, atrisk, retours10, packages, drt, dsps):
    output = io.BytesIO()
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    all_na = get_all_na_routes()

    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    fill_title = PatternFill(start_color="003366", end_color="003366", fill_type="solid")
    font_title = Font(bold=True, color="FFFFFF", size=14)
    fill_behind_hdr = PatternFill(start_color="C00000", end_color="C00000", fill_type="solid")
    fill_atrisk_hdr = PatternFill(start_color="FF8C00", end_color="FF8C00", fill_type="solid")
    fill_retour_hdr = PatternFill(start_color="C05000", end_color="C05000", fill_type="solid")
    fill_na_hdr = PatternFill(start_color="607D8B", end_color="607D8B", fill_type="solid")
    fill_bilan_hdr = PatternFill(start_color="003366", end_color="003366", fill_type="solid")
    font_hdr = Font(bold=True, color="FFFFFF", size=10)
    fill_behind_row = PatternFill(start_color="FFE0E0", end_color="FFE0E0", fill_type="solid")
    fill_atrisk_row = PatternFill(start_color="FFF3E0", end_color="FFF3E0", fill_type="solid")
    fill_retour_row = PatternFill(start_color="FFEBCD", end_color="FFEBCD", fill_type="solid")
    fill_na_row = PatternFill(start_color="ECEFF1", end_color="ECEFF1", fill_type="solid")
    fill_feedback = PatternFill(start_color="FFFFF0", end_color="FFFFF0", fill_type="solid")
    fill_analyse = PatternFill(start_color="F0F8FF", end_color="F0F8FF", fill_type="solid")
    font_normal = Font(size=10)
    align_center = Alignment(horizontal="center", vertical="center")
    align_wrap = Alignment(wrap_text=True, vertical="top")

    def apply_header_style(ws, row, max_col, fill):
        for col in range(1, max_col + 1):
            cell = ws.cell(row=row, column=col)
            cell.fill = fill
            cell.font = font_hdr
            cell.alignment = align_center
            cell.border = thin_border

    def apply_row_style(ws, row, max_col, fill=None):
        for col in range(1, max_col + 1):
            cell = ws.cell(row=row, column=col)
            cell.font = font_normal
            cell.border = thin_border
            cell.alignment = align_wrap
            if fill:
                cell.fill = fill

    def auto_width(ws, max_col, min_w=12, max_w=40):
        for col in range(1, max_col + 1):
            letter = get_column_letter(col)
            max_len = min_w
            for cell_row in ws.iter_rows(min_col=col, max_col=col, values_only=False):
                for cell in cell_row:
                    if cell.value:
                        max_len = max(max_len, min(len(str(cell.value)) + 2, max_w))
            ws.column_dimensions[letter].width = max_len

    with pd.ExcelWriter(output, engine='openpyxl') as writer:

        # ========== ONGLET RÉSUMÉ GLOBAL ==========
        ws_name = "Résumé Global"
        pd.DataFrame().to_excel(writer, sheet_name=ws_name, index=False)
        ws = writer.sheets[ws_name]

        ws.merge_cells('A1:I1')
        ws['A1'].value = f"📊 DLP2 - RÉSUMÉ OPS DU {now}"
        ws['A1'].fill = fill_title
        ws['A1'].font = font_title
        ws['A1'].alignment = align_center
        ws.row_dimensions[1].height = 35

        row = 3

        # BILAN PAR DSP
        ws.cell(row=row, column=1).value = "📋 BILAN PAR DSP"
        ws.cell(row=row, column=1).font = Font(bold=True, size=12, color="003366")
        row += 1

        bilan_headers = ["DSP", "🔴 BEHIND", "🟠 AT_RISK", "📦 10+ Retours", "⚪ NA", "Total Retours"]
        for c, h in enumerate(bilan_headers, 1):
            ws.cell(row=row, column=c).value = h
        apply_header_style(ws, row, len(bilan_headers), fill_bilan_hdr)
        row += 1

        for dsp in dsps:
            dsp_r = routes[routes["DSP"] == dsp]
            nb_b = len(dsp_r[dsp_r["Progression de la route"] == "BEHIND"])
            nb_a = len(dsp_r[dsp_r["Progression de la route"] == "AT_RISK"])
            nb_10 = len(dsp_r[dsp_r["retours"] >= 10])
            nb_na = len([r for r in all_na if r.get("DSP", "") == dsp])
            tot = int(dsp_r["retours"].sum())

            ws.cell(row=row, column=1).value = dsp
            ws.cell(row=row, column=1).font = Font(bold=True, size=10)
            ws.cell(row=row, column=2).value = nb_b
            ws.cell(row=row, column=3).value = nb_a
            ws.cell(row=row, column=4).value = nb_10
            ws.cell(row=row, column=5).value = nb_na
            ws.cell(row=row, column=6).value = tot

            fill = None
            if nb_b > 0:
                fill = fill_behind_row
            elif nb_a > 0:
                fill = fill_atrisk_row
            apply_row_style(ws, row, len(bilan_headers), fill)
            for c in range(2, len(bilan_headers) + 1):
                ws.cell(row=row, column=c).alignment = align_center
            row += 1

        row += 2

        # BEHIND
        if not behind.empty:
            ws.cell(row=row, column=1).value = "🔴 ROUTES EN RETARD (BEHIND)"
            ws.cell(row=row, column=1).font = Font(bold=True, size=12, color="C00000")
            row += 1

            behind_headers = ["Route", "DSP", "Type", "Arrêts", "Effectués", "Restants",
                              "Livraisons", "Retours", "💬 Feedback DSP", "🔍 Analyse"]
            for c, h in enumerate(behind_headers, 1):
                ws.cell(row=row, column=c).value = h
            apply_header_style(ws, row, len(behind_headers), fill_behind_hdr)
            row += 1

            for _, r in behind.iterrows():
                rc = r["Code de la route"]
                ws.cell(row=row, column=1).value = rc
                ws.cell(row=row, column=2).value = r["DSP"]
                ws.cell(row=row, column=3).value = drt.get(rc, "-")
                ws.cell(row=row, column=4).value = r.get("Tous les arrêts", "")
                ws.cell(row=row, column=5).value = r.get("Arrêts effectués", "")
                ws.cell(row=row, column=6).value = r.get("arrêts non démarrés", "")
                ws.cell(row=row, column=7).value = r.get("livraisons au total", "")
                ws.cell(row=row, column=8).value = r.get("retours", 0)
                ws.cell(row=row, column=9).value = get_feedback_for_route(rc)
                ws.cell(row=row, column=10).value = get_analyse_for_route(rc)
                apply_row_style(ws, row, len(behind_headers), fill_behind_row)
                ws.cell(row=row, column=9).fill = fill_feedback
                ws.cell(row=row, column=10).fill = fill_analyse
                row += 1
            row += 2

        # AT_RISK
        if not atrisk.empty:
            ws.cell(row=row, column=1).value = "🟠 ROUTES A RISQUE (AT_RISK)"
            ws.cell(row=row, column=1).font = Font(bold=True, size=12, color="FF8C00")
            row += 1

            atrisk_headers = ["Route", "DSP", "Type", "Arrêts", "Effectués", "Restants",
                              "Livraisons", "Retours", "💬 Feedback DSP", "🔍 Analyse"]
            for c, h in enumerate(atrisk_headers, 1):
                ws.cell(row=row, column=c).value = h
            apply_header_style(ws, row, len(atrisk_headers), fill_atrisk_hdr)
            row += 1

            for _, r in atrisk.iterrows():
                rc = r["Code de la route"]
                ws.cell(row=row, column=1).value = rc
                ws.cell(row=row, column=2).value = r["DSP"]
                ws.cell(row=row, column=3).value = drt.get(rc, "-")
                ws.cell(row=row, column=4).value = r.get("Tous les arrêts", "")
                ws.cell(row=row, column=5).value = r.get("Arrêts effectués", "")
                ws.cell(row=row, column=6).value = r.get("arrêts non démarrés", "")
                ws.cell(row=row, column=7).value = r.get("livraisons au total", "")
                ws.cell(row=row, column=8).value = r.get("retours", 0)
                ws.cell(row=row, column=9).value = get_feedback_for_route(rc)
                ws.cell(row=row, column=10).value = get_analyse_for_route(rc)
                apply_row_style(ws, row, len(atrisk_headers), fill_atrisk_row)
                ws.cell(row=row, column=9).fill = fill_feedback
                ws.cell(row=row, column=10).fill = fill_analyse
                row += 1
            row += 2

        # 10+ RETOURS
        if not retours10.empty:
            ws.cell(row=row, column=1).value = "📦 ROUTES AVEC 10+ RETOURS"
            ws.cell(row=row, column=1).font = Font(bold=True, size=12, color="C05000")
            row += 1

            ret_headers = ["Route", "DSP", "Type", "Progression", "Retours",
                           "CUST. UNAVAIL.", "BUS. CLOSED", "ADDR NOT FOUND",
                           "INACCESSIBLE", "RESCHEDULED", "LOCKER", "Autres",
                           "💬 Feedback DSP", "🔍 Analyse"]
            for c, h in enumerate(ret_headers, 1):
                ws.cell(row=row, column=c).value = h
            apply_header_style(ws, row, len(ret_headers), fill_retour_hdr)
            row += 1

            reasons_list = [
                "CUSTOMER UNAVAILABLE", "BUSINESS CLOSED", "ADDRESS NOT FOUND",
                "INACCESSIBLE DELIVERY LOCATION", "RESCHEDULED BY CUSTOMER", "LOCKER ISSUE"
            ]
            for _, r in retours10.iterrows():
                rc = r["Code de la route"]
                ws.cell(row=row, column=1).value = rc
                ws.cell(row=row, column=2).value = r["DSP"]
                ws.cell(row=row, column=3).value = drt.get(rc, "-")
                ws.cell(row=row, column=4).value = r.get("Progression de la route", "-")
                ws.cell(row=row, column=5).value = r.get("retours", 0)
                total_known = 0
                for ri, reason in enumerate(reasons_list):
                    c = count_reason(packages, rc, reason)
                    ws.cell(row=row, column=6 + ri).value = c
                    total_known += c
                ws.cell(row=row, column=12).value = int(r.get("retours", 0)) - total_known
                ws.cell(row=row, column=13).value = get_feedback_for_route(rc)
                ws.cell(row=row, column=14).value = get_analyse_for_route(rc)
                apply_row_style(ws, row, len(ret_headers), fill_retour_row)
                ws.cell(row=row, column=13).fill = fill_feedback
                ws.cell(row=row, column=14).fill = fill_analyse
                row += 1
            row += 2

        # ROUTES NA
        if all_na:
            ws.cell(row=row, column=1).value = "⚪ ROUTES NA (NON TENTÉS)"
            ws.cell(row=row, column=1).font = Font(bold=True, size=12, color="607D8B")
            row += 1

            na_headers = ["Route", "DSP", "Nb non tentés", "💬 Feedback DSP", "🔍 Analyse"]
            for c, h in enumerate(na_headers, 1):
                ws.cell(row=row, column=c).value = h
            apply_header_style(ws, row, len(na_headers), fill_na_hdr)
            row += 1

            for r in all_na:
                ws.cell(row=row, column=1).value = r.get("Route", "")
                ws.cell(row=row, column=2).value = r.get("DSP", "")
                ws.cell(row=row, column=3).value = r.get("Nb non tentés", 0)
                ws.cell(row=row, column=4).value = r.get("💬 Feedback DSP", "")
                ws.cell(row=row, column=5).value = r.get("🔍 Analyse de la route", "")
                apply_row_style(ws, row, len(na_headers), fill_na_row)
                ws.cell(row=row, column=4).fill = fill_feedback
                ws.cell(row=row, column=5).fill = fill_analyse
                row += 1

        row += 2
        ws.cell(row=row, column=1).value = f"Généré automatiquement - DLP2 Suivi Ops - {now}"
        ws.cell(row=row, column=1).font = Font(italic=True, color="808080", size=9)
        auto_width(ws, 14)

        # ========== ONGLETS PAR DSP ==========
        for dsp in dsps:
            tab_name = dsp[:31]
            pd.DataFrame().to_excel(writer, sheet_name=tab_name, index=False)
            ws_dsp = writer.sheets[tab_name]

            dsp_routes = routes[routes["DSP"] == dsp].copy()
            dsp_behind = dsp_routes[dsp_routes["Progression de la route"] == "BEHIND"]
            dsp_atrisk = dsp_routes[dsp_routes["Progression de la route"] == "AT_RISK"]
            dsp_ret10 = dsp_routes[dsp_routes["retours"] >= 10]
            dsp_na = [r for r in all_na if r.get("DSP", "") == dsp]

            ws_dsp.merge_cells('A1:J1')
            ws_dsp['A1'].value = f"🏢 DSP : {dsp} — {now}"
            ws_dsp['A1'].fill = fill_title
            ws_dsp['A1'].font = font_title
            ws_dsp['A1'].alignment = align_center
            ws_dsp.row_dimensions[1].height = 35

            ws_dsp.cell(row=2, column=1).value = f"BEHIND: {len(dsp_behind)}"
            ws_dsp.cell(row=2, column=1).font = Font(bold=True, color="C00000")
            ws_dsp.cell(row=2, column=3).value = f"AT_RISK: {len(dsp_atrisk)}"
            ws_dsp.cell(row=2, column=3).font = Font(bold=True, color="FF8C00")
            ws_dsp.cell(row=2, column=5).value = f"10+ Ret: {len(dsp_ret10)}"
            ws_dsp.cell(row=2, column=5).font = Font(bold=True, color="C05000")
            ws_dsp.cell(row=2, column=7).value = f"NA: {len(dsp_na)}"
            ws_dsp.cell(row=2, column=7).font = Font(bold=True, color="607D8B")

            row = 4
            dsp_headers = ["Route", "Type", "Arrêts", "Effectués", "Restants",
                           "Livraisons", "Retours", "💬 Feedback DSP", "🔍 Analyse"]

            if not dsp_behind.empty:
                ws_dsp.cell(row=row, column=1).value = "🔴 BEHIND"
                ws_dsp.cell(row=row, column=1).font = Font(bold=True, size=11, color="C00000")
                row += 1
                for c, h in enumerate(dsp_headers, 1):
                    ws_dsp.cell(row=row, column=c).value = h
                apply_header_style(ws_dsp, row, len(dsp_headers), fill_behind_hdr)
                row += 1
                for _, r in dsp_behind.iterrows():
                    rc = r["Code de la route"]
                    ws_dsp.cell(row=row, column=1).value = rc
                    ws_dsp.cell(row=row, column=2).value = drt.get(rc, "-")
                    ws_dsp.cell(row=row, column=3).value = r.get("Tous les arrêts", "")
                    ws_dsp.cell(row=row, column=4).value = r.get("Arrêts effectués", "")
                    ws_dsp.cell(row=row, column=5).value = r.get("arrêts non démarrés", "")
                    ws_dsp.cell(row=row, column=6).value = r.get("livraisons au total", "")
                    ws_dsp.cell(row=row, column=7).value = r.get("retours", 0)
                    ws_dsp.cell(row=row, column=8).value = get_feedback_for_route(rc)
                    ws_dsp.cell(row=row, column=9).value = get_analyse_for_route(rc)
                    apply_row_style(ws_dsp, row, len(dsp_headers), fill_behind_row)
                    ws_dsp.cell(row=row, column=8).fill = fill_feedback
                    ws_dsp.cell(row=row, column=9).fill = fill_analyse
                    row += 1
                row += 1

            if not dsp_atrisk.empty:
                ws_dsp.cell(row=row, column=1).value = "🟠 AT_RISK"
                ws_dsp.cell(row=row, column=1).font = Font(bold=True, size=11, color="FF8C00")
                row += 1
                for c, h in enumerate(dsp_headers, 1):
                    ws_dsp.cell(row=row, column=c).value = h
                apply_header_style(ws_dsp, row, len(dsp_headers), fill_atrisk_hdr)
                row += 1
                for _, r in dsp_atrisk.iterrows():
                    rc = r["Code de la route"]
                    ws_dsp.cell(row=row, column=1).value = rc
                    ws_dsp.cell(row=row, column=2).value = drt.get(rc, "-")
                    ws_dsp.cell(row=row, column=3).value = r.get("Tous les arrêts", "")
                    ws_dsp.cell(row=row, column=4).value = r.get("Arrêts effectués", "")
                    ws_dsp.cell(row=row, column=5).value = r.get("arrêts non démarrés", "")
                    ws_dsp.cell(row=row, column=6).value = r.get("livraisons au total", "")
                    ws_dsp.cell(row=row, column=7).value = r.get("retours", 0)
                    ws_dsp.cell(row=row, column=8).value = get_feedback_for_route(rc)
                    ws_dsp.cell(row=row, column=9).value = get_analyse_for_route(rc)
                    apply_row_style(ws_dsp, row, len(dsp_headers), fill_atrisk_row)
                    ws_dsp.cell(row=row, column=8).fill = fill_feedback
                    ws_dsp.cell(row=row, column=9).fill = fill_analyse
                    row += 1
                row += 1

            if not dsp_ret10.empty:
                ws_dsp.cell(row=row, column=1).value = "📦 10+ RETOURS"
                ws_dsp.cell(row=row, column=1).font = Font(bold=True, size=11, color="C05000")
                row += 1
                ret_h = ["Route", "Type", "Progression", "Retours", "Raisons",
                         "💬 Feedback DSP", "🔍 Analyse"]
                for c, h in enumerate(ret_h, 1):
                    ws_dsp.cell(row=row, column=c).value = h
                apply_header_style(ws_dsp, row, len(ret_h), fill_retour_hdr)
                row += 1
                for _, r in dsp_ret10.iterrows():
                    rc = r["Code de la route"]
                    ws_dsp.cell(row=row, column=1).value = rc
                    ws_dsp.cell(row=row, column=2).value = drt.get(rc, "-")
                    ws_dsp.cell(row=row, column=3).value = r.get("Progression de la route", "-")
                    ws_dsp.cell(row=row, column=4).value = r.get("retours", 0)
                    ws_dsp.cell(row=row, column=5).value = get_top_reasons(packages, rc)
                    ws_dsp.cell(row=row, column=6).value = get_feedback_for_route(rc)
                    ws_dsp.cell(row=row, column=7).value = get_analyse_for_route(rc)
                    apply_row_style(ws_dsp, row, len(ret_h), fill_retour_row)
                    ws_dsp.cell(row=row, column=6).fill = fill_feedback
                    ws_dsp.cell(row=row, column=7).fill = fill_analyse
                    row += 1
                row += 1

            if dsp_na:
                ws_dsp.cell(row=row, column=1).value = "⚪ ROUTES NA"
                ws_dsp.cell(row=row, column=1).font = Font(bold=True, size=11, color="607D8B")
                row += 1
                na_h = ["Route", "Nb non tentés", "💬 Feedback DSP", "🔍 Analyse"]
                for c, h in enumerate(na_h, 1):
                    ws_dsp.cell(row=row, column=c).value = h
                apply_header_style(ws_dsp, row, len(na_h), fill_na_hdr)
                row += 1
                for r in dsp_na:
                    ws_dsp.cell(row=row, column=1).value = r.get("Route", "")
                    ws_dsp.cell(row=row, column=2).value = r.get("Nb non tentés", 0)
                    ws_dsp.cell(row=row, column=3).value = r.get("💬 Feedback DSP", "")
                    ws_dsp.cell(row=row, column=4).value = r.get("🔍 Analyse de la route", "")
                    apply_row_style(ws_dsp, row, len(na_h), fill_na_row)
                    ws_dsp.cell(row=row, column=3).fill = fill_feedback
                    ws_dsp.cell(row=row, column=4).fill = fill_analyse
                    row += 1

            if dsp_behind.empty and dsp_atrisk.empty and dsp_ret10.empty and not dsp_na:
                ws_dsp.cell(row=row, column=1).value = "✅ Aucun problème à signaler pour ce DSP"
                ws_dsp.cell(row=row, column=1).font = Font(bold=True, color="008000", size=11)

            auto_width(ws_dsp, 9)

    output.seek(0)
    return output


# ============================================
# SLACK MESSAGE
# ============================================
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

    if na_routes:
        dsp_na = [r for r in na_routes if r.get("DSP", "") == dsp_name]
        if dsp_na:
            msg += "*Routes NA (non tentés) :*\n"
            for r in dsp_na:
                msg += f"  - {r['Route']} : *{r['Nb non tentés']} non tentés*\n"

    return msg


# ============================================
# STYLE CSS
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

if file_routes is None or file_packages is None:
    st.info("👈 Chargez vos fichiers CSV dans la barre latérale pour lancer l'analyse.")
    st.markdown("### 📋 Mode d'emploi")
    st.markdown("""
    1. **Glissez-déposez** vos fichiers CSV
    2. L'analyse se lance **automatiquement**
    3. Saisissez vos **💬 Feedbacks** et **🔍 Analyses** → synchronisation auto
    4. Ajoutez des **routes NA** (non tentés)
    5. Cliquez **📥 Télécharger Excel** pour exporter le résumé formaté pour SharePoint
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
        '<div class="sync-info">🔄 Les feedbacks et analyses saisis dans les onglets DSP '
        'apparaissent automatiquement ici.</div>',
        unsafe_allow_html=True
    )
    st.markdown("")

    # BEHIND
    st.markdown('<span class="behind-badge">ROUTES EN RETARD (BEHIND)</span>', unsafe_allow_html=True)
    if not behind.empty:
        display_behind = behind[[
            "Code de la route", "DSP", "Type", "Tous les arrêts",
            "Arrêts effectués", "arrêts non démarrés", "livraisons au total", "retours"
        ]].copy()
        display_behind.columns = ["Route", "DSP", "Type", "Arrêts", "Effectués", "Restants", "Livraisons", "Retours"]
        afficher_tableau_avec_feedback(display_behind, "global_behind", sync_to_global=True)
    else:
        st.success("✅ Aucune route en retard")

    st.markdown("---")

    # AT_RISK
    st.markdown('<span class="atrisk-badge">ROUTES A RISQUE (AT_RISK)</span>', unsafe_allow_html=True)
    if not atrisk.empty:
        display_atrisk = atrisk[[
            "Code de la route", "DSP", "Type", "Tous les arrêts",
            "Arrêts effectués", "arrêts non démarrés", "livraisons au total", "retours"
        ]].copy()
        display_atrisk.columns = ["Route", "DSP", "Type", "Arrêts", "Effectués", "Restants", "Livraisons", "Retours"]
        afficher_tableau_avec_feedback(display_atrisk, "global_atrisk", sync_to_global=True)
    else:
        st.success("✅ Aucune route à risque")

    st.markdown("---")

    # 10+ RETOURS
    st.markdown('<span class="retour-badge">ROUTES AVEC 10+ RETOURS</span>', unsafe_allow_html=True)
    if not retours10.empty:
        reasons_list = [
            "CUSTOMER UNAVAILABLE", "BUSINESS CLOSED", "ADDRESS NOT FOUND",
            "INACCESSIBLE DELIVERY LOCATION", "RESCHEDULED BY CUSTOMER", "LOCKER ISSUE"
        ]
        rows = []
        for _, r in retours10.iterrows():
            rc = r["Code de la route"]
            row_data = {
                "Route": rc, "DSP": r["DSP"], "Type": r["Type"],
                "Progression": r["Progression de la route"], "Retours": r["retours"]
            }
            total_known = 0
            for reason in reasons_list:
                c = count_reason(packages, rc, reason)
                short = reason.split()[0][:8]
                row_data[short] = c
                total_known += c
            row_data["Autres"] = r["retours"] - total_known
            rows.append(row_data)
        afficher_tableau_avec_feedback(pd.DataFrame(rows), "global_retours", sync_to_global=True)
    else:
        st.success("✅ Aucune route avec 10+ retours")

    st.markdown("---")

    # ROUTES NA
    st.markdown('<span class="na-badge">ROUTES NA (NON TENTÉS)</span>', unsafe_allow_html=True)
    all_na = get_all_na_routes()
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
        bilan_rows.append({
            "DSP": dsp,
            "BEHIND": len(dsp_routes[dsp_routes["Progression de la route"] == "BEHIND"]),
            "AT_RISK": len(dsp_routes[dsp_routes["Progression de la route"] == "AT_RISK"]),
            "10+ Retours": len(dsp_routes[dsp_routes["retours"] >= 10]),
            "NA": len([r for r in all_na if r.get("DSP", "") == dsp]),
            "Total Retours": int(dsp_routes["retours"].sum())
        })
    st.dataframe(pd.DataFrame(bilan_rows), use_container_width=True, hide_index=True)

    # EXPORT EXCEL
    st.markdown("---")
    st.markdown("### 📥 Exporter pour SharePoint")
    st.markdown(
        '<div class="excel-box">'
        '<b>📥 Résumé Excel formaté</b><br>'
        'Fichier Excel avec codes couleurs, tableaux, feedbacks et analyses.<br>'
        'Prêt à être uploadé sur SharePoint !</div>',
        unsafe_allow_html=True
    )

    if st.button("📥 Générer le fichier Excel", key="gen_excel", type="primary"):
        with st.spinner("Génération du fichier Excel en cours..."):
            excel_data = generate_excel_summary(
                routes, behind, atrisk, retours10, packages, drt, dsps
            )
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
        st.info(
            "💡 **Comment mettre sur SharePoint :**\n"
            "1. Téléchargez le fichier Excel\n"
            "2. Ouvrez votre SharePoint → Bibliothèque de documents\n"
            "3. Cliquez **Charger** → sélectionnez le fichier\n"
            "4. Le fichier s'ouvre directement dans le navigateur avec les couleurs !"
        )


# ============================================
# ONGLETS PAR DSP
# ============================================
for idx, dsp in enumerate(dsps):
    with tabs[idx + 1]:
        st.markdown(f"## 🏢 {dsp}")
        st.caption(f"Analyse du {now_str}")
        st.markdown(
            '<div class="sync-info">🔄 Feedbacks et analyses se synchronisent '
            'automatiquement dans le Résumé Global.</div>',
            unsafe_allow_html=True
        )
        st.markdown("")

        dsp_routes = routes[routes["DSP"] == dsp].copy()
        dsp_behind = dsp_routes[dsp_routes["Progression de la route"] == "BEHIND"]
        dsp_atrisk = dsp_routes[dsp_routes["Progression de la route"] == "AT_RISK"]
        dsp_ret10 = dsp_routes[dsp_routes["retours"] >= 10]
        dsp_na_list = [r for r in all_na if r.get("DSP", "") == dsp]

        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.metric("🔴 BEHIND", len(dsp_behind))
        with c2:
            st.metric("🟠 AT_RISK", len(dsp_atrisk))
        with c3:
            st.metric("📦 10+ Ret.", len(dsp_ret10))
        with c4:
            st.metric("⚪ NA", len(dsp_na_list))
        with c5:
            st.metric("📊 Total Ret.", int(dsp_routes["retours"].sum()))

        # BEHIND
        st.markdown('<span class="behind-badge">ROUTES EN RETARD (BEHIND)</span>', unsafe_allow_html=True)
        if not dsp_behind.empty:
            df_b = dsp_behind[[
                "Code de la route", "Type", "Tous les arrêts",
                "Arrêts effectués", "arrêts non démarrés", "livraisons au total", "retours"
            ]].copy()
            df_b.columns = ["Route", "Type", "Arrêts", "Effectués", "Restants", "Livraisons", "Retours"]
            afficher_tableau_avec_feedback(df_b, f"dsp_{dsp}_behind")
        else:
            st.success("✅ Aucune route en retard")

        # AT_RISK
        st.markdown('<span class="atrisk-badge">ROUTES A RISQUE (AT_RISK)</span>', unsafe_allow_html=True)
        if not dsp_atrisk.empty:
            df_a = dsp_atrisk[[
                "Code de la route", "Type", "Tous les arrêts",
                "Arrêts effectués", "arrêts non démarrés", "livraisons au total", "retours"
            ]].copy()
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
            prog_map = dict(zip(
                dsp_routes["Code de la route"],
                dsp_routes["Progression de la route"]
            ))
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
            if dsp in all_webhooks:
                if dsp in st.session_state.sent_messages:
                    st.markdown(
                        f'<div class="sent-ok">✅ Envoyé à '
                        f'{st.session_state.sent_messages[dsp]}</div>',
                        unsafe_allow_html=True
                    )
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
# ONGLET TOUS LES FEEDBACKS
# ============================================
with tabs[-1]:
    st.markdown("## 📝 Tous les Feedbacks & Analyses")

    all_route_keys = set()
    for fb_key in st.session_state.dsp_feedbacks:
        if fb_key.startswith("route_"):
            all_route_keys.add(fb_key.replace("route_", ""))
    for a_key in st.session_state.dsp_analyses:
        
