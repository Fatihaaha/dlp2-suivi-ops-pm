
# ==============================================
# utils.py - FONCTIONS UTILITAIRES DLP2
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
# SLACK
# ============================================
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
# FONCTIONS DE CALCUL
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


# ============================================
# TABLEAU AVEC FEEDBACK + ANALYSE
# ============================================
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
                "💬 Feedback DSP", help="Feedback envoyé au DSP",
                max_chars=500, width="large",
            ),
            "🔍 Analyse de la route": st.column_config.TextColumn(
                "🔍 Analyse de la route", help="Notre analyse interne",
                max_chars=500, width="large",
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


# ============================================
# SECTION ROUTES NA
# ============================================
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
        na_analyse = st.text_input("🔍 Analyse", key=f"na_an_{section_key}")

    if st.button("➕ Ajouter", key=f"add_na_{section_key}"):
        if na_route.strip():
            if na_key not in st.session_state.routes_na:
                st.session_state.routes_na[na_key] = []
            st.session_state.routes_na[na_key].append({
                "Route": na_route.strip(), "DSP": dsp_name,
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
                "💬 Feedback DSP": st.column_config.TextColumn("💬 Feedback", max_chars=500, width="large"),
                "🔍 Analyse de la route": st.column_config.TextColumn("🔍 Analyse", max_chars=500, width="large"),
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
# MESSAGE SLACK
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

    def apply_header(ws, row, max_col, fill):
        for col in range(1, max_col + 1):
            cell = ws.cell(row=row, column=col)
            cell.fill = fill
            cell.font = font_hdr
            cell.alignment = align_center
            cell.border = thin_border

    def apply_row(ws, row, max_col, fill=None):
        for col in range(1, max_col + 1):
            cell = ws.cell(row=row, column=col)
            cell.font = font_normal
            cell.border = thin_border
            cell.alignment = align_wrap
            if fill:
                cell.fill = fill

    def auto_w(ws, max_col):
        for col in range(1, max_col + 1):
            letter = get_column_letter(col)
            mx = 12
            for cr in ws.iter_rows(min_col=col, max_col=col, values_only=False):
                for cell in cr:
                    if cell.value:
                        mx = max(mx, min(len(str(cell.value)) + 2, 40))
            ws.column_dimensions[letter].width = mx

    reasons_list = [
        "CUSTOMER UNAVAILABLE", "BUSINESS CLOSED", "ADDRESS NOT FOUND",
        "INACCESSIBLE DELIVERY LOCATION", "RESCHEDULED BY CUSTOMER", "LOCKER ISSUE"
    ]

    with pd.ExcelWriter(output, engine='openpyxl') as writer:

        # ===== RÉSUMÉ GLOBAL =====
        pd.DataFrame().to_excel(writer, sheet_name="Résumé Global", index=False)
        ws = writer.sheets["Résumé Global"]

        ws.merge_cells('A1:I1')
        ws['A1'].value = f"📊 DLP2 - RÉSUMÉ OPS DU {now}"
        ws['A1'].fill = fill_title
        ws['A1'].font = font_title
        ws['A1'].alignment = align_center
        ws.row_dimensions[1].height = 35

        row = 3
        ws.cell(row=row, column=1).value = "📋 BILAN PAR DSP"
        ws.cell(row=row, column=1).font = Font(bold=True, size=12, color="003366")
        row += 1

        bh = ["DSP", "🔴 BEHIND", "🟠 AT_RISK", "📦 10+ Ret", "⚪ NA", "Total Ret"]
        for c, h in enumerate(bh, 1):
            ws.cell(row=row, column=c).value = h
        apply_header(ws, row, len(bh), fill_bilan_hdr)
        row += 1

        for dsp in dsps:
            dr = routes[routes["DSP"] == dsp]
            nb_b = len(dr[dr["Progression de la route"] == "BEHIND"])
            nb_a = len(dr[dr["Progression de la route"] == "AT_RISK"])
            nb_10 = len(dr[dr["retours"] >= 10])
            nb_na = len([r for r in all_na if r.get("DSP", "") == dsp])
            tot = int(dr["retours"].sum())
            ws.cell(row=row, column=1).value = dsp
            ws.cell(row=row, column=1).font = Font(bold=True, size=10)
            ws.cell(row=row, column=2).value = nb_b
            ws.cell(row=row, column=3).value = nb_a
            ws.cell(row=row, column=4).value = nb_10
            ws.cell(row=row, column=5).value = nb_na
            ws.cell(row=row, column=6).value = tot
            fl = fill_behind_row if nb_b > 0 else (fill_atrisk_row if nb_a > 0 else None)
            apply_row(ws, row, len(bh), fl)
            for c in range(2, len(bh) + 1):
                ws.cell(row=row, column=c).alignment = align_center
            row += 1

        row += 2

        # BEHIND
        if not behind.empty:
            ws.cell(row=row, column=1).value = "🔴 ROUTES EN RETARD (BEHIND)"
            ws.cell(row=row, column=1).font = Font(bold=True, size=12, color="C00000")
            row += 1
            hd = ["Route", "DSP", "Type", "Arrêts", "Effectués", "Restants", "Livraisons", "Retours", "💬 Feedback", "🔍 Analyse"]
            for c, h in enumerate(hd, 1):
                ws.cell(row=row, column=c).value = h
            apply_header(ws, row, len(hd), fill_behind_hdr)
            row += 1
            for _, r in behind.iterrows():
                rc = r["Code de la route"]
                vals = [rc, r["DSP"], drt.get(rc, "-"), r.get("Tous les arrêts", ""),
                        r.get("Arrêts effectués", ""), r.get("arrêts non démarrés", ""),
                        r.get("livraisons au total", ""), r.get("retours", 0),
                        get_feedback_for_route(rc), get_analyse_for_route(rc)]
                for c, v in enumerate(vals, 1):
                    ws.cell(row=row, column=c).value = v
                apply_row(ws, row, len(hd), fill_behind_row)
                ws.cell(row=row, column=9).fill = fill_feedback
                ws.cell(row=row, column=10).fill = fill_analyse
                row += 1
            row += 2

        # AT_RISK
        if not atrisk.empty:
            ws.cell(row=row, column=1).value = "🟠 ROUTES A RISQUE (AT_RISK)"
            ws.cell(row=row, column=1).font = Font(bold=True, size=12, color="FF8C00")
            row += 1
            hd = ["Route", "DSP", "Type", "Arrêts", "Effectués", "Restants", "Livraisons", "Retours", "💬 Feedback", "🔍 Analyse"]
            for c, h in enumerate(hd, 1):
                ws.cell(row=row, column=c).value = h
            apply_header(ws, row, len(hd), fill_atrisk_hdr)
            row += 1
            for _, r in atrisk.iterrows():
                rc = r["Code de la route"]
                vals = [rc, r["DSP"], drt.get(rc, "-"), r.get("Tous les arrêts", ""),
                        r.get("Arrêts effectués", ""), r.get("arrêts non démarrés", ""),
                        r.get("livraisons au total", ""), r.get("retours", 0),
                        get_feedback_for_route(rc), get_analyse_for_route(rc)]
                for c, v in enumerate(vals, 1):
                    ws.cell(row=row, column=c).value = v
                apply_row(ws, row, len(hd), fill_atrisk_row)
                ws.cell(row=row, column=9).fill = fill_feedback
                ws.cell(row=row, column=10).fill = fill_analyse
                row += 1
            row += 2

        # 10+ RETOURS
        if not retours10.empty:
            ws.cell(row=row, column=1).value = "📦 ROUTES AVEC 10+ RETOURS"
            ws.cell(row=row, column=1).font = Font(bold=True, size=12, color="C05000")
            row += 1
            hd = ["Route", "DSP", "Type", "Progression", "Retours",
                  "CUST.UNAVAIL", "BUS.CLOSED", "ADDR.NOTFOUND",
                  "INACCESSIBLE", "RESCHEDULED", "LOCKER", "Autres", "💬 Feedback", "🔍 Analyse"]
            for c, h in enumerate(hd, 1):
                ws.cell(row=row, column=c).value = h
            apply_header(ws, row, len(hd), fill_retour_hdr)
            row += 1
            for _, r in retours10.iterrows():
                rc = r["Code de la route"]
                ws.cell(row=row, column=1).value = rc
                ws.cell(row=row, column=2).value = r["DSP"]
                ws.cell(row=row, column=3).value = drt.get(rc, "-")
                ws.cell(row=row, column=4).value = r.get("Progression de la route", "-")
                ws.cell(row=row, column=5).value = r.get("retours", 0)
                tk = 0
                for ri, reason in enumerate(reasons_list):
                    cnt = count_reason(packages, rc, reason)
                    ws.cell(row=row, column=6 + ri).value = cnt
                    tk += cnt
                ws.cell(row=row, column=12).value = int(r.get("retours", 0)) - tk
                ws.cell(row=row, column=13).value = get_feedback_for_route(rc)
                ws.cell(row=row, column=14).value = get_analyse_for_route(rc)
                apply_row(ws, row, len(hd), fill_retour_row)
                ws.cell(row=row, column=13).fill = fill_feedback
                ws.cell(row=row, column=14).fill = fill_analyse
                row += 1
            row += 2

        # ROUTES NA
        if all_na:
            ws.cell(row=row, column=1).value = "⚪ ROUTES NA (NON TENTÉS)"
            ws.cell(row=row, column=1).font = Font(bold=True, size=12, color="607D8B")
            row += 1
            hd = ["Route", "DSP", "Nb non tentés", "💬 Feedback", "🔍 Analyse"]
            for c, h in enumerate(hd, 1):
                ws.cell(row=row, column=c).value = h
            apply_header(ws, row, len(hd), fill_na_hdr)
            row += 1
            for r in all_na:
                ws.cell(row=row, column=1).value = r.get("Route", "")
                ws.cell(row=row, column=2).value = r.get("DSP", "")
                ws.cell(row=row, column=3).value = r.get("Nb non tentés", 0)
                ws.cell(row=row, column=4).value = r.get("💬 Feedback DSP", "")
                ws.cell(row=row, column=5).value = r.get("🔍 Analyse de la route", "")
                apply_row(ws, row, len(hd), fill_na_row)
                ws.cell(row=row, column=4).fill = fill_feedback
                ws.cell(row=row, column=5).fill = fill_analyse
                row += 1

        row += 2
        ws.cell(row=row, column=1).value = f"Généré automatiquement - DLP2 - {now}"
        ws.cell(row=row, column=1).font = Font(italic=True, color="808080", size=9)
        auto_w(ws, 14)

        # ===== ONGLETS PAR DSP =====
        for dsp in dsps:
            tab = dsp[:31]
            pd.DataFrame().to_excel(writer, sheet_name=tab, index=False)
            wd = writer.sheets[tab]

            dr = routes[routes["DSP"] == dsp].copy()
            db = dr[dr["Progression de la route"] == "BEHIND"]
            da = dr[dr["Progression de la route"] == "AT_RISK"]
            d10 = dr[dr["retours"] >= 10]
            dna = [r for r in all_na if r.get("DSP", "") == dsp]

            wd.merge_cells('A1:J1')
            wd['A1'].value = f"🏢 DSP : {dsp} — {now}"
            wd['A1'].fill = fill_title
            wd['A1'].font = font_title
            wd['A1'].alignment = align_center
            wd.row_dimensions[1].height = 35

            wd.cell(row=2, column=1).value = f"BEHIND: {len(db)}"
            wd.cell(row=2, column=1).font = Font(bold=True, color="C00000")
            wd.cell(row=2, column=3).value = f"AT_RISK: {len(da)}"
            wd.cell(row=2, column=3).font = Font(bold=True, color="FF8C00")
            wd.cell(row=2, column=5).value = f"10+ Ret: {len(d10)}"
            wd.cell(row=2, column=5).font = Font(bold=True, color="C05000")
            wd.cell(row=2, column=7).value = f"NA: {len(dna)}"
            wd.cell(row=2, column=7).font = Font(bold=True, color="607D8B")

            row = 4
            dh = ["Route", "Type", "Arrêts", "Effectués", "Restants", "Livraisons", "Retours", "💬 Feedback", "🔍 Analyse"]

            if not db.empty:
                wd.cell(row=row, column=1).value = "🔴 BEHIND"
                wd.cell(row=row, column=1).font = Font(bold=True, size=11, color="C00000")
                row += 1
                for c, h in enumerate(dh, 1):
                    wd.cell(row=row, column=c).value = h
                apply_header(wd, row, len(dh), fill_behind_hdr)
                row += 1
                for _, r in db.iterrows():
                    rc = r["Code de la route"]
                    vals = [rc, drt.get(rc, "-"), r.get("Tous les arrêts", ""),
                            r.get("Arrêts effectués", ""), r.get("arrêts non démarrés", ""),
                            r.get("livraisons au total", ""), r.get("retours", 0),
                            get_feedback_for_route(rc), get_analyse_for_route(rc)]
                    for c, v in enumerate(vals, 1):
                        wd.cell(row=row, column=c).value = v
                    apply_row(wd, row, len(dh), fill_behind_row)
                    wd.cell(row=row, column=8).fill = fill_feedback
                    wd.cell(row=row, column=9).fill = fill_analyse
                    row += 1
                row += 1

            if not da.empty:
                wd.cell(row=row, column=1).value = "🟠 AT_RISK"
                wd.cell(row=row, column=1).font = Font(bold=True, size=11, color="FF8C00")
                row += 1
                for c, h in enumerate(dh, 1):
                    wd.cell(row=row, column=c).value = h
                apply_header(wd, row, len(dh), fill_atrisk_hdr)
                row += 1
                for _, r in da.iterrows():
                    rc = r["Code de la route"]
                    vals = [rc, drt.get(rc, "-"), r.get("Tous les arrêts", ""),
                            r.get("Arrêts effectués", ""), r.get("arrêts non démarrés", ""),
                            r.get("livraisons au total", ""), r.get("retours", 0),
                            get_feedback_for_route(rc), get_analyse_for_route(rc)]
                    for c, v in enumerate(vals, 1):
                        wd.cell(row=row, column=c).value = v
                    apply_row(wd, row, len(dh), fill_atrisk_row)
                    wd.cell(row=row, column=8).fill = fill_feedback
                    wd.cell(row=row, column=9).fill = fill_analyse
                    row += 1
                row += 1

            if not d10.empty:
                wd.cell(row=row, column=1).value = "📦 10+ RETOURS"
                wd.cell(row=row, column=1).font = Font(bold=True, size=11, color="C05000")
                row += 1
                rh = ["Route", "Type", "Progression", "Retours", "Raisons", "💬 Feedback", "🔍 Analyse"]
                for c, h in enumerate(rh, 1):
                    wd.cell(row=row, column=c).value = h
                apply_header(wd, row, len(rh), fill_retour_hdr)
                row += 1
                for _, r in d10.iterrows():
                    rc = r["Code de la route"]
                    vals = [rc, drt.get(rc, "-"), r.get("Progression de la route", "-"),
                            r.get("retours", 0), get_top_reasons(packages, rc),
                            get_feedback_for_route(rc), get_analyse_for_route(rc)]
                    for c, v in enumerate(vals, 1):
                        wd.cell(row=row, column=c).value = v
                    apply_row(wd, row, len(rh), fill_retour_row)
                    wd.cell(row=row, column=6).fill = fill_feedback
                    wd.cell(row=row, column=7).fill = fill_analyse
                    row += 1
                row += 1

            if dna:
                wd.cell(row=row, column=1).value = "⚪ ROUTES NA"
                wd.cell(row=row, column=1).font = Font(bold=True, size=11, color="607D8B")
                row += 1
                nh = ["Route", "Nb non tentés", "💬 Feedback", "🔍 Analyse"]
                for c, h in enumerate(nh, 1):
                    wd.cell(row=row, column=c).value = h
                apply_header(wd, row, len(nh), fill_na_hdr)
                row += 1
                for r in dna:
                    wd.cell(row=row, column=1).value = r.get("Route", "")
                    wd.cell(row=row, column=2).value = r.get("Nb non tentés", 0)
                    wd.cell(row=row, column=3).value = r.get("💬 Feedback DSP", "")
                    wd.cell(row=row, column=4).value = r.get("🔍 Analyse de la route", "")
                    apply_row(wd, row, len(nh), fill_na_row)
                    wd.cell(row=row, column=3).fill = fill_feedback
                    wd.cell(row=row, column=4).fill = fill_analyse
                    row += 1

            if db.empty and da.empty and d10.empty and not dna:
                wd.cell(row=row, column=1).value = "✅ RAS pour ce DSP"
                wd.cell(row=row, column=1).font = Font(bold=True, color="008000", size=11)

            auto_w(wd, 9)

    output.seek(0)
    return output

