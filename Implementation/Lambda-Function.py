import os
import io
import uuid
from pathlib import Path
from typing import Optional

import boto3
from PIL import Image, ImageEnhance

# --- AWS Config ---
s3 = boto3.client("s3")
DEST_BUCKET = "my-example-to-upload-modified-copy-images"


def reduce_opacity(img: Image.Image, opacity: float) -> Image.Image:
    """Return a copy of the image with reduced opacity (0.0–1.0)."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    alpha = img.getchannel("A")
    alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
    img.putalpha(alpha)
    return img

# --- Lambda Layer Path ---
WATERMARK_PATH = Path("/opt/resources/watermark.png")

def find_watermark() -> Path:
    if not WATERMARK_PATH.exists():
        raise FileNotFoundError(f"❌ Watermark not found at {WATERMARK_PATH}")
    print(f"✅ Using watermark: {WATERMARK_PATH}")
    return WATERMARK_PATH


def add_watermark(img: Image.Image, watermark_path: Path, opacity: float = 0.5) -> Image.Image:
    """Overlay a watermark image onto the given base image."""
    with open(watermark_path, "rb") as f:
        watermark_bytes = f.read()

    watermark = Image.open(io.BytesIO(watermark_bytes)).convert("RGBA")

    # Scale watermark to ~60% of image width
    wm_ratio = img.width * 0.6 / watermark.width
    new_size = (int(watermark.width * wm_ratio), int(watermark.height * wm_ratio))
    watermark = watermark.resize(new_size, Image.LANCZOS)

    # Apply opacity
    watermark = reduce_opacity(watermark, opacity)

    # Position (right-center)
    position = (img.width - watermark.width, (img.height - watermark.height) // 2)

    # Composite overlay
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    overlay.paste(watermark, position, watermark)

    return Image.alpha_composite(img, overlay)

def s3_object_exists(bucket: str, key: str) -> bool:
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except s3.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            return False
        raise


def lambda_handler(event, context):
    try:
        # 1. Extract event info
        record = event["Records"][0]
        source_bucket = record["s3"]["bucket"]["name"]
        object_key = record["s3"]["object"]["key"]

        if not s3_object_exists(source_bucket, object_key):
            return {"statusCode": 404, "body": f"Object {object_key} not found in {source_bucket}"}

        print(f"📥 New image uploaded: {object_key} in {source_bucket}")

        # 2. Download original image from S3
        response = s3.get_object(Bucket=source_bucket, Key=object_key)
        image_content = response["Body"].read()
        img = Image.open(io.BytesIO(image_content)).convert("RGBA")

        # 3. Resize base image
        img.thumbnail((600, 600))

        # 4. Load watermark (from Lambda layer)
        watermark_path = find_watermark()
        watermarked = add_watermark(img, watermark_path, opacity=0.5).convert("RGB")

        # 5. Save result to memory
        buffer = io.BytesIO()
        watermarked.save(buffer, format="JPEG")
        buffer.seek(0)

        # 6. Upload processed image to S3
        new_key = f"processed-{uuid.uuid4()}.jpg"
        s3.upload_fileobj(
            buffer,
            DEST_BUCKET,
            new_key,
            ExtraArgs={"ContentType": "image/jpeg"}
        )

        # 7. Generate pre-signed URL
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": DEST_BUCKET, "Key": new_key},
            ExpiresIn=3600,
        )

        print(f"✅ Processed image saved to {DEST_BUCKET}/{new_key}")
        return {"statusCode": 200, "body": f"Processed image available at {url}"}

    except Exception as e:
        print(f"❌ Error: {e}")
        return {"statusCode": 500, "body": f"Error: {str(e)}"}
