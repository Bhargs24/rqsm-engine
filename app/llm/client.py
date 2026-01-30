"""
LLM Client with Multiple Provider Support
Supports: Hugging Face (FREE), Ollama (FREE), Gemini (FREE), OpenAI (PAID)
"""
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
import requests
from loguru import logger

from app.config import settings


class LLMProvider(ABC):
    """Base class for LLM providers"""
    
    @abstractmethod
    def generate(self, prompt: str, temperature: float = 0.0, max_tokens: int = 500) -> str:
        """Generate text from prompt"""
        pass


class HuggingFaceLLM(LLMProvider):
    """
    Hugging Face Inference API Provider (FREE)
    Get API key: https://huggingface.co/settings/tokens
    """
    
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.api_url = f"https://api-inference.huggingface.co/models/{model}"
        logger.info(f"Initialized Hugging Face LLM: {model}")
    
    def generate(self, prompt: str, temperature: float = 0.0, max_tokens: int = 500) -> str:
        """Generate text using Hugging Face Inference API"""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "temperature": temperature,
                "max_new_tokens": max_tokens,
                "return_full_text": False,
                "do_sample": temperature > 0,
            }
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            # Handle different response formats
            if isinstance(result, list) and len(result) > 0:
                return result[0].get("generated_text", "")
            elif isinstance(result, dict):
                return result.get("generated_text", "")
            
            logger.warning(f"Unexpected response format: {result}")
            return ""
            
        except Exception as e:
            logger.error(f"Hugging Face API error: {e}")
            raise


class OllamaLLM(LLMProvider):
    """
    Ollama Provider (FREE - runs locally)
    Install: https://ollama.ai/
    """
    
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip('/')
        self.model = model
        logger.info(f"Initialized Ollama LLM: {model} at {base_url}")
    
    def generate(self, prompt: str, temperature: float = 0.0, max_tokens: int = 500) -> str:
        """Generate text using Ollama"""
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        
        try:
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "")
            
        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to Ollama at {self.base_url}. Is Ollama running?")
            raise
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            raise


class GeminiLLM(LLMProvider):
    """
    Google Gemini Provider (FREE tier - 1,500 requests/day)
    Get API key: https://makersuite.google.com/app/apikey
    """
    
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        
        # Import here to make it optional
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(model)
            logger.info(f"Initialized Google Gemini LLM: {model}")
        except ImportError:
            logger.error("google-generativeai not installed. Run: pip install google-generativeai")
            raise
    
    def generate(self, prompt: str, temperature: float = 0.0, max_tokens: int = 500) -> str:
        """Generate text using Google Gemini"""
        try:
            generation_config = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }
            
            response = self.client.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise


class OpenAILLM(LLMProvider):
    """
    OpenAI Provider (PAID)
    Only use if you have credits
    """
    
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key)
            logger.info(f"Initialized OpenAI LLM: {model}")
        except ImportError:
            logger.error("openai not installed. Run: pip install openai")
            raise
    
    def generate(self, prompt: str, temperature: float = 0.0, max_tokens: int = 500) -> str:
        """Generate text using OpenAI"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise


class LLMClient:
    """
    Universal LLM Client
    Automatically selects provider based on configuration
    """
    
    def __init__(self):
        """Initialize LLM client based on configured provider"""
        provider = settings.llm_provider.lower()
        
        logger.info(f"Initializing LLM client with provider: {provider}")
        
        if provider == "huggingface":
            if not settings.huggingface_api_key:
                raise ValueError("HUGGINGFACE_API_KEY not set in .env file")
            self.provider = HuggingFaceLLM(
                api_key=settings.huggingface_api_key,
                model=settings.huggingface_model
            )
        
        elif provider == "ollama":
            self.provider = OllamaLLM(
                base_url=settings.ollama_base_url,
                model=settings.ollama_model
            )
        
        elif provider == "gemini":
            if not settings.gemini_api_key:
                raise ValueError("GEMINI_API_KEY not set in .env file")
            self.provider = GeminiLLM(
                api_key=settings.gemini_api_key,
                model=settings.gemini_model
            )
        
        elif provider == "openai":
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY not set in .env file")
            self.provider = OpenAILLM(
                api_key=settings.openai_api_key,
                model=settings.openai_model
            )
        
        else:
            raise ValueError(
                f"Unknown LLM provider: {provider}. "
                f"Must be one of: huggingface, ollama, gemini, openai"
            )
        
        logger.info(f"LLM client initialized successfully with {provider}")
    
    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate text from prompt.
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature (default from config)
            max_tokens: Maximum tokens to generate (default from config)
            
        Returns:
            Generated text
        """
        temp = temperature if temperature is not None else settings.llm_temperature
        tokens = max_tokens if max_tokens is not None else settings.llm_max_tokens
        
        logger.debug(f"Generating with temp={temp}, max_tokens={tokens}")
        
        response = self.provider.generate(prompt, temperature=temp, max_tokens=tokens)
        
        logger.debug(f"Generated {len(response)} characters")
        
        return response
    
    def generate_role_response(
        self,
        role_name: str,
        role_prompt: str,
        context: str,
        user_input: Optional[str] = None
    ) -> str:
        """
        Generate role-based response.
        
        Args:
            role_name: Name of the role (e.g., "Explainer")
            role_prompt: Role-specific system prompt
            context: Document context
            user_input: Optional user question/input
            
        Returns:
            Role-based response
        """
        # Build full prompt
        full_prompt = f"""{role_prompt}

Context:
{context}
"""
        
        if user_input:
            full_prompt += f"\n\nUser: {user_input}\n\n{role_name}:"
        else:
            full_prompt += f"\n\n{role_name}:"
        
        logger.info(f"Generating response for role: {role_name}")
        
        return self.generate(full_prompt)
