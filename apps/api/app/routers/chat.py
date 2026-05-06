"""
Chat Router - Handles LLM conversation with tool calling and streaming
"""
import json
from typing import AsyncGenerator
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from openai import AsyncOpenAI

from app.database import get_db, get_redis
from app.config import settings
from app.schemas.chat import ChatRequest
from app.schemas.place import PlaceCard, NearbyPlacesRequest, PlaceDetail
from app.schemas.dish import DishCard, NearbyDishesRequest
from app.services.llm_tools import TOOLS, SYSTEM_PROMPT
from app.services.free_chat import (
    detect_intent, generate_text_response,
    should_search_places, should_search_dishes, build_search_args
)
from app.services.session import SessionService
from app.routers.places import search_nearby_places, get_place_detail
from app.routers.dishes import get_nearby_dishes

router = APIRouter(prefix="/api/chat", tags=["chat"])


async def execute_tool_call(
    tool_name: str,
    arguments: dict,
    db: AsyncSession
) -> tuple[str, dict]:
    """
    Execute a tool call and return (result_type, data)
    result_type: 'places' | 'dishes' | 'place_detail'
    """
    if tool_name == "search_nearby_places":
        # Convert arguments to NearbyPlacesRequest
        req = NearbyPlacesRequest(
            lat=arguments["lat"],
            lng=arguments["lng"],
            radius_m=arguments.get("radius_m", 500),
            dish_name=arguments.get("dish_name"),
            vegetarian=arguments.get("vegetarian", False),
            halal=arguments.get("halal", False),
            price_max_per_person=arguments.get("price_max_per_person"),
            people_count=arguments.get("people_count", 1),
            limit=arguments.get("limit", 5)
        )
        places = await search_nearby_places(req, db)
        places_data = [PlaceCard.model_validate(p).model_dump() for p in places]
        return "places", {"places": places_data, "count": len(places_data)}

    elif tool_name == "search_nearby_dishes":
        # Convert arguments to NearbyDishesRequest
        req = NearbyDishesRequest(
            lat=arguments["lat"],
            lng=arguments["lng"],
            radius_m=arguments.get("radius_m", 500),
            limit=arguments.get("limit", 12)
        )
        response = await get_nearby_dishes(req, db)
        dishes_data = [d.model_dump() for d in response.dishes]
        return "dishes", {"dishes": dishes_data, "count": len(dishes_data)}

    elif tool_name == "get_place_detail":
        # Get place detail
        place_id = arguments["place_id"]
        lat = arguments.get("lat")
        lng = arguments.get("lng")
        
        place_detail = await get_place_detail(place_id, lat, lng, db)
        return "place_detail", {"place": place_detail.model_dump()}

    else:
        return "error", {"message": f"Unknown tool: {tool_name}"}


@router.post("/stream")
async def chat_stream(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """
    Stream chat responses with LLM tool calling and session management

    Returns Server-Sent Events (SSE) with the following event types:
    - type: 'session_id' - Session ID for client to store
    - type: 'text' - Streaming text content from LLM
    - type: 'places' - List of place cards
    - type: 'dishes' - List of dish cards
    - type: 'place_detail' - Detailed place information
    - type: 'done' - End of stream
    """

    async def generate() -> AsyncGenerator[str, None]:
        try:
            # Step 1: Get or create session
            session_service = SessionService(redis)
            session = await session_service.get_or_create(req.session_id)
            
            # Send session_id to client
            yield f"data: {json.dumps({'type': 'session_id', 'session_id': session.session_id})}\n\n"
            
            # Step 2: Update session with location if provided
            if req.lat and req.lng:
                session.lat = req.lat
                session.lng = req.lng
                await session_service.save(session)
            
            # Step 3: Extract context from user message and update session
            if req.messages and req.messages[-1].role == "user":
                user_msg = req.messages[-1].content
                if isinstance(user_msg, str):
                    session = await session_service.update_context_from_message(
                        session.session_id, 
                        user_msg
                    )
            
            # Step 4: Build enriched context message
            context_parts = []
            if session.lat and session.lng:
                context_parts.append(f"Vị trí: lat={session.lat}, lng={session.lng}")
            if session.budget_per_person:
                context_parts.append(f"Budget: {session.budget_per_person:,}đ/người")
            if session.people_count > 1:
                context_parts.append(f"Số người: {session.people_count}")
            if session.vegetarian:
                context_parts.append("Ăn chay")
            if session.halal:
                context_parts.append("Halal")
            if session.recommended_place_ids:
                context_parts.append(f"Đã recommend: {len(session.recommended_place_ids)} quán")
            
            context_msg = "[Context: " + ", ".join(context_parts) + "]" if context_parts else ""
            
            # Get user message text
            user_text = ""
            if req.messages and req.messages[-1].role == "user":
                user_text = req.messages[-1].content if isinstance(req.messages[-1].content, str) else ""

            # === FREE MODE: Rule-based when no OpenAI API key ===
            if not settings.OPENAI_API_KEY:
                # Save user message first
                await session_service.add_message(session.session_id, "user", user_text)
                
                # Build session context for intent detection
                session_ctx = {
                    "budget_per_person": session.budget_per_person,
                    "people_count": session.people_count,
                    "vegetarian": session.vegetarian,
                    "halal": session.halal,
                }
                
                # Detect intent with session context
                intent = detect_intent(user_text, session_context=session_ctx)
                
                # Generate context-aware response
                text_response = generate_text_response(intent, session_context=session_ctx)

                # Stream text response
                yield f"data: {json.dumps({'type': 'text', 'content': text_response})}\n\n"

                # Try to search places/dishes from DB if intent requires it
                try:
                    if should_search_places(intent) and (req.lat or session.lat):
                        args = build_search_args(intent, req.lat or session.lat, req.lng or session.lng)
                        result_type, result_data = await execute_tool_call("search_nearby_places", args, db)
                        if result_data.get("places"):
                            yield f"data: {json.dumps({'type': 'places', 'data': result_data['places']})}\n\n"
                    elif should_search_dishes(intent) and (req.lat or session.lat):
                        args = build_search_args(intent, req.lat or session.lat, req.lng or session.lng)
                        result_type, result_data = await execute_tool_call("search_nearby_dishes", args, db)
                        if result_data.get("dishes"):
                            yield f"data: {json.dumps({'type': 'dishes', 'data': result_data['dishes']})}\n\n"
                except Exception as e:
                    print(f"[FREE_CHAT] DB search error (non-fatal): {e}")

                # Save assistant response after generation
                await session_service.add_message(session.session_id, "assistant", text_response)

                yield "data: [DONE]\n\n"
                return

            # === PAID MODE: OpenAI with tool calling ===
            # Step 5: Build messages for OpenAI using session history
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            
            if context_msg:
                messages.append({"role": "user", "content": context_msg})
                messages.append({"role": "assistant", "content": "Đã ghi nhận."})
            
            # Add session message history (last 20 messages)
            messages.extend(session.messages)
            
            # Add new messages from request
            for msg in req.messages:
                messages.append({
                    "role": msg.role,
                    "content": msg.content if isinstance(msg.content, str) else json.dumps(msg.content)
                })
            
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                stream=True,
                max_tokens=1000
            )
            
            full_content = ""
            tool_calls_accumulated = {}
            
            async for chunk in response:
                delta = chunk.choices[0].delta
                
                if delta.content:
                    full_content += delta.content
                    yield f"data: {json.dumps({'type': 'text', 'content': delta.content})}\n\n"
                
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_accumulated:
                            tool_calls_accumulated[idx] = {
                                "id": tc.id or "",
                                "type": "function",
                                "function": {
                                    "name": tc.function.name or "",
                                    "arguments": ""
                                }
                            }
                        if tc.function.name:
                            tool_calls_accumulated[idx]["function"]["name"] = tc.function.name
                        if tc.function.arguments:
                            tool_calls_accumulated[idx]["function"]["arguments"] += tc.function.arguments
                        if tc.id:
                            tool_calls_accumulated[idx]["id"] = tc.id
            
            if tool_calls_accumulated:
                tool_calls_list = [tool_calls_accumulated[i] for i in sorted(tool_calls_accumulated.keys())]
                tool_results = []
                
                for tc in tool_calls_list:
                    try:
                        fn_name = tc["function"]["name"]
                        args = json.loads(tc["function"]["arguments"])
                        result_type, result_data = await execute_tool_call(fn_name, args, db)
                        
                        if result_type == "places":
                            yield f"data: {json.dumps({'type': 'places', 'data': result_data['places']})}\n\n"
                            tool_results.append({"tool_call_id": tc["id"], "role": "tool", "content": json.dumps({"count": result_data["count"]})})
                        elif result_type == "dishes":
                            yield f"data: {json.dumps({'type': 'dishes', 'data': result_data['dishes']})}\n\n"
                            tool_results.append({"tool_call_id": tc["id"], "role": "tool", "content": json.dumps({"count": result_data["count"]})})
                        elif result_type == "place_detail":
                            yield f"data: {json.dumps({'type': 'place_detail', 'data': result_data['place']})}\n\n"
                            tool_results.append({"tool_call_id": tc["id"], "role": "tool", "content": "Place detail fetched"})
                        else:
                            tool_results.append({"tool_call_id": tc["id"], "role": "tool", "content": json.dumps(result_data)})
                    except Exception as e:
                        tool_results.append({"tool_call_id": tc["id"], "role": "tool", "content": json.dumps({"error": str(e)})})
                
                follow_up_messages = messages + [{"role": "assistant", "content": full_content or None, "tool_calls": tool_calls_list}] + tool_results
                follow_up_response = await client.chat.completions.create(model="gpt-4o-mini", messages=follow_up_messages, stream=True, max_tokens=500)
                
                final_response = ""
                async for chunk in follow_up_response:
                    if chunk.choices[0].delta.content:
                        final_response += chunk.choices[0].delta.content
                        yield f"data: {json.dumps({'type': 'text', 'content': chunk.choices[0].delta.content})}\n\n"
                
                if final_response:
                    await session_service.add_message(session.session_id, "assistant", final_response)
            else:
                if full_content:
                    await session_service.add_message(session.session_id, "assistant", full_content)
            
            # Save user message
            if req.messages and req.messages[-1].role == "user":
                user_content = req.messages[-1].content
                await session_service.add_message(session.session_id, "user", user_content if isinstance(user_content, str) else json.dumps(user_content))

            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )


@router.post("/session/new")
async def create_session(redis: Redis = Depends(get_redis)):
    """Create a new chat session"""
    session_service = SessionService(redis)
    session = await session_service.get_or_create(None)
    return {"session_id": session.session_id}


@router.get("/session/{session_id}/history")
async def get_session_history(session_id: str, redis: Redis = Depends(get_redis)):
    """Get chat history for a session"""
    session_service = SessionService(redis)
    session = await session_service.get(session_id)
    
    if not session:
        return {"error": "Session not found"}, 404
    
    return {
        "session_id": session.session_id,
        "messages": session.messages,
        "context": {
            "lat": session.lat,
            "lng": session.lng,
            "budget_per_person": session.budget_per_person,
            "people_count": session.people_count,
            "vegetarian": session.vegetarian,
            "halal": session.halal,
            "recommended_place_ids": session.recommended_place_ids
        },
        "created_at": session.created_at,
        "updated_at": session.updated_at
    }


@router.delete("/session/{session_id}")
async def delete_session(session_id: str, redis: Redis = Depends(get_redis)):
    """Delete a chat session"""
    session_service = SessionService(redis)
    await session_service.delete(session_id)
    return {"message": "Session deleted successfully"}
