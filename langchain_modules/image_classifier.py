import logging
import os
import base64
from typing import Dict, Any, Optional
from google.cloud import aiplatform
from google.cloud.aiplatform.gapic.schema import predict
from me_telegram_bot.bot import genai
from PIL import Image
import requests
from io import BytesIO

logger = logging.getLogger(__name__)

class RooftopImageClassifier:
    """Class for analyzing rooftop images to estimate solar potential."""
    
    def __init__(self, project_id=None, location=None, endpoint_id=None):
        """Initialize the rooftop image classifier.
        
        Args:
            project_id: Google Cloud project ID
            location: Google Cloud region
            endpoint_id: Vertex AI endpoint ID for the image analysis model
        """
        self.project_id = project_id or os.getenv("VERTEX_PROJECT_ID")
        self.location = location or os.getenv("VERTEX_LOCATION", "us-central1")
        self.endpoint_id = endpoint_id or os.getenv("VERTEX_ENDPOINT_ID")
        
        # Flag to determine if we should use mock responses for demo purposes
        self.mock_mode = os.getenv("MOCK_IMAGE_ANALYSIS", "true").lower() == "true"
    
    def analyze_image(self, image_path: str) -> Dict[str, Any]:
        
        
        """
        Analyzes a rooftop image to determine if it's suitable for solar panel installation.
        
        Args:
            image_path: Path to the rooftop image or URL
        
        Returns:
            Analysis results including suitability assessment and reasoning
        """
        try:
            # Check if image_path is a URL
            if image_path.startswith('http://') or image_path.startswith('https://'):
            
            # Download the image from URL
                response = requests.get(image_path)
                img = Image.open(BytesIO(response.content))
            else:
            # Load the image from local file path
                img = Image.open(image_path)
            
            # Initialize the Gemini Pro Vision model
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Create the prompt with specific evaluation criteria
            prompt = """
            Analyze this rooftop image and determine if it's suitable for solar panel installation.
            
            Consider the following factors:
            1. Roof orientation and angle
            2. Sunlight exposure and shading
            3. Available surface area
            4. Potential obstructions (chimneys, vents, etc.)
            5. Roof condition and material
            
            Provide the following in your response:
            - A clear yes/no suitability assessment
            - Any concerns or limitations 

            Remember:- 
                Keep the response within 100 tokens.
            """
            
            # Generate the analysis
            response = model.generate_content([prompt, img])
            return response.text
        except Exception as e:
            logger.error(f"Error analyzing image: {str(e)}")
            return {"error": str(e), "suitable": False}
    
    
    def analyze_image_url(self, image_url: str) -> Dict[str, Any]:
        """Analyze a rooftop image from a URL to estimate solar potential.
        
        Args:
            image_url: URL of the image
            
        Returns:
            Dictionary containing analysis results
        """
        # In a real implementation, this would download the image and then analyze it
        # For now, return mock results
        return self._mock_analysis_result(image_url)
    
    def _process_prediction_response(self, response) -> Dict[str, Any]:
        """Process the prediction response from Vertex AI.
        
        Args:
            response: Response from Vertex AI endpoint
            
        Returns:
            Processed analysis results
        """
        # In a real implementation, this would extract relevant information from the model response
        # For now, returning a mock result
        return {
            "suitable_area_sqm": 25.5,
            "estimated_capacity_kw": 3.8,
            "annual_generation_kwh": 5700,
            "suitable": True,
            "confidence": 0.85,
            "roof_orientation": "south",
            "shading_factor": 0.12
        }
    
    def _mock_analysis_result(self, image_path_or_url: str) -> Dict[str, Any]:
        """Generate a mock analysis result for demonstration purposes.
        
        Args:
            image_path_or_url: Path or URL to the image
            
        Returns:
            Mock analysis results
        """
        # Simple logic to vary the mock results based on the input path hash
        hash_value = sum(ord(c) for c in image_path_or_url) % 100
        
        suitable = hash_value > 20  # 80% chance of being suitable
        
        if suitable:
            area = 20 + (hash_value % 30)  # 20-50 sq meters
            capacity = area * 0.15  # rough estimate of capacity
            generation = capacity * 1500  # rough estimate of annual generation
            shading = (hash_value % 30) / 100  # 0-0.3 shading factor
            confidence = 0.7 + (hash_value % 30) / 100  # 0.7-1.0 confidence
            
            orientations = ["south", "south-west", "south-east", "west", "east"]
            orientation = orientations[hash_value % len(orientations)]
            
            return {
                "suitable_area_sqm": round(area, 1),
                "estimated_capacity_kw": round(capacity, 1),
                "annual_generation_kwh": int(generation),
                "suitable": True,
                "confidence": round(confidence, 2),
                "roof_orientation": orientation,
                "shading_factor": round(shading, 2)
            }
        else:
            reasons = [
                "Excessive shading detected",
                "Roof orientation not optimal",
                "Roof area too small",
                "Complex roof structure"
            ]
            
            return {
                "suitable": False,
                "confidence": round(0.6 + (hash_value % 40) / 100, 2),
                "reason": reasons[hash_value % len(reasons)]
            }

# Create a singleton instance
rooftop_analyzer = RooftopImageClassifier()