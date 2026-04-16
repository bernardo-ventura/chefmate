import os
import uuid
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# LangChain & LangGraph
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

# MCP Adapters
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession
from langchain_mcp_adapters.tools import load_mcp_tools
from contextlib import asynccontextmanager


import traceback

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("A variável GOOGLE_API_KEY não está definida no .env")

# ── LLM ───────────────────────────────────────────────────────────────────────
llm = ChatGoogleGenerativeAI(model="models/gemini-flash-lite-latest", google_api_key=GOOGLE_API_KEY) # Modelo lite latest

# ── MEMORY (persists across requests for the same thread_id) ──────────────────
memory = MemorySaver()
thread_config = {"configurable": {"thread_id": str(uuid.uuid4())}}


class ChatRequest(BaseModel):
    message: str


def extract_text(content) -> str:
    """Safely extract a plain string from an AI message's content field.
    content can be:
      - a plain string  →  return as-is
      - a list of dicts →  join the text blocks 
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [
            block["text"]
            for block in content
            if isinstance(block, dict) and block.get("type") == "text" and block.get("text")
        ]
        return " ".join(parts)
    return str(content)

agent = None
system_prompt = ""  # Global para armazenar o system prompt

@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent, system_prompt
    url = "http://127.0.0.1:8002/sse"

    # NÃO fecha a sessão — fica aberta até ao shutdown
    async with sse_client(url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            prompt_data = await session.get_prompt(
                "meal_planner_assistant", arguments={"user_name": "Visitante"}
            )
            system_instruction = prompt_data.messages[0].content.text

            # ── Resources ✅ lidos aqui pelo cliente, injetados no system prompt ──
            # Lê o guia nutricional (mais útil para o LLM)
            nutrition_guide = await session.read_resource("meal://nutrition-guide")
            nutrition_text = nutrition_guide.contents[0].text
            print(f"\n📖 RESOURCE LIDO [meal://nutrition-guide]:\n{nutrition_text[:200]}...")
            
            # Lê o schema do banco de dados
            db_schema = await session.read_resource("meal://db-schema")
            schema_text = db_schema.contents[0].text
            print(f"\n📖 RESOURCE LIDO [meal://db-schema]:\n{schema_text[:200]}...")
            
            resource_text = f"\n=== DATABASE SCHEMA ===\n{schema_text}\n\n=== NUTRITION GUIDE ===\n{nutrition_text}"
            system_prompt = system_instruction + f"\n\nServer context:\n{resource_text}"


            tools = await load_mcp_tools(session)
            print("\n=== TOOLS CARREGADAS ===", len(tools), "tools")

            # Criar o agent SEM system prompt (vamos passar no chat)
            agent = create_react_agent(
                llm,
                tools,
                checkpointer=memory
            )
            print("✅ Agente inicializado com sucesso.")

            yield  # ← app corre DENTRO dos async with, sessão mantém-se aberta

    print("🛑 A encerrar o servidor.")

app = FastAPI(title="ChefMate - Meal Planner Agent API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/chat")
async def chat(req: ChatRequest):
    if agent is None:
        raise HTTPException(status_code=503, detail="Agente ainda não inicializado.")
    try:
        inputs = {"messages": [HumanMessage(content=req.message)]}
        final_response = ""

        async for event in agent.astream(
            inputs, config=thread_config, stream_mode="values"
        ):
            msg = event["messages"][-1]
            print(f"\n📨 Message type: {msg.type}, content type: {type(msg.content)}")

            if msg.type == "ai" and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    print(f"\n🔧 TOOL CALL: {tool_call['name']}")
                    print(f"   Args: {tool_call['args']}")
            elif msg.type == "tool":
                print(f"\n✅ TOOL RESULT [{msg.name}]: {msg.content}")
            elif msg.type == "ai" and msg.content:
                final_response = extract_text(msg.content)
                print(f"\n💬 AI RESPONSE: {final_response}")
        
        print(f"\n🎯 Final response being sent: '{final_response}'")
        return {"reply": final_response}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Erro interno. Verifica o terminal.")


@app.post("/reset")
async def reset():
    """Generate a new thread_id — effectively clears conversation history."""
    global thread_config
    thread_config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    return {"status": "Histórico limpo com sucesso"}


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)