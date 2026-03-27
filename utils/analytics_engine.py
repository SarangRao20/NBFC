"""
Analytics Engine for loan marketplace operations
Calculates metrics, trends, and performance indicators
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from statistics import mean, stdev
import json


@dataclass
class KPIMetrics:
    """Key Performance Indicators for the marketplace"""
    total_loans_compared: int
    total_unique_users: int
    conversions: int
    conversion_rate: float
    avg_emi: float
    avg_interest_rate: float
    avg_approval_probability: float
    total_cost_savings: float
    processed_at: datetime


@dataclass
class LenderPerformance:
    """Performance metrics for individual lender"""
    lender_id: str
    lender_name: str
    selections: int
    selection_rate: float
    avg_emi_offered: float
    avg_rate: float
    avg_approval_prob: float
    market_share: float
    trend: str  # up, down, stable


@dataclass
class ConversionFunnel:
    """Conversion funnel metrics"""
    total_views: int
    total_comparisons: int
    total_selections: int
    view_to_compare: float  # percentage
    compare_to_select: float  # percentage
    overall_conversion: float  # percentage


class AnalyticsEngine:
    """
    Analytics engine for marketplace metrics and reporting
    """
    
    def __init__(self):
        """Initialize analytics engine"""
        self.mock_data = self._load_mock_data()
        self.last_calculation = None
        
    def _load_mock_data(self) -> Dict:
        """Load mock analytics data"""
        return {
            "daily_metrics": [
                {
                    "date": (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d"),
                    "total_loans_compared": 45 + (i * 3),
                    "conversions": 15 + (i * 1),
                    "avg_emi": 12500 - (i * 50),
                    "avg_rate": 8.5 - (i * 0.05),
                    "avg_approval_prob": 0.78 + (i * 0.01),
                    "total_cost_savings": 450000 + (i * 30000),
                }
                for i in range(30)
            ],
            "lender_performance": {
                "bank_a": {"selections": 645, "avg_emi": 12100, "avg_rate": 8.2, "approval_prob": 0.85},
                "bank_b": {"selections": 520, "avg_emi": 12800, "avg_rate": 8.6, "approval_prob": 0.82},
                "nbfc_x": {"selections": 385, "avg_emi": 11500, "avg_rate": 7.9, "approval_prob": 0.92},
                "fintech_y": {"selections": 290, "avg_emi": 13200, "avg_rate": 9.1, "approval_prob": 0.75},
                "credit_union_z": {"selections": 210, "avg_emi": 11900, "avg_rate": 8.3, "approval_prob": 0.88},
            },
            "conversion_funnel": {
                "total_views": 3400,
                "total_comparisons": 2450,
                "total_selections": 847,
            },
            "user_profiles": {
                "avg_loan_amount": 425000,
                "avg_tenure": 60,
                "avg_salary": 45000,
                "avg_credit_score": 720,
                "avg_obligations": 8500,
                "avg_age": 32,
            }
        }
    
    def calculate_kpis(self, days: int = 30) -> KPIMetrics:
        """Calculate key performance indicators for last N days"""
        recent_metrics = self.mock_data["daily_metrics"][-days:]
        
        total_loans = sum(m["total_loans_compared"] for m in recent_metrics)
        total_users = int(total_loans / 1.2)  # Approximate unique users
        conversions = sum(m["conversions"] for m in recent_metrics)
        conversion_rate = (conversions / total_loans * 100) if total_loans > 0 else 0
        
        avg_emi = mean(m["avg_emi"] for m in recent_metrics)
        avg_rate = mean(m["avg_rate"] for m in recent_metrics)
        avg_approval = mean(m["avg_approval_prob"] for m in recent_metrics)
        total_savings = sum(m["total_cost_savings"] for m in recent_metrics)
        
        kpi = KPIMetrics(
            total_loans_compared=total_loans,
            total_unique_users=total_users,
            conversions=conversions,
            conversion_rate=round(conversion_rate, 2),
            avg_emi=round(avg_emi, 2),
            avg_interest_rate=round(avg_rate, 2),
            avg_approval_probability=round(avg_approval, 3),
            total_cost_savings=total_savings,
            processed_at=datetime.now()
        )
        
        self.last_calculation = kpi
        return kpi
    
    def get_lender_performance(self) -> Dict[str, LenderPerformance]:
        """Calculate performance metrics for all lenders"""
        lender_data = self.mock_data["lender_performance"]
        funnel = self.mock_data["conversion_funnel"]
        
        total_selections = sum(lender["selections"] for lender in lender_data.values())
        
        lenders = {
            "bank_a": ("Bank A", 0),
            "bank_b": ("Bank B", -1),
            "nbfc_x": ("NBFC X", 2),
            "fintech_y": ("Fintech Y", -2),
            "credit_union_z": ("Credit Union Z", 1),
        }
        
        performance = {}
        for lender_id, (lender_name, trend_days) in lenders.items():
            data = lender_data[lender_id]
            selections = data["selections"]
            market_share = (selections / total_selections * 100) if total_selections > 0 else 0
            
            trend_direction = "up" if trend_days > 0 else ("down" if trend_days < 0 else "stable")
            
            performance[lender_id] = LenderPerformance(
                lender_id=lender_id,
                lender_name=lender_name,
                selections=selections,
                selection_rate=round((selections / funnel["total_comparisons"] * 100), 2),
                avg_emi_offered=data["avg_emi"],
                avg_rate=data["avg_rate"],
                avg_approval_prob=round(data["approval_prob"], 3),
                market_share=round(market_share, 2),
                trend=trend_direction
            )
        
        return performance
    
    def get_conversion_funnel(self) -> ConversionFunnel:
        """Calculate conversion funnel metrics"""
        funnel = self.mock_data["conversion_funnel"]
        
        view_to_compare = (funnel["total_comparisons"] / funnel["total_views"] * 100) if funnel["total_views"] > 0 else 0
        compare_to_select = (funnel["total_selections"] / funnel["total_comparisons"] * 100) if funnel["total_comparisons"] > 0 else 0
        overall = (funnel["total_selections"] / funnel["total_views"] * 100) if funnel["total_views"] > 0 else 0
        
        return ConversionFunnel(
            total_views=funnel["total_views"],
            total_comparisons=funnel["total_comparisons"],
            total_selections=funnel["total_selections"],
            view_to_compare=round(view_to_compare, 2),
            compare_to_select=round(compare_to_select, 2),
            overall_conversion=round(overall, 2)
        )
    
    def get_trends(self, days: int = 30) -> Dict:
        """Get historical trends for last N days"""
        recent = self.mock_data["daily_metrics"][-days:]
        
        return {
            "dates": [m["date"] for m in recent],
            "loans_compared": [m["total_loans_compared"] for m in recent],
            "conversions": [m["conversions"] for m in recent],
            "avg_emi": [m["avg_emi"] for m in recent],
            "avg_rate": [m["avg_rate"] for m in recent],
            "avg_approval": [m["avg_approval_prob"] for m in recent],
            "cost_savings": [m["total_cost_savings"] for m in recent],
        }
    
    def get_user_profile_stats(self) -> Dict:
        """Get aggregated user profile statistics"""
        return self.mock_data["user_profiles"]
    
    def calculate_cost_efficiency(self, lender_performances: Dict[str, LenderPerformance]) -> Dict:
        """Calculate cost efficiency scores for lenders"""
        efficiency = {}
        
        all_emis = [lp.avg_emi_offered for lp in lender_performances.values()]
        all_rates = [lp.avg_rate for lp in lender_performances.values()]
        
        min_emi = min(all_emis)
        max_emi = max(all_emis)
        min_rate = min(all_rates)
        max_rate = max(all_rates)
        
        for lender_id, lender_perf in lender_performances.items():
            # Normalize EMI (lower is better): 0-100
            emi_score = 100 - ((lender_perf.avg_emi_offered - min_emi) / (max_emi - min_emi) * 100)
            
            # Normalize rate (lower is better): 0-100
            rate_score = 100 - ((lender_perf.avg_rate - min_rate) / (max_rate - min_rate) * 100)
            
            # Approval score: higher is better
            approval_score = lender_perf.avg_approval_prob * 100
            
            # Composite efficiency score
            efficiency_score = (emi_score * 0.35 + rate_score * 0.35 + approval_score * 0.30)
            
            efficiency[lender_id] = {
                "lender_name": lender_perf.lender_name,
                "efficiency_score": round(efficiency_score, 2),
                "emi_score": round(emi_score, 2),
                "rate_score": round(rate_score, 2),
                "approval_score": round(approval_score, 2),
            }
        
        return efficiency
    
    def generate_daily_report(self) -> Dict:
        """Generate daily report with all metrics"""
        kpis = self.calculate_kpis(days=1)
        lender_perf = self.get_lender_performance()
        funnel = self.get_conversion_funnel()
        efficiency = self.calculate_cost_efficiency(lender_perf)
        user_stats = self.get_user_profile_stats()
        
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "kpis": {
                "total_loans_compared": kpis.total_loans_compared,
                "conversions": kpis.conversions,
                "conversion_rate": kpis.conversion_rate,
                "avg_emi": kpis.avg_emi,
                "avg_rate": kpis.avg_interest_rate,
                "avg_approval_prob": kpis.avg_approval_probability,
                "total_cost_savings": kpis.total_cost_savings,
            },
            "funnel": {
                "total_views": funnel.total_views,
                "total_comparisons": funnel.total_comparisons,
                "total_selections": funnel.total_selections,
                "view_to_compare": funnel.view_to_compare,
                "compare_to_select": funnel.compare_to_select,
                "overall_conversion": funnel.overall_conversion,
            },
            "lender_performance": {
                lender_id: {
                    "lender_name": lp.lender_name,
                    "selections": lp.selections,
                    "selection_rate": lp.selection_rate,
                    "avg_emi": lp.avg_emi_offered,
                    "avg_rate": lp.avg_rate,
                    "approval_prob": lp.avg_approval_prob,
                    "market_share": lp.market_share,
                    "trend": lp.trend,
                }
                for lender_id, lp in lender_perf.items()
            },
            "efficiency": efficiency,
            "user_stats": user_stats,
        }
    
    def generate_weekly_report(self) -> Dict:
        """Generate weekly report"""
        kpis = self.calculate_kpis(days=7)
        trends = self.get_trends(days=7)
        lender_perf = self.get_lender_performance()
        
        return {
            "period": f"Last 7 days (ending {datetime.now().strftime('%Y-%m-%d')})",
            "summary": {
                "total_loans_compared": kpis.total_loans_compared,
                "avg_daily_comparisons": round(kpis.total_loans_compared / 7, 0),
                "conversions": kpis.conversions,
                "conversion_rate": kpis.conversion_rate,
                "avg_emi": kpis.avg_emi,
                "avg_rate": kpis.avg_interest_rate,
                "avg_approval_prob": kpis.avg_approval_probability,
                "total_cost_savings": kpis.total_cost_savings,
            },
            "trends": trends,
            "top_lenders": sorted(
                lender_perf.items(),
                key=lambda x: x[1].selections,
                reverse=True
            )[:3],
        }
    
    def generate_monthly_report(self) -> Dict:
        """Generate monthly report"""
        kpis = self.calculate_kpis(days=30)
        trends = self.get_trends(days=30)
        lender_perf = self.get_lender_performance()
        efficiency = self.calculate_cost_efficiency(lender_perf)
        
        return {
            "period": f"Last 30 days (ending {datetime.now().strftime('%Y-%m-%d')})",
            "summary": {
                "total_loans_compared": kpis.total_loans_compared,
                "avg_daily_comparisons": round(kpis.total_loans_compared / 30, 0),
                "distinct_users": kpis.total_unique_users,
                "conversions": kpis.conversions,
                "conversion_rate": kpis.conversion_rate,
                "avg_emi": kpis.avg_emi,
                "avg_rate": kpis.avg_interest_rate,
                "avg_approval_prob": kpis.avg_approval_probability,
                "total_cost_savings": kpis.total_cost_savings,
            },
            "trends": trends,
            "lender_rankings": {
                lender_id: {
                    "name": lp.lender_name,
                    "market_share": lp.market_share,
                    "selections": lp.selections,
                    "efficiency_score": efficiency.get(lender_id, {}).get("efficiency_score", 0),
                    "trend": lp.trend,
                }
                for lender_id, lp in lender_perf.items()
            },
        }


# Singleton instance
analytics = AnalyticsEngine()
