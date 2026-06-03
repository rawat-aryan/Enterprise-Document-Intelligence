from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class VendorRecommendation:
    def __init__(
        self,
        vendor_name: str,
        risk_level: str,
        score: float,
        recommendations: list[str],
        metrics: dict[str, Any],
    ):
        self.vendor_name = vendor_name
        self.risk_level = risk_level
        self.score = score
        self.recommendations = recommendations
        self.metrics = metrics

    def to_dict(self) -> dict:
        return {
            "vendor_name": self.vendor_name,
            "risk_level": self.risk_level,
            "score": self.score,
            "recommendations": self.recommendations,
            "metrics": self.metrics,
        }


class CostOptimization:
    def __init__(self, title: str, potential_savings: float, action: str, priority: str):
        self.title = title
        self.potential_savings = potential_savings
        self.action = action
        self.priority = priority

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "potential_savings": self.potential_savings,
            "action": self.action,
            "priority": self.priority,
        }


class RecommendationService:
    def analyze_vendors(self, invoices: list[dict]) -> list[VendorRecommendation]:
        """Analyze vendor performance and return recommendations."""
        vendor_data: dict[str, dict] = defaultdict(lambda: {
            "invoices": [],
            "total_amount": 0.0,
            "duplicate_count": 0,
            "late_count": 0,
            "invalid_count": 0,
        })

        for inv in invoices:
            name = inv.get("vendor_name") or "Unknown"
            vendor_data[name]["invoices"].append(inv)
            vendor_data[name]["total_amount"] += inv.get("total_amount") or 0
            if inv.get("is_duplicate"):
                vendor_data[name]["duplicate_count"] += 1
            if inv.get("validation_status") == "invalid":
                vendor_data[name]["invalid_count"] += 1
            # Check late payments
            due_date = inv.get("due_date")
            if due_date and isinstance(due_date, date) and due_date < date.today():
                vendor_data[name]["late_count"] += 1

        recommendations = []
        for vendor_name, data in vendor_data.items():
            count = len(data["invoices"])
            dup_rate = data["duplicate_count"] / max(count, 1)
            invalid_rate = data["invalid_count"] / max(count, 1)
            avg_amount = data["total_amount"] / max(count, 1)

            # Compute risk score
            risk_score = (dup_rate * 0.4 + invalid_rate * 0.3 + min(data["late_count"] / max(count, 1), 1) * 0.3)

            recs = []
            if dup_rate > 0.1:
                recs.append(f"High duplicate rate ({dup_rate:.1%}): Review invoice submission process")
            if invalid_rate > 0.15:
                recs.append(f"High invalid invoice rate ({invalid_rate:.1%}): Require standardized invoice format")
            if data["late_count"] > 2:
                recs.append(f"{data['late_count']} overdue invoices: Escalate payment disputes")
            if avg_amount > 500_000:
                recs.append("High average invoice amount: Consider milestone-based payments")
            if count < 3:
                recs.append("Low invoice volume: Consider volume discounts negotiation")
            if not recs:
                recs.append("Vendor performance is satisfactory")

            risk_level = "HIGH" if risk_score > 0.6 else ("MEDIUM" if risk_score > 0.3 else "LOW")

            recommendations.append(VendorRecommendation(
                vendor_name=vendor_name,
                risk_level=risk_level,
                score=round(risk_score, 3),
                recommendations=recs,
                metrics={
                    "invoice_count": count,
                    "total_amount": round(data["total_amount"], 2),
                    "average_amount": round(avg_amount, 2),
                    "duplicate_rate": round(dup_rate, 3),
                    "invalid_rate": round(invalid_rate, 3),
                    "late_payments": data["late_count"],
                },
            ))

        return sorted(recommendations, key=lambda x: x.score, reverse=True)

    def detect_cost_anomalies(self, invoices: list[dict]) -> list[CostOptimization]:
        """Detect cost anomalies and optimization opportunities."""
        optimizations = []

        if not invoices:
            return optimizations

        amounts = [inv.get("total_amount") or 0 for inv in invoices if inv.get("total_amount")]
        if not amounts:
            return optimizations

        avg = sum(amounts) / len(amounts)
        sorted_amounts = sorted(amounts)
        p75 = sorted_amounts[int(len(sorted_amounts) * 0.75)]
        p25 = sorted_amounts[int(len(sorted_amounts) * 0.25)]
        iqr = p75 - p25

        # Outlier detection
        outliers = [a for a in amounts if a > p75 + 1.5 * iqr]
        if outliers:
            optimizations.append(CostOptimization(
                title=f"High-value invoice outliers detected ({len(outliers)} invoices)",
                potential_savings=sum(o - avg for o in outliers),
                action="Review invoices above threshold for possible overbilling",
                priority="HIGH",
            ))

        # Duplicate savings
        duplicate_invoices = [inv for inv in invoices if inv.get("is_duplicate")]
        if duplicate_invoices:
            dup_total = sum(inv.get("total_amount") or 0 for inv in duplicate_invoices)
            optimizations.append(CostOptimization(
                title=f"Duplicate invoices: {len(duplicate_invoices)} detected",
                potential_savings=dup_total,
                action="Block duplicate invoice payments immediately",
                priority="CRITICAL",
            ))

        # Vendor consolidation
        vendor_counts: dict[str, int] = defaultdict(int)
        for inv in invoices:
            name = inv.get("vendor_name") or "Unknown"
            vendor_counts[name] += 1

        single_invoice_vendors = [v for v, c in vendor_counts.items() if c == 1]
        if len(single_invoice_vendors) > 5:
            optimizations.append(CostOptimization(
                title=f"Vendor fragmentation: {len(single_invoice_vendors)} one-time vendors",
                potential_savings=avg * len(single_invoice_vendors) * 0.05,
                action="Consolidate procurement to fewer preferred vendors for volume discounts",
                priority="MEDIUM",
            ))

        # Early payment discount opportunity
        today = date.today()
        early_payment_candidates = [
            inv for inv in invoices
            if inv.get("due_date") and isinstance(inv.get("due_date"), date)
            and 0 < (inv["due_date"] - today).days <= 30
        ]
        if early_payment_candidates:
            early_total = sum(inv.get("total_amount") or 0 for inv in early_payment_candidates)
            optimizations.append(CostOptimization(
                title=f"Early payment discount opportunity ({len(early_payment_candidates)} invoices)",
                potential_savings=early_total * 0.02,
                action="Negotiate 2% early payment discount with vendors for invoices due within 30 days",
                priority="LOW",
            ))

        return sorted(optimizations, key=lambda x: ["CRITICAL", "HIGH", "MEDIUM", "LOW"].index(x.priority))

    def score_contracts(self, contracts: list[dict]) -> list[dict]:
        """Analyze contracts for risk and generate alerts."""
        alerts = []
        today = date.today()

        for contract in contracts:
            exp_date = contract.get("expiration_date")
            if exp_date and isinstance(exp_date, date):
                days_to_expiry = (exp_date - today).days
                if days_to_expiry < 0:
                    alerts.append({
                        "contract_id": contract.get("id"),
                        "alert_type": "EXPIRED",
                        "severity": "CRITICAL",
                        "message": f"Contract expired {abs(days_to_expiry)} days ago",
                        "parties": contract.get("parties"),
                    })
                elif days_to_expiry <= 30:
                    alerts.append({
                        "contract_id": contract.get("id"),
                        "alert_type": "EXPIRING_SOON",
                        "severity": "HIGH",
                        "message": f"Contract expires in {days_to_expiry} days",
                        "parties": contract.get("parties"),
                    })
                elif days_to_expiry <= 90:
                    alerts.append({
                        "contract_id": contract.get("id"),
                        "alert_type": "RENEWAL_REVIEW",
                        "severity": "MEDIUM",
                        "message": f"Contract expires in {days_to_expiry} days - start renewal process",
                        "parties": contract.get("parties"),
                    })

            risk_score = contract.get("risk_score") or 0
            if risk_score > 0.7:
                alerts.append({
                    "contract_id": contract.get("id"),
                    "alert_type": "HIGH_RISK",
                    "severity": "HIGH",
                    "message": f"High contract risk score: {risk_score:.2f}",
                    "risk_factors": contract.get("risk_factors", []),
                })

        return alerts


recommendation_service = RecommendationService()
