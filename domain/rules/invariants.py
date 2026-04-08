PHASE_ONE_CHAIN = (
    "signal",
    "topic",
    "content_variant",
    "image_asset",
    "publish_check",
    "retro_record",
)

REQUIRED_FOREIGN_KEYS = {
    "topic": ("signal_id",),
    "content_variant": ("topic_id",),
    "image_asset": ("content_variant_id",),
    "publish_check": ("content_variant_id",),
    "publish_check_item": ("publish_check_id",),
    "retro_record": ("publish_check_id",),
}

APPEND_ONLY_OBJECTS = ("publish_check", "publish_check_item")

CHECK_GATE_RULES = {
    "pass_allows_next_step": True,
    "warn_allows_next_step": True,
    "warn_requires_risk_note": True,
    "block_forces_rework": True,
    "content_or_image_change_requires_new_check": True,
}
