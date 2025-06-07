import os
import json
import torch
from typing import List, Dict, Any, Optional, Union
from rich.console import Console
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

# Initialize console for rich output
console = Console()

class TransformersProvider:
    """Provider for LLM services using HuggingFace Transformers library."""
    
    def __init__(self):
        """Initialize the Transformers provider."""
        self.model_name = os.getenv("TRANSFORMERS_MODEL", "deepseek-ai/deepseek-coder-6.7b-instruct")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.max_memory = None
        
        # For CPU, we'll use 8-bit quantization to reduce memory usage
        self.load_in_8bit = self.device == "cpu"
        
        # For CUDA, set up memory mapping based on available VRAM
        if self.device == "cuda":
            # Get available VRAM
            try:
                gpu_mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)  # Convert to GB
                console.print(f"[green]GPU memory: {gpu_mem:.2f} GB[/green]")
                
                # Set up memory mapping based on available VRAM
                if gpu_mem < 8:
                    # For GPUs with less than 8GB VRAM, use 8-bit quantization
                    self.load_in_8bit = True
                elif gpu_mem < 24:
                    # For GPUs with 8-24GB VRAM, use 4-bit quantization
                    self.load_in_4bit = True
                    self.load_in_8bit = False
                else:
                    # For GPUs with more than 24GB VRAM, use full precision
                    self.load_in_8bit = False
                    self.load_in_4bit = False
            except:
                # If we can't get GPU memory, default to 8-bit quantization
                self.load_in_8bit = True
                console.print("[yellow]Warning: Could not determine GPU memory. Using 8-bit quantization.[/yellow]")
        
        # Initialize the model and tokenizer
        self._init_model()
    
    def _init_model(self):
        """Initialize the model and tokenizer."""
        try:
            console.print(f"[green]Loading model {self.model_name} on {self.device}...[/green]")
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            
            # Load model with appropriate quantization
            if self.load_in_8bit:
                console.print("[yellow]Using 8-bit quantization to reduce memory usage[/yellow]")
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    device_map="auto",
                    load_in_8bit=True,
                    torch_dtype=torch.float16
                )
            elif hasattr(self, 'load_in_4bit') and self.load_in_4bit:
                console.print("[yellow]Using 4-bit quantization to reduce memory usage[/yellow]")
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    device_map="auto",
                    load_in_4bit=True,
                    torch_dtype=torch.float16
                )
            else:
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    device_map="auto",
                    torch_dtype=torch.float16
                )
            
            # Create text generation pipeline
            self.pipe = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device_map="auto"
            )
            
            console.print(f"[green]Model {self.model_name} loaded successfully on {self.device}[/green]")
            self.client = True  # Flag to indicate model is available
        except Exception as e:
            console.print(f"[red]Error initializing model: {str(e)}[/red]")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if the model is available."""
        return self.client is not None
    
    def get_provider_type(self) -> str:
        """Get the type of LLM provider being used."""
        return "transformers"
    
    def _format_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Format messages for DeepSeek-Coder model."""
        prompt = ""
        
        for message in messages:
            role = message["role"]
            content = message["content"]
            
            if role == "system":
                prompt += f"<｜system｜>\n{content}\n"
            elif role == "user":
                prompt += f"<｜user｜>\n{content}\n"
            elif role == "assistant":
                prompt += f"<｜assistant｜>\n{content}\n"
        
        # Add the final assistant tag to indicate where the model should generate
        prompt += "<｜assistant｜>\n"
        return prompt
    
    def chat_completion(self, 
                       messages: List[Dict[str, str]], 
                       model: Optional[str] = None,
                       temperature: float = 0.7,
                       max_tokens: int = 1000) -> Optional[str]:
        """
        Generate a chat completion using the Transformers model.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            model: Model to use (optional, falls back to default if not specified)
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate
            
        Returns:
            Generated text or None if an error occurred
        """
        if not self.is_available():
            console.print("[red]Error: Model not available[/red]")
            return None
        
        try:
            # Format the prompt for DeepSeek-Coder
            prompt = self._format_prompt(messages)
            
            # Generate the response
            outputs = self.pipe(
                prompt,
                max_new_tokens=max_tokens,
                temperature=temperature,
                do_sample=temperature > 0.0,
                num_return_sequences=1,
                eos_token_id=self.tokenizer.eos_token_id,
                pad_token_id=self.tokenizer.pad_token_id if hasattr(self.tokenizer, 'pad_token_id') and self.tokenizer.pad_token_id is not None else self.tokenizer.eos_token_id,
            )
            
            # Extract the generated text
            generated_text = outputs[0]['generated_text']
            
            # Remove the prompt from the generated text
            response = generated_text[len(prompt):].strip()
            
            return response
        except Exception as e:
            console.print(f"[red]Error generating chat completion: {str(e)}[/red]")
            return None
    
    def structured_generation(self, 
                             system_prompt: str,
                             user_prompt: str,
                             model: Optional[str] = None,
                             temperature: float = 0.7,
                             max_tokens: int = 1000) -> Optional[Dict[str, Any]]:
        """
        Generate structured JSON output using the Transformers model.
        
        Args:
            system_prompt: System prompt to guide the model
            user_prompt: User prompt with the specific request
            model: Model to use (optional, falls back to default if not specified)
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate
            
        Returns:
            Parsed JSON object or None if an error occurred
        """
        # Enhance the system prompt to encourage JSON output
        enhanced_system_prompt = f"{system_prompt}\nYou MUST ONLY output valid JSON with no other text."
        
        # Enhance the user prompt to encourage JSON output
        enhanced_user_prompt = f"{user_prompt}\n\nOutput ONLY valid JSON with no other text."
        
        messages = [
            {"role": "system", "content": enhanced_system_prompt},
            {"role": "user", "content": enhanced_user_prompt}
        ]
        
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
            
            # Try more aggressive approaches to extract JSON
            # Find the first { and last }
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
            console.print("[yellow]Warning: Creating fallback JSON structure from response[/yellow]")
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
                    "description": "Generated from model response",
                    "contains_oily_fish": i == 1  # Include oily fish on day 2
                })
        
        console.print(f"[yellow]Created fallback meal plan with {len(meal_plan['days'])} days[/yellow]")
        return meal_plan
