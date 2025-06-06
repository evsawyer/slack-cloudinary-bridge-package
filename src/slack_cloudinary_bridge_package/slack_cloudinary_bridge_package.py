from fastmcp import FastMCP
# from .slack_helper import download_slack_image
# from .cloudinary_helper import upload_to_cloudinary
import os
import requests
import cloudinary
import cloudinary.uploader
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

mcp = FastMCP("Slack-Cloudinary-Bridge")

@mcp.tool()
async def download_slack_image(slack_url: str) -> bytes:
    """
    Downloads an image from a Slack private URL using the bot token from env vars.
    
    Args:
        slack_url (str): The private Slack image URL.
    
    Returns:
        bytes: The image content in bytes.
        
    Raises:
        ValueError: If the BOT_TOKEN environment variable is not set.
    """
    slack_token = os.environ.get("BOT_TOKEN")
    logger.info(f"Attempting to download image from Slack URL: {slack_url}")
    
    if not slack_token:
        logger.error("BOT_TOKEN environment variable not set")
        return "Failed to download image from Slack"
        
    headers = {
        "Authorization": f"Bearer {slack_token}"
    }
    try:
        response = requests.get(slack_url, headers=headers)
        response.raise_for_status()
        logger.info(f"Successfully downloaded image. Size: {len(response.content)} bytes")
        return response.content
    except requests.RequestException as e:
        logger.error(f"Failed to download image: {e}")
        return "Failed to download image from Slack"

@mcp.tool()
async def upload_to_cloudinary(image_bytes: bytes) -> str:
    """
    Uploads image bytes to Cloudinary using credentials from env vars and returns the public URL.
    
    Args:
        image_bytes (bytes): The image content in bytes. 
        
    Returns:
        str: The public URL of the uploaded image.
        
    Raises:
        ValueError: If required Cloudinary environment variables are not set.
    """
    logger.info("Starting Cloudinary upload")
    
    api_key = os.environ.get("CLOUDINARY_API_KEY")
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME")

    if not all([api_key, api_secret, cloud_name]):
        missing = []
        if not api_key: missing.append("CLOUDINARY_API_KEY")
        if not api_secret: missing.append("CLOUDINARY_API_SECRET")
        if not cloud_name: missing.append("CLOUDINARY_CLOUD_NAME")
        logger.error(f"Missing Cloudinary credentials: {', '.join(missing)}")
        return "Missing required environment variables"

    # Note: Consider configuring Cloudinary once globally instead of per-call if possible.
    try:
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True
        )
        logger.info("Cloudinary configured, attempting upload")
        
        result = cloudinary.uploader.upload(image_bytes)
        if not result or "secure_url" not in result:
            logger.error(f"Cloudinary upload failed or missing secure_url. Result: {result}")
            return "Failed to upload image to Cloudinary"
            
        logger.info(f"Successfully uploaded to Cloudinary. URL: {result['secure_url']}")
        return result["secure_url"]
        
    except Exception as e:
        logger.error(f"Error during Cloudinary upload: {e}")
        return "Failed to upload image to Cloudinary"

# Helper function to check for required environment variables
def check_env_vars(*vars):
    missing = [var for var in vars if not os.environ.get(var)]
    if missing:
        logger.warning(f"Missing environment variables: {', '.join(missing)}")
        return f"Missing required environment variables: {', '.join(missing)}"
    logger.info("All required environment variables are set")
    return None

@mcp.tool()
async def upload_slack_image(slack_url: str) -> str:
    """
    Downloads an image from a Slack private URL and uploads it to Cloudinary.
    Reads required credentials (BOT_TOKEN, CLOUDINARY_*) from environment variables.
    
    Args:
        slack_url (str): The private Slack image URL.
        
    Returns:
        str: The public URL of the uploaded image on Cloudinary, or an error message.
    """
    logger.info(f"Starting Slack to Cloudinary transfer for URL: {slack_url}")
    
    env_error = check_env_vars("BOT_TOKEN", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET", "CLOUDINARY_CLOUD_NAME")
    if env_error:
        return env_error

    try:
        image_bytes = await download_slack_image(slack_url)
        if not image_bytes:
            return "Failed to download image from Slack"
            
        public_url = await upload_to_cloudinary(image_bytes)
        if not public_url:
            return "Failed to upload image to Cloudinary"

        return public_url
        
    except Exception as e:
        logger.error(f"Unexpected error during transfer: {e}")
        return f"An unexpected error occurred: {str(e)}"

# if __name__ == "__main__":
#     mcp.run(transport='stdio')