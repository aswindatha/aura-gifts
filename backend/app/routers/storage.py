import uuid
import os
import shutil
from datetime import datetime, timedelta
from typing import Optional
import boto3
from botocore.config import Config
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import User, MediaFile
from app.auth import get_current_user
from app.schemas import StandardResponse

router = APIRouter(prefix="/api/storage", tags=["Storage"])

ALLOWED_CATEGORIES = {"products", "tasks", "print-orders", "book-prints", "receipts", "users", "banners"}

# Validation Rules
SIZE_LIMITS = {
    "receipts": 10 * 1024 * 1024,      # 10 MB
    "tasks": 20 * 1024 * 1024,         # 20 MB
    "products": 100 * 1024 * 1024,     # 100 MB
    "print-orders": 500 * 1024 * 1024, # 500 MB
    "book-prints": 500 * 1024 * 1024,  # 500 MB
    "users": 10 * 1024 * 1024,         # 10 MB
    "banners": 20 * 1024 * 1024,       # 20 MB
}

ALLOWED_MIMES = {
    "receipts": {"image/png", "image/jpeg", "image/jpg"},
    "tasks": {"image/png", "image/jpeg", "image/jpg", "image/webp"},
    "products": {"image/png", "image/jpeg", "image/jpg", "image/webp", "video/mp4", "video/webm"},
    "print-orders": {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/tiff", "application/pdf"},
    "book-prints": {"image/png", "image/jpeg", "image/jpg", "image/webp", "application/pdf"},
    "users": {"image/png", "image/jpeg", "image/jpg", "image/webp"},
    "banners": {"image/png", "image/jpeg", "image/jpg", "image/webp"},
}

def validate_upload(category: str, content_type: str, size: Optional[int] = None):
    # 1. File Size Limits Check
    if size is not None:
        limit = SIZE_LIMITS.get(category)
        if limit and size > limit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds the limit of {limit // (1024 * 1024)} MB for category '{category}'."
            )
            
    # 2. Dangerous Upload File Type Blocking
    allowed = ALLOWED_MIMES.get(category)
    if allowed and content_type.lower() not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"MIME type '{content_type}' is not allowed for category '{category}'. Allowed: {list(allowed)}"
        )

# Check if using local dev mock mode
# Always use R2 when credentials are configured, regardless of PRODUCTION flag
def check_is_mock() -> bool:
    return (
        not settings.R2_ACCESS_KEY_ID or 
        not settings.R2_SECRET_ACCESS_KEY or
        not settings.R2_ACCOUNT_ID or
        settings.R2_ACCESS_KEY_ID == "your_r2_access_key_id" or
        "your_r2" in settings.R2_ACCESS_KEY_ID
    )

# Schema for requesting presigned URL
class PresignedUrlRequest(BaseModel):
    file_name: str
    content_type: str
    category: str = Field(..., description="Allowed: 'products', 'tasks', 'print-orders', 'book-prints', 'receipts'")
    size: Optional[int] = None

# Schema for the response
class PresignedUrlResponse(BaseModel):
    upload_url: str
    public_url: str
    key: str

@router.post("/presign", response_model=PresignedUrlResponse)
async def generate_presigned_url(
    payload: PresignedUrlRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate an upload ticket (presigned PUT URL for R2 or local mock fallback).
    Routes file uploads into specific folders and stores metadata in Postgres.
    """
    # Validate category prefix folder
    if payload.category not in ALLOWED_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file category. Must be one of: {list(ALLOWED_CATEGORIES)}"
        )

    # Perform validation on file size and MIME type
    validate_upload(payload.category, payload.content_type, payload.size)

    # Generate the unique S3 folder key
    unique_key = f"{payload.category}/{uuid.uuid4()}-{payload.file_name}"
    
    # Calculate retention period (delete_after)
    delete_after_dt = None
    if payload.category in ("tasks", "print-orders", "book-prints"):
        delete_after_dt = datetime.utcnow() + timedelta(days=30)
        
    is_public = (payload.category in ("products", "users", "banners"))

    # Local Developer Mock Fallback Mode
    if check_is_mock():
        base_url = str(request.base_url).rstrip("/")
        upload_url = f"{base_url}/api/storage/local-upload-mock?key={unique_key}"
        public_url = f"{base_url}/static/uploads/{unique_key}"
        
        # Persist upload metadata in PostgreSQL
        media_file = MediaFile(
            object_key=unique_key,
            mime_type=payload.content_type,
            size=payload.size,
            is_public=is_public,
            category=payload.category,
            delete_after=delete_after_dt
        )
        db.add(media_file)
        await db.commit()
        
        return PresignedUrlResponse(
            upload_url=upload_url,
            public_url=public_url,
            key=unique_key
        )

    # Production R2 Mode
    r2_endpoint = f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
    
    try:
        # 1. Initialize boto3 client
        s3_client = boto3.client(
            "s3",
            endpoint_url=r2_endpoint,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name="auto",
            config=Config(signature_version="s3v4"),
        )
        
        # 2. Generate presigned PUT URL
        upload_url = s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": settings.R2_BUCKET_NAME,
                "Key": unique_key,
                "ContentType": payload.content_type,
            },
            ExpiresIn=3600,
        )
        
        # 3. Calculate public asset URL
        if is_public and settings.R2_PUBLIC_CUSTOM_DOMAIN:
            domain = settings.R2_PUBLIC_CUSTOM_DOMAIN.rstrip("/")
            public_url = f"{domain}/{unique_key}"
        else:
            public_url = f"{r2_endpoint}/{settings.R2_BUCKET_NAME}/{unique_key}"
            
        # 4. Persist upload metadata in PostgreSQL
        media_file = MediaFile(
            object_key=unique_key,
            mime_type=payload.content_type,
            size=payload.size,
            is_public=is_public,
            category=payload.category,
            delete_after=delete_after_dt
        )
        db.add(media_file)
        await db.commit()
        
        return PresignedUrlResponse(
            upload_url=upload_url,
            public_url=public_url,
            key=unique_key
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate upload ticket: {str(e)}"
        )


# Local Developer Upload Mock Endpoint (Handles simulated PUT requests)
@router.put("/local-upload-mock")
async def local_upload_mock(
    request: Request,
    key: str
):
    """
    Simulates writing direct PUT payload uploads to local disk when R2 is not configured.
    """
    file_bytes = await request.body()
    local_path = os.path.join("uploads", key)
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    
    with open(local_path, "wb") as f:
        f.write(file_bytes)
        
    return {"message": "Direct upload simulated locally successfully."}


# Local Developer Multipart Chunk Upload Mock Endpoint
@router.put("/local-multipart-upload-mock")
async def local_multipart_upload_mock(
    request: Request,
    key: str,
    part: int,
    upload_id: str
):
    """
    Simulates writing a multipart chunk segment to local disk.
    """
    file_bytes = await request.body()
    temp_dir = os.path.join("uploads", "temp_chunks", upload_id)
    os.makedirs(temp_dir, exist_ok=True)
    
    chunk_path = os.path.join(temp_dir, f"part-{part}")
    with open(chunk_path, "wb") as f:
        f.write(file_bytes)
        
    return {"message": f"Part {part} uploaded successfully."}


# Multipart Upload Handlers for Large Files (> 100 MB)
class MultipartInitiateRequest(BaseModel):
    file_name: str
    content_type: str
    category: str
    size: int

class MultipartInitiateResponse(BaseModel):
    upload_id: str
    key: str
    chunk_size: int
    total_parts: int

@router.post("/multipart/initiate", response_model=MultipartInitiateResponse)
async def initiate_multipart_upload(
    payload: MultipartInitiateRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Initiates a multipart upload session.
    """
    if payload.category not in ALLOWED_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file category. Must be one of: {list(ALLOWED_CATEGORIES)}"
        )

    # Perform validation rules
    validate_upload(payload.category, payload.content_type, payload.size)

    # Construct object key
    unique_key = f"{payload.category}/{uuid.uuid4()}-{payload.file_name}"
    
    # Calculate parts (default 20MB parts)
    chunk_size = 20 * 1024 * 1024
    total_parts = (payload.size + chunk_size - 1) // chunk_size

    # Local Mock Mode
    if check_is_mock():
        upload_id = f"mock-upload-{uuid.uuid4()}"
        return MultipartInitiateResponse(
            upload_id=upload_id,
            key=unique_key,
            chunk_size=chunk_size,
            total_parts=total_parts
        )

    # R2 Mode
    if not settings.R2_ACCESS_KEY_ID or not settings.R2_SECRET_ACCESS_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cloudflare R2 storage is not configured."
        )

    r2_endpoint = f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
    try:
        s3_client = boto3.client(
            "s3",
            endpoint_url=r2_endpoint,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name="auto",
        )
        
        response = s3_client.create_multipart_upload(
            Bucket=settings.R2_BUCKET_NAME,
            Key=unique_key,
            ContentType=payload.content_type
        )

        return MultipartInitiateResponse(
            upload_id=response["UploadId"],
            key=unique_key,
            chunk_size=chunk_size,
            total_parts=total_parts
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate multipart session: {str(e)}"
        )


class PresignPartsRequest(BaseModel):
    key: str
    upload_id: str
    part_numbers: list[int]

class PresignedPart(BaseModel):
    part_number: int
    upload_url: str

class PresignPartsResponse(BaseModel):
    parts: list[PresignedPart]

@router.post("/multipart/presign-parts", response_model=PresignPartsResponse)
async def presign_multipart_parts(
    payload: PresignPartsRequest,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Generates presigned upload part URLs for specified chunk indexes.
    """
    # Local Mock Mode
    if payload.upload_id.startswith("mock-upload-"):
        base_url = str(request.base_url).rstrip("/")
        parts_list = []
        for part_num in payload.part_numbers:
            url = f"{base_url}/api/storage/local-multipart-upload-mock?key={payload.key}&part={part_num}&upload_id={payload.upload_id}"
            parts_list.append(PresignedPart(part_number=part_num, upload_url=url))
        return PresignPartsResponse(parts=parts_list)

    # R2 Mode
    if not settings.R2_ACCESS_KEY_ID or not settings.R2_SECRET_ACCESS_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cloudflare R2 storage is not configured."
        )

    r2_endpoint = f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
    try:
        s3_client = boto3.client(
            "s3",
            endpoint_url=r2_endpoint,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name="auto",
            config=Config(signature_version="s3v4")
        )
        
        parts_list = []
        for part_num in payload.part_numbers:
            url = s3_client.generate_presigned_url(
                ClientMethod="upload_part",
                Params={
                    "Bucket": settings.R2_BUCKET_NAME,
                    "Key": payload.key,
                    "UploadId": payload.upload_id,
                    "PartNumber": part_num
                },
                ExpiresIn=3600
            )
            parts_list.append(PresignedPart(part_number=part_num, upload_url=url))
            
        return PresignPartsResponse(parts=parts_list)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate part presigned URLs: {str(e)}"
        )


class CompletedPart(BaseModel):
    part_number: int = Field(..., alias="partNumber")
    etag: str

    class Config:
        populate_by_name = True

class MultipartCompleteRequest(BaseModel):
    key: str
    upload_id: str
    parts: list[CompletedPart]
    category: str
    file_name: str
    content_type: str
    size: int

class MultipartCompleteResponse(BaseModel):
    public_url: str
    key: str

@router.post("/multipart/complete", response_model=MultipartCompleteResponse)
async def complete_multipart_upload(
    payload: MultipartCompleteRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Completes the multipart upload session and commits file metadata to PostgreSQL.
    """
    is_public = (payload.category in ("products", "users", "banners"))
    delete_after_dt = None
    if payload.category in ("tasks", "print-orders", "book-prints"):
        delete_after_dt = datetime.utcnow() + timedelta(days=30)

    # Local Mock Mode
    if payload.upload_id.startswith("mock-upload-"):
        # Combine temporary parts into one file
        temp_dir = os.path.join("uploads", "temp_chunks", payload.upload_id)
        local_path = os.path.join("uploads", payload.key)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        try:
            with open(local_path, "wb") as final_file:
                for part in sorted(payload.parts, key=lambda x: x.part_number):
                    part_file = os.path.join(temp_dir, f"part-{part.part_number}")
                    if os.path.exists(part_file):
                        with open(part_file, "rb") as pf:
                            final_file.write(pf.read())
            
            # Clean up temp folder
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

            base_url = str(request.base_url).rstrip("/")
            public_url = f"{base_url}/static/uploads/{payload.key}"
            
            # Register in database
            media_file = MediaFile(
                object_key=payload.key,
                mime_type=payload.content_type,
                size=payload.size,
                is_public=is_public,
                category=payload.category,
                delete_after=delete_after_dt
            )
            db.add(media_file)
            await db.commit()

            return MultipartCompleteResponse(public_url=public_url, key=payload.key)
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to assemble local mock chunks: {str(e)}"
            )

    # R2 Mode
    if not settings.R2_ACCESS_KEY_ID or not settings.R2_SECRET_ACCESS_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cloudflare R2 storage is not configured."
        )

    r2_endpoint = f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
    try:
        s3_client = boto3.client(
            "s3",
            endpoint_url=r2_endpoint,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name="auto",
        )
        
        # Sort and construct parts format required by S3 API
        formatted_parts = [
            {"PartNumber": p.part_number, "ETag": p.etag}
            for p in sorted(payload.parts, key=lambda x: x.part_number)
        ]
        
        s3_client.complete_multipart_upload(
            Bucket=settings.R2_BUCKET_NAME,
            Key=payload.key,
            UploadId=payload.upload_id,
            MultipartUpload={"Parts": formatted_parts}
        )

        if is_public and settings.R2_PUBLIC_CUSTOM_DOMAIN:
            domain = settings.R2_PUBLIC_CUSTOM_DOMAIN.rstrip("/")
            public_url = f"{domain}/{payload.key}"
        else:
            public_url = f"{r2_endpoint}/{settings.R2_BUCKET_NAME}/{payload.key}"

        media_file = MediaFile(
            object_key=payload.key,
            mime_type=payload.content_type,
            size=payload.size,
            is_public=is_public,
            category=payload.category,
            delete_after=delete_after_dt
        )
        db.add(media_file)
        await db.commit()
        
        return MultipartCompleteResponse(public_url=public_url, key=payload.key)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete multipart upload: {str(e)}"
        )


class MultipartAbortRequest(BaseModel):
    key: str
    upload_id: str

@router.post("/multipart/abort", response_model=StandardResponse)
async def abort_multipart_upload(
    payload: MultipartAbortRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Aborts a multipart upload session to free up buffered resources.
    """
    # Local Mock Mode
    if payload.upload_id.startswith("mock-upload-"):
        temp_dir = os.path.join("uploads", "temp_chunks", payload.upload_id)
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        return StandardResponse(success=True, message="Local mock multipart upload session aborted.")

    # R2 Mode
    if not settings.R2_ACCESS_KEY_ID or not settings.R2_SECRET_ACCESS_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cloudflare R2 storage is not configured."
        )

    r2_endpoint = f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
    try:
        s3_client = boto3.client(
            "s3",
            endpoint_url=r2_endpoint,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name="auto",
        )
        
        s3_client.abort_multipart_upload(
            Bucket=settings.R2_BUCKET_NAME,
            Key=payload.key,
            UploadId=payload.upload_id
        )
        
        return StandardResponse(success=True, message="Multipart upload session aborted successfully.")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to abort multipart upload: {str(e)}"
        )


# Daily Cron Cleanup Route
@router.post("/cron/cleanup", response_model=StandardResponse)
async def cleanup_expired_files(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Daily cron cleanup job.
    Deletes expired media records from Cloudflare R2 (or local disk in mock mode) and PostgreSQL.
    """
    # Validate authorization token header
    expected_token = f"Bearer {settings.CRON_SECRET_KEY}"
    if not authorization or authorization != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized. Invalid cron authorization token."
        )

    # Fetch expired records
    now = datetime.utcnow()
    query = select(MediaFile).where(MediaFile.delete_after < now)
    res = await db.execute(query)
    expired_files = res.scalars().all()
    
    if not expired_files:
        return StandardResponse(success=True, message="No expired files found for cleanup.")

    is_mock = check_is_mock()

    if not is_mock and (not settings.R2_ACCESS_KEY_ID or not settings.R2_SECRET_ACCESS_KEY):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cloudflare R2 credentials are not configured on the backend."
        )

    s3_client = None
    if not is_mock:
        r2_endpoint = f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
        s3_client = boto3.client(
            "s3",
            endpoint_url=r2_endpoint,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name="auto",
        )

    deleted_count = 0
    errors = []

    for file_record in expired_files:
        try:
            if is_mock:
                local_path = os.path.join("uploads", file_record.object_key)
                if os.path.exists(local_path):
                    os.remove(local_path)
            else:
                if s3_client is not None:
                    s3_client.delete_object(
                        Bucket=settings.R2_BUCKET_NAME,
                        Key=file_record.object_key
                    )
            await db.delete(file_record)
            deleted_count += 1
        except Exception as e:
            errors.append(f"Failed to delete {file_record.object_key}: {str(e)}")

    if deleted_count > 0:
        await db.commit()

    message = f"Cleaned up {deleted_count} expired files."
    if errors:
        message += f" Failures: {len(errors)}."

    return StandardResponse(success=True, message=message)

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Uploads a file to the local storage space (same as NAS storage upload)"""
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate unique filename to avoid collision
    filename = file.filename or "file"
    file_ext = os.path.splitext(filename)[1]
    unique_filename = f"{uuid.uuid4().hex}{file_ext}"
    file_path = os.path.join(upload_dir, unique_filename)
    
    # Save the file locally
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {e}")
        
    return {
        "filename": file.filename,
        "unique_filename": unique_filename,
        "url": f"/uploads/{unique_filename}"
    }
