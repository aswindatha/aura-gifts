import urllib.parse
from typing import Optional
import boto3
from botocore.config import Config
from app.config import settings

def sign_r2_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return url
    
    # Check if this is an R2 URL (either endpoint or custom domain)
    is_r2 = False
    object_key = None
    
    try:
        parsed = urllib.parse.urlparse(url)
        # Check if hostname contains 'r2.cloudflarestorage.com' or matches the custom domain
        if "r2.cloudflarestorage.com" in parsed.netloc:
            is_r2 = True
            # Path format is: /<bucket-name>/<key>
            path_parts = parsed.path.lstrip("/").split("/")
            if len(path_parts) > 1:
                # The first part is the bucket name, the rest is the key
                object_key = "/".join(path_parts[1:])
        elif settings.R2_PUBLIC_CUSTOM_DOMAIN and parsed.netloc == urllib.parse.urlparse(settings.R2_PUBLIC_CUSTOM_DOMAIN).netloc:
            is_r2 = True
            object_key = parsed.path.lstrip("/")
    except Exception:
        pass
        
    if not is_r2 or not object_key:
        return url
        
    # Check if the key belongs to a public category. If so, return custom domain URL directly (no signature needed)
    category = object_key.split("/")[0] if "/" in object_key else ""
    if category in ("products", "users", "banners"):
        if settings.R2_PUBLIC_CUSTOM_DOMAIN:
            domain = settings.R2_PUBLIC_CUSTOM_DOMAIN.rstrip("/")
            return f"{domain}/{object_key}"
        return url

    # Generate presigned download GET URL if R2 credentials are configured
    if not settings.R2_ACCESS_KEY_ID or not settings.R2_SECRET_ACCESS_KEY or not settings.R2_ACCOUNT_ID:
        return url

    try:
        r2_endpoint = f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
        s3_client = boto3.client(
            "s3",
            endpoint_url=r2_endpoint,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name="auto",
            config=Config(signature_version="s3v4"),
        )
        download_url = s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": settings.R2_BUCKET_NAME,
                "Key": object_key,
            },
            ExpiresIn=3600,
        )
        return download_url
    except Exception as e:
        # Fallback to returning original URL if signing fails
        print(f"Error signing URL {url}: {e}")
        return url
