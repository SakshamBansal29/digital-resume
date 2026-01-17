from pypdf import PdfReader
import json
import boto3

try:
    reader = PdfReader("./data/Saksham_Bansal.pdf")
    linkedin = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            linkedin += text
except FileNotFoundError:
    linkedin = "Saksham full profile not available"


with open("./data/summary.txt", "r") as f:
    summary = f.read()

with open("./data/style.txt", "r", encoding="utf-8") as f:
    style = f.read()

with open("./data/facts.json", "r", encoding="utf-8") as f:
    facts = json.load(f)



def rename_memory_files_s3(bucket_name: str, session_id: str, last_email: str):
    """
    Rename S3 memory files from session_id → last_email
    Equivalent to your local os.rename() logic
    """
    s3_client = boto3.client('s3')
    print("old and new file names -- ")
    # S3 paths (equivalent to local MEMORY_DIR)
    old_path_con = f"conversations/{session_id}.json"
    old_path_md = f"log_mails/{session_id}.json"
    
    new_path_con = f"conversations/{last_email}.json"
    new_path_md = f"log_mails/{last_email}.json"
    
    renamed_files = []
    
    # Check if both old files exist (S3 equivalent of os.path.exists())
    print("checking start")
    print("exception key -- ", s3_client.exceptions.NoSuchKey)
    
    try:
        s3_client.head_object(Bucket=bucket_name, Key=old_path_con)
        print("✅ conversations exists")
    except Exception as e:  # ← Catch ANYTHING
        print(f"❌ conversations check failed: {type(e).__name__}: {str(e)[:100]}")
        print("Old files not found - skipping rename")
        return False  # ← Early return
    
    try:
        s3_client.head_object(Bucket=bucket_name, Key=old_path_md)
        print("✅ log_mails exists")
    except Exception as e:  # ← Separate try for each file
        print(f"❌ log_mails check failed: {type(e).__name__}: {str(e)[:100]}")
        print("Old files not found - skipping rename")
        return False

    print("checking done")

    # Skip if no change needed (same as your local logic)
    if old_path_con == new_path_con and old_path_md == new_path_md:
        print("No rename needed - paths unchanged")
        return False
    
    # Rename conversations file
    try:
        copy_source_con = {'Bucket': bucket_name, 'Key': old_path_con}
        s3_client.copy_object(CopySource=copy_source_con, Bucket=bucket_name, Key=new_path_con)
        s3_client.delete_object(Bucket=bucket_name, Key=old_path_con)
        renamed_files.append(f"{old_path_con} → {new_path_con}")
    except Exception as e:
        print(f"Failed to rename conversations: {e}")
        return False
    
    # Rename log_mails file  
    try:
        copy_source_md = {'Bucket': bucket_name, 'Key': old_path_md}
        s3_client.copy_object(CopySource=copy_source_md, Bucket=bucket_name, Key=new_path_md)
        s3_client.delete_object(Bucket=bucket_name, Key=old_path_md)
        renamed_files.append(f"{old_path_md} → {new_path_md}")
    except Exception as e:
        print(f"Failed to rename log_mails: {e}")
        return False
    
    # Success logging (same as your local print)
    print(f"✅ Renamed:")
    for renamed in renamed_files:
        print(f"   {renamed}")
    
    return True