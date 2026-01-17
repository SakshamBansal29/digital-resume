from mangum import Mangum
from server import app
from mails import _send
import json
from datetime import datetime
import boto3
from server import send_notify
from dotenv import load_dotenv
import os
import asyncio

load_dotenv(override = True)

USE_S3 = os.getenv("USE_S3", "false").lower() == "true"
S3_BUCKET = os.getenv("S3_BUCKET", "")
MEMORY_DIR = os.getenv("MEMORY_DIR", "../memory")


api_handler = Mangum(app)


def send_mails_notify():

    s3_client = boto3.client("s3")

    METADATA_PREFIX = "metadata/"

    response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=METADATA_PREFIX
    )

    if "Contents" not in response:
        print("No metadata found.")
        return {"status": "no-metadata"}

    for obj in response['Contents']:
        key = obj['Key']
        session_id = key.replace(METADATA_PREFIX, "").replace(".json", "")
        print(f"Checking: {session_id}")

        asyncio.run(send_notify(session_id))


def handler(event, context):

    # 1️⃣ Detect CloudWatch Scheduled Event
    if event.get("source") == "aws.events":
        print("Detected CloudWatch Event → Running inactivity check")
        return send_mails_notify()

    print("Detected API Gateway Event → Routing to FastAPI")
    return api_handler(event, context)



