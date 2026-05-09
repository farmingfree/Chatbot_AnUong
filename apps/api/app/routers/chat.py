"""
Chat Router - Handles LLM conversation with tool calling and streaming
"""
import json
import logging
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from redis.asyncio import Redis

from app.database import get_db, get_redis
from app.config import settings
from app.schemas.chat import ChatRequest
from app.schemas.place import PlaceCard, NearbyPlacesRequest, PlaceDetail
from app.schemas.dish import DishCard, NearbyDishesRequest
from app.services.llm_tools import TOOLS, build_system_prompt
from app.services.context import (
    compress_place_context, compress_chat_history, build_context_message,
)
from app.services.llm_client import LLMClient, LLMResponse
from app.services.free_chat import (
    detect_intent, generate_text_response,
    should_search_places, should_search_dishes, build_search_args
)
from app.services.session import SessionService
from app.routers.places import search_nearby_places, get_place_detail
from app.routers.dishes import get_nearby_dishes

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


async def execute_tool_call(
    tool_name: str,
    arguments: dict,
    db: AsyncSession,
    app_state=None,
    user_profile: dict | None = None,
) -> tuple[str, dict]:
    """
    Execute a tool call and return (result_type, data)
    result_type: 'places' | 'dishes' | 'place_detail' | 'semantic_places'
    """
    if tool_name == "search_nearby_places":
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

    elif tool_name == "search_places_semantic":
        embedder = getattr(app_state, "embedder", None) if app_state else None
        qdrant = getattr(app_state, "qdrant", None) if app_state else None

        if not embedder or not qdrant:
            logger.warning("RAG not available, falling back to keyword search")
            fallback_args = {
                "lat": arguments["lat"],
                "lng": arguments["lng"],
                "radius_m": arguments.get("radius_m", 2000),
                "limit": arguments.get("limit", 5),
            }
            return await execute_tool_call("search_nearby_places", fallback_args, db, app_state, user_profile=user_profile)

        from app.rag.retriever import hybrid_search
        from app.rag.reranker import rerank
        from app.rag.query_understanding import parse_query

        parsed = parse_query(arguments["query"])

        candidates = await hybrid_search(
            query=arguments["query"],
            lat=arguments["lat"],
            lng=arguments["lng"],
            radius_m=arguments.get("radius_m", 2000),
            embedder=embedder,
            qdrant=qdrant,
            db=db,
            limit=arguments.get("limit", 5) * 3,
            parsed=parsed,
        )

        ranked = rerank(
            candidates=candidates,
            radius_m=arguments.get("radius_m", 2000),
            parsed=parsed,
            budget_per_person=arguments.get("budget_per_person"),
            user_profile=user_profile,
            limit=min(arguments.get("limit", 5), 6),
        )

        # Fetch and summarize reviews for ranked places
        if ranked:
            place_ids = [r["place_id"] for r in ranked]
            from app.services.context import summarize_reviews
            review_rows = await db.execute(text(
                "SELECT place_id::text, rating, content FROM reviews "
                "WHERE place_id = ANY(:ids::uuid[]) ORDER BY published_at DESC"
            ), {"ids": place_ids})
            reviews_by_place: dict[str, list] = {}
            for row in review_rows.fetchall():
                reviews_by_place.setdefault(row.place_id, []).append(
                    {"rating": row.rating, "content": row.content}
                )
            for r in ranked:
                r["review_summary"] = summarize_reviews(
                    reviews_by_place.get(r["place_id"], [])
                )

        places_data = []
        for r in ranked:
            places_data.append({
                "id": r["place_id"],
                "name": r["name"],
                "district": r.get("district", ""),
                "distance_m": int(r["distance_m"]) if r["distance_m"] else None,
                "rating": r.get("rating"),
                "price_min": r.get("price_min"),
                "price_max": r.get("price_max"),
                "dishes": r.get("dish_names", []),
            })

        compact_context = compress_place_context(ranked)

        return "semantic_places", {
            "places": places_data,
            "count": len(places_data),
            "context": compact_context,
        }

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
    request: Request,
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
            session = await session_service.get_or_create(req.session_id, user_id=req.user_id)
            
            # Send session_id to client
            yield f"data: {json.dumps({'type': 'session_id', 'session_id': session.session_id})}\n\n"

            # Load long-term user profile
            user_profile = None
            if session.user_id:
                user_profile_obj = await session_service.get_profile(session.user_id)
                user_profile = user_profile_obj.to_prompt_dict()

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
            
            # Step 4: Build compact context message
            context_msg = build_context_message(session)
            
            # Get user message text
            user_text = ""
            if req.messages and req.messages[-1].role == "user":
                user_text = req.messages[-1].content if isinstance(req.messages[-1].content, str) else ""

            # Learn long-term preferences from message
            if user_text and session.user_id:
                await session_service.learn_from_message(session.user_id, user_text)

            # === LLM MODE: Fallback chain (Ollama → Gemini → OpenAI → cache) ===
            has_any_llm = settings.OLLAMA_URL or settings.GEMINI_API_KEY or settings.OPENAI_API_KEY
            if not has_any_llm:
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
                        result_type, result_data = await execute_tool_call("search_nearby_places", args, db, request.app.state)
                        if result_data.get("places"):
                            yield f"data: {json.dumps({'type': 'places', 'data': result_data['places']})}\n\n"
                    elif should_search_dishes(intent) and (req.lat or session.lat):
                        args = build_search_args(intent, req.lat or session.lat, req.lng or session.lng)
                        result_type, result_data = await execute_tool_call("search_nearby_dishes", args, db, request.app.state)
                        if result_data.get("dishes"):
                            yield f"data: {json.dumps({'type': 'dishes', 'data': result_data['dishes']})}\n\n"
                except Exception as e:
                    print(f"[FREE_CHAT] DB search error (non-fatal): {e}")

                # Save assistant response after generation
                await session_service.add_message(session.session_id, "assistant", text_response)

                yield "data: [DONE]\n\n"
                return

            # === PAID MODE: LLM with fallback chain ===
            # Step 5: Build messages
            system_prompt = build_system_prompt(user_profile)
            messages = [{"role": "system", "content": system_prompt}]

            if context_msg:
                messages.append({"role": "user", "content": context_msg})
                messages.append({"role": "assistant", "content": "OK."})

            messages.extend(compress_chat_history(session.messages))

            for msg in req.messages:
                messages.append({
                    "role": msg.role,
                    "content": msg.content if isinstance(msg.content, str) else json.dumps(msg.content)
                })

            # Step 6: Call LLM with fallback
            llm = LLMClient(redis)
            try:
                llm_response = await llm.chat_completion(
                    messages=messages, tools=TOOLS, stream=False, max_tokens=1000
                )
            finally:
                await llm.close()

            full_content = llm_response.content
            if full_content:
                yield f"data: {json.dumps({'type': 'text', 'content': full_content})}\n\n"

            # Step 7: Handle tool calls
            if llm_response.tool_calls:
                tool_calls_list = llm_response.tool_calls
                tool_results = []

                for tc in tool_calls_list:
                    try:
                        fn_name = tc["function"]["name"]
                        args = json.loads(tc["function"]["arguments"])
                        result_type, result_data = await execute_tool_call(fn_name, args, db, request.app.state, user_profile=user_profile)

                        if result_type == "places":
                            yield f"data: {json.dumps({'type': 'places', 'data': result_data['places']})}\n\n"
                            tool_results.append({"tool_call_id": tc["id"], "role": "tool", "content": json.dumps({"count": result_data["count"]})})
                        elif result_type == "semantic_places":
                            yield f"data: {json.dumps({'type': 'places', 'data': result_data['places']})}\n\n"
                            tool_results.append({"tool_call_id": tc["id"], "role": "tool", "content": result_data["context"]})
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

                # Follow-up call with tool results
                follow_up_messages = messages + [
                    {"role": "assistant", "content": full_content or None, "tool_calls": tool_calls_list}
                ] + tool_results

                llm2 = LLMClient(redis)
                try:
                    follow_up = await llm2.chat_completion(
                        messages=follow_up_messages, stream=False, max_tokens=500
                    )
                finally:
                    await llm2.close()

                if follow_up.content:
                    yield f"data: {json.dumps({'type': 'text', 'content': follow_up.content})}\n\n"
                    await session_service.add_message(session.session_id, "assistant", follow_up.content)
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


@router.get("/profile/{user_id}")
async def get_user_profile(user_id: str, redis: Redis = Depends(get_redis)):
    """Get user's long-term food preferences"""
    session_service = SessionService(redis)
    profile = await session_service.get_profile(user_id)
    return profile.model_dump()


@router.put("/profile/{user_id}")
async def update_user_profile(user_id: str, body: dict, redis: Redis = Depends(get_redis)):
    """Manually update user food preferences"""
    session_service = SessionService(redis)
    profile = await session_service.get_profile(user_id)

    if "favorite_cuisines" in body:
        profile.favorite_cuisines = body["favorite_cuisines"]
    if "disliked_cuisines" in body:
        profile.disliked_cuisines = body["disliked_cuisines"]
    if "spicy_tolerance" in body:
        profile.spicy_tolerance = body["spicy_tolerance"]
    if "budget_preference" in body:
        profile.budget_preference = body["budget_preference"]
    if "favorite_districts" in body:
        profile.favorite_districts = body["favorite_districts"]

    await session_service.save_profile(profile)
    return profile.model_dump()
