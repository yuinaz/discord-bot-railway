
import os
print("XP_STATE_CHANNEL_ID =", os.getenv("XP_STATE_CHANNEL_ID"))
print("XP_STATE_MESSAGE_ID =", os.getenv("XP_STATE_MESSAGE_ID"))
print("XP_STATE_MARKER     =", os.getenv("XP_STATE_MARKER", "[XP_STATE]"))
print("DB DSN present?     =", bool(os.getenv("DATABASE_URL") or os.getenv("RENDER_POSTGRES_URL")))
print("If DB present, discord backend will skip itself.")
