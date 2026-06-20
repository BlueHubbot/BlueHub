"""
BlueHub Telegram Bot - VPN Handler
===================================
Full-featured VPN service management via Telegram bot.
Handles account creation, listing, config generation, traffic
statistics, and account management operations.

Covers:
- /vpn - Main VPN menu and account overview
- /vpn_create - Create new VPN account
- /vpn_list - List all VPN accounts
- /vpn_config - Download VPN configuration
- /vpn_stats - View traffic usage and statistics
- /vpn_renew - Renew VPN configuration
- /vpn_delete - Delete VPN account
- /vpn_qr - Get QR code for mobile config
"""

from __future__ import annotations

import logging
from uuid import UUID

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputFile,
    Message,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.middleware.auth import require_auth
from modules.vpn.models import (
    VpnAccount,
    VpnAccountStatus,
    VpnProtocol,
)
from modules.vpn.services import VpnAccountService

logger = logging.getLogger("bluehub.bot.handlers.vpn")

router = Router(name="vpn")


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

async def _get_user_vpn_accounts(
    db: AsyncSession, user_id: UUID
) -> list[VpnAccount]:
    """Fetch all VPN accounts for a given user."""
    result = await db.execute(
        select(VpnAccount)
        .where(
            VpnAccount.user_id == user_id,
            VpnAccount.status != VpnAccountStatus.DELETED,
        )
        .order_by(VpnAccount.created_at.desc())
    )
    return list(result.scalars().all())


async def _format_account_list(
    accounts: list[VpnAccount], T, db: AsyncSession
) -> str:
    """Format a list of VPN accounts for display."""
    if not accounts:
        return await T("bot.vpn.no_accounts")

    lines = [await T("bot.vpn.account_list_header")]
    for idx, acc in enumerate(accounts, 1):
        traffic = await VpnAccountService.get_account_traffic(db, acc.id)
        used_gb = (traffic.total_download + traffic.total_upload) / (1024**3)
        limit_str = (
            f"{acc.traffic_limit_gb} GB"
            if acc.traffic_limit_gb
            else await T("bot.vpn.unlimited")
        )
        status_emoji = {
            VpnAccountStatus.ACTIVE: "🟢",
            VpnAccountStatus.SUSPENDED: "🟡",
            VpnAccountStatus.EXPIRED: "🔴",
            VpnAccountStatus.DELETED: "⚫",
        }.get(acc.status, "⚪")

        account_line = await T(
            "bot.vpn.account_item",
            index=idx,
            status_emoji=status_emoji,
            name=acc.name or f"VPN-{acc.id.hex[:8]}",
            protocol=acc.protocol.value.upper(),
            used_gb=f"{used_gb:.2f}",
            limit=limit_str,
        )
        lines.append(account_line)
    return "\n".join(lines)


def _vpn_main_keyboard(T_get, accounts_exist: bool) -> InlineKeyboardMarkup:
    """Build the main VPN menu keyboard with translation-aware labels."""
    kb = [
        [
            InlineKeyboardButton(
                text=T_get("bot.vpn.btn_create"),
                callback_data="vpn:create",
            )
        ],
    ]

    if accounts_exist:
        kb.extend([
            [
                InlineKeyboardButton(
                    text=T_get("bot.vpn.btn_list"),
                    callback_data="vpn:list",
                ),
                InlineKeyboardButton(
                    text=T_get("bot.vpn.btn_stats"),
                    callback_data="vpn:stats",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=T_get("bot.vpn.btn_config"),
                    callback_data="vpn:select_config",
                ),
                InlineKeyboardButton(
                    text=T_get("bot.vpn.btn_qr"),
                    callback_data="vpn:select_qr",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=T_get("bot.vpn.btn_renew"),
                    callback_data="vpn:select_renew",
                ),
                InlineKeyboardButton(
                    text=T_get("bot.vpn.btn_delete"),
                    callback_data="vpn:select_delete",
                ),
            ],
        ])

    kb.append([
        InlineKeyboardButton(
            text=T_get("bot.vpn.btn_back"),
            callback_data="main_menu",
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def _account_selection_keyboard(
    accounts: list[VpnAccount], action: str, T_get
) -> InlineKeyboardMarkup:
    """Build a keyboard to select a specific VPN account for an action."""
    buttons = []
    for acc in accounts:
        label = f"{acc.name or 'VPN-' + acc.id.hex[:8]} ({acc.protocol.value.upper()})"
        buttons.append([
            InlineKeyboardButton(
                text=label,
                callback_data=f"vpn:{action}:{acc.id}",
            )
        ])
    buttons.append([
        InlineKeyboardButton(
            text=T_get("bot.vpn.btn_back"),
            callback_data="vpn:menu",
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _protocol_selection_keyboard(T_get) -> InlineKeyboardMarkup:
    """Build a keyboard for selecting VPN protocol."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="WireGuard",
                callback_data="vpn:create_protocol:wireguard",
            ),
            InlineKeyboardButton(
                text="VLESS+REALITY",
                callback_data="vpn:create_protocol:xray",
            ),
        ],
        [
            InlineKeyboardButton(
                text=T_get("bot.vpn.btn_back"),
                callback_data="vpn:menu",
            )
        ],
    ])


# ------------------------------------------------------------------
# Command: /vpn (Main Menu)
# ------------------------------------------------------------------

@router.message(Command("vpn"))
@router.message(F.text.lower().in_(["vpn", "/vpn", "🛡 vpn", "🛡 وی‌پی‌ان"]))
@require_auth
async def cmd_vpn_menu(message: Message, T, db_user, db_session) -> None:
    """Show the main VPN management menu."""
    if db_user is None:
        await message.answer(await T("bot.auth_required"))
        return

    accounts = await _get_user_vpn_accounts(db_session, db_user.id)
    summary = await _format_account_list(accounts, T, db_session)
    keyboard = _vpn_main_keyboard(T, len(accounts) > 0)

    await message.answer(summary, reply_markup=keyboard)


# ------------------------------------------------------------------
# Callback: Main Menu
# ------------------------------------------------------------------

@router.callback_query(F.data == "vpn:menu")
async def cb_vpn_menu(callback: CallbackQuery, T, db_user, db_session) -> None:
    """Return to VPN main menu."""
    await callback.answer()
    accounts = await _get_user_vpn_accounts(db_session, db_user.id)
    summary = await _format_account_list(accounts, T, db_session)
    keyboard = _vpn_main_keyboard(T, len(accounts) > 0)
    await callback.message.edit_text(summary, reply_markup=keyboard)


# ------------------------------------------------------------------
# Command: /vpn_create
# ------------------------------------------------------------------

@router.message(Command("vpn_create"))
@require_auth
async def cmd_vpn_create(message: Message, T, db_user, db_session) -> None:
    """Start VPN account creation by showing protocol selection."""
    if db_user is None:
        await message.answer(await T("bot.auth_required"))
        return

    await message.answer(
        await T("bot.vpn.select_protocol"),
        reply_markup=_protocol_selection_keyboard(T),
    )


# ------------------------------------------------------------------
# Callback: Create - Protocol Selection
# ------------------------------------------------------------------

@router.callback_query(F.data.startswith("vpn:create_protocol:"))
async def cb_vpn_create_protocol(
    callback: CallbackQuery, T, db_user, db_session
) -> None:
    """Handle protocol selection and create the VPN account."""
    await callback.answer()
    protocol_str = callback.data.split(":")[2]
    protocol = VpnProtocol(protocol_str)

    try:
        account = await VpnAccountService.create_account(
            db=db_session,
            user_id=db_user.id,
            protocol=protocol,
            name=f"{protocol.value.upper()}-{db_user.username or 'user'}",
        )
        await db_session.commit()

        success_text = await T(
            "bot.vpn.account_created",
            name=account.name,
            protocol=protocol.value.upper(),
            account_id=account.id.hex[:8],
        )
        await callback.message.edit_text(
            success_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=await T("bot.vpn.btn_get_config"),
                        callback_data=f"vpn:config:{account.id}",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text=await T("bot.vpn.btn_back"),
                        callback_data="vpn:menu",
                    ),
                ],
            ]),
        )
    except Exception as e:
        logger.error("VPN account creation failed: %s", e)
        error_text = await T("bot.vpn.create_error", error=str(e))
        await callback.message.edit_text(error_text)


# ------------------------------------------------------------------
# Callback: Create
# ------------------------------------------------------------------

@router.callback_query(F.data == "vpn:create")
async def cb_vpn_create_button(
    callback: CallbackQuery, T, db_user, db_session
) -> None:
    """Handle 'Create' button click from main menu."""
    await callback.answer()
    await callback.message.edit_text(
        await T("bot.vpn.select_protocol"),
        reply_markup=_protocol_selection_keyboard(T),
    )


# ------------------------------------------------------------------
# Command/Callback: List Accounts
# ------------------------------------------------------------------

@router.message(Command("vpn_list"))
@router.callback_query(F.data == "vpn:list")
@require_auth
async def cmd_vpn_list(
    event: Message | CallbackQuery, T, db_user, db_session
) -> None:
    """List all VPN accounts."""
    if db_user is None:
        if isinstance(event, Message):
            await event.answer(await T("bot.auth_required"))
        return

    if isinstance(event, CallbackQuery):
        await event.answer()
        target = event.message
    else:
        target = event

    accounts = await _get_user_vpn_accounts(db_session, db_user.id)
    summary = await _format_account_list(accounts, T, db_session)
    keyboard = _vpn_main_keyboard(T, len(accounts) > 0)
    await target.edit_text(summary, reply_markup=keyboard)


# ------------------------------------------------------------------
# Callback: Account Selection for Config
# ------------------------------------------------------------------

@router.callback_query(F.data == "vpn:select_config")
async def cb_vpn_select_config(
    callback: CallbackQuery, T, db_user, db_session
) -> None:
    """Show list of accounts to select for config download."""
    await callback.answer()
    accounts = await _get_user_vpn_accounts(db_session, db_user.id)
    if not accounts:
        await callback.message.edit_text(
            await T("bot.vpn.no_accounts"),
            reply_markup=_vpn_main_keyboard(T, False),
        )
        return
    await callback.message.edit_text(
        await T("bot.vpn.select_account_config"),
        reply_markup=_account_selection_keyboard(accounts, "config", T),
    )


# ------------------------------------------------------------------
# Callback: Account Selection for QR
# ------------------------------------------------------------------

@router.callback_query(F.data == "vpn:select_qr")
async def cb_vpn_select_qr(
    callback: CallbackQuery, T, db_user, db_session
) -> None:
    """Show list of accounts to select for QR code."""
    await callback.answer()
    accounts = await _get_user_vpn_accounts(db_session, db_user.id)
    if not accounts:
        await callback.message.edit_text(
            await T("bot.vpn.no_accounts"),
            reply_markup=_vpn_main_keyboard(T, False),
        )
        return
    await callback.message.edit_text(
        await T("bot.vpn.select_account_qr"),
        reply_markup=_account_selection_keyboard(accounts, "qr", T),
    )


# ------------------------------------------------------------------
# Callback: Account Selection for Renew
# ------------------------------------------------------------------

@router.callback_query(F.data == "vpn:select_renew")
async def cb_vpn_select_renew(
    callback: CallbackQuery, T, db_user, db_session
) -> None:
    """Show list of accounts to select for config renewal."""
    await callback.answer()
    accounts = await _get_user_vpn_accounts(db_session, db_user.id)
    if not accounts:
        await callback.message.edit_text(
            await T("bot.vpn.no_accounts"),
            reply_markup=_vpn_main_keyboard(T, False),
        )
        return
    await callback.message.edit_text(
        await T("bot.vpn.select_account_renew"),
        reply_markup=_account_selection_keyboard(accounts, "renew", T),
    )


# ------------------------------------------------------------------
# Callback: Account Selection for Delete
# ------------------------------------------------------------------

@router.callback_query(F.data == "vpn:select_delete")
async def cb_vpn_select_delete(
    callback: CallbackQuery, T, db_user, db_session
) -> None:
    """Show list of accounts to select for deletion."""
    await callback.answer()
    accounts = await _get_user_vpn_accounts(db_session, db_user.id)
    if not accounts:
        await callback.message.edit_text(
            await T("bot.vpn.no_accounts"),
            reply_markup=_vpn_main_keyboard(T, False),
        )
        return
    await callback.message.edit_text(
        await T("bot.vpn.select_account_delete"),
        reply_markup=_account_selection_keyboard(accounts, "delete", T),
    )


# ------------------------------------------------------------------
# Callback: Download Config
# ------------------------------------------------------------------

@router.callback_query(F.data.startswith("vpn:config:"))
async def cb_vpn_config(
    callback: CallbackQuery, T, db_user, db_session
) -> None:
    """Generate and send VPN configuration file for the selected account."""
    await callback.answer()
    account_id = UUID(callback.data.split(":")[2])

    result = await db_session.execute(
        select(VpnAccount).where(
            VpnAccount.id == account_id,
            VpnAccount.user_id == db_user.id,
        )
    )
    account = result.scalar_one_or_none()

    if not account:
        await callback.message.edit_text(
            await T("bot.vpn.account_not_found"),
            reply_markup=_vpn_main_keyboard(T, True),
        )
        return

    try:
        config_text = await VpnAccountService.generate_account_config(
            db_session, account_id
        )
        # Send as a downloadable file
        from io import BytesIO

        config_file = BytesIO(config_text.encode("utf-8"))
        config_file.name = f"vpn_{account.protocol.value}_{account.id.hex[:8]}.conf"

        await callback.message.answer_document(
            document=InputFile(config_file, filename=config_file.name),
            caption=await T(
                "bot.vpn.config_ready",
                protocol=account.protocol.value.upper(),
                name=account.name or "VPN",
            ),
        )
        await callback.message.edit_text(
            await T("bot.vpn.config_sent"),
            reply_markup=_vpn_main_keyboard(T, True),
        )
    except Exception as e:
        logger.error("VPN config generation failed: %s", e)
        await callback.message.edit_text(
            await T("bot.vpn.config_error", error=str(e)),
            reply_markup=_vpn_main_keyboard(T, True),
        )


# ------------------------------------------------------------------
# Callback: QR Code
# ------------------------------------------------------------------

@router.callback_query(F.data.startswith("vpn:qr:"))
async def cb_vpn_qr(
    callback: CallbackQuery, T, db_user, db_session
) -> None:
    """Generate and send QR code for the selected VPN account."""
    await callback.answer()
    account_id = UUID(callback.data.split(":")[2])

    result = await db_session.execute(
        select(VpnAccount).where(
            VpnAccount.id == account_id,
            VpnAccount.user_id == db_user.id,
        )
    )
    account = result.scalar_one_or_none()

    if not account:
        await callback.message.edit_text(
            await T("bot.vpn.account_not_found"),
            reply_markup=_vpn_main_keyboard(T, True),
        )
        return

    try:
        config_text = await VpnAccountService.generate_account_config(
            db_session, account_id
        )
        # Generate QR code image
        import io

        import qrcode

        qr_img = qrcode.make(config_text)
        buf = io.BytesIO()
        qr_img.save(buf, format="PNG")
        buf.seek(0)

        await callback.message.answer_photo(
            photo=InputFile(buf, filename=f"vpn_qr_{account.id.hex[:8]}.png"),
            caption=await T(
                "bot.vpn.qr_ready",
                name=account.name or "VPN",
                protocol=account.protocol.value.upper(),
            ),
        )
    except Exception as e:
        logger.error("VPN QR generation failed: %s", e)
        await callback.message.edit_text(
            await T("bot.vpn.qr_error", error=str(e)),
            reply_markup=_vpn_main_keyboard(T, True),
        )


# ------------------------------------------------------------------
# Callback: Renew Config
# ------------------------------------------------------------------

@router.callback_query(F.data.startswith("vpn:renew:"))
async def cb_vpn_renew(
    callback: CallbackQuery, T, db_user, db_session
) -> None:
    """Renew VPN configuration for the selected account."""
    await callback.answer()
    account_id = UUID(callback.data.split(":")[2])

    result = await db_session.execute(
        select(VpnAccount).where(
            VpnAccount.id == account_id,
            VpnAccount.user_id == db_user.id,
        )
    )
    account = result.scalar_one_or_none()

    if not account:
        await callback.message.edit_text(
            await T("bot.vpn.account_not_found"),
            reply_markup=_vpn_main_keyboard(T, True),
        )
        return

    try:
        await VpnAccountService.renew_account_config(db_session, account_id)
        await db_session.commit()

        await callback.message.edit_text(
            await T(
                "bot.vpn.renew_success",
                name=account.name or "VPN",
            ),
            reply_markup=_vpn_main_keyboard(T, True),
        )
    except Exception as e:
        logger.error("VPN config renewal failed: %s", e)
        await callback.message.edit_text(
            await T("bot.vpn.renew_error", error=str(e)),
            reply_markup=_vpn_main_keyboard(T, True),
        )


# ------------------------------------------------------------------
# Callback: Delete Account
# ------------------------------------------------------------------

@router.callback_query(F.data.startswith("vpn:delete:"))
async def cb_vpn_delete_confirm(
    callback: CallbackQuery, T, db_user, db_session
) -> None:
    """Show delete confirmation dialog."""
    await callback.answer()
    account_id = UUID(callback.data.split(":")[2])

    await callback.message.edit_text(
        await T("bot.vpn.delete_confirm", account_id=account_id.hex[:8]),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=await T("bot.vpn.btn_confirm_delete"),
                    callback_data=f"vpn:delete_confirm:{account_id}",
                ),
                InlineKeyboardButton(
                    text=await T("bot.vpn.btn_cancel"),
                    callback_data="vpn:menu",
                ),
            ],
        ]),
    )


@router.callback_query(F.data.startswith("vpn:delete_confirm:"))
async def cb_vpn_delete_execute(
    callback: CallbackQuery, T, db_user, db_session
) -> None:
    """Execute VPN account deletion."""
    await callback.answer()
    account_id = UUID(callback.data.split(":")[2])

    result = await db_session.execute(
        select(VpnAccount).where(
            VpnAccount.id == account_id,
            VpnAccount.user_id == db_user.id,
        )
    )
    account = result.scalar_one_or_none()

    if not account:
        await callback.message.edit_text(
            await T("bot.vpn.account_not_found"),
            reply_markup=_vpn_main_keyboard(T, True),
        )
        return

    try:
        await VpnAccountService.delete_account(db_session, account_id)
        await db_session.commit()
        await callback.message.edit_text(
            await T("bot.vpn.delete_success"),
            reply_markup=_vpn_main_keyboard(T, True),
        )
    except Exception as e:
        logger.error("VPN account deletion failed: %s", e)
        await callback.message.edit_text(
            await T("bot.vpn.delete_error", error=str(e)),
            reply_markup=_vpn_main_keyboard(T, True),
        )


# ------------------------------------------------------------------
# Callback: Traffic Statistics
# ------------------------------------------------------------------

@router.message(Command("vpn_stats"))
@router.callback_query(F.data == "vpn:stats")
@require_auth
async def cmd_vpn_stats(
    event: Message | CallbackQuery, T, db_user, db_session
) -> None:
    """Show traffic usage statistics for all VPN accounts."""
    if db_user is None:
        if isinstance(event, Message):
            await event.answer(await T("bot.auth_required"))
        return

    if isinstance(event, CallbackQuery):
        await event.answer()
        target = event.message
    else:
        target = event

    accounts = await _get_user_vpn_accounts(db_session, db_user.id)
    if not accounts:
        await target.edit_text(
            await T("bot.vpn.no_accounts"),
            reply_markup=_vpn_main_keyboard(T, False),
        )
        return

    total_dl = 0
    total_ul = 0
    stats_lines = [await T("bot.vpn.stats_header")]
    for acc in accounts:
        traffic = await VpnAccountService.get_account_traffic(db_session, acc.id)
        total_dl += traffic.total_download
        total_ul += traffic.total_upload
        dl_gb = traffic.total_download / (1024**3)
        ul_gb = traffic.total_upload / (1024**3)
        total_gb = dl_gb + ul_gb

        stats_lines.append(
            await T(
                "bot.vpn.stats_item",
                name=acc.name or f"VPN-{acc.id.hex[:8]}",
                protocol=acc.protocol.value.upper(),
                dl_gb=f"{dl_gb:.2f}",
                ul_gb=f"{ul_gb:.2f}",
                total_gb=f"{total_gb:.2f}",
            )
        )

    total_all = (total_dl + total_ul) / (1024**3)
    stats_lines.append(
        await T("bot.vpn.stats_total", total_gb=f"{total_all:.2f}")
    )

    await target.edit_text(
        "\n".join(stats_lines),
        reply_markup=_vpn_main_keyboard(T, True),
    )


__all__ = ["router"]
