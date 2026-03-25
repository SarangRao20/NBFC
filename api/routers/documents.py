"""Documents Router — Steps 5, 6, 7, 8 (Verification Loop)."""

import os
import shutil
import tempfile
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from api.schemas.documents import (
    RequestDocumentsResponse, OCRExtractionResponse,
    TamperCheckResponse, VerifyIncomeResponse,
)
from api.services import document_service
from api.core.exceptions import SessionNotFoundError

router = APIRouter(prefix="/session", tags=["Document Verification"])


@router.post("/{session_id}/request-documents", response_model=RequestDocumentsResponse,
             summary="Step 5: Request Documents")
async def request_documents(session_id: str):
    """List the documents required for this loan application based on
    the loan type and amount relative to the pre-approved limit.
    """
    result = await document_service.request_documents(session_id)
    if result is None:
        raise SessionNotFoundError(session_id)
    return result


@router.post("/{session_id}/extract-ocr", response_model=OCRExtractionResponse,
             summary="Step 6: Extract Data via OCR")
async def extract_ocr(session_id: str, file: UploadFile = File(...)):
    """Upload a document and extract data via OCR.
    Supports: JPG, PNG, PDF.
    Extracts: name, salary, employer, document type, confidence score.
    """
    # Save uploaded file temporarily
    suffix = os.path.splitext(file.filename)[1] or ".jpg"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir="data/uploads")
    try:
        shutil.copyfileobj(file.file, tmp)
        tmp.close()
        result = await document_service.extract_ocr(session_id, tmp.name, file.filename)
        return result
    finally:
        file.file.close()


@router.post("/{session_id}/extract-ocr-batch", summary="Step 6 (Batch): Extract Data via OCR from multiple files")
async def extract_ocr_batch(session_id: str, files: list[UploadFile] = File(...)):
    """Upload multiple documents at once and extract data via OCR.
    Only call when ALL required documents have been selected for better UX.
    """
    tmp_files = []
    try:
        for file in files:
            suffix = os.path.splitext(file.filename)[1] or ".jpg"
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir="data/uploads")
            shutil.copyfileobj(file.file, tmp)
            tmp.close()
            tmp_files.append({"path": tmp.name, "name": file.filename})
            file.file.close()

        result = await document_service.extract_ocr_batch(session_id, tmp_files)
        if result is None:
            raise SessionNotFoundError(session_id)
        return result
    finally:
        pass # tmp files handled by agent / saved audit copies


@router.post("/{session_id}/check-tampering", response_model=TamperCheckResponse,
             summary="Step 7: Check Document Tampering")
async def check_tampering(session_id: str):
    """Analyze the previously uploaded document for signs of tampering.
    Returns risk assessment based on OCR confidence and tamper flags.
    """
    result = await document_service.check_tampering(session_id)
    if result is None:
        raise SessionNotFoundError(session_id)
    return result


@router.post("/{session_id}/verify-income", response_model=VerifyIncomeResponse,
             summary="Step 8: State Update — Income Verified")
async def verify_income(session_id: str):
    """Cross-check extracted salary from document against the claimed salary.
    Marks income as verified. Flags significant variance (>20%).
    """
    result = await document_service.verify_income(session_id)
    if result is None:
        raise SessionNotFoundError(session_id)
    return result


@router.get("/{session_id}/download-document/{gridfs_file_id}",
            summary="Download Document from MongoDB GridFS")
async def download_document(session_id: str, gridfs_file_id: str):
    """Download a document that was stored in MongoDB GridFS.
    
    Args:
        session_id: Session ID
        gridfs_file_id: MongoDB GridFS file ID (from OCR extraction response)
    
    Returns:
        File stream with appropriate content-type
    """
    try:
        from db.gridfs_service import download_file_from_gridfs
        
        # Download file from GridFS
        file_content, file_info = await download_file_from_gridfs(gridfs_file_id)
        
        if not file_content:
            raise HTTPException(status_code=404, detail="File not found in GridFS")
        
        filename = file_info.get("filename", "document")
        content_type = file_info.get("contentType", "application/octet-stream")
        
        # Return as streaming response
        async def generate():
            yield file_content
        
        return StreamingResponse(
            generate(),
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    except Exception as e:
        print(f"❌ Failed to download document: {e}")
        raise HTTPException(status_code=500, detail=str(e))
