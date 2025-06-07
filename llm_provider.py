import os
import json
import requests
from typing import List, Dict, Any, Optional, Union
from dotenv import load_dotenv
from rich.console import Console

# Import the TransformersProvider if available
try:
    from transformers_provider import TransformersProvider
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

# Load environment variables
load_dotenv()

# Initialize console for rich output
console = Console()

class LLMProvider:
    """Provider for LLM services that supports both OpenAI and local LLMs."""
    
    def __init__(self):
        """Initialize the LLM provider."""
        self.provider_type = os.getenv("LLM_PROVIDER", "openai").lower()
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3")
        self.transformers_model = os.getenv("TRANSFORMERS_MODEL", "deepseek-ai/deepseek-coder-6.7b-instruct")
        
        # Initialize the appropriate client
        if self.provider_type == "openai":
            self._init_openai()
        elif self.provider_type == "ollama":
            self._init_ollama()
        elif self.provider_type == "transformers":
            self._init_transformers()
        else:
            console.print(f"[yellow]Warning: Unknown LLM provider '{self.provider_type}'. Falling back to OpenAI.[/yellow]")
            self.provider_type = "openai"
            self._init_openai()
    
    def _init_openai(self):
        """Initialize OpenAI client."""
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.openai_api_key)
            console.print("[green]OpenAI client initialized successfully[/green]")
        except ImportError:
            console.print("[red]Error: OpenAI package not installed. Run 'pip install openai'[/red]")
            self.client = None
        except Exception as e:
            console.print(f"[red]Error initializing OpenAI client: {str(e)}[/red]")
            self.client = None
    
    def _init_ollama(self):
        """Initialize Ollama client."""
        # Ollama uses a REST API, so we don't need a special client
        # Just verify the server is running
        try:
            response = requests.get(f"{self.ollama_base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [model.get("name") for model in models]
                
                if not model_names:
                    console.print("[yellow]Warning: No models found in Ollama. Please pull a model using 'ollama pull llama3'[/yellow]")
                elif self.ollama_model not in model_names:
                    console.print(f"[yellow]Warning: Model '{self.ollama_model}' not found in Ollama. Available models: {', '.join(model_names)}[/yellow]")
                    console.print(f"[yellow]Please pull the model using 'ollama pull {self.ollama_model}'[/yellow]")
                else:
                    console.print(f"[green]Ollama initialized successfully with model '{self.ollama_model}'[/green]")
                
                self.client = True  # Just a flag to indicate Ollama is available
            else:
                console.print(f"[red]Error connecting to Ollama: {response.status_code} {response.text}[/red]")
                self.client = None
        except requests.exceptions.ConnectionError:
            console.print(f"[red]Error: Could not connect to Ollama at {self.ollama_base_url}[/red]")
            console.print("[yellow]Is Ollama running? Start it with 'ollama serve'[/yellow]")
            self.client = None
        except Exception as e:
            console.print(f"[red]Error initializing Ollama: {str(e)}[/red]")
            self.client = None
            
    def _init_transformers(self):
        """Initialize Transformers model."""
        if not TRANSFORMERS_AVAILABLE:
            console.print("[red]Error: Transformers provider not available. Make sure transformers_provider.py exists and required packages are installed.[/red]")
            self.client = None
            return
            
        try:
            # Create a TransformersProvider instance
            self.transformers_provider = TransformersProvider()
            
            if self.transformers_provider.is_available():
                console.print(f"[green]Transformers provider initialized successfully with model '{self.transformers_model}'[/green]")
                self.client = True  # Flag to indicate Transformers is available
            else:
                console.print("[red]Error: Transformers provider not available[/red]")
                self.client = None
        except Exception as e:
            console.print(f"[red]Error initializing Transformers provider: {str(e)}[/red]")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if the LLM provider is available."""
        return self.client is not None
    
    def get_provider_type(self) -> str:
        """Get the type of LLM provider being used."""
        return self.provider_type
    
    def chat_completion(self, 
                        messages: List[Dict[str, str]], 
                        model: Optional[str] = None,
                        temperature: float = 0.7,
                        max_tokens: int = 1000) -> Optional[str]:
        """
        Generate a chat completion using the configured LLM provider.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            model: Model to use (optional, falls back to default if not specified)
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate
            
        Returns:
            Generated text or None if an error occurred
        """
        if not self.is_available():
            console.print("[red]Error: LLM provider not available[/red]")
            return None
        
        try:
            if self.provider_type == "openai":
                return self._openai_chat_completion(messages, model, temperature, max_tokens)
            elif self.provider_type == "ollama":
                return self._ollama_chat_completion(messages, model, temperature, max_tokens)
            elif self.provider_type == "transformers":
                return self._transformers_chat_completion(messages, model, temperature, max_tokens)
            else:
                console.print(f"[red]Error: Unknown provider type '{self.provider_type}'[/red]")
                return None
        except Exception as e:
            console.print(f"[red]Error generating chat completion: {str(e)}[/red]")
            return None
    
    def _openai_chat_completion(self, 
                               messages: List[Dict[str, str]], 
                               model: Optional[str] = None,
                               temperature: float = 0.7,
                               max_tokens: int = 1000) -> Optional[str]:
        """Generate a chat completion using OpenAI."""
        try:
            model = model or "gpt-4o"
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            console.print(f"[red]OpenAI API error: {str(e)}[/red]")
            return None
    
    def _ollama_chat_completion(self, 
                               messages: List[Dict[str, str]], 
                               model: Optional[str] = None,
                               temperature: float = 0.7,
                               max_tokens: int = 1000) -> Optional[str]:
        """Generate a chat completion using Ollama."""
        try:
            model = model or self.ollama_model
            
            # Ollama API endpoint for chat completions
            url = f"{self.ollama_base_url}/api/chat"
            
            # Prepare the request payload
            payload = {
                "model": model,
                "messages": messages,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }
            
            # Make the API request
            response = requests.post(url, json=payload)
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    return result.get("message", {}).get("content", "").strip()
                except json.JSONDecodeError as e:
                    # Handle streaming responses or malformed JSON
                    console.print(f"[yellow]Warning: JSON parsing error: {str(e)}[/yellow]")
                    # Try to extract content from the response text
                    content = response.text
                    # If it's a streaming response, take the first chunk
                    if '\n' in content:
                        content = content.split('\n')[0]
                    try:
                        # Try to parse the first chunk as JSON
                        first_chunk = json.loads(content)
                        return first_chunk.get("message", {}).get("content", "").strip()
                    except:
                        console.print("[yellow]Warning: Could not parse response as JSON. Using text response.[/yellow]")
                        return content
            else:
                console.print(f"[red]Ollama API error: {response.status_code} {response.text}[/red]")
                return None
        except Exception as e:
            console.print(f"[red]Ollama API error: {str(e)}[/red]")
            return None
            
    def _transformers_chat_completion(self, 
                                    messages: List[Dict[str, str]], 
                                    model: Optional[str] = None,
                                    temperature: float = 0.7,
                                    max_tokens: int = 1000) -> Optional[str]:
        """Generate a chat completion using the Transformers provider."""
        try:
            # Delegate to the TransformersProvider
            return self.transformers_provider.chat_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            )
        except Exception as e:
            console.print(f"[red]Transformers API error: {str(e)}[/red]")
            return None
            
    def _transformers_structured_generation(self,
                                          system_prompt: str,
                                          user_prompt: str,
                                          model: Optional[str] = None,
                                          temperature: float = 0.7,
                                          max_tokens: int = 1000) -> Optional[Dict[str, Any]]:
        """Generate structured JSON using the Transformers provider."""
        try:
            # Delegate to the TransformersProvider
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response_text = self.transformers_provider.chat_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Process the response text to extract JSON
            if not response_text:
                return None
                
            # Try to extract JSON from the response
            try:
                # First, try to parse the entire response as JSON
                return json.loads(response_text)
            except json.JSONDecodeError:
                # If that fails, try to extract JSON from markdown code blocks
                import re
                json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
                if json_match:
                    try:
                        return json.loads(json_match.group(1))
                    except json.JSONDecodeError:
                        console.print("[red]Error: Could not parse JSON from code block[/red]")
                
                # If all else fails, try to find anything that looks like JSON
                json_match = re.search(r'(\{[\s\S]*\})', response_text)
                if json_match:
                    try:
                        return json.loads(json_match.group(1))
                    except json.JSONDecodeError:
                        console.print("[red]Error: Could not parse JSON from response[/red]")
                
                # Try more aggressive cleaning
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}')
                
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    cleaned_text = response_text[start_idx:end_idx+1]
                    try:
                        return json.loads(cleaned_text)
                    except json.JSONDecodeError:
                        # Try more aggressive cleaning
                        cleaned_text = re.sub(r'[^{}\[\]:,"0-9a-zA-Z_.-]', ' ', cleaned_text)
                        try:
                            return json.loads(cleaned_text)
                        except json.JSONDecodeError:
                            pass
            
            console.print("[red]Error: Transformers response does not contain valid JSON[/red]")
            console.print(f"[yellow]Response: {response_text}[/yellow]")
            return None
        except Exception as e:
            console.print(f"[red]Transformers structured generation error: {str(e)}[/red]")
            return None
    
    def structured_generation(self, 
                              system_prompt: str,
                              user_prompt: str,
                              model: Optional[str] = None,
                              temperature: float = 0.7,
                              max_tokens: int = 1000) -> Optional[Dict[str, Any]]:
        """
        Generate structured JSON output using the configured LLM provider.
        
        Args:
            system_prompt: System prompt to guide the model
            user_prompt: User prompt with the specific request
            model: Model to use (optional, falls back to default if not specified)
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate
            
        Returns:
            Parsed JSON object or None if an error occurred
        """
        # For Ollama or Transformers, add explicit instructions to return only JSON
        if self.provider_type in ["ollama", "transformers"]:
            # Special handling for DeepSeek Coder model which is good at code generation
            if (self.provider_type == "ollama" and "deepseek" in self.ollama_model.lower()) or \
               (self.provider_type == "transformers" and "deepseek" in self.transformers_model.lower()):
                system_prompt = "You are a JSON generation assistant. You MUST ONLY output valid JSON with no other text."
                user_prompt = f"Generate a JSON object with the following structure for a {user_prompt}\nDo not include any explanations, just the JSON."
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Use the appropriate method based on provider type
        if self.provider_type == "transformers":
            return self._transformers_structured_generation(system_prompt, user_prompt, model, temperature, max_tokens)
        else:
            response_text = self.chat_completion(messages, model, temperature, max_tokens)
        
        if not response_text:
            return None
        
        # Try to extract JSON from the response
        try:
            # First, try to parse the entire response as JSON
            return json.loads(response_text)
        except json.JSONDecodeError:
            # If that fails, try to extract JSON from markdown code blocks
            import re
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    console.print("[red]Error: Could not parse JSON from code block[/red]")
            
            # If all else fails, try to find anything that looks like JSON
            json_match = re.search(r'(\{[\s\S]*\})', response_text)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    console.print("[red]Error: Could not parse JSON from response[/red]")
            
            # For Ollama or Transformers, try a more aggressive approach to extract JSON
            if self.provider_type in ["ollama", "transformers"]:
                # Try to extract JSON from code blocks first (common with DeepSeek Coder)
                code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
                if code_block_match:
                    try:
                        return json.loads(code_block_match.group(1))
                    except json.JSONDecodeError:
                        pass
                
                # Try to clean up the response by removing any non-JSON text
                # First, find the first { and last }
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}')
                
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    cleaned_text = response_text[start_idx:end_idx+1]
                    try:
                        return json.loads(cleaned_text)
                    except json.JSONDecodeError:
                        # Try more aggressive cleaning
                        cleaned_text = re.sub(r'[^{}\[\]:,"0-9a-zA-Z_.-]', ' ', cleaned_text)
                        try:
                            return json.loads(cleaned_text)
                        except json.JSONDecodeError:
                            pass
                
                # If we still can't parse it, create a fallback structure
                console.print("[yellow]Warning: Creating fallback JSON structure from Ollama response[/yellow]")
                if "days" in user_prompt.lower() or "meal plan" in user_prompt.lower():
                    # This is likely a meal plan request
                    return self._create_fallback_meal_plan(response_text)
            
            console.print("[red]Error: Response does not contain valid JSON[/red]")
            console.print(f"[yellow]Response: {response_text}[/yellow]")
            return None
    
    def _create_fallback_meal_plan(self, response_text: str) -> Dict[str, Any]:
        """Create a fallback meal plan structure when JSON parsing fails."""
        import re
        
        # Default to 3 days if we can't determine the number
        num_days = 3
        
        # Try to extract the number of days from the response
        day_match = re.search(r'(\d+)[-\s]day meal plan', response_text, re.IGNORECASE)
        if day_match:
            num_days = int(day_match.group(1))
        
        # Initialize the meal plan structure
        meal_plan = {
            "days": []
        }
        
        # Look for day patterns in the text
        day_patterns = [
            r'Day (\d+)[:\s]+(.*?)(?=Day \d+:|$)',  # Day 1: Meal name
            r'(\d+)\. (.*?)(?=\d+\.|$)',            # 1. Meal name
            r'(\w+day)[:\s]+(.*?)(?=\w+day:|$)'     # Monday: Meal name
        ]
        
        days_found = False
        
        # Try each pattern to extract days and meals
        for pattern in day_patterns:
            matches = re.findall(pattern, response_text, re.DOTALL)
            if matches:
                days_found = True
                for day_num, content in matches[:num_days]:
                    # Extract meal name and description
                    meal_name = content.strip().split('\n')[0].strip()
                    description = ""
                    if '\n' in content:
                        description = ' '.join([line.strip() for line in content.split('\n')[1:] if line.strip()])
                    
                    # Check if it contains oily fish
                    contains_oily_fish = any(fish in content.lower() for fish in 
                                           ['salmon', 'mackerel', 'sardines', 'trout', 'herring', 'tuna'])
                    
                    meal_plan["days"].append({
                        "day": f"Day {day_num}",
                        "meal": meal_name,
                        "description": description[:100],  # Limit description length
                        "contains_oily_fish": contains_oily_fish
                    })
                break  # Stop after finding matches with the first successful pattern
        
        # If no days were found with the patterns, create a basic structure
        if not days_found:
            # Split the text into chunks and use them as meals
            chunks = re.split(r'\n\n+', response_text)
            for i in range(min(num_days, len(chunks))):
                chunk = chunks[i].strip()
                lines = chunk.split('\n')
                
                # Use the first line as the meal name
                meal_name = lines[0].strip()
                if len(meal_name) > 50:  # If it's too long, it's probably not a meal name
                    meal_name = f"Meal for Day {i+1}"
                
                # Join the rest as the description
                description = ' '.join(lines[1:]) if len(lines) > 1 else ""
                
                # Check if it contains oily fish
                contains_oily_fish = any(fish in chunk.lower() for fish in 
                                       ['salmon', 'mackerel', 'sardines', 'trout', 'herring', 'tuna'])
                
                meal_plan["days"].append({
                    "day": f"Day {i+1}",
                    "meal": meal_name,
                    "description": description[:100],  # Limit description length
                    "contains_oily_fish": contains_oily_fish
                })
        
        # If we still don't have any days, create dummy entries
        if not meal_plan["days"]:
            for i in range(num_days):
                meal_plan["days"].append({
                    "day": f"Day {i+1}",
                    "meal": f"Meal for Day {i+1}",
                    "description": "Generated from Ollama response",
                    "contains_oily_fish": i == 1  # Include oily fish on day 2
                })
        
        console.print(f"[yellow]Created fallback meal plan with {len(meal_plan['days'])} days[/yellow]")
        return meal_plan
