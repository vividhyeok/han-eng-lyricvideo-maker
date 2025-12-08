import google.generativeai as genai

# Configure the API key
genai.configure(api_key="gen-lang-client-0890576080")

# List available models
print("Available models:")
for model in genai.list_models():
    print(model.name)

# Create a model instance with a supported model
try:
    model = genai.GenerativeModel("gemini-2.5-flash")
    # Generate content
    response = model.generate_content("Hello, how are you?")
    # Print the response
    print("Response from GEMINI:")
    print(response.text)
except Exception as e:
    print(f"Error: {e}")