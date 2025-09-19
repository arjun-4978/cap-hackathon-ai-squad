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
# AI Agents
# --------------------------
extractor_agent = Agent(
    model="anthropic.claude-3-sonnet-20240229-v1:0",
    system_prompt="""
    Extract brand and feature from user query. Look for:
    - Brand names (like Test_Brand, Brand_Name, etc.)
    - Feature names (like promotions, loyalty, rewards, etc.)
    - Match against available options when provided
    
    Return JSON only: {"brand": "exact_brand_name", "feature": "exact_feature_name"}
    If unclear, return {"brand": null, "feature": null}
    """
)

brd_agent = Agent(
    model="anthropic.claude-3-sonnet-20240229-v1:0",
    system_prompt="""
    You are a Business Analyst AI. 
    Your task is to generate a clear and detailed Business Requirement Document (BRD)
    based on the provided JSON/MD feature input. 
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

def list_brands(bucket: str):
    try:
        response = s3_client.list_objects_v2(Bucket=bucket, Delimiter='/')
        return [prefix['Prefix'].rstrip('/') for prefix in response.get('CommonPrefixes', [])]
    except:
        return []

def list_features(bucket: str, brand: str):
    try:
        prefix = f"{brand}/Feature/input/"
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix, Delimiter='/')
        return [prefix['Prefix'].split('/')[-2] for prefix in response.get('CommonPrefixes', [])]
    except:
        return []

# --------------------------
# Entrypoint
# --------------------------
@app.entrypoint
def invoke(payload):
    bucket = payload.get("bucket", "ai-solution-squad")
    query = payload.get("query")
    brand = payload.get("brand")
    feature = payload.get("feature")

    # Handle natural language query
    if query and not (brand and feature):
        # 1. Extract all brands and features from S3
        brands = list_brands(bucket)
        all_features = set()
        features_by_brand = {}
        
        for b in brands:
            brand_features = list_features(bucket, b)
            features_by_brand[b] = brand_features
            all_features.update(brand_features)
        
        all_features = list(all_features)
        
        # 2. Find best matching brand and feature
        extract_prompt = f"""
        User query: "{query}"
        
        Available brands: {brands}
        Available features: {all_features}
        Features by brand: {features_by_brand}
        
        Find the MOST MATCHING brand name first, then the MOST MATCHING feature name.
        Return JSON: {{"brand": "best_match_brand", "feature": "best_match_feature"}}
        """
        
        result = extractor_agent(extract_prompt)
        try:
            if hasattr(result, 'content') and result.content:
                extracted = json.loads(result.content[0].text)
            else:
                extracted = json.loads(str(result))
            brand = brand or extracted.get("brand")
            feature = feature or extracted.get("feature")
        except:
            logger.error(f"Failed to parse extraction result: {result}")
    
    # List available options if missing parameters
    if not brand or not feature:
        if 'brands' not in locals():
            brands = list_brands(bucket)
            features_by_brand = {b: list_features(bucket, b) for b in brands}
        
        missing = []
        if not brand: missing.append("Brand")
        if not feature: missing.append("Feature")
        
        return {
            "error": f"{' or '.join(missing)} is not understood from Prompt",
            "available_brands": brands,
            "available_features": features_by_brand,
            "query_received": query
        }

    logger.info(f"Processing: bucket={bucket}, brand={brand}, feature={feature}")
    
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
 Generate a comprehensive Business Requirements Document (BRD) for a new feature.

The BRD must be created by analyzing and synthesizing the following content:

1.  {json.dumps(combined_input, indent=2)} Combine the content from all provided JSON and Markdown files. These files contain specific feature requirements, technical specifications, and user stories.
2.  Extract and integrate relevant business and functional requirements from the following web pages:
    -   `https://info.kognitivloyalty.com/Promotions.html`
    -   `https://info.kognitivloyalty.com/Segment_Group.html`

The BRD must be a single, well-structured Markdown document. Ensure the final output is a clean, professional, and well-organized document ready for business and technical stakeholders. Avoid including any raw or unprocessed data dumps from the source files or URLs.

"""

    # Generate BRD (prompt logged separately if needed)
    logger.info("Generating BRD with LLM...")

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
