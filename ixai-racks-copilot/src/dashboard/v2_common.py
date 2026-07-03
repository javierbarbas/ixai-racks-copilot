from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.chat_interface import init_chat_session, render_chat_interface
from src.data.excel_capture import load_capture_dataframe, save_capture_dataframe
from src.data.warehouse import load_warehouse_bundle, run_ingest_refresh


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STYLE_PATH = PROJECT_ROOT / "src" / "styles" / "style.css"

URGENCY_ORDER = {
    "Vencida": 0,
    "Semana actual": 1,
    "Proximas 2 semanas": 2,
    "Futura": 3,
    "Sin fecha": 4,
}

URGENCY_COLOR = {
    "Vencida": "#d84f60",
    "Semana actual": "#ff8c42",
    "Proximas 2 semanas": "#57b7ff",
    "Futura": "#4f7cac",
    "Sin fecha": "#94a3b8",
}


def configure_page(title: str) -> None:
    st.set_page_config(page_title=title, page_icon="📦", layout="wide", initial_sidebar_state="expanded")
    if STYLE_PATH.exists():
        st.markdown(f"<style>{STYLE_PATH.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
        st.markdown(
                """
                <style>
                [data-testid="stSidebar"],
                [data-testid="stSidebarCollapsedControl"] {
                    display: block !important;
                }

                [data-testid="stSidebar"] {
                    min-width: 320px !important;
                    max-width: 320px !important;
                    border-right: 1px solid rgba(255, 255, 255, 0.12) !important;
                    background: linear-gradient(180deg, rgba(16, 21, 31, 0.98), rgba(12, 17, 26, 0.98)) !important;
                }

                [data-testid="stSidebar"] * {
                    color: #f4f6fa !important;
                }

                [data-testid="stSidebarNav"] {
                    display: none !important;
                }
                </style>
                """,
                unsafe_allow_html=True,
        )


def load_bundle() -> dict[str, pd.DataFrame]:
    return load_warehouse_bundle()


def render_sidebar(df: pd.DataFrame) -> dict[str, object]:
    with st.sidebar:
        st.page_link("main.py", label="Inicio", icon="🏠")
        st.page_link("pages/2_Operacion_Semanal.py", label="Operacion Semanal", icon="📅")
        st.page_link("pages/3_Detalle_PO_Planeador.py", label="Detalle PO Planeador", icon="📋")
        st.page_link("pages/4_Pregunta_tus_Datos.py", label="Pregunta tus Datos", icon="🤖")
        st.page_link("pages/5_Captura_Datos.py", label="Captura de Datos", icon="📝")
        st.divider()
        st.markdown("## Control Global")

        if st.button("Actualizar datos", width="stretch"):
            with st.spinner("Ejecutando ETL..."):
                output = run_ingest_refresh()
            st.success("DuckDB actualizado")
            st.caption(output.splitlines()[-1] if output else "ETL completado")
            st.rerun()

        date_series = pd.to_datetime(df.get("fecha_entrega_real"), errors="coerce")
        valid_dates = date_series.dropna()
        min_date = valid_dates.min().date() if not valid_dates.empty else pd.Timestamp.today().date()
        max_date = valid_dates.max().date() if not valid_dates.empty else pd.Timestamp.today().date()

        date_range = st.date_input(
            "Rango de entrega",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key="global_date_range",
        )
        if not isinstance(date_range, tuple) or len(date_range) != 2:
            date_range = (min_date, max_date)

        planeadores = sorted(df["Planeador"].dropna().astype(str).unique().tolist()) if "Planeador" in df.columns else []
        ingenieros = sorted(df["Ingeniero"].dropna().astype(str).unique().tolist()) if "Ingeniero" in df.columns else []
        estatus = sorted(df["estatus_real"].dropna().astype(str).unique().tolist()) if "estatus_real" in df.columns else []

        selected_planeadores = st.multiselect("Planeador", planeadores, default=planeadores, key="global_planeadores")
        selected_ingenieros = st.multiselect("Ingeniero", ingenieros, default=ingenieros, key="global_ingenieros")
        selected_estatus = st.multiselect("Estatus real", estatus, default=estatus, key="global_estatus")

    return {
        "date_range": date_range,
        "planeadores": selected_planeadores,
        "ingenieros": selected_ingenieros,
        "estatus": selected_estatus,
    }


def apply_filters(df: pd.DataFrame, filters: dict[str, object]) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    out = df.copy()
    date_range = filters.get("date_range")
    if isinstance(date_range, tuple) and len(date_range) == 2 and "fecha_entrega_real" in out.columns:
        start_date, end_date = date_range
        fechas = pd.to_datetime(out["fecha_entrega_real"], errors="coerce").dt.date
        out = out[(fechas >= start_date) & (fechas <= end_date)]

    if filters.get("planeadores") and "Planeador" in out.columns:
        out = out[out["Planeador"].astype(str).isin(filters["planeadores"])]

    if filters.get("ingenieros") and "Ingeniero" in out.columns:
        out = out[out["Ingeniero"].astype(str).isin(filters["ingenieros"])]

    if filters.get("estatus") and "estatus_real" in out.columns:
        out = out[out["estatus_real"].astype(str).isin(filters["estatus"])]

    return out.reset_index(drop=True)


def _safe_pct(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _render_summary_kpis(df: pd.DataFrame) -> None:
    qty = pd.to_numeric(df.get("Qty."), errors="coerce").fillna(0)
    entregados = pd.to_numeric(df.get("Entregados"), errors="coerce").fillna(0)
    valor_pendiente = pd.to_numeric(df.get("valor_pendiente"), errors="coerce").fillna(0)

    total_qty = float(qty.sum())
    total_entregados = float(entregados.sum())
    avance_global = _safe_pct(total_entregados, total_qty) * 100
    valor_pendiente_total = float(valor_pendiente.sum())

    riesgo_mask = df["urgencia"].isin(["Vencida", "Semana actual"]) if "urgencia" in df.columns else pd.Series(False, index=df.index)
    pos_riesgo = int(df.loc[riesgo_mask, "PO"].astype(str).nunique()) if "PO" in df.columns else 0

    planeador_share = 0.0
    top_planeador = "-"
    if "Planeador" in df.columns and not df.empty:
        grouped = df.groupby("Planeador", dropna=False)["valor_pendiente"].sum().sort_values(ascending=False)
        if not grouped.empty and valor_pendiente_total > 0:
            top_planeador = str(grouped.index[0])
            planeador_share = grouped.iloc[0] / valor_pendiente_total * 100

    with st.container(border=True):
        cols = st.columns(4)
        with cols[0]:
            st.metric(
                "Avance global",
                f"{avance_global:.1f}%",
                delta=f"{int(total_entregados):,} / {int(total_qty):,} piezas",
                help="Porcentaje real de avance del total de piezas. Se calcula dividiendo las piezas entregadas entre las piezas ordenadas.",
            )
        with cols[1]:
            st.metric(
                "Valor pendiente",
                f"${valor_pendiente_total:,.0f}",
                delta=f"{int((qty - entregados).clip(lower=0).sum()):,} piezas pendientes",
                help="Monto economico aun no entregado. Se obtiene sumando el valor pendiente de todas las partidas abiertas.",
            )
        with cols[2]:
            st.metric(
                "POs en riesgo",
                f"{pos_riesgo}",
                delta="Vencida + Semana actual",
                help="Numero de ordenes de compra que tienen al menos una partida vencida o comprometida para la semana actual.",
            )
        with cols[3]:
            st.metric(
                "Concentracion top",
                f"{planeador_share:.1f}%",
                delta=top_planeador,
                help="Participacion del planeador con mayor valor pendiente respecto al total pendiente. Mide concentracion de riesgo operativo.",
            )


def _timeline_chart(df: pd.DataFrame) -> go.Figure:
    work = df.copy()
    work = work[work["fecha_entrega_real"].notna()].copy()
    work["week_start"] = pd.to_datetime(work["fecha_entrega_real"]).dt.to_period("W-MON").dt.start_time
    work["piezas_pendientes"] = pd.to_numeric(work["por_entregar_recalculado"], errors="coerce").fillna(0)
    grouped = work.groupby(["week_start", "urgencia"], as_index=False)["piezas_pendientes"].sum().sort_values("week_start")

    fig = go.Figure()
    for urgency in ["Vencida", "Semana actual", "Proximas 2 semanas", "Futura", "Sin fecha"]:
        chunk = grouped[grouped["urgencia"] == urgency]
        if chunk.empty:
            continue
        fig.add_trace(
            go.Bar(
                x=chunk["week_start"],
                y=chunk["piezas_pendientes"],
                name=urgency,
                marker_color=URGENCY_COLOR[urgency],
                width=5 * 24 * 60 * 60 * 1000,
            )
        )

    today = pd.Timestamp.now().normalize()
    fig.add_vline(x=today, line_width=2, line_dash="dash", line_color="#f4d35e")
    fig.update_layout(
        barmode="stack",
        height=550,
        margin={"l": 10, "r": 10, "t": 72, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        title={"text": "Piezas pendientes por semana de entrega", "x": 0.02, "xanchor": "left", "font": {"size": 20}},
        xaxis={"title": "Semana de entrega", "color": "#d7dee8", "showgrid": False},
        yaxis={"title": "Piezas pendientes", "color": "#d7dee8", "gridcolor": "rgba(148,163,184,0.18)"},
        legend={"orientation": "h", "y": 1.03, "x": 0, "font": {"color": "#d7dee8"}},
        font={"color": "#d7dee8"},
    )
    return fig


def _proportion_chart(df: pd.DataFrame) -> go.Figure:
    valor_entregado = float(pd.to_numeric(df.get("valor_entregado"), errors="coerce").fillna(0).sum())
    valor_pendiente = float(pd.to_numeric(df.get("valor_pendiente"), errors="coerce").fillna(0).sum())
    total = valor_entregado + valor_pendiente
    entregado_pct = _safe_pct(valor_entregado, total) * 100
    pendiente_pct = _safe_pct(valor_pendiente, total) * 100

    fig = go.Figure()
    fig.add_trace(go.Bar(y=[""], x=[entregado_pct], orientation="h", marker_color="#4f7cac", text=[f"Entregado: {entregado_pct:.1f}%"], textposition="inside", textangle=0, insidetextfont={"size": 12}))
    fig.add_trace(go.Bar(y=[""], x=[pendiente_pct], orientation="h", marker_color="#d84f60", text=[f"Pendiente: {pendiente_pct:.1f}%"], textposition="inside", textangle=0, insidetextfont={"size": 12}))
    fig.update_layout(
        title={"text": "% Estatus Pedidos", "x": 0.02, "xanchor": "left"},
        barmode="stack",
        height=130,
        margin={"l": 10, "r": 10, "t": 40, "b": 20},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis={"visible": False, "range": [0, 100]},
        yaxis={"visible": False},
        font={"color": "#d7dee8"},
    )
    return fig


def _planeador_chart(df: pd.DataFrame) -> go.Figure:
    def _compact_mxn_label(value: float) -> str:
        absolute = abs(float(value))
        if absolute >= 1_000_000:
            return f"{value / 1_000_000:.0f}M"
        if absolute >= 1_000:
            return f"{value / 1_000:.0f}K"
        return f"{value:,.0f}"

    grouped = (
        df.groupby("Planeador", dropna=False)["valor_pendiente"]
        .sum()
        .reset_index()
        .sort_values("valor_pendiente", ascending=True)
    )
    planeadores = grouped["Planeador"].fillna("Sin planeador").astype(str)
    labels = grouped["valor_pendiente"].apply(_compact_mxn_label)
    fig = go.Figure(
        go.Bar(
            x=grouped["valor_pendiente"],
            y=planeadores,
            orientation="h",
            marker={"color": grouped["valor_pendiente"], "colorscale": [[0, "#4f7cac"], [1, "#d84f60"]]},
            text=labels,
            textposition="inside",
            insidetextanchor="middle",
            textfont={"color": "#f4f6fa", "size": 12},
        )
    )
    fig.update_layout(
        title={"text": "Backlog por Planeador", "x": 0.02, "xanchor": "left"},
        height=372,
        margin={"l": 10, "r": 10, "t": 50, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis={"title": "", "showticklabels": False, "showgrid": False, "zeroline": False, "color": "#d7dee8"},
        yaxis={"title": None, "showticklabels": True, "color": "#d7dee8"},
        showlegend=False,
        font={"color": "#d7dee8"},
    )
    fig.update_yaxes(tickangle=-90)
    return fig


def render_resumen_ejecutivo(df: pd.DataFrame, historico: pd.DataFrame) -> None:
    st.markdown("# Resumen Ejecutivo")
    st.caption("Riesgo, urgencia y accion operativa")

    if df.empty:
        st.warning("No hay registros para mostrar en estado_actual.")
        return

    _render_summary_kpis(df)
    st.divider()

    col_left, col_right = st.columns([7, 3])
    with col_left:
        with st.container(border=True):
            st.plotly_chart(
                _timeline_chart(df),
                width="stretch",
                config={"displayModeBar": False},
                key="resumen_timeline_chart",
            )

    with col_right:
        with st.container(border=True):
            st.plotly_chart(
                _proportion_chart(df),
                width="stretch",
                config={"displayModeBar": False},
                key="resumen_proportion_chart",
            )
        with st.container(border=True):
            st.plotly_chart(
                _planeador_chart(df),
                width="stretch",
                config={"displayModeBar": False},
                key="resumen_planeador_chart",
            )

    st.divider()
    render_alertas_table(df, search_key="resumen_alert_search_po")


def render_alertas_table(df: pd.DataFrame, search_key: str = "alert_search_po") -> None:
    if df.empty:
        st.info("No hay alertas para mostrar.")
        return

    work = df.copy()
    work = work[pd.to_numeric(work["por_entregar_recalculado"], errors="coerce").fillna(0) > 0].copy()
    work["urgencia_rank"] = work["urgencia"].map(URGENCY_ORDER).fillna(99)
    work["valor_pendiente"] = pd.to_numeric(work["valor_pendiente"], errors="coerce").fillna(0)
    work = work.sort_values(["urgencia_rank", "valor_pendiente"], ascending=[True, False])

    with st.container(border=True):
        st.markdown("### Alertas Criticas")
        po_search = st.text_input("Buscar por Numero de Orden (PO)", key=search_key)
        if po_search:
            work = work[work["PO"].astype(str).str.contains(po_search.strip(), case=False, na=False)]

        display_cols = [
            "PO",
            "RA",
            "Planeador",
            "Ingeniero",
            "estatus_real",
            "urgencia",
            "fecha_entrega_real",
            "Qty.",
            "Entregados",
            "por_entregar_recalculado",
            "valor_pendiente",
        ]
        display = work[[column for column in display_cols if column in work.columns]].copy()
        if "fecha_entrega_real" in display.columns:
            display["fecha_entrega_real"] = pd.to_datetime(display["fecha_entrega_real"], errors="coerce").dt.date
        display.columns = [column.replace("_", " ") for column in display.columns]
        st.dataframe(display, hide_index=True, width="stretch")


def _render_operacion_semanal_kpis(df: pd.DataFrame) -> None:
    if df.empty:
        return

    today = pd.Timestamp.now().normalize()
    week_start = today - pd.to_timedelta(today.weekday(), unit="D")
    week_end = week_start + pd.Timedelta(days=6)

    work = df.copy()
    work["fecha_entrega_real"] = pd.to_datetime(work.get("fecha_entrega_real"), errors="coerce")
    work["pendiente_pzas"] = pd.to_numeric(work.get("por_entregar_recalculado"), errors="coerce").fillna(0)
    work["valor_pendiente_num"] = pd.to_numeric(work.get("valor_pendiente"), errors="coerce").fillna(0)

    pendientes = work[work["pendiente_pzas"] > 0].copy()
    vencidas = pendientes[pendientes["fecha_entrega_real"] < today]
    semana_actual = pendientes[
        (pendientes["fecha_entrega_real"] >= today)
        & (pendientes["fecha_entrega_real"] <= week_end)
    ]

    piezas_vencidas = int(vencidas["pendiente_pzas"].sum())
    piezas_semana = int(semana_actual["pendiente_pzas"].sum())
    valor_comprometido = float(pd.concat([vencidas, semana_actual], axis=0)["valor_pendiente_num"].sum())
    pos_criticas = int(
        pd.concat([vencidas, semana_actual], axis=0)["PO"].astype(str).nunique()
        if "PO" in work.columns
        else 0
    )

    with st.container(border=True):
        cols = st.columns(4)
        cols[0].metric("Piezas vencidas", f"{piezas_vencidas:,}", delta="Atrasadas al dia de hoy")
        cols[1].metric("Piezas a entregar semana", f"{piezas_semana:,}", delta=f"Semana {week_start.date()} a {week_end.date()}")
        cols[2].metric("POs criticas semana", f"{pos_criticas}", delta="Vencidas + semana actual")
        cols[3].metric("Valor comprometido", f"${valor_comprometido:,.0f}", delta="Backlog operativo inmediato")


def _operacion_diaria_chart(df: pd.DataFrame) -> go.Figure:
    today = pd.Timestamp.now().normalize()
    horizon_end = today + pd.Timedelta(days=14)

    work = df.copy()
    work["fecha_entrega_real"] = pd.to_datetime(work.get("fecha_entrega_real"), errors="coerce")
    work["pendiente_pzas"] = pd.to_numeric(work.get("por_entregar_recalculado"), errors="coerce").fillna(0)
    work = work[(work["pendiente_pzas"] > 0) & work["fecha_entrega_real"].notna()].copy()
    work = work[(work["fecha_entrega_real"] >= today) & (work["fecha_entrega_real"] <= horizon_end)]

    grouped = (
        work.groupby([work["fecha_entrega_real"].dt.date, "urgencia"], as_index=False)["pendiente_pzas"]
        .sum()
        .sort_values("fecha_entrega_real")
    )

    fig = go.Figure()
    for urgency in ["Vencida", "Semana actual", "Proximas 2 semanas", "Futura", "Sin fecha"]:
        chunk = grouped[grouped["urgencia"] == urgency]
        if chunk.empty:
            continue
        fig.add_trace(
            go.Bar(
                x=chunk["fecha_entrega_real"],
                y=chunk["pendiente_pzas"],
                name=urgency,
                marker_color=URGENCY_COLOR[urgency],
            )
        )

    fig.update_layout(
        barmode="stack",
        height=420,
        margin={"l": 10, "r": 10, "t": 56, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        title={"text": "Carga diaria operativa (proximos 14 dias)", "x": 0.02, "xanchor": "left"},
        xaxis={"title": "Fecha compromiso", "color": "#d7dee8", "showgrid": False},
        yaxis={"title": "Piezas pendientes", "color": "#d7dee8", "gridcolor": "rgba(148,163,184,0.18)"},
        legend={"orientation": "h", "y": 1.05, "x": 0, "font": {"color": "#d7dee8"}},
        font={"color": "#d7dee8"},
    )
    return fig


def render_operacion_semanal(df: pd.DataFrame) -> None:
    st.markdown("# Operacion Semanal")
    st.caption("Vista tactica semanal para ejecucion: backlog vencido, compromisos de la semana y carga diaria operativa.")
    if df.empty:
        st.warning("No hay datos filtrados para esta vista.")
        return

    _render_operacion_semanal_kpis(df)
    st.divider()

    with st.container(border=True):
        st.plotly_chart(
            _operacion_diaria_chart(df),
            width="stretch",
            config={"displayModeBar": False},
            key="operacion_diaria_chart",
        )

    st.divider()

    # Operacion semanal muestra solo alertas criticas inmediatas (vencidas + semana actual)
    work = df.copy()
    today = pd.Timestamp.now().normalize()
    week_end = today - pd.to_timedelta(today.weekday(), unit="D") + pd.Timedelta(days=6)
    fechas = pd.to_datetime(work.get("fecha_entrega_real"), errors="coerce")
    pendientes = pd.to_numeric(work.get("por_entregar_recalculado"), errors="coerce").fillna(0)
    urgente = (fechas < today) | ((fechas >= today) & (fechas <= week_end))
    criticas = work[(pendientes > 0) & urgente].copy()
    render_alertas_table(criticas, search_key="operacion_alert_search_po")


def render_detalle(df: pd.DataFrame) -> None:
    st.markdown("# Detalle por PO / Planeador")
    if df.empty:
        st.warning("No hay datos filtrados para esta vista.")
        return

    mode = st.radio("Modo de detalle", ["PO", "Planeador"], horizontal=True)
    selector_col = "PO" if mode == "PO" else "Planeador"
    options = sorted(df[selector_col].dropna().astype(str).unique().tolist())
    selected = st.selectbox(f"Selecciona {selector_col}", options)
    detail = df[df[selector_col].astype(str) == selected].copy()

    with st.container(border=True):
        st.dataframe(detail, hide_index=True, width="stretch")


def render_nl2sql_shell(df: pd.DataFrame, historico: pd.DataFrame) -> None:
    st.markdown("# Pregunta a tus Datos")
    st.caption("Haz preguntas sobre tus pedidos y recibe respuestas claras basadas en los datos filtrados.")

    init_chat_session()
    render_chat_interface(df)


def render_captura_datos() -> None:
    st.markdown("# Centro de Captura Operativa")
    st.caption("Actualiza recepciones y cantidades entregadas para reflejar el estatus real en el dashboard.")

    try:
        source_df = load_capture_dataframe()
    except Exception as exc:
        st.error(f"No fue posible cargar el Excel fuente: {exc}")
        return

    with st.container(border=True):
        st.write("Usa esta tabla para agregar filas nuevas o editar filas existentes.")
        st.write("Al guardar, se crea un respaldo del Excel y se ejecuta la ingesta a DuckDB.")

    po_filter = st.text_input(
        "Filtrar por PO",
        key="captura_po_filter",
        placeholder="Ejemplo: 45001234",
        help="Filtra filas cuyo valor en la columna PO contenga este texto.",
    )

    filtered_mode = bool(po_filter.strip()) and "PO" in source_df.columns
    if filtered_mode:
        mask = source_df["PO"].astype(str).str.contains(po_filter.strip(), case=False, na=False)
        editor_df = source_df.loc[mask].copy()
        st.caption(f"Filtro activo: {len(editor_df):,} fila(s) visibles de {len(source_df):,} totales.")
        st.caption("Con filtro activo solo puedes editar filas existentes.")
    else:
        editor_df = source_df.copy()

    preferred_order = [
        "PO",
        "Item",
        "Description",
        "Qty.",
        "Entregados",
        "Por Entregar",
        "%",
        "PO Date",
        "Fecha de Entrega",
        "Costo Unitario",
        "Total",
        "RA",
        "Ingeniero",
        "Planeador",
        "Condicion",
        "Peso",
        "Dimensiones",
        "Cubicaje",
        "Lison",
    ]
    column_order = [column for column in preferred_order if column in editor_df.columns] + [
        column for column in editor_df.columns if column not in preferred_order
    ]
    disabled_columns = [column for column in ["Total", "Por Entregar", "%"] if column in editor_df.columns]

    edited_df = st.data_editor(
        editor_df,
        width="stretch",
        num_rows="fixed" if filtered_mode else "dynamic",
        key="captura_excel_editor_v2",
        column_order=column_order,
        disabled=disabled_columns,
        column_config={
            "PO": st.column_config.NumberColumn("PO", format="%d", min_value=0, help="Numero de orden de compra."),
            "PO Date": st.column_config.DateColumn("PO Date", format="YYYY-MM-DD", help="Fecha de emision de la orden."),
            "Item": st.column_config.NumberColumn("Item", format="%d", min_value=0),
            "Costo Unitario": st.column_config.NumberColumn("Costo Unitario", format="$ %.2f", min_value=0.0, help="Costo por pieza."),
            "Total": st.column_config.NumberColumn("Total", format="$ %.2f", help="Campo calculado."),
            "Peso": st.column_config.NumberColumn("Peso", format="%.2f", min_value=0.0),
            "Cubicaje": st.column_config.NumberColumn("Cubicaje", format="%.3f", min_value=0.0),
            "Qty.": st.column_config.NumberColumn("Qty.", format="%d", min_value=0, help="Cantidad total ordenada."),
            "Entregados": st.column_config.NumberColumn("Entregados", format="%d", min_value=0, help="Cantidad fisica recibida hasta hoy."),
            "Por Entregar": st.column_config.NumberColumn("Por Entregar", format="%d", help="Campo calculado."),
            "%": st.column_config.NumberColumn("%", format="%.2f", help="Campo calculado."),
        },
    )

    if st.button("Guardar y Actualizar Dashboard", type="primary", width="stretch"):
        try:
            qty = pd.to_numeric(edited_df.get("Qty."), errors="coerce")
            entregados = pd.to_numeric(edited_df.get("Entregados"), errors="coerce")
            invalid_qty = int(qty.lt(0).fillna(False).sum()) if qty is not None else 0
            invalid_entregados = int(entregados.lt(0).fillna(False).sum()) if entregados is not None else 0
            entregados_gt_qty = int(((entregados > qty) & qty.notna() & entregados.notna()).fillna(False).sum())

            missing_po = 0
            if "PO" in edited_df.columns:
                po_series = edited_df["PO"].astype(str).str.strip()
                missing_po = int(po_series.eq("").sum() + edited_df["PO"].isna().sum())

            issues: list[str] = []
            if invalid_qty:
                issues.append(f"Hay {invalid_qty} fila(s) con Qty. negativa.")
            if invalid_entregados:
                issues.append(f"Hay {invalid_entregados} fila(s) con Entregados negativo.")
            if entregados_gt_qty:
                issues.append(f"Hay {entregados_gt_qty} fila(s) donde Entregados es mayor a Qty.")
            if missing_po:
                issues.append(f"Hay {missing_po} fila(s) sin PO.")

            if issues:
                st.error("No se guardaron cambios. Corrige estos puntos:")
                for issue in issues:
                    st.write(f"- {issue}")
                return

            with st.status("Procesando cambios...", expanded=True) as status:
                status.write("Validacion completada.")
                status.write("Guardando cambios en Excel fuente...")

                dataframe_to_save = edited_df
                if filtered_mode:
                    dataframe_to_save = source_df.copy()
                    dataframe_to_save.loc[edited_df.index, edited_df.columns] = edited_df

                backup_path = save_capture_dataframe(dataframe_to_save)
                status.write("Ejecutando ETL para refrescar DuckDB...")
                output = run_ingest_refresh()
                status.update(label="Actualizacion completada", state="complete")

            st.success("Cambios guardados y ETL ejecutado correctamente.")
            st.caption(f"Respaldo generado: {backup_path.name}")
            st.caption(output.splitlines()[-1] if output else "ETL completado")
            try:
                st.switch_page("main.py")
            except Exception:
                st.page_link("main.py", label="Volver al Resumen Ejecutivo", icon="🏠")
                st.rerun()
        except Exception as exc:
            st.error(f"No fue posible guardar y actualizar datos: {exc}")