"""Capa de presentacion del dashboard ejecutivo."""

import streamlit as st
import pandas as pd
import altair as alt
import math
import plotly.graph_objects as go

from src.config.constants import Colors, Columns, Labels
from src.logic.metrics import (
    compute_kpis,
    trend_kpis,
    risk_by_owner,
    prioritized_actions,
    group_by_planeador,
    group_by_condicion,
    top_descriptions,
    with_datetime_cols,
)


def _color(name: str, fallback: str) -> str:
    return getattr(Colors, name, fallback)


NAVY = _color("NAVY", "#16324F")
TEAL = _color("TEAL", "#2E6F95")
SKY = _color("SKY", "#4F7CAC")
BG_APP = _color("BG_APP", "#F7F8FA")
TEXT_MUTED = _color("TEXT_MUTED", "#7B8794")
SUCCESS = _color("SUCCESS", "#2E8B57")
WARNING = _color("WARNING", "#C08A00")
DANGER = _color("DANGER", "#B23A48")


def _safe_num(value: object, default: float = 0.0) -> float:
    """Normalize KPI values to avoid blank renders from NaN/None."""
    try:
        num = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(num) or math.isinf(num):
        return default
    return num


def _coerce_to_dataframe(value: object) -> pd.DataFrame:
    """Convierte entradas heterogeneas a DataFrame de forma segura."""
    if isinstance(value, pd.DataFrame):
        return value.copy()

    inner_data = getattr(value, "data", None)
    if isinstance(inner_data, pd.DataFrame):
        return inner_data.copy()

    try:
        return pd.DataFrame(value).copy()
    except Exception:
        return pd.DataFrame()


def _apply_chart_style(chart: alt.Chart) -> alt.Chart:
    return (
        chart
        .configure(background="transparent")
        .configure_view(strokeOpacity=0)
        .configure_axis(
            labelColor="#D7DEE8",
            titleColor="#D7DEE8",
            gridColor="rgba(148,163,184,0.22)",
        )
        .configure_legend(labelColor="#D7DEE8", titleColor="#D7DEE8")
    )

def render_header():
    """Encabezado compacto con prioridad en lectura ejecutiva."""
    st.markdown(
        f"""
        <div style=\"padding: 0.25rem 0 0.6rem 0;\">
            <div style=\"display:flex;justify-content:space-between;align-items:center;gap:0.75rem;flex-wrap:wrap;\">
                <div>
                    <h1 style=\"margin:0;\">{Labels.APP_TITLE}</h1>
                    <p style=\"margin:0.2rem 0 0 0;color:#5b6f94;font-weight:600;\">{Labels.APP_SUBTITLE}</p>
                </div>
                <div style=\"display:flex;gap:0.5rem;flex-wrap:wrap;\">
                    <span style=\"padding:0.35rem 0.7rem;border-radius:999px;background:#e7f2ff;color:#1b4d9e;font-size:0.78rem;font-weight:700;\">Control Tower</span>
                    <span style=\"padding:0.35rem 0.7rem;border-radius:999px;background:#e8fbf5;color:#147a59;font-size:0.78rem;font-weight:700;\">Executive Mode</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_special_cases_panel(df_special: pd.DataFrame, dropped_columns: list[str] | None = None):
    """Muestra casos especiales fuera del flujo operativo para no contaminar KPIs."""
    if dropped_columns:
        st.caption("Columnas removidas por ser 100% nulas: " + ", ".join(dropped_columns))

    if df_special is None or df_special.empty:
        return

    with st.expander("⚠️ Casos Especiales (fuera de KPI operativo)", expanded=False):
        st.warning(
            "Estas ordenes no participan en el OTD operativo 2026. "
            "Se visualizan aparte por ser historicas activas o tener fecha no normalizada."
        )

        view = df_special.copy()
        if Columns.PO_DATE in view.columns:
            view[Columns.PO_DATE] = pd.to_datetime(view[Columns.PO_DATE], errors="coerce")
        if "Fecha_Entrega_Normalizada" in view.columns:
            view["Fecha_Entrega_Normalizada"] = pd.to_datetime(
                view["Fecha_Entrega_Normalizada"], errors="coerce"
            )

        cols = [
            c
            for c in [
                "CasoEspecial",
                Columns.PO,
                Columns.RA,
                Columns.PLANEADOR,
                Columns.INGENIERO,
                Columns.PO_DATE,
                Columns.FECHA_ENTREGA,
                "Fecha_Entrega_Normalizada",
                Columns.POR_ENTREGAR,
                Columns.COSTO_UNITARIO,
                Columns.TOTAL,
            ]
            if c in view.columns
        ]
        view = view[cols]

        st.dataframe(
            view,
            hide_index=True,
            use_container_width=True,
            column_config={
                Columns.PO_DATE: st.column_config.DateColumn("PO Date", format="DD/MM/YYYY"),
                "Fecha_Entrega_Normalizada": st.column_config.DateColumn("Entrega normalizada", format="DD/MM/YYYY"),
                Columns.COSTO_UNITARIO: st.column_config.NumberColumn("Costo unitario", format="$%0,d"),
                Columns.TOTAL: st.column_config.NumberColumn("Monto", format="$%0,d"),
            },
        )

def render_kpi_cards(df: pd.DataFrame):
    """Fila 1: 4 KPI principales en formato ejecutivo."""
    if df.empty:
        return

    kpi = compute_kpis(df)
    otd = _safe_num(kpi.otd)
    otd_target = _safe_num(kpi.otd_target, 95.0)
    lead_time = _safe_num(kpi.lead_time_promedio_dias)
    lead_delta = _safe_num(kpi.lead_time_delta_pct)
    backlog = _safe_num(kpi.backlog_riesgo_financiero)
    backlog_orders = int(_safe_num(kpi.backlog_riesgo_ordenes))
    otd_delta = otd - otd_target
    otd_has_due = int(getattr(kpi, "otd_due_count", 0)) > 0
    otd_due_count = int(getattr(kpi, "otd_due_count", 0))
    otd_on_time_count = int(getattr(kpi, "otd_on_time_count", 0))

    with st.container(border=True):
        cols = st.columns(4)

        with cols[0]:
            st.metric(
                label="Estado Global",
                value=str(kpi.estado_global),
                delta=f"{kpi.record_count:,} registros",
            )
            st.caption("Estado operacional actual")

        with cols[1]:
            if otd_has_due:
                st.metric(
                    label="OTD",
                    value=f"{otd:.1f}%",
                    delta=f"A tiempo {otd_on_time_count}/{otd_due_count}",
                )
                st.caption(f"Objetivo: {otd_target:.0f}% | Delta: {otd_delta:+.1f} PP")
            else:
                st.metric(
                    label="OTD",
                    value="N/A",
                    delta="Sin vencimientos en el corte",
                )
                st.caption("No evaluable hasta tener ordenes vencidas")

        with cols[2]:
            st.metric(
                label="Lead Time Promedio",
                value=f"{lead_time:.1f} dias",
                delta=f"{lead_delta:+.1f}%",
                delta_color="inverse",
            )
            st.caption("Variación vs periodo anterior")

        with cols[3]:
            st.metric(
                label="Backlog en Riesgo",
                value=f"${backlog:,.0f}",
                delta=f"{backlog_orders} ordenes en riesgo",
                delta_color="inverse" if backlog_orders > 0 else "normal",
            )
            st.caption("Vencido o <= 7 dias")


def render_operational_insights(df: pd.DataFrame):
    """Fila 2: timeline a la izquierda y dos graficas apiladas a la derecha."""
    if df.empty:
        return

    st.markdown("### Insights Operativos")
    col_left, col_right = st.columns([7, 3], gap="large")

    with col_left:
        with st.container(border=True):
            st.markdown("**Linea de Tiempo de Entregas (Backlog vs Forecast)**")

            date_col = Columns.FECHA_ENTREGA if Columns.FECHA_ENTREGA in df.columns else None
            if date_col is None and "Fecha_Entrega_Normalizada" in df.columns:
                date_col = "Fecha_Entrega_Normalizada"

            if date_col is None:
                st.info("No hay columna de fecha de entrega para construir la linea de tiempo.")
            else:
                time_view = with_datetime_cols(df.copy())

                # Fallback defensivo: si FECHA_ENTREGA no pudo parsearse, usar la normalizada.
                if (
                    date_col == Columns.FECHA_ENTREGA
                    and "Fecha_Entrega_Normalizada" in time_view.columns
                    and pd.to_datetime(time_view[date_col], errors="coerce").notna().sum() == 0
                ):
                    date_col = "Fecha_Entrega_Normalizada"

                time_view[date_col] = pd.to_datetime(time_view[date_col], errors="coerce")
                time_view = time_view[time_view[date_col].notna()].copy()

                if time_view.empty:
                    st.info("No hay fechas de entrega validas para el analisis temporal.")
                else:
                    today = pd.Timestamp.now().normalize()
                    time_view["EstadoEntrega"] = time_view[date_col].apply(
                        lambda x: "Atrasado" if x.normalize() < today else "Forecast"
                    )
                    time_view["SemanaInicio"] = time_view[date_col].dt.to_period("W-MON").dt.start_time

                    timeline = (
                        time_view.groupby(["SemanaInicio", "EstadoEntrega"], as_index=False)
                        .size()
                        .rename(columns={"size": "Ordenes"})
                        .sort_values("SemanaInicio")
                    )

                    if timeline.empty:
                        st.info("Sin datos suficientes para la linea de tiempo.")
                    else:
                        fig_timeline = go.Figure()
                        for status_name, color in [("Forecast", "#5b6a86"), ("Atrasado", "#d84f60")]:
                            chunk = timeline[timeline["EstadoEntrega"] == status_name]
                            if chunk.empty:
                                continue
                            fig_timeline.add_trace(
                                go.Bar(
                                    x=chunk["SemanaInicio"],
                                    y=chunk["Ordenes"],
                                    width=5 * 24 * 60 * 60 * 1000,
                                    name=status_name,
                                    marker_color=color,
                                    hovertemplate="Semana: %{x|%Y-%m-%d}<br>Estado: " + status_name + "<br>Ordenes: %{y}<extra></extra>",
                                )
                            )

                        if len(fig_timeline.data) == 0:
                            st.info("Sin datos suficientes para la linea de tiempo.")
                        else:
                            min_x = timeline["SemanaInicio"].min()
                            max_x = timeline["SemanaInicio"].max() + pd.Timedelta(days=7)
                            fig_timeline.add_vline(
                                x=today,
                                line_width=2,
                                line_dash="dash",
                                line_color="#f4d35e",
                                annotation_text="Hoy",
                                annotation_position="top",
                                annotation_font_color="#f4d35e",
                            )
                            fig_timeline.update_layout(
                                barmode="stack",
                                paper_bgcolor="rgba(0,0,0,0)",
                                plot_bgcolor="rgba(0,0,0,0)",
                                height=550,
                                margin={"l": 10, "r": 10, "t": 40, "b": 10},
                                xaxis={
                                    "title": "Horizonte temporal completo",
                                    "showgrid": False,
                                    "color": "#d7dee8",
                                    "range": [min_x, max_x],
                                },
                                yaxis={"title": "Ordenes", "showgrid": True, "gridcolor": "rgba(148,163,184,0.18)", "color": "#d7dee8"},
                                legend={"orientation": "h", "y": 1.12, "x": 0, "font": {"color": "#d7dee8"}},
                            )
                            st.plotly_chart(fig_timeline, use_container_width=True, config={"displayModeBar": False})

    with col_right:
        with st.container(border=True):
            delivered_count = 0
            pending_count = 0

            po_col = Columns.PO if Columns.PO in df.columns else None
            if Columns.POR_ENTREGAR in df.columns:
                status_df = df.copy()
                status_df[Columns.POR_ENTREGAR] = pd.to_numeric(status_df[Columns.POR_ENTREGAR], errors="coerce").fillna(0)
                status_df["EstadoPO"] = status_df[Columns.POR_ENTREGAR].apply(
                    lambda x: "Pendiente" if x > 0 else "Entregado"
                )

                if po_col:
                    po_status = (
                        status_df.groupby(po_col, as_index=False)[Columns.POR_ENTREGAR]
                        .sum()
                        .rename(columns={Columns.POR_ENTREGAR: "PendienteTotal"})
                    )
                    po_status["EstadoPO"] = po_status["PendienteTotal"].apply(
                        lambda x: "Pendiente" if x > 0 else "Entregado"
                    )
                    delivered_count = int((po_status["EstadoPO"] == "Entregado").sum())
                    pending_count = int((po_status["EstadoPO"] == "Pendiente").sum())
                else:
                    delivered_count = int((status_df["EstadoPO"] == "Entregado").sum())
                    pending_count = int((status_df["EstadoPO"] == "Pendiente").sum())

            total_count = delivered_count + pending_count
            if total_count == 0:
                st.info("No hay datos suficientes para calcular la composicion de carga.")
            else:
                delivered_pct = (delivered_count / total_count) * 100
                pending_pct = (pending_count / total_count) * 100

                fig_stack = go.Figure()
                fig_stack.add_trace(
                    go.Bar(
                        y=[""],
                        x=[delivered_pct],
                        orientation="h",
                        marker_color="#4f7cac",
                        text=[f"Entregado: {delivered_pct:.1f}%"],
                        textposition="inside",
                        textangle=0,
                        insidetextfont={"size": 12},
                        hovertemplate="Entregado: %{x:.1f}%<extra></extra>",
                    )
                )
                fig_stack.add_trace(
                    go.Bar(
                        y=[""],
                        x=[pending_pct],
                        orientation="h",
                        marker_color="#d84f60",
                        text=[f"Pendiente: {pending_pct:.1f}%"],
                        textposition="inside",
                        textangle=0,
                        insidetextfont={"size": 12},
                        hovertemplate="Pendiente: %{x:.1f}%<extra></extra>",
                    )
                )
                fig_stack.update_layout(
                    title={"text": "Proporcion de Carga: Entregado vs Pendiente", "x": 0.02, "xanchor": "left"},
                    barmode="stack",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    height=150,
                    margin={"l": 10, "r": 10, "t": 40, "b": 20},
                    showlegend=False,
                    xaxis={"visible": False, "range": [0, 100]},
                    yaxis={"visible": False},
                    font={"color": "#d7dee8"},
                )
                st.plotly_chart(fig_stack, use_container_width=True, config={"displayModeBar": False})

        st.write("")

        with st.container(border=True):
            owner_risk = _coerce_to_dataframe(risk_by_owner(df, owner_col=Columns.PLANEADOR))
            if owner_risk.empty:
                st.info("No hay backlog en riesgo para los planeadores.")
            else:
                planeador_col = Columns.PLANEADOR if Columns.PLANEADOR in owner_risk.columns else owner_risk.columns[0]
                risk_col = "RiesgoFinanciero" if "RiesgoFinanciero" in owner_risk.columns else None

                if risk_col is None:
                    st.info("No se pudo calcular el riesgo financiero por planeador.")
                else:
                    plot_risk = owner_risk[[planeador_col, risk_col]].copy()
                    plot_risk[planeador_col] = plot_risk[planeador_col].fillna("Sin asignar").astype(str)
                    plot_risk[risk_col] = pd.to_numeric(plot_risk[risk_col], errors="coerce").fillna(0)
                    plot_risk = plot_risk.sort_values(risk_col, ascending=True)

                    fig_risk = go.Figure(
                        go.Bar(
                            x=plot_risk[risk_col],
                            y=plot_risk[planeador_col],
                            orientation="h",
                            marker={
                                "color": plot_risk[risk_col],
                                "colorscale": [[0, "#4f7cac"], [1, "#d84f60"]],
                            },
                            hovertemplate="Planeador: %{y}<br>Riesgo: $%{x:,.0f}<extra></extra>",
                        )
                    )
                    fig_risk.update_layout(
                        title={"text": "Backlog en Riesgo por Planeador", "x": 0.02, "xanchor": "left"},
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        height=370,
                        margin={"l": 10, "r": 10, "t": 50, "b": 10},
                        xaxis={"title": "Riesgo financiero ($)", "showgrid": True, "gridcolor": "rgba(148,163,184,0.18)", "color": "#d7dee8"},
                        yaxis={"title": "", "color": "#d7dee8"},
                        showlegend=False,
                    )
                    st.plotly_chart(fig_risk, use_container_width=True, config={"displayModeBar": False})


def render_top_offenders(df: pd.DataFrame):
    """Fila 3: hitlist operativo con top 5 articulos/POs de mayor retraso."""
    with st.container(border=True):
        st.markdown("### Top 5 Ofensores")

        if df.empty or Columns.FECHA_ENTREGA not in df.columns:
            st.info("No hay datos suficientes para calcular ofensores.")
            return

        work = df.copy()
        work[Columns.FECHA_ENTREGA] = pd.to_datetime(work[Columns.FECHA_ENTREGA], errors="coerce")
        work = work[work[Columns.FECHA_ENTREGA].notna()].copy()
        if work.empty:
            st.info("No hay fechas validas para calcular ofensores.")
            return

        today = pd.Timestamp.now().normalize()
        work["Dias de Atraso"] = (today - work[Columns.FECHA_ENTREGA].dt.normalize()).dt.days
        work = work[work["Dias de Atraso"] > 0].copy()

        if work.empty:
            st.info("No hay ordenes vencidas en este momento.")
            return

        if Columns.TOTAL in work.columns:
            work["Riesgo ($)"] = pd.to_numeric(work[Columns.TOTAL], errors="coerce").fillna(0)
        elif Columns.POR_ENTREGAR in work.columns and Columns.COSTO_UNITARIO in work.columns:
            qty = pd.to_numeric(work[Columns.POR_ENTREGAR], errors="coerce").fillna(0)
            cost = pd.to_numeric(work[Columns.COSTO_UNITARIO], errors="coerce").fillna(0)
            work["Riesgo ($)"] = qty * cost
        else:
            work["Riesgo ($)"] = 0.0

        key_col = Columns.ITEM if Columns.ITEM in work.columns else Columns.PO
        if key_col not in work.columns:
            key_col = Columns.RA if Columns.RA in work.columns else None

        if key_col is None:
            st.info("No existe columna de Articulo/PO para generar el hitlist.")
            return

        offenders = (
            work.groupby(key_col, as_index=False)
            .agg({"Dias de Atraso": "max", "Riesgo ($)": "sum"})
            .sort_values(["Dias de Atraso", "Riesgo ($)"], ascending=[False, False])
            .head(5)
            .rename(columns={key_col: "Articulo/PO"})
        )

        offenders["Articulo/PO"] = offenders["Articulo/PO"].astype(str)
        offenders["Dias de Atraso"] = pd.to_numeric(offenders["Dias de Atraso"], errors="coerce").round().astype("Int64")
        offenders["Riesgo ($)"] = pd.to_numeric(offenders["Riesgo ($)"], errors="coerce").fillna(0)

        st.dataframe(
            offenders,
            hide_index=True,
            width="stretch",
            column_config={
                "Articulo/PO": st.column_config.TextColumn("Articulo/PO", width="medium"),
                "Dias de Atraso": st.column_config.NumberColumn("Dias de Atraso", format="%d", width="small"),
                "Riesgo ($)": st.column_config.NumberColumn("Riesgo ($)", format="$%0,d", width="medium"),
            },
        )


def render_alerts_table(df: pd.DataFrame):
    """Fila 2: tabla accionable de alertas criticas con formato condicional."""
    if df.empty:
        st.info("No hay ordenes con riesgo accionable en este momento.")
        return

    with st.container(border=True):
        st.markdown("### Alertas Criticas")
        actions = _coerce_to_dataframe(prioritized_actions(df, top_n=10))
        if actions.empty:
            st.info("No hay ordenes con riesgo accionable en este momento.")
            return

        priority_view = actions.copy().rename(
            columns={
                Columns.PO: "Orden",
                Columns.RA: "RA",
                Columns.FECHA_ENTREGA: "Entrega",
                "MontoRiesgo": "Riesgo financiero",
                "AccionSugerida": "Accion",
                "DiasAtraso": "Atraso",
            }
        )

        visible_cols = [
            col for col in ["Orden", "RA", "Entrega", "EstadoPlazo", "Atraso", "Riesgo financiero", "Accion"]
            if col in priority_view.columns
        ]
        priority_view = priority_view[visible_cols]

        if "Orden" in priority_view.columns:
            priority_view["Orden"] = priority_view["Orden"].fillna("-").astype(str)
        if "RA" in priority_view.columns:
            priority_view["RA"] = priority_view["RA"].fillna("-").astype(str)
        if "Accion" in priority_view.columns:
            priority_view["Accion"] = priority_view["Accion"].fillna("-").astype(str)
        if "Entrega" in priority_view.columns:
            priority_view["Entrega"] = pd.to_datetime(priority_view["Entrega"], errors="coerce").dt.date
        if "Riesgo financiero" in priority_view.columns:
            priority_view["Riesgo financiero"] = pd.to_numeric(priority_view["Riesgo financiero"], errors="coerce").fillna(0)
        if "Atraso" in priority_view.columns:
            priority_view["Atraso"] = pd.to_numeric(priority_view["Atraso"], errors="coerce")

        if "Atraso" in priority_view.columns:
            def _plazo_label(v):
                if pd.isna(v):
                    return "Sin fecha"
                v = int(v)
                if v > 0:
                    return f"{v} dias vencido"
                if v < 0:
                    return f"Faltan {abs(v)} dias"
                return "Vence hoy"

            priority_view["EstadoPlazo"] = priority_view["Atraso"].apply(_plazo_label)
            priority_view["Atraso"] = priority_view["Atraso"].round().astype("Int64")

        display_priority = _coerce_to_dataframe(priority_view)
        try:
            if "Riesgo financiero" in display_priority.columns:
                display_priority["Riesgo financiero"] = pd.to_numeric(
                    display_priority["Riesgo financiero"], errors="coerce"
                ).fillna(0.0)
            if "Atraso" in display_priority.columns:
                display_priority["Atraso"] = pd.to_numeric(
                    display_priority["Atraso"], errors="coerce"
                ).round().astype("Int64")
        except Exception:
            display_priority = _coerce_to_dataframe(priority_view)

        priority_column_config = {
            "Orden": st.column_config.TextColumn("Orden", width="small"),
            "RA": st.column_config.TextColumn("RA", width="small"),
            "EstadoPlazo": st.column_config.TextColumn("Plazo", width="medium"),
            "Atraso": st.column_config.NumberColumn("Dias atraso", width="small", format="%d"),
            "Accion": st.column_config.TextColumn("Accion", width="large"),
        }
        if "Entrega" in display_priority.columns:
            priority_column_config["Entrega"] = st.column_config.DateColumn(
                "Entrega", format="DD/MM/YYYY", width="small"
            )
        if "Riesgo financiero" in display_priority.columns:
            risk_max = float(display_priority["Riesgo financiero"].max() or 0.0)
            risk_max = risk_max if risk_max > 0 else 1.0
            priority_column_config["Riesgo financiero"] = st.column_config.ProgressColumn(
                "Riesgo ($)",
                format="$%0,d",
                min_value=0,
                max_value=risk_max,
                width="medium",
            )

        po_search = st.text_input("Buscar por Numero de Orden (PO)", "")
        if po_search and "Orden" in display_priority.columns:
            display_priority = display_priority[
                display_priority["Orden"].astype(str).str.contains(po_search, case=False, na=False)
            ]

        if display_priority.empty:
            st.info("No hay ordenes que coincidan con la busqueda actual.")
            return

        st.dataframe(
            display_priority,
            hide_index=True,
            column_config=priority_column_config,
            use_container_width=True,
        )

def render_charts(df: pd.DataFrame):
    """Diagnostico ejecutivo: tendencia, ranking de riesgo y tabla accionable."""
    if df.empty:
        return

    st.markdown("<div class='section-gap'></div>", unsafe_allow_html=True)
    st.markdown("### Diagnostico operacional")

    col1, col2 = st.columns([2, 1])

    with col1:
        trend = trend_kpis(df)
        kpi = compute_kpis(df)
        with st.container(border=True):
            st.markdown("<div class='section-title'>Cashflow de riesgo y OTD semanal</div>", unsafe_allow_html=True)
            if not trend.empty:
                trend_plot = trend.copy()
                trend_plot["Week"] = pd.to_datetime(trend_plot["Week"], errors="coerce")
                trend_plot["BacklogRisk"] = pd.to_numeric(trend_plot["BacklogRisk"], errors="coerce").fillna(0)
                trend_plot["OTD"] = pd.to_numeric(trend_plot["OTD"], errors="coerce").fillna(0)

                fig = go.Figure()
                fig.add_trace(
                    go.Scatter(
                        x=trend_plot["Week"],
                        y=trend_plot["BacklogRisk"],
                        mode="lines",
                        name="Backlog Riesgo",
                        line={"color": "#38bdf8", "width": 3, "shape": "spline", "smoothing": 1.1},
                        fill="tozeroy",
                        fillcolor="rgba(56, 189, 248, 0.18)",
                        hovertemplate="Semana: %{x|%d/%m/%Y}<br>Backlog: $%{y:,.0f}<extra></extra>",
                    )
                )
                fig.add_trace(
                    go.Scatter(
                        x=trend_plot["Week"],
                        y=trend_plot["OTD"],
                        mode="lines",
                        name="OTD %",
                        yaxis="y2",
                        line={"color": "#22c55e", "width": 2.5, "shape": "spline", "smoothing": 1.1},
                        hovertemplate="Semana: %{x|%d/%m/%Y}<br>OTD: %{y:.1f}%<extra></extra>",
                    )
                )
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    margin={"l": 10, "r": 10, "t": 6, "b": 10},
                    legend={"orientation": "h", "y": 1.1, "x": 0},
                    xaxis={"title": "Semana", "showgrid": False, "zeroline": False, "color": "#d7dee8"},
                    yaxis={
                        "title": "Backlog en riesgo ($)",
                        "showgrid": True,
                        "gridcolor": "rgba(148,163,184,0.18)",
                        "zeroline": False,
                        "color": "#d7dee8",
                    },
                    yaxis2={
                        "title": "OTD (%)",
                        "overlaying": "y",
                        "side": "right",
                        "showgrid": False,
                        "range": [0, 100],
                        "color": "#d7dee8",
                    },
                    height=320,
                )
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
            else:
                st.caption("Sin datos suficientes para tendencia temporal.")

    with col2:
        owner_risk = risk_by_owner(df, owner_col=Columns.PLANEADOR)
        with st.container(border=True):
            st.markdown("**Carga y riesgo por planeador**")
            if not owner_risk.empty:
                top_owner = owner_risk.head(8)
                chart_owner = (
                    alt.Chart(top_owner)
                    .mark_bar(cornerRadiusEnd=6)
                    .encode(
                        x=alt.X("RiesgoFinanciero:Q", title="Riesgo financiero ($)"),
                        y=alt.Y(f"{Columns.PLANEADOR}:N", sort="-x", title="Planeador"),
                        color=alt.Color(
                            "RiesgoFinanciero:Q",
                            scale=alt.Scale(range=[SKY, DANGER]),
                            legend=None,
                        ),
                        tooltip=[f"{Columns.PLANEADOR}:N", "RiesgoFinanciero:Q", "Ordenes:Q", "CargaPendiente:Q"],
                    )
                    .properties(height=420)
                )
                st.altair_chart(_apply_chart_style(chart_owner), width="stretch")
            else:
                st.caption("Sin riesgo acumulado para responsables.")

    with st.container(border=True):
        st.markdown("**Backlog priorizado para accion inmediata**")
        actions = prioritized_actions(df, top_n=12)
        if actions.empty:
            st.caption("No hay backlog pendiente con riesgo accionable.")
        else:
            backlog_view = actions.copy()
            item_cardinality = int(df[Columns.ITEM].nunique(dropna=True)) if Columns.ITEM in df.columns else 0
            item_is_catalog = item_cardinality > 0 and item_cardinality <= max(25, int(len(df) * 0.5))

            rename_map = {
                Columns.PO: "PO",
                Columns.ITEM: "Item",
                Columns.RA: "RA",
                Columns.PLANEADOR: "Planeador",
                Columns.INGENIERO: "Ingeniero",
                Columns.FECHA_ENTREGA: "Entrega",
                Columns.POR_ENTREGAR: "Pendiente",
                "DiasAtraso": "Atraso",
                "MontoRiesgo": "Riesgo",
                "AccionSugerida": "Accion",
            }
            rename_map[Columns.ITEM] = "Modelo_ID" if item_is_catalog else ""

            visible_columns = [
                column
                for column in [
                    Columns.RA,
                    Columns.PO,
                    Columns.ITEM if item_is_catalog else None,
                    Columns.PLANEADOR,
                    Columns.FECHA_ENTREGA,
                    Columns.POR_ENTREGAR,
                    "MontoRiesgo",
                    "DiasAtraso",
                    "AccionSugerida",
                ]
                if column and column in backlog_view.columns
            ]

            backlog_view = backlog_view[visible_columns].rename(columns=rename_map)
            if "PO" in backlog_view.columns:
                backlog_view = backlog_view.rename(columns={"PO": "Orden (PO)"})
            if "Pendiente" in backlog_view.columns:
                backlog_view = backlog_view.rename(columns={"Pendiente": "Pendientes"})

            for text_col in ["RA", "Orden (PO)", "Modelo_ID", "Planeador", "Accion"]:
                if text_col in backlog_view.columns:
                    backlog_view[text_col] = backlog_view[text_col].fillna("").astype(str)
            for num_col in ["Pendientes", "Atraso", "Riesgo"]:
                if num_col in backlog_view.columns:
                    backlog_view[num_col] = pd.to_numeric(backlog_view[num_col], errors="coerce").fillna(0)

            po_search = st.text_input("Buscar Orden (PO)", placeholder="Ej. 4590214203")
            if po_search and "Orden (PO)" in backlog_view.columns:
                backlog_view = backlog_view[
                    backlog_view["Orden (PO)"].str.contains(po_search.strip(), case=False, na=False)
                ]

            if backlog_view.empty:
                st.info("No hay ordenes que coincidan con el criterio de busqueda actual.")
            else:
                st.dataframe(
                    backlog_view,
                    hide_index=True,
                    width="stretch",
                    column_config={
                        "RA": st.column_config.TextColumn("RA", width="small"),
                        "Orden (PO)": st.column_config.TextColumn("Orden (PO)", width="small"),
                        "Modelo_ID": st.column_config.TextColumn("Modelo ID", width="small"),
                        "Planeador": st.column_config.TextColumn("Planeador", width="medium"),
                        "Entrega": st.column_config.DateColumn("Entrega", format="DD/MM/YYYY"),
                        "Pendientes": st.column_config.NumberColumn("Cantidad", format="%.0f"),
                        "Atraso": st.column_config.NumberColumn("Dias atraso", format="%d"),
                        "Riesgo": st.column_config.NumberColumn("Riesgo ($)", format="$%,.2f"),
                        "Accion": st.column_config.TextColumn("Accion sugerida", width="large"),
                    },
                )

    st.markdown("<div class='section-gap'></div>", unsafe_allow_html=True)
    st.markdown("### Visuales operativas")
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown("**Carga de Trabajo por Planeador**")
            df_plan = group_by_planeador(df)
            if not df_plan.empty and float(pd.to_numeric(df_plan.get("CantidadSolicitada", 0), errors="coerce").fillna(0).sum()) > 0:
                plot_plan = df_plan.rename(columns={Columns.PLANEADOR: "Planeador"}).copy()
                plot_plan["Planeador"] = plot_plan["Planeador"].astype(str)
                plot_plan["CantidadSolicitada"] = pd.to_numeric(
                    plot_plan["CantidadSolicitada"], errors="coerce"
                ).fillna(0)
                chart_plan = (
                    alt.Chart(plot_plan)
                    .mark_bar(color=TEAL, cornerRadiusEnd=6)
                    .encode(
                        x=alt.X("CantidadSolicitada:Q", title="Cantidad"),
                        y=alt.Y("Planeador:N", sort="-x", title=None),
                        tooltip=["Planeador:N", "CantidadSolicitada:Q"],
                    )
                    .properties(height=220)
                )
                st.altair_chart(_apply_chart_style(chart_plan), width="stretch")
            else:
                st.info("No hay datos para este criterio en Carga de Trabajo por Planeador.")

        with c2:
            st.markdown("**Estatus de Entrega**")
            df_cond = group_by_condicion(df)
            if not df_cond.empty and float(pd.to_numeric(df_cond.get(Columns.QTY, 0), errors="coerce").fillna(0).sum()) > 0:
                plot_cond = df_cond.rename(
                    columns={
                        Columns.CONDICION: "Estatus",
                        Columns.QTY: "Cantidad",
                    }
                )
                plot_cond["Estatus"] = plot_cond["Estatus"].astype(str)
                plot_cond["Cantidad"] = pd.to_numeric(
                    plot_cond["Cantidad"], errors="coerce"
                ).fillna(0)
                if len(plot_cond) > 3:
                    chart_cond = (
                        alt.Chart(plot_cond)
                        .mark_bar(cornerRadiusEnd=6)
                        .encode(
                            x=alt.X("Cantidad:Q", title="Cantidad"),
                            y=alt.Y("Estatus:N", sort="-x", title=None),
                            color=alt.Color(
                                "Estatus:N",
                                scale=alt.Scale(range=[SUCCESS, WARNING, DANGER, SKY]),
                                legend=alt.Legend(title=None, orient="bottom"),
                            ),
                            tooltip=["Estatus:N", "Cantidad:Q"],
                        )
                        .properties(height=220)
                    )
                else:
                    chart_cond = (
                        alt.Chart(plot_cond)
                        .mark_arc(innerRadius=55)
                        .encode(
                            theta=alt.Theta("Cantidad:Q"),
                            color=alt.Color(
                                "Estatus:N",
                                scale=alt.Scale(range=[SUCCESS, WARNING, DANGER, SKY]),
                                legend=alt.Legend(title=None, orient="bottom"),
                            ),
                            tooltip=["Estatus:N", "Cantidad:Q"],
                        )
                        .properties(height=220)
                    )
                st.altair_chart(_apply_chart_style(chart_cond), width="stretch")
            else:
                st.info("No hay datos para este criterio en Estatus de Entrega.")

        with c3:
            st.markdown("**Top 5 RA con Mayor Demanda**")
            if Columns.RA in df.columns and Columns.QTY in df.columns:
                plot_top = (
                    df[[Columns.RA, Columns.QTY, Columns.DESCRIPTION]]
                    .copy()
                    .assign(
                        **{
                            Columns.RA: lambda x: x[Columns.RA].astype(str).str.strip(),
                            Columns.QTY: lambda x: pd.to_numeric(x[Columns.QTY], errors="coerce").fillna(0),
                        }
                    )
                    .groupby(Columns.RA, as_index=False)
                    .agg(
                        Demanda=(Columns.QTY, "sum"),
                        Description=(Columns.DESCRIPTION, "first"),
                    )
                    .sort_values("Demanda", ascending=False)
                    .head(5)
                )
                if not plot_top.empty:
                    chart_top = (
                        alt.Chart(plot_top)
                        .mark_bar(color=NAVY, cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
                        .encode(
                            x=alt.X(f"{Columns.RA}:N", title="RA"),
                            y=alt.Y("Demanda:Q", title="Demanda"),
                            tooltip=[f"{Columns.RA}:N", "Demanda:Q", "Description:N"],
                        )
                        .properties(height=220)
                    )
                    st.altair_chart(_apply_chart_style(chart_top), width="stretch")
                else:
                    st.caption("Sin datos para top RA.")
            else:
                st.caption("Sin columna RA disponible para este visual.")


def render_detail_table(df: pd.DataFrame):
    """Tabla ejecutiva de detalle de ordenes con filtros rapidos y columnas clave."""
    if df.empty:
        st.info("No hay registros para mostrar en detalle con los filtros actuales.")
        return

    detail = df.copy()

    if Columns.FECHA_ENTREGA in detail.columns:
        detail[Columns.FECHA_ENTREGA] = pd.to_datetime(detail[Columns.FECHA_ENTREGA], errors="coerce")

    numeric_cols = [Columns.QTY, Columns.ENTREGADOS, Columns.POR_ENTREGAR, Columns.TOTAL, Columns.COSTO_UNITARIO]
    for col in numeric_cols:
        if col in detail.columns:
            detail[col] = pd.to_numeric(detail[col], errors="coerce")

    if Columns.QTY in detail.columns and Columns.ENTREGADOS in detail.columns:
        ratio = (detail[Columns.ENTREGADOS] / detail[Columns.QTY].replace(0, pd.NA)) * 100
        detail["Avance (%)"] = ratio.round(1)

    if Columns.FECHA_ENTREGA in detail.columns:
        now = pd.Timestamp.now().normalize()
        detail["Dias al compromiso"] = (detail[Columns.FECHA_ENTREGA] - now).dt.days

    c1, c2, c3 = st.columns([1.2, 1, 1])
    with c1:
        po_query = st.text_input("Buscar PO", placeholder="Ej. 4590214203")
    with c2:
        show_pending = st.toggle("Solo pendientes", value=False)
    with c3:
        max_rows = st.slider("Filas", min_value=20, max_value=500, value=120, step=20)

    if po_query and Columns.PO in detail.columns:
        detail = detail[detail[Columns.PO].astype(str).str.contains(po_query.strip(), case=False, na=False)]

    if show_pending and Columns.POR_ENTREGAR in detail.columns:
        detail = detail[pd.to_numeric(detail[Columns.POR_ENTREGAR], errors="coerce").fillna(0) > 0]

    sort_cols: list[str] = []
    asc: list[bool] = []
    if "Dias al compromiso" in detail.columns:
        sort_cols.append("Dias al compromiso")
        asc.append(True)
    if Columns.TOTAL in detail.columns:
        sort_cols.append(Columns.TOTAL)
        asc.append(False)
    if sort_cols:
        detail = detail.sort_values(sort_cols, ascending=asc, na_position="last")

    view_columns = [
        col for col in [
            Columns.PO,
            Columns.RA,
            Columns.DESCRIPTION,
            Columns.PLANEADOR,
            Columns.INGENIERO,
            Columns.CONDICION,
            Columns.FECHA_ENTREGA,
            "Dias al compromiso",
            Columns.QTY,
            Columns.ENTREGADOS,
            Columns.POR_ENTREGAR,
            "Avance (%)",
            Columns.COSTO_UNITARIO,
            Columns.TOTAL,
        ]
        if col in detail.columns
    ]

    detail = detail[view_columns].head(max_rows).copy()
    st.caption(f"Mostrando {len(detail):,} registros")
    st.dataframe(
        detail,
        hide_index=True,
        use_container_width=True,
        column_config={
            Columns.FECHA_ENTREGA: st.column_config.DateColumn("Entrega", format="DD/MM/YYYY"),
            "Dias al compromiso": st.column_config.NumberColumn("Dias al compromiso", format="%d"),
            "Avance (%)": st.column_config.ProgressColumn("Avance", min_value=0, max_value=100, format="%.1f%%"),
            Columns.COSTO_UNITARIO: st.column_config.NumberColumn("Costo unitario", format="$%,.2f"),
            Columns.TOTAL: st.column_config.NumberColumn("Monto", format="$%,.2f"),
        },
    )
