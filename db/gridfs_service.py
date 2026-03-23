"""MongoDB GridFS Service — Store and retrieve files directly from MongoDB."""

import io
from datetime import datetime
from gridfs import GridFS
from pymongo.database import Database

# Global GridFS instance
_gridfs_instance = None


def init_gridfs_sync(database: Database):
    """Initialize GridFS with the given PyMongo database."""
    global _gridfs_instance
    _gridfs_instance = GridFS(database)
    print("✅ GridFS initialized")
    return _gridfs_instance


def get_gridfs() -> GridFS:
    """Get the GridFS instance."""
    if _gridfs_instance is None:
        raise RuntimeError("GridFS not initialized. Call init_gridfs_sync() first.")
    return _gridfs_instance


def upload_file_to_gridfs(
    file_content: bytes,
    file_name: str,
    session_id: str,
    file_type: str = "document",
    metadata: dict = None
) -> str:
    """
    Upload a file to MongoDB GridFS.
    
    Args:
        file_content: Raw file bytes
        file_name: Original filename
        session_id: Session ID for tracking
        file_type: Type of file (document, kyc_doc, etc.)
        metadata: Additional metadata to store
    
    Returns:
        file_id: MongoDB GridFS file ID (ObjectId as string)
    """
    try:
        gridfs = get_gridfs()
        
        # Prepare metadata
        file_metadata = {
            "session_id": session_id,
            "file_type": file_type,
            "uploaded_at": datetime.utcnow().isoformat(),
            "file_size": len(file_content),
            "original_filename": file_name,
        }
        
        if metadata:
            file_metadata.update(metadata)
        
        # Upload to GridFS (synchronous)
        file_id = gridfs.put(
            file_content,
            filename=file_name,
            metadata=file_metadata
        )
        
        print(f"📤 File uploaded to GridFS: {file_name} (ID: {file_id})")
        return str(file_id)
    
    except Exception as e:
        print(f"❌ Failed to upload file to GridFS: {e}")
        raise


def download_file_from_gridfs(file_id: str) -> tuple[bytes, dict]:
    """
    Download a file from MongoDB GridFS.
    
    Args:
        file_id: MongoDB GridFS file ID
    
    Returns:
        (file_content, file_info) tuple
    """
    try:
        from bson import ObjectId
        
        gridfs = get_gridfs()
        
        # Convert string ID back to ObjectId if needed
        try:
            oid = ObjectId(file_id)
        except:
            oid = file_id
        
        # Retrieve file (synchronous)
        grid_out = gridfs.get(oid)
        file_content = grid_out.read()
        
        file_info = {
            "filename": grid_out.filename,
            "contentType": grid_out.content_type,
            "uploadDate": grid_out.upload_date.isoformat(),
            "metadata": grid_out.metadata or {}
        }
        
        print(f"📥 File downloaded from GridFS: {grid_out.filename}")
        return file_content, file_info
    
    except Exception as e:
        print(f"❌ Failed to download file from GridFS: {e}")
        raise


def delete_file_from_gridfs(file_id: str) -> bool:
    """
    Delete a file from MongoDB GridFS.
    
    Args:
        file_id: MongoDB GridFS file ID
    
    Returns:
        True if successful, False otherwise
    """
    try:
        from bson import ObjectId
        
        gridfs = get_gridfs()
        
        # Convert string ID back to ObjectId if needed
        try:
            oid = ObjectId(file_id)
        except:
            oid = file_id
        
        gridfs.delete(oid)
        print(f"🗑️ File deleted from GridFS: {file_id}")
        return True
    
    except Exception as e:
        print(f"❌ Failed to delete file from GridFS: {e}")
        return False


def list_session_files(session_id: str, file_type: str = None) -> list:
    """
    List all files for a session.
    
    Args:
        session_id: Session ID to filter by
        file_type: Optional file type filter (document, kyc_doc, etc.)
    
    Returns:
        List of file info dicts
    """
    try:
        gridfs = get_gridfs()
        
        # Query GridFS for files matching session
        query = {"metadata.session_id": session_id}
        if file_type:
            query["metadata.file_type"] = file_type
        
        files = []
        for grid_out in gridfs.find(query):
            files.append({
                "id": str(grid_out._id),
                "filename": grid_out.filename,
                "uploadDate": grid_out.upload_date.isoformat(),
                "metadata": grid_out.metadata or {}
            })
        
        print(f"📋 Found {len(files)} files for session {session_id}")
        return files
    
    except Exception as e:
        print(f"❌ Failed to list session files: {e}")
        return []


def get_file_stream(file_id: str) -> io.BytesIO:
    """
    Get file as BytesIO stream (useful for streaming responses).
    
    Args:
        file_id: MongoDB GridFS file ID
    
    Returns:
        BytesIO stream of file content
    """
    try:
        file_content, _ = download_file_from_gridfs(file_id)
        return io.BytesIO(file_content)
    except Exception as e:
        print(f"❌ Failed to get file stream: {e}")
        raise
