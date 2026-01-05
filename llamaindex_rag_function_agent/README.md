# RAG Golf Agent

An intelligent RAG (Retrieval-Augmented Generation) agent powered by LlamaIndex, designed to assist users with golf-related queries, course information, scorecards, tee details, and application support.

## Features

- **Golf Course Search**: Find and get detailed information about golf courses worldwide
- **Scorecard Information**: Retrieve hole-by-hole par, handicap, and rating data
- **Tee Details**: Access yardages, course ratings, and slope ratings for all tee colors
- **Application Support**: Get help with GolfGuiders app features and usage
- **Multi-turn Conversations**: Maintains context across conversation turns
- **Streaming Responses**: Real-time token streaming for better UX
- **Persistent Chat History**: Conversations saved in Supabase for continuity

## Capabilities

The agent uses 4 specialized tools to answer queries:

1. **`search_golf_courses`**: Searches Pinecone vector database for golf course information

2. **`search_scorecards`**: Queries Cassandra database for scorecard data

3. **`search_tee_details`**: Retrieves tee information from Cassandra

4. **`search_app_manual`**: Searches Pinecone vector database for application documentation

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start FastAPI Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Base URL
```bash
http://localhost:8000
```

### Endpoints

#### 1. Chat Stream (Streaming)

**Method**: `POST`  
**Endpoint**: `/chat/stream`  

**Request Body**:
```json
{
  "message": "string (required) - User's question or message",
  "user_id": "string (required) - Unique user identifier (UUID format)",
  "chat_id": "string (optional) - Existing chat ID to continue conversation"
}
```

**Example Request**:
```bash
curl -X POST "http://localhost:8000/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Tell me about Bellevue Golf Course, WA",
    "user_id": "123e4567-e89b-12d3-a456-426614174000"
  }'
```


## Architecture

- **LLM**: Google Gemini 2.5 Flash/OpenAI GPT-4.1-mini (must support function calling)
- **Agent Type**: FunctionAgent (LlamaIndex)
- **Vector Store**: Pinecone (golf courses, app manual)
- **Database**: Cassandra (scorecards, tee details)
- **Chat History**: Supabase/PostgreSQL
- **Frameworks**: LlamaIndex + FastAPI with streaming support