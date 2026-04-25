# skills/INSTAGRAM.md

## Goal
Full Instagram Graph API integration. Publish + analytics + comment NLP.

## Base Setup
```python
BASE = "https://graph.facebook.com/v21.0"
ACCOUNT_ID = settings.INSTAGRAM_ACCOUNT_ID
TOKEN = settings.INSTAGRAM_ACCESS_TOKEN
```

## Publish Flow (3 steps + 1 comment)
```python
# Step 1: Container
POST {BASE}/{ACCOUNT_ID}/media
  {media_type: "REELS", video_url: R2_PUBLIC_URL, caption: CAPTION_TEXT, access_token: TOKEN}
→ {id: container_id}

# Step 2: Poll until ready
GET {BASE}/{container_id}?fields=status_code&access_token={TOKEN}
Poll every 15s. Status: IN_PROGRESS → FINISHED (or ERROR/EXPIRED)
Timeout after 5 minutes.

# Step 3: Publish
POST {BASE}/{ACCOUNT_ID}/media_publish
  {creation_id: container_id, access_token: TOKEN}
→ {id: post_id}

# Step 4: Hashtags as first comment
POST {BASE}/{post_id}/comments
  {message: "#tag1 #tag2 ...", access_token: TOKEN}
```

## Analytics Endpoints
```python
# Insights for a post
GET {BASE}/{post_id}/insights
  ?metric=plays,reach,saved,shares,comments,follows,impressions
  &access_token={TOKEN}

# Comments (for NLP at T+7d)
GET {BASE}/{post_id}/comments
  ?fields=text,timestamp,like_count&limit=100&access_token={TOKEN}
```

## Token Refresh (weekly cron job)
```python
GET {BASE}/oauth/access_token
  ?grant_type=fb_exchange_token
  &client_id={APP_ID}
  &client_secret={APP_SECRET}
  &fb_exchange_token={CURRENT_TOKEN}
→ {access_token: NEW_TOKEN, expires_in: 5183944}
# Store new token to Supabase secrets table
# Schedule next refresh for 50 days from now
```

## Video Requirements for R2 Upload
Format: MP4 (H.264 + AAC)  |  Aspect: 9:16  |  Min: 1080x1920  |  Max: 1GB  |  Duration: 3-90s

## Cloudflare R2 Upload
```python
import boto3
s3 = boto3.client("s3",
    endpoint_url=f"https://{CF_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_KEY, aws_secret_access_key=R2_SECRET)
s3.upload_file(local_path, "ekfollowekchara-reelmind", filename,
               ExtraArgs={"ContentType": "video/mp4"})
public_url = f"https://pub-{CF_ACCOUNT_ID}.r2.dev/{filename}"
```

## Rate Limits
200 API calls/hour per token. Publishing: 50 reels/day max.
Use tenacity for retries: stop_after_attempt(3), wait_exponential(min=4, max=30).
