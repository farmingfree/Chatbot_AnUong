"""
Title Generation Service - Rule-based + LLM lazy generation
"""
import re
import logging
from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)


def generate_title_rule_based(first_message: str) -> str:
    """
    Generate conversation title from first user message using rules.
    Fast, no API calls needed.

    Examples:
    - "Tìm quán phở gần đây" -> "Tìm quán phở"
    - "Ăn gì ngon ở quận 1" -> "Ăn gì ở quận 1"
    - "Gợi ý món ăn chay" -> "Món ăn chay"
    """
    # Clean message
    text = first_message.strip()

    # Remove common prefixes
    prefixes_to_remove = [
        r'^(?:xin )?(?:cho )?(?:tôi|mình|em) (?:hỏi|muốn biết|muốn tìm|cần)\s+',
        r'^(?:bạn )?(?:có thể|giúp|gợi ý)\s+',
    ]
    for pattern in prefixes_to_remove:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    # Extract key phrases
    patterns = [
        (r'(?:tìm|tìm kiếm|search)\s+(.+?)(?:\s+(?:gần|ở|tại|quanh)|\s*$)', r'Tìm \1'),
        (r'(?:ăn|ăn gì|ăn uống)\s+(.+?)(?:\s+(?:ở|tại|quanh)|\s*$)', r'Ăn \1'),
        (r'(?:quán|nhà hàng|món)\s+(.+?)(?:\s+(?:ở|tại|gần)|\s*$)', r'\1'),
        (r'(?:gợi ý|recommend)\s+(.+?)(?:\s*$)', r'Gợi ý \1'),
    ]

    for pattern, replacement in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            title = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            return _truncate_title(title)

    # Fallback: take first 50 chars
    return _truncate_title(text)


def _truncate_title(title: str, max_length: int = 50) -> str:
    """Truncate title to max_length, breaking at word boundary"""
    title = title.strip()
    if len(title) <= max_length:
        return title

    # Find last space before max_length
    truncated = title[:max_length]
    last_space = truncated.rfind(' ')
    if last_space > max_length * 0.7:  # At least 70% of max_length
        return truncated[:last_space] + '...'
    return truncated + '...'


async def generate_title_llm(
    messages: list[dict],
    llm_client: LLMClient
) -> str:
    """
    Generate conversation title using LLM.
    More natural but requires API call.

    Args:
        messages: List of first few messages (user + assistant)
        llm_client: LLM client instance

    Returns:
        Generated title (max 50 chars)
    """
    try:
        # Build prompt
        conversation_text = "\n".join([
            f"{msg['role']}: {msg['content'][:200]}"
            for msg in messages[:4]  # Only first 2 exchanges
        ])

        prompt = f"""Tạo tiêu đề ngắn gọn (tối đa 50 ký tự) cho cuộc trò chuyện sau.
Tiêu đề phải súc tích, dễ hiểu, không dùng dấu ngoặc kép.

Cuộc trò chuyện:
{conversation_text}

Tiêu đề:"""

        # Call LLM with low priority (use fastest model)
        response = await llm_client.generate(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
            temperature=0.3,
        )

        title = response.content.strip()

        # Clean up
        title = title.strip('"\'')
        title = re.sub(r'^(?:Tiêu đề|Title):\s*', '', title, flags=re.IGNORECASE)

        return _truncate_title(title)

    except Exception as e:
        logger.error(f"LLM title generation failed: {e}")
        # Fallback to rule-based
        if messages and messages[0].get('role') == 'user':
            return generate_title_rule_based(messages[0]['content'])
        return "Cuộc trò chuyện mới"


async def improve_title_background(
    conversation_id: str,
    messages: list[dict],
    llm_client: LLMClient,
    conversation_service
):
    """
    Background task to improve title using LLM.
    Called after conversation is created with rule-based title.
    """
    try:
        improved_title = await generate_title_llm(messages, llm_client)
        await conversation_service.update_title(
            conversation_id,
            improved_title,
            generated_by="llm"
        )
        logger.info(f"Improved title for conversation {conversation_id}: {improved_title}")
    except Exception as e:
        logger.error(f"Background title improvement failed for {conversation_id}: {e}")
