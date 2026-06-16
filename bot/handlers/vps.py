"""
BlueHub Telegram Bot - VPS Handler
===================================
Full-featured VPS service management via Telegram bot.
Handles instance listing, power management, snapshots,
console access, resize, and status monitoring.

Covers:
- /vps - Main VPS menu and instance overview
- /vps_list - List all VPS instances
- /vps_power - Power management (start, stop, reboot, etc.)
- /vps_snapshots - Snapshot management
- /vps_vnc - VNC console access
- /vps_stats - Resource usage and status

All bot-to-API calls go through the internal FastAPI endpoints
to keep business logic in one place.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.middleware.auth import require_auth
from modules.vps.models import VpsInstance, VpsPowerStatus, VpsSnapshot

logger = logging.getLogger("bluehub.bot.handlers.vps")

router = Router(name="vps")


# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

POWER_EMOJI_MAP: Dict[VpsPowerStatus, str] = {
    VpsPowerStatus.RUNNING: "🟢",
    VpsPowerStatus.STOPPED: "🔴",
    VpsPowerStatus.PAUSED: "🟡",
    VpsPowerStatus.SUSPENDED: "⚫",
}

VPS_POWER_ACTIONS: Dict[str, str] = {
    "start": "▶️ Start",
    "stop": "⏹ Stop",
    "reboot": "🔄 Reboot",
    "shutdown": "⏏️ Shutdown",
    "pause": "⏸ Pause",
    "resume": "▶️ Resume",
}


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

async def _get_user_vps_instances(
    db: AsyncSession, user_id: UUID,
) -> List[VpsInstance]:
    """Fetch all VPS instances for a given user via their services."""
    from shared.models.service import Service
    result = await db.execute(
        select(VpsInstance)
        .join(Service, VpsInstance.service_id == Service.id)
        .where(Service.user_id == str(user_id))
        .order_by(VpsInstance.created_at.desc())
    )
    return list(result.scalars().all())


async def _get_instance(
    db: AsyncSession, instance_id: UUID, user_id: UUID,
) -> Optional[VpsInstance]:
    """Fetch a specific VPS instance, ensuring user ownership."""
    from shared.models.service import Service
    result = await db.execute(
        select(VpsInstance)
        .join(Service, VpsInstance.service_id == Service.id)
        .where(
            VpsInstance.id == instance_id,
            Service.user_id == str(user_id),
        )
    )
    return result.scalar_one_or_none()


def _vps_main_keyboard(
    T_get, instances_exist: bool,
) -> InlineKeyboardMarkup:
    """Build the main VPS menu keyboard with translation-aware labels."""
    kb: List[List[InlineKeyboardButton]] = []

    if instances_exist:
        kb.extend([
            [
                InlineKeyboardButton(
                    text=T_get("bot.vps.btn_list"),
                    callback_data="vps:list",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=T_get("bot.vps.btn_power"),
                    callback_data="vps:select_power",
                ),
                InlineKeyboardButton(
                    text=T_get("bot.vps.btn_snapshots"),
                    callback_data="vps:select_snapshots",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=T_get("bot.vps.btn_vnc"),
                    callback_data="vps:select_vnc",
                ),
                InlineKeyboardButton(
                    text=T_get("bot.vps.btn_stats"),
                    callback_data="vps:stats",
                ),
            ],
        ])

    kb.append([
        InlineKeyboardButton(
            text=T_get("bot.vps.btn_back"),
            callback_data="main_menu",
        ),
    ])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def _instance_selection_keyboard(
    instances: List[VpsInstance], action: str, T_get,
) -> InlineKeyboardMarkup:
    """Build a keyboard to select a specific VPS instance for an action."""
    buttons: List[List[InlineKeyboardButton]] = []
    for inst in instances:
        emoji = POWER_EMOJI_MAP.get(inst.power_status, "⚪")
        label = (
            f"{emoji} VPS-{inst.proxmox_vmid or inst.id.hex[:8]} "
            f"({inst.cpu_cores}C/{inst.memory_mb}M/{inst.disk_gb}G)"
        )
        if len(label) > 64:
            label = f"{emoji} VPS-{inst.proxmox_vmid or inst.id.hex[:8]}"
        buttons.append([
            InlineKeyboardButton(
                text=label,
                callback_data=f"vps:{action}:{inst.id}",
            ),
        ])
    buttons.append([
        InlineKeyboardButton(
            text=T_get("bot.vps.btn_back"),
            callback_data="vps:menu",
        ),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _power_actions_keyboard(
    instance_id: UUID, current_status: VpsPowerStatus, T_get,
) -> InlineKeyboardMarkup:
    """Build keyboard with available power actions based on current status."""
    buttons: List[List[InlineKeyboardButton]] = []

    # Determine which actions make sense based on current state
    if current_status == VpsPowerStatus.RUNNING:
        available = ["stop", "reboot", "shutdown", "pause"]
    elif current_status == VpsPowerStatus.STOPPED:
        available = ["start"]
    elif current_status == VpsPowerStatus.PAUSED:
        available = ["resume", "stop"]
    elif current_status == VpsPowerStatus.SUSPENDED:
        available = ["resume"]
    else:
        available = ["start", "stop"]

    # Build buttons in pairs
    for i in range(0, len(available), 2):
        pair = available[i:i + 2]
        row: List[InlineKeyboardButton] = []
        for action in pair:
            row.append(
                InlineKeyboardButton(
                    text=VPS_POWER_ACTIONS[action],
                    callback_data=f"vps:power:{action}:{instance_id}",
                )
            )
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton(
            text=T_get("bot.vps.btn_back"),
            callback_data="vps:menu",
        ),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _snapshot_actions_keyboard(
    instance_id: UUID, snapshots_exist: bool, T_get,
) -> InlineKeyboardMarkup:
    """Build snapshot management keyboard."""
    kb: List[List[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=T_get("bot.vps.btn_snapshot_create"),
                callback_data=f"vps:snapshot_create:{instance_id}",
            ),
        ],
    ]

    if snapshots_exist:
        kb.append([
            InlineKeyboardButton(
                text=T_get("bot.vps.btn_snapshot_list"),
                callback_data=f"vps:snapshot_list:{instance_id}",
            ),
            InlineKeyboardButton(
                text=T_get("bot.vps.btn_snapshot_restore"),
                callback_data=f"vps:snapshot_select_restore:{instance_id}",
            ),
        ])

    kb.append([
        InlineKeyboardButton(
            text=T_get("bot.vps.btn_back"),
            callback_data="vps:menu",
        ),
    ])
    return InlineKeyboardMarkup(inline_keyboard=kb)


# ------------------------------------------------------------------
# Command: /vps (Main Menu)
# ------------------------------------------------------------------

@router.message(Command("vps"))
@router.message(F.text.lower().in_(["vps", "/vps", "🖥 vps", "🖥 سرور مجازی"]))
@require_auth
async def cmd_vps_menu(
    message: Message, T, db_user, db_session,
) -> None:
    """Show the main VPS management menu with instance overview."""
    if db_user is None:
        await message.answer(await T("bot.auth_required"))
        return

    instances = await _get_user_vps_instances(db_session, db_user.id)
    summary = await _format_instance_list(instances, T)
    keyboard = _vps_main_keyboard(T, len(instances) > 0)

    await message.answer(summary, reply_markup=keyboard)


async def _format_instance_list(
    instances: List[VpsInstance], T,
) -> str:
    """Format a list of VPS instances for display."""
    if not instances:
        return await T("bot.vps.no_instances")

    lines = [await T("bot.vps.instance_list_header")]
    for idx, inst in enumerate(instances, 1):
        emoji = POWER_EMOJI_MAP.get(inst.power_status, "⚪")
        ip_str = inst.primary_ipv4 or await T("bot.vps.no_ip")
        vmid = inst.proxmox_vmid or "—"
        line = await T(
            "bot.vps.instance_item",
            index=idx,
            emoji=emoji,
            vmid=vmid,
            cores=inst.cpu_cores,
            memory=inst.memory_mb,
            disk=inst.disk_gb,
            ip=ip_str,
            status=inst.power_status.value,
        )
        lines.append(line)
    return "\n".join(lines)


# ------------------------------------------------------------------
# Callback: Main Menu
# ------------------------------------------------------------------

@router.callback_query(F.data == "vps:menu")
async def cb_vps_menu(
    callback: CallbackQuery, T, db_user, db_session,
) -> None:
    """Return to VPS main menu."""
    await callback.answer()
    instances = await _get_user_vps_instances(db_session, db_user.id)
    summary = await _format_instance_list(instances, T)
    keyboard = _vps_main_keyboard(T, len(instances) > 0)
    await callback.message.edit_text(summary, reply_markup=keyboard)


# ------------------------------------------------------------------
# Command/Callback: List Instances
# ------------------------------------------------------------------

@router.message(Command("vps_list"))
@router.callback_query(F.data == "vps:list")
@require_auth
async def cmd_vps_list(
    event: Message | CallbackQuery, T, db_user, db_session,
) -> None:
    """List all VPS instances with detailed info."""
    if db_user is None:
        if isinstance(event, Message):
            await event.answer(await T("bot.auth_required"))
        return

    if isinstance(event, CallbackQuery):
        await event.answer()
        target = event.message
    else:
        target = event

    instances = await _get_user_vps_instances(db_session, db_user.id)
    if not instances:
        await target.edit_text(
            await T("bot.vps.no_instances"),
            reply_markup=_vps_main_keyboard(T, False),
        )
        return

    # Show detailed info for each instance
    for inst in instances:
        detail = await _format_instance_detail(inst, T, db_session)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=await T("bot.vps.btn_power_mgmt"),
                    callback_data=f"vps:power_mgmt:{inst.id}",
                ),
                InlineKeyboardButton(
                    text=await T("bot.vps.btn_snapshots_mgmt"),
                    callback_data=f"vps:snapshot_mgmt:{inst.id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=await T("bot.vps.btn_back"),
                    callback_data="vps:menu",
                ),
            ],
        ])
        await target.answer(detail, reply_markup=keyboard)


async def _format_instance_detail(
    inst: VpsInstance, T, db: AsyncSession,
) -> str:
    """Format detailed info for a single VPS instance."""
    emoji = POWER_EMOJI_MAP.get(inst.power_status, "⚪")
    ip = inst.primary_ipv4 or await T("bot.vps.no_ip")
    os_template = inst.os_template or await T("bot.vps.not_specified")
    vmid = inst.proxmox_vmid or "—"
    node = inst.proxmox_node or "—"
    bandwidth_used = inst.bandwidth_used_bytes / (1024 ** 3)

    return await T(
        "bot.vps.instance_detail",
        emoji=emoji,
        vmid=vmid,
        status=inst.power_status.value,
        cores=inst.cpu_cores,
        memory=inst.memory_mb,
        disk=inst.disk_gb,
        ip=ip,
        os=os_template,
        node=node,
        bandwidth_gb=f"{bandwidth_used:.2f}",
    )


# ------------------------------------------------------------------
# Stats Overview
# ------------------------------------------------------------------

@router.callback_query(F.data == "vps:stats")
async def cb_vps_stats(
    callback: CallbackQuery, T, db_user, db_session,
) -> None:
    """Show resource usage stats across all VPS instances."""
    await callback.answer()
    instances = await _get_user_vps_instances(db_session, db_user.id)
    if not instances:
        await callback.message.edit_text(
            await T("bot.vps.no_instances"),
            reply_markup=_vps_main_keyboard(T, False),
        )
        return

    total_cores = sum(i.cpu_cores for i in instances)
    total_memory = sum(i.memory_mb for i in instances)
    total_disk = sum(i.disk_gb for i in instances)
    total_bandwidth = sum(i.bandwidth_used_bytes for i in instances) / (1024 ** 3)
    running = sum(1 for i in instances if i.power_status == VpsPowerStatus.RUNNING)
    stopped = sum(1 for i in instances if i.power_status == VpsPowerStatus.STOPPED)

    stats = await T(
        "bot.vps.stats_overview",
        count=len(instances),
        running=running,
        stopped=stopped,
        total_cores=total_cores,
        total_memory=total_memory,
        total_disk=total_disk,
        bandwidth_gb=f"{total_bandwidth:.2f}",
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=await T("bot.vps.btn_back"),
                callback_data="vps:menu",
            ),
        ],
    ])
    await callback.message.edit_text(stats, reply_markup=keyboard)


# ------------------------------------------------------------------
# Power Management - Select Instance
# ------------------------------------------------------------------

@router.callback_query(F.data == "vps:select_power")
async def cb_vps_select_power(
    callback: CallbackQuery, T, db_user, db_session,
) -> None:
    """Show list of instances to select for power management."""
    await callback.answer()
    instances = await _get_user_vps_instances(db_session, db_user.id)
    if not instances:
        await callback.message.edit_text(
            await T("bot.vps.no_instances"),
            reply_markup=_vps_main_keyboard(T, False),
        )
        return
    await callback.message.edit_text(
        await T("bot.vps.select_instance_power"),
        reply_markup=_instance_selection_keyboard(instances, "power_mgmt", T),
    )


# ------------------------------------------------------------------
# Power Management - Show Actions
# ------------------------------------------------------------------

@router.callback_query(F.data.startswith("vps:power_mgmt:"))
async def cb_vps_power_mgmt(
    callback: CallbackQuery, T, db_user, db_session,
) -> None:
    """Show power actions for a specific instance."""
    await callback.answer()
    instance_id = UUID(callback.data.split(":")[2])
    inst = await _get_instance(db_session, instance_id, db_user.id)
    if not inst:
        await callback.message.edit_text(
            await T("bot.vps.instance_not_found"),
            reply_markup=_vps_main_keyboard(T, True),
        )
        return

    status_text = await T(
        "bot.vps.power_status_current",
        vmid=inst.proxmox_vmid or inst.id.hex[:8],
        status=inst.power_status.value,
    )
    keyboard = _power_actions_keyboard(inst.id, inst.power_status, T)
    await callback.message.edit_text(status_text, reply_markup=keyboard)


# ------------------------------------------------------------------
# Power Action Execution
# ------------------------------------------------------------------

@router.callback_query(F.data.startswith("vps:power:"))
async def cb_vps_power_action(
    callback: CallbackQuery, T, db_user, db_session,
) -> None:
    """Execute a power action on a VPS instance."""
    await callback.answer()
    # Format: vps:power:{action}:{instance_id}
    parts = callback.data.split(":")
    action = parts[2]
    instance_id = UUID(parts[3])

    inst = await _get_instance(db_session, instance_id, db_user.id)
    if not inst:
        await callback.message.edit_text(
            await T("bot.vps.instance_not_found"),
            reply_markup=_vps_main_keyboard(T, True),
        )
        return

    try:
        from modules.vps.services import VpsInstanceService
        vps_service = VpsInstanceService(db_session)

        action_map = {
            "start": vps_service.start_instance,
            "stop": vps_service.stop_instance,
            "reboot": vps_service.reboot_instance,
            "shutdown": vps_service.shutdown_instance,
            "pause": vps_service.pause_instance,
            "resume": vps_service.resume_instance,
        }

        handler = action_map.get(action)
        if handler is None:
            await callback.message.edit_text(
                await T("bot.vps.invalid_action"),
                reply_markup=_vps_main_keyboard(T, True),
            )
            return

        await handler(instance_id)
        await db_session.commit()

        # Refresh instance to get new status
        await db_session.refresh(inst)

        success_text = await T(
            "bot.vps.power_action_success",
            action=action,
            vmid=inst.proxmox_vmid or inst.id.hex[:8],
        )
        keyboard = _power_actions_keyboard(inst.id, inst.power_status, T)
        await callback.message.edit_text(success_text, reply_markup=keyboard)

    except Exception as e:
        logger.error("VPS power action '%s' failed: %s", action, e)
        error_text = await T("bot.vps.power_action_error", error=str(e))
        await callback.message.edit_text(
            error_text,
            reply_markup=_vps_main_keyboard(T, True),
        )


# ------------------------------------------------------------------
# Snapshot Management - Select Instance
# ------------------------------------------------------------------

@router.callback_query(F.data == "vps:select_snapshots")
async def cb_vps_select_snapshots(
    callback: CallbackQuery, T, db_user, db_session,
) -> None:
    """Show list of instances for snapshot management."""
    await callback.answer()
    instances = await _get_user_vps_instances(db_session, db_user.id)
    if not instances:
        await callback.message.edit_text(
            await T("bot.vps.no_instances"),
            reply_markup=_vps_main_keyboard(T, False),
        )
        return
    await callback.message.edit_text(
        await T("bot.vps.select_instance_snapshots"),
        reply_markup=_instance_selection_keyboard(instances, "snapshot_mgmt", T),
    )


# ------------------------------------------------------------------
# Snapshot Management - Show Actions
# ------------------------------------------------------------------

@router.callback_query(F.data.startswith("vps:snapshot_mgmt:"))
async def cb_vps_snapshot_mgmt(
    callback: CallbackQuery, T, db_user, db_session,
) -> None:
    """Show snapshot management options for a specific instance."""
    await callback.answer()
    instance_id = UUID(callback.data.split(":")[2])
    inst = await _get_instance(db_session, instance_id, db_user.id)
    if not inst:
        await callback.message.edit_text(
            await T("bot.vps.instance_not_found"),
            reply_markup=_vps_main_keyboard(T, True),
        )
        return

    # Check if snapshots exist
    snapshots_exists = len(inst.snapshots) > 0 if inst.snapshots else False

    snap_text = await T(
        "bot.vps.snapshot_mgmt_header",
        vmid=inst.proxmox_vmid or inst.id.hex[:8],
        snapshot_count=len(inst.snapshots) if inst.snapshots else 0,
    )
    keyboard = _snapshot_actions_keyboard(inst.id, snapshots_exists, T)
    await callback.message.edit_text(snap_text, reply_markup=keyboard)


# ------------------------------------------------------------------
# Create Snapshot
# ------------------------------------------------------------------

@router.callback_query(F.data.startswith("vps:snapshot_create:"))
async def cb_vps_snapshot_create(
    callback: CallbackQuery, T, db_user, db_session,
) -> None:
    """Create a new snapshot for a VPS instance."""
    await callback.answer()
    instance_id = UUID(callback.data.split(":")[2])
    inst = await _get_instance(db_session, instance_id, db_user.id)
    if not inst:
        await callback.message.edit_text(
            await T("bot.vps.instance_not_found"),
            reply_markup=_vps_main_keyboard(T, True),
        )
        return

    try:
        from modules.vps.services import VpsInstanceService
        vps_service = VpsInstanceService(db_session)

        snapshot = await vps_service.create_snapshot(
            instance_id=instance_id,
            snapshot_name=f"snap-{int(datetime.now(timezone.utc).timestamp())}",
            description=await T("bot.vps.snapshot_bot_created"),
        )
        await db_session.commit()

        success_text = await T(
            "bot.vps.snapshot_created",
            name=snapshot.snapshot_name,
            vmid=inst.proxmox_vmid or inst.id.hex[:8],
        )
        keyboard = _snapshot_actions_keyboard(inst.id, True, T)
        await callback.message.edit_text(success_text, reply_markup=keyboard)

    except Exception as e:
        logger.error("VPS snapshot creation failed: %s", e)
        error_text = await T("bot.vps.snapshot_create_error", error=str(e))
        await callback.message.edit_text(
            error_text,
            reply_markup=_vps_main_keyboard(T, True),
        )


# ------------------------------------------------------------------
# List Snapshots
# ------------------------------------------------------------------

@router.callback_query(F.data.startswith("vps:snapshot_list:"))
async def cb_vps_snapshot_list(
    callback: CallbackQuery, T, db_user, db_session,
) -> None:
    """List all snapshots for a VPS instance."""
    await callback.answer()
    instance_id = UUID(callback.data.split(":")[2])
    inst = await _get_instance(db_session, instance_id, db_user.id)
    if not inst:
        await callback.message.edit_text(
            await T("bot.vps.instance_not_found"),
            reply_markup=_vps_main_keyboard(T, True),
        )
        return

    if not inst.snapshots:
        await callback.message.edit_text(
            await T("bot.vps.no_snapshots"),
            reply_markup=_snapshot_actions_keyboard(inst.id, False, T),
        )
        return

    lines = [await T("bot.vps.snapshot_list_header")]
    for snap in inst.snapshots:
        size_str = (
            f"{(snap.size_bytes or 0) / (1024**3):.2f} GB"
            if snap.size_bytes
            else await T("bot.vps.unknown")
        )
        ram_flag = "💾" if snap.is_ram_included else ""
        taken = (
            snap.snapshot_taken_at.strftime("%Y-%m-%d %H:%M")
            if snap.snapshot_taken_at
            else await T("bot.vps.unknown_date")
        )
        line = await T(
            "bot.vps.snapshot_item",
            name=snap.snapshot_name,
            size=size_str,
            ram=ram_flag,
            taken=taken,
        )
        lines.append(line)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=await T("bot.vps.btn_delete_snapshot"),
                callback_data=f"vps:snapshot_select_delete:{instance_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                text=await T("bot.vps.btn_back"),
                callback_data=f"vps:snapshot_mgmt:{instance_id}",
            ),
        ],
    ])
    await callback.message.edit_text("\n".join(lines), reply_markup=keyboard)


# ------------------------------------------------------------------
# Select Snapshot for Restore
# ------------------------------------------------------------------

@router.callback_query(F.data.startswith("vps:snapshot_select_restore:"))
async def cb_vps_snapshot_select_restore(
    callback: CallbackQuery, T, db_user, db_session,
) -> None:
    """Show list of snapshots to select for restore."""
    await callback.answer()
    instance_id = UUID(callback.data.split(":")[2])
    inst = await _get_instance(db_session, instance_id, db_user.id)
    if not inst or not inst.snapshots:
        await callback.message.edit_text(
            await T("bot.vps.no_snapshots"),
            reply_markup=_snapshot_actions_keyboard(
                inst.id if inst else instance_id, False, T,
            ),
        )
        return

    buttons: List[List[InlineKeyboardButton]] = []
    for snap in inst.snapshots:
        taken = (
            snap.snapshot_taken_at.strftime("%m/%d %H:%M")
            if snap.snapshot_taken_at
            else "—"
        )
        buttons.append([
            InlineKeyboardButton(
                text=f"{snap.snapshot_name} ({taken})",
                callback_data=f"vps:snapshot_restore:{snap.id}:{instance_id}",
            ),
        ])
    buttons.append([
        InlineKeyboardButton(
            text=await T("bot.vps.btn_back"),
            callback_data=f"vps:snapshot_mgmt:{instance_id}",
        ),
    ])
    await callback.message.edit_text(
        await T("bot.vps.select_snapshot_restore"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


# ------------------------------------------------------------------
# Restore Snapshot
# ------------------------------------------------------------------

@router.callback_query(F.data.startswith("vps:snapshot_restore:"))
async def cb_vps_snapshot_restore(
    callback: CallbackQuery, T, db_user, db_session,
) -> None:
    """Restore a VPS instance from a snapshot."""
    await callback.answer()
    # Format: vps:snapshot_restore:{snapshot_id}:{instance_id}
    parts = callback.data.split(":")
    snapshot_id = UUID(parts[2])
    instance_id = UUID(parts[3])

    inst = await _get_instance(db_session, instance_id, db_user.id)
    if not inst:
        await callback.message.edit_text(
            await T("bot.vps.instance_not_found"),
            reply_markup=_vps_main_keyboard(T, True),
        )
        return

    try:
        from modules.vps.services import VpsInstanceService
        vps_service = VpsInstanceService(db_session)

        await vps_service.restore_snapshot(instance_id, snapshot_id)
        await db_session.commit()

        success_text = await T(
            "bot.vps.snapshot_restored",
            vmid=inst.proxmox_vmid or inst.id.hex[:8],
        )
        keyboard = _snapshot_actions_keyboard(
            inst.id, len(inst.snapshots) > 0, T,
        )
        await callback.message.edit_text(success_text, reply_markup=keyboard)

    except Exception as e:
        logger.error("VPS snapshot restore failed: %s", e)
        error_text = await T("bot.vps.snapshot_restore_error", error=str(e))
        await callback.message.edit_text(
            error_text,
            reply_markup=_vps_main_keyboard(T, True),
        )


# ------------------------------------------------------------------
# Select Snapshot for Delete
# ------------------------------------------------------------------

@router.callback_query(F.data.startswith("vps:snapshot_select_delete:"))
async def cb_vps_snapshot_select_delete(
    callback: CallbackQuery, T, db_user, db_session,
) -> None:
    """Show list of snapshots to select for deletion."""
    await callback.answer()
    instance_id = UUID(callback.data.split(":")[2])
    inst = await _get_instance(db_session, instance_id, db_user.id)
    if not inst or not inst.snapshots:
        await callback.message.edit_text(
            await T("bot.vps.no_snapshots"),
            reply_markup=_snapshot_actions_keyboard(
                inst.id if inst else instance_id, False, T,
            ),
        )
        return

    buttons: List[List[InlineKeyboardButton]] = []
    for snap in inst.snapshots:
        buttons.append([
            InlineKeyboardButton(
                text=f"🗑 {snap.snapshot_name}",
                callback_data=f"vps:snapshot_delete:{snap.id}:{instance_id}",
            ),
        ])
    buttons.append([
        InlineKeyboardButton(
            text=await T("bot.vps.btn_back"),
            callback_data=f"vps:snapshot_mgmt:{instance_id}",
        ),
    ])
    await callback.message.edit_text(
        await T("bot.vps.select_snapshot_delete"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


# ------------------------------------------------------------------
# Delete Snapshot
# ------------------------------------------------------------------

@router.callback_query(F.data.startswith("vps:snapshot_delete:"))
async def cb_vps_snapshot_delete(
    callback: CallbackQuery, T, db_user, db_session,
) -> None:
    """Delete a specific snapshot."""
    await callback.answer()
    # Format: vps:snapshot_delete:{snapshot_id}:{instance_id}
    parts = callback.data.split(":")
    snapshot_id = UUID(parts[2])
    instance_id = UUID(parts[3])

    inst = await _get_instance(db_session, instance_id, db_user.id)
    if not inst:
        await callback.message.edit_text(
            await T("bot.vps.instance_not_found"),
            reply_markup=_vps_main_keyboard(T, True),
        )
        return

    try:
        from modules.vps.services import VpsInstanceService
        vps_service = VpsInstanceService(db_session)

        await vps_service.delete_snapshot(instance_id, snapshot_id)
        await db_session.commit()

        success_text = await T(
            "bot.vps.snapshot_deleted",
            vmid=inst.proxmox_vmid or inst.id.hex[:8],
        )
        # Refresh to get updated snapshots
        await db_session.refresh(inst)
        keyboard = _snapshot_actions_keyboard(
            inst.id, len(inst.snapshots) if inst.snapshots else False, T,
        )
        await callback.message.edit_text(success_text, reply_markup=keyboard)

    except Exception as e:
        logger.error("VPS snapshot deletion failed: %s", e)
        error_text = await T("bot.vps.snapshot_delete_error", error=str(e))
        await callback.message.edit_text(
            error_text,
            reply_markup=_vps_main_keyboard(T, True),
        )


# ------------------------------------------------------------------
# VNC Console - Select Instance
# ------------------------------------------------------------------

@router.callback_query(F.data == "vps:select_vnc")
async def cb_vps_select_vnc(
    callback: CallbackQuery, T, db_user, db_session,
) -> None:
    """Show list of instances to get VNC access."""
    await callback.answer()
    instances = await _get_user_vps_instances(db_session, db_user.id)
    if not instances:
        await callback.message.edit_text(
            await T("bot.vps.no_instances"),
            reply_markup=_vps_main_keyboard(T, False),
        )
        return
    await callback.message.edit_text(
        await T("bot.vps.select_instance_vnc"),
        reply_markup=_instance_selection_keyboard(instances, "vnc", T),
    )


# ------------------------------------------------------------------
# VNC Console - Get Access Info
# ------------------------------------------------------------------

@router.callback_query(F.data.startswith("vps:vnc:"))
async def cb_vps_vnc(
    callback: CallbackQuery, T, db_user, db_session,
) -> None:
    """Show VNC console access details for a specific instance."""
    await callback.answer()
    instance_id = UUID(callback.data.split(":")[2])
    inst = await _get_instance(db_session, instance_id, db_user.id)
    if not inst:
        await callback.message.edit_text(
            await T("bot.vps.instance_not_found"),
            reply_markup=_vps_main_keyboard(T, True),
        )
        return

    try:
        from modules.vps.services import VpsInstanceService
        vps_service = VpsInstanceService(db_session)

        vnc_info = await vps_service.get_vnc_console(instance_id)

        vnc_text = await T(
            "bot.vps.vnc_info",
            vmid=inst.proxmox_vmid or inst.id.hex[:8],
            port=str(vnc_info.vnc_port) if hasattr(vnc_info, 'vnc_port') else await T("bot.vps.not_available"),
            password=vnc_info.vnc_password if hasattr(vnc_info, 'vnc_password') else await T("bot.vps.not_available"),
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=await T("bot.vps.btn_back"),
                    callback_data="vps:menu",
                ),
            ],
        ])
        await callback.message.edit_text(vnc_text, reply_markup=keyboard)

    except Exception as e:
        logger.error("VPS VNC access failed: %s", e)
        error_text = await T("bot.vps.vnc_error", error=str(e))
        await callback.message.edit_text(
            error_text,
            reply_markup=_vps_main_keyboard(T, True),
        )


# ------------------------------------------------------------------
# Export
# ------------------------------------------------------------------

__all__ = ["router"]