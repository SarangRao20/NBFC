"""
Admin Service - Business logic layer for admin operations
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from api.schemas.admin import (
    KPIMetrics,
    LenderPerformanceData,
    AdminStatsOverviewResponse,
    ConversionFunnelData,
    LenderInfoRequest,
    LenderInfoResponse,
    LendersListResponse,
    ReportRequest,
    ReportResponse,
    PerformanceMetricsResponse,
    EfficiencyScore,
    UserProfileStats,
    TrendData,
    AdminTrendsResponse,
)
from utils.analytics_engine import analytics
import json
from io import BytesIO
import uuid


class AdminService:
    """Service layer for admin operations"""
    
    def __init__(self):
        """Initialize admin service"""
        self.analytics = analytics
        self.mock_lenders = self._load_mock_lenders()
        self.reports = {}
    
    def _load_mock_lenders(self) -> Dict:
        """Load mock lender data"""
        return {
            "bank_a": {
                "id": "bank_a",
                "name": "Bank A",
                "type": "bank",
                "min_loan_amount": 100000,
                "max_loan_amount": 5000000,
                "min_tenure": 6,
                "max_tenure": 84,
                "interest_rate_min": 7.5,
                "interest_rate_max": 12.5,
                "processing_fee": 1000,
                "approval_probability": 0.85,
                "is_active": True,
                "created_at": datetime.now() - timedelta(days=365),
                "updated_at": datetime.now(),
            },
            "bank_b": {
                "id": "bank_b",
                "name": "Bank B",
                "type": "bank",
                "min_loan_amount": 150000,
                "max_loan_amount": 4000000,
                "min_tenure": 6,
                "max_tenure": 84,
                "interest_rate_min": 8.0,
                "interest_rate_max": 13.0,
                "processing_fee": 2000,
                "approval_probability": 0.82,
                "is_active": True,
                "created_at": datetime.now() - timedelta(days=365),
                "updated_at": datetime.now(),
            },
            "nbfc_x": {
                "id": "nbfc_x",
                "name": "NBFC X",
                "type": "nbfc",
                "min_loan_amount": 50000,
                "max_loan_amount": 2500000,
                "min_tenure": 6,
                "max_tenure": 60,
                "interest_rate_min": 7.0,
                "interest_rate_max": 12.0,
                "processing_fee": 1500,
                "approval_probability": 0.92,
                "is_active": True,
                "created_at": datetime.now() - timedelta(days=180),
                "updated_at": datetime.now(),
            },
            "fintech_y": {
                "id": "fintech_y",
                "name": "Fintech Y",
                "type": "fintech",
                "min_loan_amount": 100000,
                "max_loan_amount": 3000000,
                "min_tenure": 12,
                "max_tenure": 120,
                "interest_rate_min": 8.5,
                "interest_rate_max": 14.0,
                "processing_fee": 500,
                "approval_probability": 0.75,
                "is_active": True,
                "created_at": datetime.now() - timedelta(days=90),
                "updated_at": datetime.now(),
            },
            "credit_union_z": {
                "id": "credit_union_z",
                "name": "Credit Union Z",
                "type": "credit_union",
                "min_loan_amount": 200000,
                "max_loan_amount": 4500000,
                "min_tenure": 12,
                "max_tenure": 84,
                "interest_rate_min": 7.8,
                "interest_rate_max": 12.5,
                "processing_fee": 1200,
                "approval_probability": 0.88,
                "is_active": True,
                "created_at": datetime.now() - timedelta(days=150),
                "updated_at": datetime.now(),
            },
        }
    
    # ========================================================================
    # Statistics & Overview
    # ========================================================================
    
    def get_stats_overview(self, days: int = 30) -> AdminStatsOverviewResponse:
        """Get admin dashboard overview stats"""
        kpis = self.analytics.calculate_kpis(days=days)
        funnel = self.analytics.get_conversion_funnel()
        
        return AdminStatsOverviewResponse(
            kpis=kpis,
            funnel=funnel,
            period_days=days,
        )
    
    def get_loan_analytics(self, days: int = 30) -> Dict:
        """Get loan comparison analytics"""
        trends = self.analytics.get_trends(days=days)
        user_stats = self.analytics.get_user_profile_stats()
        
        return {
            "trends": trends,
            "user_profile_stats": user_stats,
            "period_days": days,
        }
    
    def get_conversion_funnel(self) -> Dict:
        """Get detailed conversion funnel data"""
        funnel = self.analytics.get_conversion_funnel()
        
        return {
            "total_views": funnel.total_views,
            "total_comparisons": funnel.total_comparisons,
            "total_selections": funnel.total_selections,
            "view_to_compare_rate": funnel.view_to_compare,
            "compare_to_select_rate": funnel.compare_to_select,
            "overall_conversion_rate": funnel.overall_conversion,
            "details": {
                "view_to_compare_count": int(funnel.total_views * funnel.view_to_compare / 100),
                "dropped_at_compare": int(funnel.total_views - (funnel.total_views * funnel.view_to_compare / 100)),
                "compare_to_select_count": int(funnel.total_comparisons * funnel.compare_to_select / 100),
                "dropped_at_select": int(funnel.total_comparisons - (funnel.total_comparisons * funnel.compare_to_select / 100)),
            }
        }
    
    # ========================================================================
    # Lender Management
    # ========================================================================
    
    def list_lenders(self) -> LendersListResponse:
        """Get list of all lenders with performance data"""
        lender_perf = self.analytics.get_lender_performance()
        
        lenders_data = [
            LenderPerformanceData(
                lender_id=lp.lender_id,
                lender_name=lp.lender_name,
                selections=lp.selections,
                selection_rate=lp.selection_rate,
                avg_emi_offered=lp.avg_emi_offered,
                avg_rate=lp.avg_rate,
                avg_approval_prob=lp.avg_approval_prob,
                market_share=lp.market_share,
                trend=lp.trend,
            )
            for lp in lender_perf.values()
        ]
        
        active_lenders = [l for l in self.mock_lenders.values() if l["is_active"]]
        
        return LendersListResponse(
            lenders=lenders_data,
            total_count=len(self.mock_lenders),
            active_count=len(active_lenders),
        )
    
    def get_lender(self, lender_id: str) -> Optional[LenderInfoResponse]:
        """Get specific lender details"""
        if lender_id not in self.mock_lenders:
            return None
        
        lender = self.mock_lenders[lender_id]
        return LenderInfoResponse(**lender)
    
    def create_lender(self, request: LenderInfoRequest) -> LenderInfoResponse:
        """Create new lender"""
        lender_id = request.name.lower().replace(" ", "_")
        
        new_lender = {
            "id": lender_id,
            "name": request.name,
            "type": request.type,
            "min_loan_amount": request.min_loan_amount,
            "max_loan_amount": request.max_loan_amount,
            "min_tenure": request.min_tenure,
            "max_tenure": request.max_tenure,
            "interest_rate_min": request.interest_rate_min,
            "interest_rate_max": request.interest_rate_max,
            "processing_fee": request.processing_fee,
            "approval_probability": request.approval_probability,
            "is_active": request.is_active,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        
        self.mock_lenders[lender_id] = new_lender
        return LenderInfoResponse(**new_lender)
    
    def update_lender(self, lender_id: str, request: LenderInfoRequest) -> Optional[LenderInfoResponse]:
        """Update existing lender"""
        if lender_id not in self.mock_lenders:
            return None
        
        lender = self.mock_lenders[lender_id]
        lender.update({
            "name": request.name,
            "type": request.type,
            "min_loan_amount": request.min_loan_amount,
            "max_loan_amount": request.max_loan_amount,
            "min_tenure": request.min_tenure,
            "max_tenure": request.max_tenure,
            "interest_rate_min": request.interest_rate_min,
            "interest_rate_max": request.interest_rate_max,
            "processing_fee": request.processing_fee,
            "approval_probability": request.approval_probability,
            "is_active": request.is_active,
            "updated_at": datetime.now(),
        })
        
        self.mock_lenders[lender_id] = lender
        return LenderInfoResponse(**lender)
    
    def delete_lender(self, lender_id: str) -> bool:
        """Deactivate lender"""
        if lender_id not in self.mock_lenders:
            return False
        
        self.mock_lenders[lender_id]["is_active"] = False
        self.mock_lenders[lender_id]["updated_at"] = datetime.now()
        return True
    
    # ========================================================================
    # Performance & Trends
    # ========================================================================
    
    def get_performance_metrics(self, days: int = 30) -> PerformanceMetricsResponse:
        """Get comprehensive performance metrics"""
        kpis = self.analytics.calculate_kpis(days=days)
        lender_perf = self.analytics.get_lender_performance()
        efficiency = self.analytics.calculate_cost_efficiency(lender_perf)
        
        lenders_data = [
            LenderPerformanceData(
                lender_id=lp.lender_id,
                lender_name=lp.lender_name,
                selections=lp.selections,
                selection_rate=lp.selection_rate,
                avg_emi_offered=lp.avg_emi_offered,
                avg_rate=lp.avg_rate,
                avg_approval_prob=lp.avg_approval_prob,
                market_share=lp.market_share,
                trend=lp.trend,
            )
            for lp in lender_perf.values()
        ]
        
        efficiency_scores = [
            EfficiencyScore(
                lender_id=lender_id,
                lender_name=eff["lender_name"],
                efficiency_score=eff["efficiency_score"],
                emi_score=eff["emi_score"],
                rate_score=eff["rate_score"],
                approval_score=eff["approval_score"],
            )
            for lender_id, eff in efficiency.items()
        ]
        
        top_performers = sorted(
            [(lender_id, lp.market_share) for lender_id, lp in lender_perf.items()],
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        return PerformanceMetricsResponse(
            period_days=days,
            kpis=kpis,
            lender_performance=lenders_data,
            efficiency_scores=efficiency_scores,
            top_performers=[lp[0] for lp in top_performers],
        )
    
    def get_trends(self, days: int = 30) -> AdminTrendsResponse:
        """Get historical trends data"""
        trends_dict = self.analytics.get_trends(days=days)
        
        # Create TrendData object
        trend_data = TrendData(
            dates=trends_dict["dates"],
            loans_compared=trends_dict["loans_compared"],
            conversions=trends_dict["conversions"],
            avg_emi=trends_dict["avg_emi"],
            avg_rate=trends_dict["avg_rate"],
            avg_approval=trends_dict["avg_approval"],
            cost_savings=trends_dict["cost_savings"],
        )
        
        # Calculate summary from trends
        summary = {
            "total_loans": sum(trend_data.loans_compared),
            "total_conversions": sum(trend_data.conversions),
            "avg_daily_loans": round(sum(trend_data.loans_compared) / len(trend_data.loans_compared), 2),
            "avg_daily_conversions": round(sum(trend_data.conversions) / len(trend_data.conversions), 2),
            "peak_day_loans": max(trend_data.loans_compared),
            "peak_day_loans_date": trend_data.dates[trend_data.loans_compared.index(max(trend_data.loans_compared))],
        }
        
        return AdminTrendsResponse(
            trends=trend_data,
            period_days=days,
            summary=summary,
        )
    
    # ========================================================================
    # Reporting & Export
    # ========================================================================
    
    def generate_report(self, request: ReportRequest) -> ReportResponse:
        """Generate report"""
        report_id = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
        
        # Generate report based on type
        if request.report_type.value == "daily":
            report_data = self.analytics.generate_daily_report()
            period = datetime.now().strftime("%Y-%m-%d")
        elif request.report_type.value == "weekly":
            report_data = self.analytics.generate_weekly_report()
            period = f"Week of {(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')}"
        elif request.report_type.value == "monthly":
            report_data = self.analytics.generate_monthly_report()
            period = datetime.now().strftime("%B %Y")
        else:
            period = "Unknown"
            report_data = {}
        
        # Store report metadata
        self.reports[report_id] = {
            "data": report_data,
            "type": request.report_type.value,
            "format": request.export_format.value,
            "created_at": datetime.now(),
            "email_to": request.email_to,
        }
        
        # Create response
        response = ReportResponse(
            report_id=report_id,
            report_type=request.report_type.value,
            period=period,
            url=f"/admin/reports/{report_id}.{request.export_format.value}",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(days=30),
        )
        
        return response
    
    def get_report(self, report_id: str) -> Optional[Dict]:
        """Retrieve generated report"""
        return self.reports.get(report_id)
    
    def export_report(self, report_id: str, format: str) -> Optional[bytes]:
        """Export report in specified format"""
        report = self.reports.get(report_id)
        if not report:
            return None
        
        if format == "json":
            return json.dumps(report["data"], indent=2).encode()
        elif format == "csv":
            return self._generate_csv(report["data"])
        elif format == "pdf":
            return self._generate_pdf(report["data"])
        
        return None
    
    def _generate_csv(self, data: Dict) -> bytes:
        """Generate CSV from report data"""
        csv_content = "Loan Marketplace Report\\n"
        csv_content += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n\\n"
        
        csv_content += "Key Metrics\\n"
        if "kpis" in data:
            for key, value in data["kpis"].items():
                csv_content += f"{key},{value}\\n"
        
        csv_content += "\\nLender Performance\\n"
        if "lender_performance" in data:
            csv_content += "Lender,Selections,Selection Rate,Market Share,Trend\\n"
            for lender_id, perf in data["lender_performance"].items():
                csv_content += f"{perf['lender_name']},{perf['selections']},{perf['selection_rate']},{perf['market_share']},{perf['trend']}\\n"
        
        return csv_content.encode()
    
    def _generate_pdf(self, data: Dict) -> bytes:
        """Generate PDF from report data"""
        # For now, return a simple text PDF
        pdf_content = f"LOAN MARKETPLACE REPORT\\n"
        pdf_content += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n\\n"
        
        pdf_content += "KEY METRICS\\n"
        if "kpis" in data:
            for key, value in data["kpis"].items():
                pdf_content += f"• {key}: {value}\\n"
        
        return pdf_content.encode()


# Singleton instance
admin_service = AdminService()

