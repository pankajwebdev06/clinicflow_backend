from supabase import create_client, Client
import os
from typing import Optional
import uuid

class StorageService:
    def __init__(self):
        # In production, these will be in .env
        self.url = os.getenv("SUPABASE_URL", "")
        self.key = os.getenv("SUPABASE_KEY", "")
        self.supabase: Optional[Client] = None
        
        if self.url and self.key:
            self.supabase = create_client(self.url, self.key)

    async def upload_file(self, bucket: str, file_data: bytes, filename: str) -> Optional[str]:
        """
        Uploads a file to Supabase storage and returns the public URL.
        """
        if not self.supabase:
            print("Supabase client not initialized. Check your environment variables.")
            return None
            
        # Generate a unique path: bucket/uuid_filename.webp
        ext = os.path.splitext(filename)[1]
        unique_name = f"{uuid.uuid4()}{ext}"
        path = f"{unique_name}"
        
        try:
            # Uploading bytes to bucket
            response = self.supabase.storage.from_(bucket).upload(
                path=path,
                file=file_data,
                file_options={"content-type": "image/webp"}
            )
            
            # Get Public URL
            public_url = self.supabase.storage.from_(bucket).get_public_url(path)
            return public_url
        except Exception as e:
            print(f"Error uploading to Supabase: {str(e)}")
            return None

storage_service = StorageService()
