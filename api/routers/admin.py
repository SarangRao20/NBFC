"""
Admin API Router - REST endpoints for admin operations
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from api.services.admin_service import admin_service
from api.schemas.admin import (
    AdminStatsOverviewResponse,
    LendersListResponse,
    LenderInfoRequest,
    LenderInfoResponse,
    ReportRequest,
    ReportResponse,
    PerformanceMetricsResponse,
    AdminTrendsResponse,
    AdminHealthResponse,
)

router = APIRouter(prefix="/admin", tags=["admin"])


# ============================================================================
# Health & Status
# ============================================================================

@router.get(
    "/health",
    response_model=AdminHealthResponse,
    summary="Admin API Health Check",
    description="Check admin API status and authentication",
)
async def health_check():
    """
    Health check endpoint for admin API.
    
    Returns:
        AdminHealthResponse: Status and timestamp
    """
    return AdminHealthResponse()


# ============================================================================
# Statistics & Overview
# ============================================================================

@router.get(
    "/stats/overview",
    response_model=AdminStatsOverviewResponse,
    summary="Dashboard Overview Stats",
    description="Get KPIs and funnel metrics for admin dashboard",
)
async def get_stats_overview(days: int = Query(default=30, ge=1, le=365)):
    """
    Get admin dashboard overview with key metrics.
    
    Args:
        days: Number of days to include in metrics (1-365)
    
    Returns:
        AdminStatsOverviewResponse: KPIs and conversion funnel data
    
    Example:
        GET /admin/stats/overview?days=30
    """
    return admin_service.get_stats_overview(days=days)


@router.get(
    "/stats/loans",
    summary="Loan Comparison Analytics",
    description="Get detailed analytics for loan comparisons",
)
async def get_loan_analytics(days: int = Query(default=30, ge=1, le=365)):
    """
    Get loan comparison analytics with trends and user profiles.
    
    Args:
        days: Number of days to include in analysis
    
    Returns:
        Dict with trends and user statistics
    """
    return admin_service.get_loan_analytics(days=days)


@router.get(
    "/stats/conversion",
    summary="Conversion Funnel Metrics",
    description="Get detailed conversion funnel breakdown",
)
async def get_conversion_funnel():
    """
    Get detailed conversion funnel metrics.
    
    Returns:
        Dict with funnel stages and conversion rates
    """
    return admin_service.get_conversion_funnel()


# ============================================================================
# Lender Management
# ============================================================================

@router.get(
    "/lenders",
    response_model=LendersListResponse,
    summary="List All Lenders",
    description="Get list of all lenders with performance data",
)
async def list_lenders():
    """
    Get list of all lenders with current performance metrics.
    
    Returns:
        LendersListResponse: List of lenders with selection rates and trends
    
    Example:
        GET /admin/lenders
    """
    return admin_service.list_lenders()


@router.get(
    "/lenders/{lender_id}",
    response_model=LenderInfoResponse,
    summary="Get Lender Details",
    description="Get detailed information for a specific lender",
)
async def get_lender(lender_id: str):
    """
    Get detailed information for a specific lender.
    
    Args:
        lender_id: ID of the lender
    
    Returns:
        LenderInfoResponse: Lender details
    
    Raises:
        HTTPException: 404 if lender not found
    """
    lender = admin_service.get_lender(lender_id)
    if not lender:
        raise HTTPException(status_code=404, detail="Lender not found")
    return lender


@router.post(
    "/lenders",
    response_model=LenderInfoResponse,
    status_code=201,
    summary="Create New Lender",
    description="Add a new lender to the marketplace",
)
async def create_lender(request: LenderInfoRequest):
    """
    Create a new lender in the system.
    
    Args:
        request: Lender details
    
    Returns:
        LenderInfoResponse: Created lender with ID
    
    Example:
        POST /admin/lenders
        {
            "name": "New Bank",
            "type": "bank",
            "min_loan_amount": 100000,
            "max_loan_amount": 5000000,
            "min_tenure": 6,
            "max_tenure": 84,
            "interest_rate_min": 7.5,
            "interest_rate_max": 12.5,
            "approval_probability": 0.85
        }
    """
    return admin_service.create_lender(request)


@router.put(
    "/lenders/{lender_id}",
    response_model=LenderInfoResponse,
    summary="Update Lender",
    description="Update lender details",
)
async def update_lender(lender_id: str, request: LenderInfoRequest):
    """
    Update an existing lender's details.
    
    Args:
        lender_id: ID of lender to update
        request: Updated lender details
    
    Returns:
        LenderInfoResponse: Updated lender
    
    Raises:
        HTTPException: 404 if lender not found
    """
    lender = admin_service.update_lender(lender_id, request)
    if not lender:
        raise HTTPException(status_code=404, detail="Lender not found")
    return lender


@router.delete(
    "/lenders/{lender_id}",
    status_code=204,
    summary="Deactivate Lender",
    description="Deactivate a lender (soft delete)",
)
async def delete_lender(lender_id: str):
    """
    Deactivate a lender (marks as inactive, doesn't delete).
    
    Args:
        lender_id: ID of lender to deactivate
    
    Raises:
        HTTPException: 404 if lender not found
    """
    if not admin_service.delete_lender(lender_id):
        raise HTTPException(status_code=404, detail="Lender not found")
    return None


# ============================================================================
# Performance & Metrics
# ============================================================================

@router.get(
    "/performance",
    response_model=PerformanceMetricsResponse,
    summary="Performance Metrics",
    description="Get comprehensive performance metrics and efficiency scores",
)
async def get_performance(days: int = Query(default=30, ge=1, le=365)):
    """
    Get comprehensive performance metrics including efficiency scores.
    
    Args:
        days: Number of days to include in analysis
    
    Returns:
        PerformanceMetricsResponse: Performance data and efficiency rankings
    """
    return admin_service.get_performance_metrics(days=days)


@router.get(
    "/trends",
    response_model=AdminTrendsResponse,
    summary="Historical Trends",
    description="Get historical trend data for metrics",
)
async def get_trends(days: int = Query(default=30, ge=1, le=365)):
    """
    Get historical trends for loan comparisons and metrics.
    
    Args:
        days: Number of days to include in trends (1-365)
    
    Returns:
        AdminTrendsResponse: Trend data and summary statistics
    
    Example:
        GET /admin/trends?days=30
    """
    return admin_service.get_trends(days=days)


# ============================================================================
# Reporting & Export
# ============================================================================

@router.post(
    "/reports/generate",
    response_model=ReportResponse,
    status_code=201,
    summary="Generate Report",
    description="Generate a report in specified format",
)
async def generate_report(request: ReportRequest):
    """
    Generate a report (daily, weekly, or monthly).
    
    Args:
        request: Report generation request with type and format
    
    Returns:
        ReportResponse: Report metadata with download URL
    
    Example:
        POST /admin/reports/generate
        {
            "report_type": "daily",
            "export_format": "pdf",
            "email_to": "admin@company.com"
        }
    """
    return admin_service.generate_report(request)


@router.get(
    "/reports/{report_id}",
    summary="Get Report",
    description="Retrieve generated report details",
)
async def get_report(report_id: str):
    """
    Get details of a generated report.
    
    Args:
        report_id: ID of the report
    
    Returns:
        Dict with report details
    
    Raises:
        HTTPException: 404 if report not found
    """
    report = admin_service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get(
    "/reports/{report_id}/download",
    summary="Download Report",
    description="Download report in specified format",
)
async def download_report(
    report_id: str,
    format: str = Query(default="json", pattern="^(json|csv|pdf)$")
):
    """
    Download a generated report in specified format.
    
    Args:
        report_id: ID of the report
        format: Export format (json, csv, pdf)
    
    Returns:
        File download
    
    Raises:
        HTTPException: 404 if report not found
    """
    content = admin_service.export_report(report_id, format)
    if not content:
        raise HTTPException(status_code=404, detail="Report not found")
    
    media_types = {
        "json": "application/json",
        "csv": "text/csv",
        "pdf": "application/pdf",
    }
    
    return {
        "status": "success",
        "report_id": report_id,
        "format": format,
        "size_bytes": len(content),
        "download_url": f"/admin/reports/{report_id}/file.{format}",
    }


# ============================================================================
# System Info & Configuration
# ============================================================================

@router.get(
    "/system/info",
    summary="System Information",
    description="Get admin system information",
)
async def get_system_info():
    """
    Get system and marketplace information.
    
    Returns:
        Dict with system details
    """
    return {
        "status": "operational",
        "version": "1.0.0",
        "marketplace_version": "3+phases",
        "features": [
            "analytics",
            "lender_management",
            "reporting",
            "performance_tracking",
        ],
        "total_lenders": len(admin_service.mock_lenders),
        "active_lenders": sum(1 for l in admin_service.mock_lenders.values() if l["is_active"]),
        "timestamp": __import__("datetime").datetime.now().isoformat(),
    }

