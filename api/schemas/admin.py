"""
Admin API schemas - Pydantic models for request/response validation
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class ReportType(str, Enum):
    """Report type enumeration"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ExportFormat(str, Enum):
    """Export format enumeration"""
    CSV = "csv"
    JSON = "json"
    PDF = "pdf"


# ============================================================================
# Admin Overview & Statistics
# ============================================================================

class KPIMetrics(BaseModel):
    """KPI metrics response"""
    total_loans_compared: int = Field(..., description="Total loan comparisons")
    total_unique_users: int = Field(..., description="Unique users in period")
    conversions: int = Field(..., description="Number of selections made")
    conversion_rate: float = Field(..., description="Conversion rate as percentage")
    avg_emi: float = Field(..., description="Average EMI offered")
    avg_interest_rate: float = Field(..., description="Average interest rate")
    avg_approval_probability: float = Field(..., description="Average approval probability")
    total_cost_savings: float = Field(..., description="Total user cost savings")
    processed_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_loans_compared": 2450,
                "total_unique_users": 2100,
                "conversions": 847,
                "conversion_rate": 34.6,
                "avg_emi": 12500,
                "avg_interest_rate": 8.5,
                "avg_approval_probability": 0.85,
                "total_cost_savings": 15600000,
                "processed_at": "2024-03-26T10:30:00"
            }
        }


class ConversionFunnelData(BaseModel):
    """Conversion funnel metrics"""
    total_views: int
    total_comparisons: int
    total_selections: int
    view_to_compare: float
    compare_to_select: float
    overall_conversion: float
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_views": 3400,
                "total_comparisons": 2450,
                "total_selections": 847,
                "view_to_compare": 72.06,
                "compare_to_select": 34.6,
                "overall_conversion": 24.9
            }
        }


class AdminStatsOverviewResponse(BaseModel):
    """Admin dashboard overview response"""
    kpis: KPIMetrics
    funnel: ConversionFunnelData
    period_days: int = Field(default=30, description="Period covered by metrics")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_schema_extra = {
            "example": {
                "kpis": {
                    "total_loans_compared": 2450,
                    "conversions": 847,
                    "conversion_rate": 34.6,
                    "avg_emi": 12500,
                    "avg_interest_rate": 8.5,
                    "avg_approval_probability": 0.85,
                    "total_cost_savings": 15600000,
                    "processed_at": "2024-03-26T10:30:00",
                    "total_unique_users": 2100
                },
                "funnel": {
                    "total_views": 3400,
                    "total_comparisons": 2450,
                    "total_selections": 847,
                    "view_to_compare": 72.06,
                    "compare_to_select": 34.6,
                    "overall_conversion": 24.9
                },
                "period_days": 30,
                "timestamp": "2024-03-26T10:35:00"
            }
        }


# ============================================================================
# Lender Management
# ============================================================================

class LenderPerformanceData(BaseModel):
    """Lender performance metrics"""
    lender_id: str
    lender_name: str
    selections: int = Field(..., description="Number of times selected")
    selection_rate: float = Field(..., description="Selection rate as percentage")
    avg_emi_offered: float = Field(..., description="Average EMI offered by lender")
    avg_rate: float = Field(..., description="Average interest rate offered")
    avg_approval_prob: float = Field(..., description="Average approval probability")
    market_share: float = Field(..., description="Market share percentage")
    trend: str = Field(..., description="Trend direction: up, down, stable")
    
    class Config:
        json_schema_extra = {
            "example": {
                "lender_id": "bank_a",
                "lender_name": "Bank A",
                "selections": 645,
                "selection_rate": 26.3,
                "avg_emi_offered": 12100,
                "avg_rate": 8.2,
                "avg_approval_prob": 0.85,
                "market_share": 26.3,
                "trend": "up"
            }
        }


class LenderInfoRequest(BaseModel):
    """Request to create/update lender"""
    name: str = Field(..., min_length=1, description="Lender name")
    type: str = Field(..., description="Lender type (bank, nbfc, fintech, etc.)")
    min_loan_amount: float = Field(..., gt=0)
    max_loan_amount: float = Field(..., gt=0)
    min_tenure: int = Field(..., gt=0, description="In months")
    max_tenure: int = Field(..., gt=0, description="In months")
    interest_rate_min: float = Field(..., ge=0)
    interest_rate_max: float = Field(..., ge=0)
    processing_fee: float = Field(default=0.0, ge=0)
    approval_probability: float = Field(..., ge=0, le=1)
    is_active: bool = Field(default=True)
    
    class Config:
        json_schema_extra = {
            "example": {
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
                "is_active": True
            }
        }


class LenderInfoResponse(BaseModel):
    """Lender information response"""
    id: str = Field(..., description="Lender ID")
    name: str
    type: str
    min_loan_amount: float
    max_loan_amount: float
    min_tenure: int
    max_tenure: int
    interest_rate_min: float
    interest_rate_max: float
    processing_fee: float
    approval_probability: float
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
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
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-03-26T10:30:00"
            }
        }


class LendersListResponse(BaseModel):
    """List of lenders with performance data"""
    lenders: List[LenderPerformanceData]
    total_count: int
    active_count: int
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_schema_extra = {
            "example": {
                "lenders": [
                    {
                        "lender_id": "bank_a",
                        "lender_name": "Bank A",
                        "selections": 645,
                        "selection_rate": 26.3,
                        "avg_emi_offered": 12100,
                        "avg_rate": 8.2,
                        "avg_approval_prob": 0.85,
                        "market_share": 26.3,
                        "trend": "up"
                    }
                ],
                "total_count": 5,
                "active_count": 5,
                "timestamp": "2024-03-26T10:35:00"
            }
        }


# ============================================================================
# Analytics & Reporting
# ============================================================================

class TrendData(BaseModel):
    """Trend data for chart visualization"""
    dates: List[str]
    loans_compared: List[int]
    conversions: List[int]
    avg_emi: List[float]
    avg_rate: List[float]
    avg_approval: List[float]
    cost_savings: List[float]
    
    class Config:
        json_schema_extra = {
            "example": {
                "dates": ["2024-02-25", "2024-02-26", "2024-02-27"],
                "loans_compared": [42, 45, 48],
                "conversions": [14, 15, 16],
                "avg_emi": [12600, 12550, 12500],
                "avg_rate": [8.6, 8.55, 8.5],
                "avg_approval": [0.76, 0.77, 0.78],
                "cost_savings": [420000, 450000, 480000]
            }
        }


class AdminTrendsResponse(BaseModel):
    """Analytics trends response"""
    trends: TrendData
    period_days: int
    summary: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)


class ReportRequest(BaseModel):
    """Request to generate report"""
    report_type: ReportType = Field(..., description="Type of report")
    export_format: ExportFormat = Field(default=ExportFormat.JSON)
    email_to: Optional[str] = Field(default=None, description="Optional email to send report")
    
    class Config:
        json_schema_extra = {
            "example": {
                "report_type": "daily",
                "export_format": "pdf",
                "email_to": "admin@company.com"
            }
        }


class ReportResponse(BaseModel):
    """Report generation response"""
    report_id: str
    report_type: str
    period: str
    url: str = Field(..., description="URL to download report")
    created_at: datetime
    expires_at: datetime = Field(..., description="Report expiry time")
    
    class Config:
        json_schema_extra = {
            "example": {
                "report_id": "report_20240326_001",
                "report_type": "daily",
                "period": "2024-03-26",
                "url": "/admin/reports/report_20240326_001.pdf",
                "created_at": "2024-03-26T10:35:00",
                "expires_at": "2024-04-26T10:35:00"
            }
        }


# ============================================================================
# Performance Metrics
# ============================================================================

class EfficiencyScore(BaseModel):
    """Cost efficiency score for lender"""
    lender_id: str
    lender_name: str
    efficiency_score: float = Field(..., ge=0, le=100)
    emi_score: float = Field(..., ge=0, le=100)
    rate_score: float = Field(..., ge=0, le=100)
    approval_score: float = Field(..., ge=0, le=100)
    
    class Config:
        json_schema_extra = {
            "example": {
                "lender_id": "bank_a",
                "lender_name": "Bank A",
                "efficiency_score": 85.5,
                "emi_score": 87.0,
                "rate_score": 84.5,
                "approval_score": 85.0
            }
        }


class PerformanceMetricsResponse(BaseModel):
    """Performance metrics response"""
    period_days: int
    kpis: KPIMetrics
    lender_performance: List[LenderPerformanceData]
    efficiency_scores: List[EfficiencyScore]
    top_performers: List[str] = Field(..., description="Top 3 lender IDs by market share")
    timestamp: datetime = Field(default_factory=datetime.now)


# ============================================================================
# User Profile Statistics
# ============================================================================

class UserProfileStats(BaseModel):
    """Aggregated user profile statistics"""
    avg_loan_amount: float
    avg_tenure: int
    avg_salary: float
    avg_credit_score: int
    avg_obligations: float
    avg_age: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "avg_loan_amount": 425000,
                "avg_tenure": 60,
                "avg_salary": 45000,
                "avg_credit_score": 720,
                "avg_obligations": 8500,
                "avg_age": 32
            }
        }


class AdminHealthResponse(BaseModel):
    """Admin API health check response"""
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = "1.0.0"
    authenticated: bool = True
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2024-03-26T10:35:00",
                "version": "1.0.0",
                "authenticated": True
            }
        }

