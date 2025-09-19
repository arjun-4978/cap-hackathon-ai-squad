import json
import boto3
import logging
from datetime import datetime
from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent

# --------------------------
# Setup logging
# --------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# --------------------------
# Initialize AgentCore app
# --------------------------
app = BedrockAgentCoreApp()

# --------------------------
# AI Agent: BRD Generator
# --------------------------
brd_agent = Agent(
    model="anthropic.claude-3-sonnet-20240229-v1:0",
    system_prompt="""
    You are a Business Analyst AI. 
    Your task is to generate a clear and detailed Business Requirement Document (BRD)
    based on the provided JSON feature input. 
    Provide the output as markdown. Do not include greetings.
    """
)

# --------------------------
# Initialize S3 client
# --------------------------
s3_client = boto3.client("s3")

# --------------------------
# Helper functions
# --------------------------
def list_s3_files(bucket: str, prefix: str):
    paginator = s3_client.get_paginator("list_objects_v2")
    page_iterator = paginator.paginate(Bucket=bucket, Prefix=prefix)
    files = []
    for page in page_iterator:
        for obj in page.get("Contents", []):
            if not obj["Key"].endswith("/"):
                files.append(obj["Key"])
    return files

def read_s3_file(bucket: str, key: str) -> str:
    response = s3_client.get_object(Bucket=bucket, Key=key)
    return response["Body"].read().decode("utf-8")

def write_s3_file(bucket: str, key: str, content: str):
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=content.encode("utf-8"),
        ContentType="text/markdown"
    )

# --------------------------
# Entrypoint
# --------------------------
@app.entrypoint
def invoke(payload):
    bucket = payload.get("bucket")
    brand = payload.get("brand")
    feature = payload.get("feature")

    if not bucket or not brand or not feature:
        return {"error": "Please provide 'bucket', 'brand', and 'feature' in the payload."}

    # 1️⃣ List input files
    input_prefix = f"{brand}/Feature/input/{feature}/"
    input_files = list_s3_files(bucket, input_prefix)
    if not input_files:
        return {"error": f"No input files found under {input_prefix}"}

    # Log the input files for tracking
    logger.info(f"Input files found for processing ({len(input_files)}):")
    for f in input_files:
        logger.info(f" - {f}")

    # 2️⃣ Read and combine input
    combined_input = {}
    for key in input_files:
        content = read_s3_file(bucket, key)
        try:
            data = json.loads(content)
        except:
            data = content
        combined_input[key.split("/")[-1]] = data

    # 3️⃣ Build prompt for BRD agent
    brd_prompt = f"""
Create BRD document from below contents remove unwanted contents while gnerating BRD      
{json.dumps(combined_input, indent=2)}
Provide the output as markdown.
"""

    # Log the final message being sent to the LLM
    logger.info("Final prompt/message sent to the LLM for BRD generation:")
    logger.info(brd_prompt)

    # 4️⃣ Generate BRD
    brd_result = brd_agent(brd_prompt)
    if isinstance(brd_result, dict):
        if "content" in brd_result and isinstance(brd_result["content"], list):
            brd_text = brd_result["content"][0]["text"]
        else:
            brd_text = json.dumps(brd_result, indent=2)
    elif hasattr(brd_result, "message"):
        brd_text = str(brd_result.message)
    else:
        brd_text = str(brd_result)

    # 5️⃣ Write BRD markdown to S3
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_md_key = f"{brand}/Feature/output/{feature}/BRD_{feature}_{timestamp}.md"
    write_s3_file(bucket, output_md_key, brd_text)

    logger.info(f"BRD markdown written to: s3://{bucket}/{output_md_key}")

    return {
        "brd_s3_md_path": f"s3://{bucket}/{output_md_key}",
        "input_files": input_files
    }

# --------------------------
# Run locally
# --------------------------
if __name__ == "__main__":
    logger.info("🚀 Starting AgentCore locally at http://localhost:8080")
    app.run(host="0.0.0.0", port=8080)
