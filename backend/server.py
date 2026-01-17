import email
from ntpath import exists
from re import S
import sre_compile
import time
import fastapi
#import instructor
from httpx import Request
from requests import session
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from openai import OpenAI, api_key
import os
from dotenv import load_dotenv
from typing import Annotated, Optional, List, Dict, Literal
import json
from datetime import datetime, timedelta
import uuid
from pathlib import Path
import boto3
import asyncio
from botocore.exceptions import ClientError
from context import prompt, eval_prompt
from mails import _send
from resources import rename_memory_files_s3

from langchain_openai import ChatOpenAI
# from langchain_core.messages import HumanMessage, SystemMessage  
# from langchain_core.messages.ai import AIMessage


load_dotenv(override=True)

app = FastAPI()

origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
print("Starting client process")
# # Initialize Bedrock client
# bedrock_client = boto3.client(
#     service_name="bedrock-runtime", 
#     region_name=os.getenv("DEFAULT_AWS_REGION", "us-east-1")
# )
# print("bedrock client enabled ")
# # client = instructor.from_provider("bedrock/amazon.nova-micro-v1:0", aws_access_key_id = os.getenv("AWS_ACCESS_KEY"))
# # BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "amazon.nova-micro-v1:0")

# client = OpenAI(
#     base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
#     api_key=os.getenv("GOOGLE_API_KEY")
# )

USE_S3 = os.getenv("USE_S3", "false").lower() == "true"
S3_BUCKET = os.getenv("S3_BUCKET", "")
MEMORY_DIR = os.getenv("MEMORY_DIR", "../memory")


if USE_S3:
    s3_client = boto3.client("s3")

class ReplyClass(BaseModel):
    Reply: str = Field(description = "Record your detailed Reply not just summarized version of your reply")
    Name: Optional[str] = Field(description = "Extract Name from the User input or query")
    Email: Optional[str] = Field(description = "Extract Email from the User question or query if provided")
    Phone: Optional[str] = Field(description = "Extract Phone from the User question or query if provided")
    Company: Optional[str] = Field(description = "Extract Company name from the User question or query if provided")
    Unanswered: Optional[str] = Field(description = "Extract Question of User If a question cannot be answered from the profile")



class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    name: Optional[str] = None
    email_id: str
    Unanswered: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    email_id: str


class message(BaseModel):
    role: str
    content: str
    timestamp: str

def get_memory_path(session_id, path_type):
    if path_type == "metadata":
        return f"log_mails/{session_id}.json"
    else:
        return f"conversations/{session_id}.json"


def load_conversation(session_id: str) -> List[Dict]:
    if USE_S3:
        try:
            response = s3_client.get_object(Bucket=S3_BUCKET, Key=get_memory_path(session_id, path_type="conversation"))
            user_metadata = s3_client.get_object(Bucket=S3_BUCKET, Key=get_memory_path(session_id, path_type="metadata"))
            message_response = json.loads(response['Body'].read().decode("utf-8"))
            user_metadata_response = json.loads(user_metadata['Body'].read().decode("utf-8"))
            return message_response, user_metadata_response
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return [], []
            raise
        except Exception as e:
            # Handles ANY other Python exception
            print("Non-boto error:", str(e))
            return [], []
    else:
        file_path_conv = f"{MEMORY_DIR}/conversations/{session_id}.json"
        file_path_mail = f"{MEMORY_DIR}/log_mails/{session_id}.json"
        if os.path.exists(file_path_conv):
            with open(file_path_conv, "r", encoding="utf-8") as f:
                conv = json.load(f)
        else:
            conv = []
        
        if os.path.exists(file_path_mail):
            with open(file_path_mail, "r", encoding="utf-8") as f:
                log_mail = json.load(f)
        else:
            log_mail = []
        return conv, log_mail
            


def save_conversation(session_id: str, messages: List[Dict], metadata: List[Dict] = None):
    if USE_S3:
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=get_memory_path(session_id, path_type="conversation"),
            Body=json.dumps(messages, indent=2),
            ContentType="application/json"
        )
        if metadata:
            s3_client.put_object(
                Bucket=S3_BUCKET,
                Key=get_memory_path(session_id, path_type="metadata"),
                Body=json.dumps(metadata, indent=2),
                ContentType="application/json"
            )
    else:
        file_path_conv = f"{MEMORY_DIR}/conversations/{session_id}.json"
        os.makedirs(f"{MEMORY_DIR}/conversations", exist_ok = True)
        with open(file_path_conv, "w", encoding="utf-8") as f:
            json.dump(messages, f, indent=2, ensure_ascii = False)
        if metadata:
            os.makedirs(f"{MEMORY_DIR}/log_mails", exist_ok = True)
            file_path_mail = f"{MEMORY_DIR}/log_mails/{session_id}.json"
            with open(file_path_mail, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii = False)



@app.get("/")
async def root():
    return {
        'message': "AI Digital Twin",
        'memory_enabled': True,
        "storage": "S3" if USE_S3 else "local"
    }


@app.get("/health")
async def health_check():
    return {'status':'healthy', "use_s3": USE_S3}


def call_bedrock(conversation: List[Dict], user_message: str) -> ReplyClass:
    """Call AWS Bedrock with conversation history"""
    
    # Build messages in Bedrock format
    messages = []
    
    # Add system prompt as first user message (Bedrock convention)
    messages.append({
        "role": "user", 
        "content": [{"text": f"System: {prompt()}"}]
    })
    
    # Add conversation history (limit to last 10 exchanges to manage context)
    for msg in conversation[-20:]:  # Last 10 back-and-forth exchanges
        messages.append({
            "role": msg["role"],
            "content": [{"text": msg["content"]}]
        })
    
    # Add current user message
    messages.append({
        "role": "user",
        "content": [{"text": user_message}]
    })
    
    try:
        # Call Bedrock using the converse API
        # response = bedrock_client.converse(
        #     modelId=BEDROCK_MODEL_ID,
        #     messages=messages,
        #     inferenceConfig={
        #         "maxTokens": 150,
        #         "temperature": 0,
        #         "topP": 0.9
        #     }
        # )
        
        response = client.chat.completions.create(
            model="amazon.nova-lite-v1:0",
            messages = messages,
            max_tokens = 500,
            response_model = ReplyClass,
            temperature = 0
        )
        return json.loads(response.json())
        # Extract the response text
        #return response["output"]["message"]["content"][0]["text"]
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ValidationException':
            # Handle message format issues
            print(f"Bedrock validation error: {e}")
            raise HTTPException(status_code=400, detail="Invalid message format for Bedrock")
        elif error_code == 'AccessDeniedException':
            print(f"Bedrock access denied: {e}")
            raise HTTPException(status_code=403, detail="Access denied to Bedrock model")
        else:
            print(f"Bedrock error: {e}")
            raise HTTPException(status_code=500, detail=f"Bedrock error: {str(e)}")


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):

    try:
        session_id = request.session_id or request.email_id 
        print("session id  ----- ", session_id)
        conversation, metadata = load_conversation(session_id)

        #response_str = call_bedrock(conversation, request.message)

        messages = [
            {"role":"system", "content":prompt()}
        ]
        # messages = []
        for msg in conversation:
            messages.append(msg)

        messages.append({"role":"user", "content":request.message})

        # langchain_core_messages = []
        # for m in messages:
        #     if m["role"] == "system":
        #         langchain_core_messages.append(
        #             SystemMessage(content=m["content"])
        #         )
        #     elif m["role"] == "user":
        #         langchain_core_messages.append(
        #             HumanMessage(content=m["content"])
        #         )
        #     else:
        #         langchain_core_messages.append(
        #             AIMessage(content=m["content"])
        #         )

        #print("langchain_core_messages -------------------- ", messages)
        #llm = ChatPerplexity(model = "sonar", pplx_api_key=os.getenv("PPLX_API_KEY"), temperature = 0, max_tokens = 500)
        start_model = time.time()
        llm = ChatOpenAI(model="gpt-4.1", temperature = 0, api_key=os.getenv("OPEN_API_KEY"))
        model_time = time.time() - start_model
        print("LLM Time ---- ", model_time)
        llm_str_opt = llm.with_structured_output(ReplyClass)
        response_str = llm_str_opt.invoke(messages)
        
        assistant_response = response_str.Reply
        unanswered_question = response_str.Unanswered
        phone = response_str.Phone
        name = response_str.Name
        email = response_str.Email

        md = {'name':name, 'email':email, 'unanswered_questions':unanswered_question, 'phone':phone, 'last_time':datetime.now().isoformat()}
        metadata.append(md)
        conversation.append({"role":"user", "content":request.message, "timestamp":datetime.now().isoformat()})
        conversation.append({"role":"assistant", "content":assistant_response, "timestamp":datetime.now().isoformat()})

        last_email = next(
            (d["email"] for d in reversed(metadata) if d.get("email")),
            None
        )
        print("Conversation started -- ")
        if last_email:

            if USE_S3:
                print("renaming files if any")
                rename_memory_files_s3(S3_BUCKET, session_id, last_email)
                print("renaming done")
            else:
                old_path_con = f"{MEMORY_DIR}/conversations/{session_id}.json"
                old_path_md = f"{MEMORY_DIR}/log_mails/{session_id}.json"

                new_path_con = f"{MEMORY_DIR}/conversations/{last_email}.json"
                new_path_md = f"{MEMORY_DIR}/log_mails/{last_email}.json"

                if os.path.exists(old_path_con) and os.path.exists(old_path_md) and old_path_con != new_path_con and old_path_md != new_path_md:
                    
                    os.rename(old_path_con, new_path_con)
                    os.rename(old_path_md, new_path_md)

                    print(f"Renamed: {old_path_con} → {new_path_con}")
                    print(f"Renamed: {old_path_md} → {new_path_md}")
            
            session_id = last_email


        save_conversation(session_id, conversation, metadata)

        return ChatResponse(
            response=assistant_response,
            session_id = session_id,
            email_id = session_id
        )

    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def send_notify(session_id: str):

    now = datetime.now()
    conversations, metadata = load_conversation(session_id)
    
    print(f"[INFO] Sending notification to Saksham")
    notify_sender = _send(session_id, metadata)
    status = notify_sender.notify_via_ntfy()


@app.post("/chat-close")
async def chat_close(request: fastapi.Request):
    print("🔥 /chat-close HIT")
    try:
        body_bytes = await request.body()
        body_json = json.loads(body_bytes.decode("utf-8"))
        session_id = body_json.get("session_id")
        if not session_id:
            raise HTTPException(status_code=400, detail="Missing session_id")

        _, metadata = load_conversation(session_id)

        print(f"[INFO] Notification {session_id}")
        notify_sender = _send(session_id, metadata)
        status = notify_sender.notify_via_ntfy()
        print('status ---- ', status)
        
        return {"status": "Notification triggered"}

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    except Exception as e:
        print(f"Error in chat-close: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/conversation/{session_id}")
async def get_conversation(session_id: str):
    """Retrieve conversation history"""
    try:
        conversation, _ = load_conversation(session_id)
        return {"session_id": session_id, "messages": conversation}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port = 8000)


