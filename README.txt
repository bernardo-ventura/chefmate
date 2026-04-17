Google API studio: https://aistudio.google.com/app/api-keys

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt

# Terminal 1
python mcp_server.py

# Terminal 2
python langchain_agent.py

# Then open index.html in your browser