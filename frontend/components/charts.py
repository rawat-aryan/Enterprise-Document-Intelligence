"""Reusable Plotly chart components."""
from typing import Any
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd


def monthly_spend_chart(monthly_data: list[dict]) -> go.Figure:
    """Line chart of monthly spend trends."""
    if not monthly_data:
        fig = go.Figure()
        fig.update_layout(title="Monthly Spend Trend (No Data)")
        return fig

    df = pd.DataFrame(monthly_data)
    fig = px.line(
        df,
        x="month",
        y="total",
        title="Monthly Spend Trend",
        labels={"month": "Month", "total": "Amount (INR)"},
        markers=True,
    )
    fig.update_layout(
        hovermode="x unified",
        plot_bgcolor="white",
        paper_bgcolor="white",
        font_family="Arial",
    )
    fig.update_traces(line_color="#2E75B6", line_width=3, marker_size=8)
    return fig


def vendor_distribution_chart(vendor_data: list[dict]) -> go.Figure:
    """Pie chart of vendor spend distribution."""
    if not vendor_data:
        fig = go.Figure()
        fig.update_layout(title="Vendor Distribution (No Data)")
        return fig

    labels = [v.get("vendor_name", v.get("vendor", "Unknown")) for v in vendor_data[:10]]
    values = [v.get("total_amount", v.get("total_spend", 0)) for v in vendor_data[:10]]

    fig = go.Figure(data=[
        go.Pie(
            labels=labels,
            values=values,
            hole=0.4,
            textposition="inside",
            textinfo="percent+label",
        )
    ])
    fig.update_layout(
        title="Vendor Spend Distribution (Top 10)",
        showlegend=True,
        legend=dict(orientation="v", x=1.0, y=0.5),
    )
    return fig


def invoice_status_chart(validation_breakdown: dict) -> go.Figure:
    """Bar chart of invoice validation status."""
    statuses = list(validation_breakdown.keys())
    counts = list(validation_breakdown.values())
    colors = {
        "valid": "#2ECC71",
        "invalid": "#E74C3C",
        "needs_review": "#F39C12",
        "pending": "#95A5A6",
    }

    fig = go.Figure(data=[
        go.Bar(
            x=statuses,
            y=counts,
            marker_color=[colors.get(s, "#3498DB") for s in statuses],
            text=counts,
            textposition="auto",
        )
    ])
    fig.update_layout(
        title="Invoice Validation Status",
        xaxis_title="Status",
        yaxis_title="Count",
        plot_bgcolor="white",
    )
    return fig


def risk_gauge_chart(risk_score: float, title: str = "Risk Score") -> go.Figure:
    """Gauge chart for risk score display."""
    color = "#2ECC71" if risk_score < 0.3 else ("#F39C12" if risk_score < 0.7 else "#E74C3C")

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=risk_score * 100,
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": title},
        delta={"reference": 50},
        gauge={
            "axis": {"range": [None, 100]},
            "bar": {"color": color},
            "steps": [
                {"range": [0, 30], "color": "#D5F5E3"},
                {"range": [30, 70], "color": "#FDEBD0"},
                {"range": [70, 100], "color": "#FADBD8"},
            ],
            "threshold": {
                "line": {"color": "red", "width": 4},
                "thickness": 0.75,
                "value": 70,
            },
        },
    ))
    fig.update_layout(height=300)
    return fig


def contract_health_chart(contracts: list[dict]) -> go.Figure:
    """Scatter chart of contracts by risk score and days to expiry."""
    if not contracts:
        fig = go.Figure()
        fig.update_layout(title="Contract Health Matrix (No Data)")
        return fig

    from datetime import date
    today = date.today()
    names, risk_scores, days_to_expiry, values = [], [], [], []

    for c in contracts:
        names.append(str(c.get("id", ""))[:8])
        risk_scores.append(c.get("risk_score") or 0.0)
        exp = c.get("expiration_date")
        if exp:
            from datetime import datetime
            if isinstance(exp, str):
                try:
                    exp = datetime.fromisoformat(exp).date()
                except Exception:
                    exp = None
        days_to_expiry.append((exp - today).days if exp else 365)
        values.append(c.get("contract_value") or 10000)

    fig = go.Figure(data=[
        go.Scatter(
            x=days_to_expiry,
            y=risk_scores,
            mode="markers+text",
            text=names,
            textposition="top center",
            marker=dict(
                size=[max(10, min(v / 10000, 50)) for v in values],
                color=risk_scores,
                colorscale="RdYlGn_r",
                showscale=True,
                colorbar=dict(title="Risk Score"),
            ),
        )
    ])
    fig.update_layout(
        title="Contract Health Matrix",
        xaxis_title="Days to Expiry",
        yaxis_title="Risk Score",
        plot_bgcolor="white",
    )
    return fig


def processing_metrics_chart(metrics: dict) -> go.Figure:
    """Funnel chart of document processing pipeline metrics."""
    stages = ["Uploaded", "Processing", "Extracted", "Validated", "Failed"]
    values = [
        metrics.get("uploaded", 0),
        metrics.get("processing", 0),
        metrics.get("extracted", 0),
        metrics.get("validated", 0),
        metrics.get("failed", 0),
    ]

    fig = go.Figure(go.Funnel(
        y=stages,
        x=values,
        textinfo="value+percent initial",
        marker_color=["#3498DB", "#2E75B6", "#1F4E79", "#2ECC71", "#E74C3C"],
    ))
    fig.update_layout(title="Document Processing Pipeline")
    return fig


def spend_trend_chart(data: list[dict], x_col: str, y_col: str, title: str = "Spend Trend") -> go.Figure:
    """Generic spend trend bar chart."""
    if not data:
        fig = go.Figure()
        fig.update_layout(title=f"{title} (No Data)")
        return fig

    df = pd.DataFrame(data)
    fig = px.bar(df, x=x_col, y=y_col, title=title, color_discrete_sequence=["#2E75B6"])
    fig.update_layout(plot_bgcolor="white", xaxis_title="", yaxis_title="Amount (INR)")
    return fig


def duplicate_analysis_chart(total: int, duplicate: int) -> go.Figure:
    """Donut chart showing duplicate vs unique invoices."""
    labels = ["Unique", "Potential Duplicates"]
    values = [max(total - duplicate, 0), duplicate]
    colors = ["#2ECC71", "#E74C3C"]

    fig = go.Figure(data=[
        go.Pie(labels=labels, values=values, hole=0.5, marker_colors=colors)
    ])
    fig.update_layout(
        title="Invoice Uniqueness Analysis",
        annotations=[dict(text=f"{duplicate}<br>Dups", x=0.5, y=0.5, font_size=14, showarrow=False)],
    )
    return fig
