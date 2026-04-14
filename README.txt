Google API studio: https://aistudio.google.com/app/api-keys

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt

# Terminal 1
python mcp_server.py

# Terminal 2
export GEMINI_API_KEY=your-key
python gemini_agent.py

# Then open webapp.html in your browser


pip install -U langgraph langchain langchain-google-genai


curl -X POST http://localhost:8000/reset

curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, how are you?"}'

curl -X POST "http://127.0.0.1:8000/chat" -H "Content-Type: application/json" -d '{"message":"Olá! Podes calcular o meu IMC? Peso 70kg e tenho 1.75m."}'