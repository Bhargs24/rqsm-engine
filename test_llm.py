"""
Test LLM Client with Different Providers
"""
from app.llm.client import LLMClient
from app.config import settings


def test_llm():
    """Test LLM generation"""
    
    print(f"\n{'='*60}")
    print(f"LLM CLIENT TEST")
    print(f"{'='*60}\n")
    
    print(f"Provider: {settings.llm_provider}")
    print(f"Temperature: {settings.llm_temperature}")
    print(f"Max Tokens: {settings.llm_max_tokens}\n")
    
    try:
        # Initialize client
        print("Initializing LLM client...")
        client = LLMClient()
        print("✓ Client initialized\n")
        
        # Test 1: Simple generation
        print("Test 1: Simple Generation")
        print("-" * 40)
        prompt = "Explain what a neural network is in one sentence."
        print(f"Prompt: {prompt}\n")
        
        response = client.generate(prompt)
        print(f"Response: {response}\n")
        
        # Test 2: Role-based generation
        print("\nTest 2: Role-Based Generation")
        print("-" * 40)
        
        role_prompt = "You are an Explainer. Explain concepts clearly and simply."
        context = "Neural networks are computational models inspired by the human brain."
        
        response = client.generate_role_response(
            role_name="Explainer",
            role_prompt=role_prompt,
            context=context,
            user_input="What is a neural network?"
        )
        
        print(f"Role: Explainer")
        print(f"Response: {response}\n")
        
        print(f"{'='*60}")
        print(f"✅ ALL TESTS PASSED")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        print("Troubleshooting:")
        
        if settings.llm_provider == "huggingface":
            print("- Check HUGGINGFACE_API_KEY in .env")
            print("- Get key: https://huggingface.co/settings/tokens")
        
        elif settings.llm_provider == "ollama":
            print("- Make sure Ollama is running: ollama serve")
            print("- Install Ollama: https://ollama.ai/")
            print("- Download model: ollama pull llama2")
        
        elif settings.llm_provider == "gemini":
            print("- Check GEMINI_API_KEY in .env")
            print("- Get key: https://makersuite.google.com/app/apikey")
        
        elif settings.llm_provider == "openai":
            print("- Check OPENAI_API_KEY in .env")
            print("- Note: OpenAI is NOT free")
        
        print(f"\nSee FREE_LLM_SETUP.md for detailed setup instructions\n")


if __name__ == "__main__":
    test_llm()
