"""
Usage Limit Service

Checks per-user usage limits and returns remaining allowance.
"""

from datetime import datetime, timedelta
from typing import Any, Dict

from sqlalchemy import text

class UsageLimitService:
    """Service for enforcing per-user usage limits."""

    def _get_engine(self):
        from app.database import engine
        return engine

    async def _ensure_user(self, conn, user_email: str) -> None:
        await conn.execute(
            text(
                """
                INSERT INTO users (email, name, is_super_admin, created_at)
                VALUES (:email, SPLIT_PART(:email_for_name, '@', 1), false, NOW())
                ON CONFLICT (email) DO NOTHING
                """
            ),
            {"email": user_email, "email_for_name": user_email},
        )

    async def check_user_limit(self, user_email: str) -> Dict[str, Any]:
        engine = self._get_engine()
        if engine is None:
            return {"allowed": True, "reason": "db_not_initialized"}

        async with engine.begin() as conn:
            await self._ensure_user(conn, user_email)

            result = await conn.execute(
                text(
                    """
                    SELECT
                        u.id AS user_id,
                        l.id AS limit_id,
                        l.is_active,
                        l.period_days,
                        l.max_requests,
                        l.max_tokens,
                        l.max_cost,
                        l.last_reset_at
                    FROM users u
                    LEFT JOIN user_usage_limits l ON l.user_id = u.id
                    WHERE u.email = :email
                    """
                ),
                {"email": user_email},
            )
            row = result.fetchone()

            if not row:
                return {"allowed": True, "reason": "user_not_found"}

            limit_id = row.limit_id
            if not limit_id or not row.is_active:
                return {"allowed": True, "reason": "no_limit"}

            period_days = row.period_days or 30
            last_reset_at = row.last_reset_at
            now = datetime.utcnow()

            if last_reset_at is None:
                last_reset_at = now
                await conn.execute(
                    text(
                        """
                        UPDATE user_usage_limits
                        SET last_reset_at = :last_reset_at, updated_at = NOW()
                        WHERE id = :limit_id
                        """
                    ),
                    {"last_reset_at": last_reset_at, "limit_id": limit_id},
                )

            window_end = last_reset_at + timedelta(days=period_days)
            if now >= window_end:
                last_reset_at = now
                window_end = last_reset_at + timedelta(days=period_days)
                await conn.execute(
                    text(
                        """
                        UPDATE user_usage_limits
                        SET last_reset_at = :last_reset_at, updated_at = NOW()
                        WHERE id = :limit_id
                        """
                    ),
                    {"last_reset_at": last_reset_at, "limit_id": limit_id},
                )

            usage_result = await conn.execute(
                text(
                    """
                    SELECT
                        COUNT(*) AS total_requests,
                        COALESCE(SUM(tokens_input + tokens_output + tokens_cached), 0) AS total_tokens,
                        COALESCE(SUM(cost_estimate), 0.0) AS total_cost
                    FROM audit_logs
                    WHERE user_id = :user_id
                      AND created_at >= :window_start
                    """
                ),
                {"user_id": row.user_id, "window_start": last_reset_at},
            )
            usage = usage_result.fetchone()

            total_requests = int(usage.total_requests or 0)
            total_tokens = int(usage.total_tokens or 0)
            total_cost = float(usage.total_cost or 0.0)

            max_requests = row.max_requests
            max_tokens = row.max_tokens
            max_cost = float(row.max_cost) if row.max_cost is not None else None

            exceeded_requests = max_requests is not None and total_requests >= max_requests
            exceeded_tokens = max_tokens is not None and total_tokens >= max_tokens
            exceeded_cost = max_cost is not None and total_cost >= max_cost

            allowed = not (exceeded_requests or exceeded_tokens or exceeded_cost)

            return {
                "allowed": allowed,
                "user_id": row.user_id,
                "period_days": period_days,
                "window_start": last_reset_at,
                "window_end": window_end,
                "total_requests": total_requests,
                "total_tokens": total_tokens,
                "total_cost": total_cost,
                "max_requests": max_requests,
                "max_tokens": max_tokens,
                "max_cost": max_cost,
                "exceeded_requests": exceeded_requests,
                "exceeded_tokens": exceeded_tokens,
                "exceeded_cost": exceeded_cost,
            }


_usage_limit_service = None


def get_usage_limit_service() -> UsageLimitService:
    global _usage_limit_service
    if _usage_limit_service is None:
        _usage_limit_service = UsageLimitService()
    return _usage_limit_service
