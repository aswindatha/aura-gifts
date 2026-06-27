import os
import boto3
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Read production R2 settings
account_id = os.getenv("PROD_R2_ACCOUNT_ID")
access_key = os.getenv("PROD_R2_ACCESS_KEY_ID")
secret_key = os.getenv("PROD_R2_SECRET_ACCESS_KEY")
bucket_name = os.getenv("PROD_R2_BUCKET_NAME", "aura-prints")

if not all([account_id, access_key, secret_key]):
    print("Error: Missing R2 credentials in backend/.env file.")
    exit(1)

# Initialize S3 client for Cloudflare R2
r2_endpoint = f"https://{account_id}.r2.cloudflarestorage.com"
s3 = boto3.client(
    "s3",
    endpoint_url=r2_endpoint,
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    region_name="auto"
)

# Define the CORS configuration
cors_configuration = {
    'CORSRules': [
        {
            'AllowedHeaders': ['*'],
            'AllowedMethods': ['PUT', 'GET', 'POST', 'DELETE', 'HEAD'],
            'AllowedOrigins': [
                'https://auraprintsandgifts.in',
                'https://www.auraprintsandgifts.in',
                'http://localhost:5173',
                'http://127.0.0.1:5173'
            ],
            'ExposeHeaders': ['ETag'],
            'MaxAgeSeconds': 3000
        }
    ]
}

try:
    print(f"Applying CORS configuration to R2 bucket '{bucket_name}'...")
    s3.put_bucket_cors(
        Bucket=bucket_name,
        CORSConfiguration=cors_configuration
    )
    print("Success! CORS rules configured successfully.")
except Exception as e:
    print(f"Error applying CORS: {e}")
