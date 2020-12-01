import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram.error import BadRequest
from telegram.ext import run_async, CommandHandler, Filters
from telegram.utils.helpers import mention_html
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, User, CallbackQuery

from tg_bot import dispatcher, BAN_STICKER, LOGGER
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import bot_admin, user_admin, is_user_ban_protected, can_restrict, \
    is_user_admin, is_user_in_chat, is_bot_admin
from tg_bot.modules.helper_funcs.extraction import extract_user_and_text
from tg_bot.modules.helper_funcs.string_handling import extract_time
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.helper_funcs.filters import CustomFilters

RBAN_ERRORS = {
    "Kullanıcı sohbetin yöneticisidir!",
    "Sohbet bulunamadı",
    "Sohbet üyesini kısıtlamak için yeterli hak yok",
    "Kullanıcı bu grupta değil",
    "ID kimliği geçersiz",
    "Grup sohbeti devre dışı bırakıldı!",
    "Need to be inviter of a user to kick it from a basic group",
    "Sohbet yöneticiliği gerekli",
    "Yalnızca grubu oluşturan kişi grup yöneticilerini atabilir",
    "Kanal özel(!)",
    "Sohbette değil"
}

RUNBAN_ERRORS = {
    "Kullanıcı sohbetin yöneticisidir!",
    "Sohbet bulunamadı",
    "Sohbet üyesini kısıtlamak için yeterli hak yok",
    "Kullanıcı bu grupta değil",
    "ID kimliği geçersiz",
    "Grup sohbeti devre dışı bırakıldı!",
    "Need to be inviter of a user to kick it from a basic group",
    "Sohbet yöneticiliği gerekli",
    "Yalnızca grubu oluşturan kişi grup yöneticilerini atabilir",
    "Kanal özel(!)",
    "Sohbette değil"
}



@run_async
@bot_admin
@can_restrict
@user_admin
@loggable
def ban(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Bir kullanıcıya atıfta bulunmuyorsunuz.")
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "Kullanıcı bulunamadı!":
            message.reply_text("Bu kullanıcıyı bulamıyorum.")
            return ""
        else:
            raise

    if is_user_ban_protected(chat, user_id, member):
        message.reply_text("Yöneticileri yasaklayabilmeyi gerçekten çok isterdim ...")
        return ""

    if user_id == bot.id:
        message.reply_text("Ben kendimi banlamayacağım, deli misin?")
        return ""

    log = "<b>{}:</b>" \
          "\n#BANNED" \
          "\n<b>Admin:</b> {}" \
          "\n<b>User:</b> {}".format(html.escape(chat.title), mention_html(user.id, user.first_name),
                                     mention_html(member.user.id, member.user.first_name))
    if reason:
        log += "\n<b>Nedeni:</b> {}".format(reason)

    try:
        chat.kick_member(user_id)
        bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        keyboard = []
        reply = "{} Yasaklandı!".format(mention_html(member.user.id, member.user.first_name))
        message.reply_text(reply, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        return log

    except BadRequest as excp:
        if excp.message == "Yanıtlanan mesaj bulunamadı!":
            # Do not reply
            message.reply_text('Yasaklandı!', quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR: kullanıcıyı yasaklayan %s in chat %s (%s) due to %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("Kahretsin, o kullanıcıyı yasaklayamam.")

    return ""


@run_async
@bot_admin
@can_restrict
@user_admin
@loggable
def temp_ban(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Bir kullanıcıya atıfta bulunmuyorsunuz.")
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "kullanıcı bulunamadı!":
            message.reply_text("Bu kullanıcıyı bulamıyorum")
            return ""
        else:
            raise

    if is_user_ban_protected(chat, user_id, member):
        message.reply_text("Yöneticileri yasaklayabilmeyi gerçekten çok isterdim ...")
        return ""

    if user_id == bot.id:
        message.reply_text("Kendimi yasaklayamam. Sanırım beni sevmedin?")
        return ""

    if not reason:
        message.reply_text("Bu kullanıcıyı yasaklamak için bir zaman belirtmediniz!")
        return ""

    split_reason = reason.split(None, 1)

    time_val = split_reason[0].lower()
    if len(split_reason) > 1:
        reason = split_reason[1]
    else:
        reason = ""

    bantime = extract_time(message, time_val)

    if not bantime:
        return ""

    log = "<b>{}:</b>" \
          "\n#TEMP BANNED" \
          "\n<b>Admin:</b> {}" \
          "\n<b>User:</b> {}" \
          "\n<b>Time:</b> {}".format(html.escape(chat.title), mention_html(user.id, user.first_name),
                                     mention_html(member.user.id, member.user.first_name), time_val)
    if reason:
        log += "\n<b>Nedeni:</b> {}".format(reason)

    try:
        chat.kick_member(user_id, until_date=bantime)
        bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        message.reply_text("Yasaklandı! Kullanıcı {} için yasaklanacak.".format(time_val))
        return log

    except BadRequest as excp:
        if excp.message == "Yanıtlanan mesaj bulununamadı!":
            # Do not reply
            message.reply_text("Yasaklandı! Kullanıcı {} için yasaklanacak!.".format(time_val), quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR kullanıcıyı yasaklayan %s in chat %s (%s) due to %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("Kahretsin, o kullanıcıyı yasaklayamam.")

    return ""


@run_async
@bot_admin
@can_restrict
@user_admin
@loggable
def kick(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found - Kullanıcı bulunamadı!":
            message.reply_text("Bu kullanıcıyı bulamıyorum")
            return ""
        else:
            raise

    if is_user_ban_protected(chat, user_id):
        message.reply_text("Keşke yöneticileri tekmeleyebilseydim ...")
        return ""

    if user_id == bot.id:
        message.reply_text("Evetttt, bunu yapmayacağım")
        return ""

    res = chat.unban_member(user_id)  # unban on current user = kick
    if res:
        bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        message.reply_text("Gruptan !")
        log = "<b>{}:</b>" \
              "\n#KICKED" \
              "\n<b>Admin:</b> {}" \
              "\n<b>User:</b> {}".format(html.escape(chat.title),
                                         mention_html(user.id, user.first_name),
                                         mention_html(member.user.id, member.user.first_name))
        if reason:
            log += "\n<b>Sebep:</b> {}".format(reason)

        return log

    else:
        message.reply_text("Lanet olsun, o kullanıcıyı gruptan atamam:(")

    return ""


@run_async
@bot_admin
@can_restrict
def kickme(bot: Bot, update: Update):
    user_id = update.effective_message.from_user.id
    if is_user_admin(update.effective_chat, user_id):
        update.effective_message.reply_text("Keşke yapabilseydim ... ama sen bir yöneticisin.")
        return

    res = update.effective_chat.unban_member(user_id)  # unban on current user = kick
    if res:
        update.effective_message.reply_text("Sorun değil.")
    else:
        update.effective_message.reply_text("Huh? Yapamam :/")


@run_async
@bot_admin
@can_restrict
@user_admin
@loggable
def unban(bot: Bot, update: Update, args: List[str]) -> str:
    message = update.effective_message  # type: Optional[Message]
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "Kimden bahsettiğin hakkında bir fikrim yok":
            message.reply_text("Bu kullanıcıyı bulamıyorum!")
            return ""
        else:
            raise

    if user_id == bot.id:
        message.reply_text("!Burada olmasaydım kendimi nasıl kaldırırdım ...?")
        return ""

    if is_user_in_chat(chat, user_id):
        message.reply_text("Zaten sohbette olan birinin yasağını neden kaldırmaya çalışıyorsun?")
        return ""

    chat.unban_member(user_id)
    message.reply_text("Evet, bu kullanıcı tekrardan katılabilir! rtık kendini nasıl affettirdiyse jslshdlsj")

    log = "<b>{}:</b>" \
          "\n#UNBANNED" \
          "\n<b>Admin:</b> {}" \
          "\n<b>User:</b> {}".format(html.escape(chat.title),
                                     mention_html(user.id, user.first_name),
                                     mention_html(member.user.id, member.user.first_name))
    if reason:
        log += "\n<b>Sebep:</b> {}".format(reason)

    return log


@run_async
@bot_admin
def rban(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message

    if not args:
        message.reply_text("Görünüşe göre bir sohbetten / kullanıcıdan bahsetmiyorsunuz.")
        return

    user_id, chat_id = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Bir kullanıcıya atıfta bulunmuyorsunuz.")
        return
    elif not chat_id:
        message.reply_text("Görünüşe göre bir sohbetten bahsetmiyorsun.")
        return

    try:
        chat = bot.get_chat(chat_id.split()[0])
    except BadRequest as excp:
        if excp.message == "Sohbet bulunamadı":
            message.reply_text("Sohbet bulunamadı! Geçerli bir sohbet kimliği girdiğinizden emin olun ve ben de o sohbetin bir parçasıyım.🥰")
            return
        else:
            raise

    if chat.type == 'private':
        message.reply_text("Üzgünüm ama bu özel bir sohbet🦍!")
        return

    if not is_bot_admin(chat, bot.id) or not chat.get_member(bot.id).can_restrict_members:
        message.reply_text("Oradaki insanları kısıtlayamam! Yönetici olduğumdan ve kullanıcıları yasaklayabileceğimden emin olun.🥴")
        return

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "Kullanıcı bulunamadı! ID doğrumu?":
            message.reply_text("Bu kullanıcıyı bulamıyorum!")
            return
        else:
            raise

    if is_user_ban_protected(chat, user_id, member):
        message.reply_text("Yöneticileri yasaklayabilmeyi gerçekten çok isterdim ...🦍")
        return

    if user_id == bot.id:
        message.reply_text("Kendimi banlayamam, deli misin? Beni sevmiyorsun galiba! Hıh🥺")
        return

    try:
        chat.kick_member(user_id)
        message.reply_text("Yasaklandı!")
    except BadRequest as excp:
        if excp.message == "Yanıtlanan mesaj nerde? Bulamadım.":
            # Do not reply
            message.reply_text('Yasaklandı, puhahah!', quote=False)
        elif excp.message in RBAN_ERRORS:
            message.reply_text(excp.message)
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR banning user %s in chat %s (%s) due to %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("Kahretsin, o kullanıcıyı yasaklayamam.")

@run_async
@bot_admin
def runban(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message

    if not args:
        message.reply_text("Görünüşe göre bir sohbetten / kullanıcıdan bahsetmiyorsunuz.")
        return

    user_id, chat_id = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Bir kullanıcıya atıfta bulunmuyorsunuz.")
        return
    elif not chat_id:
        message.reply_text("Görünüşe göre bir sohbetten bahsetmiyorsun.")
        return

    try:
        chat = bot.get_chat(chat_id.split()[0])
    except BadRequest as excp:
        if excp.message == "Çet bulunamadı":
            message.reply_text("Sohbet bulunamadı! Geçerli bir sohbet kimliği girdiğinizden emin olun ve ben de o sohbetin bir parçasıyım.🦍")
            return
        else:
            raise

    if chat.type == 'private':
        message.reply_text("Üzgünüm, ama burası özel mesaj!")
        return

    if not is_bot_admin(chat, bot.id) or not chat.get_member(bot.id).can_restrict_members:
        message.reply_text("Oradaki insanları kısıtlayamam! Yönetici olduğumdan ve kullanıcıların yasağını kaldırabileceğinden emin olun.")
        return

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "Kullanıcı yko":
            message.reply_text("Bu kullanıcıyı orada bulamıyorum")
            return
        else:
            raise
            
    if is_user_in_chat(chat, user_id):
        message.reply_text("Zaten o sohbette olan birinin yasağını neden uzaktan kaldırmaya çalışıyorsun?")
        return

    if user_id == bot.id:
        message.reply_text("BUNU KALDIRMAYACAĞIM, orada bir yöneticiyim!")
        return

    try:
        chat.unban_member(user_id)
        message.reply_text("Kullanıcı tekrardan katılabilir!")
    except BadRequest as excp:
        if excp.message == "Yanıtlanan mesaj bulunamadı":
            # Do not reply
            message.reply_text('Yasak kaldırıldı!', quote=False)
        elif excp.message in RUNBAN_ERRORS:
            message.reply_text(excp.message)
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR unbanning user %s in chat %s (%s) due to %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("Lanet olsun, o kullanıcının yasağını kaldıramam.")


__help__ = """
 - /kickme: komutu veren kullanıcıyı atar!

*Sadece adminler:*
 - /ban <username>: kullanıcıyı banlar. (Kullanıcı adını yazın, veya mesajını yanıtlayın)
 - /tban <username> x(m/h/d): kullanıcyı . (belirt veya yanıtla). m = dakika, h = saat, d = gün.
 - /unban <username>: bir kullanıcının yasağını kaldırır. (belirt veya yanıt yoluyla)
 - /kick <username>: bir kullanıcıyı gruptan at (Belirt veya yanıt yoluyla)
"""

__mod_name__ = "Bans"

BAN_HANDLER = CommandHandler("ban", ban, pass_args=True, filters=Filters.group)
TEMPBAN_HANDLER = CommandHandler(["tban", "tempban"], temp_ban, pass_args=True, filters=Filters.group)
KICK_HANDLER = CommandHandler("kick", kick, pass_args=True, filters=Filters.group)
UNBAN_HANDLER = CommandHandler("unban", unban, pass_args=True, filters=Filters.group)
KICKME_HANDLER = DisableAbleCommandHandler("kickme", kickme, filters=Filters.group)
RBAN_HANDLER = CommandHandler("rban", rban, pass_args=True, filters=CustomFilters.sudo_filter)
RUNBAN_HANDLER = CommandHandler("runban", runban, pass_args=True, filters=CustomFilters.sudo_filter)

dispatcher.add_handler(BAN_HANDLER)
dispatcher.add_handler(TEMPBAN_HANDLER)
dispatcher.add_handler(KICK_HANDLER)
dispatcher.add_handler(UNBAN_HANDLER)
dispatcher.add_handler(KICKME_HANDLER)
dispatcher.add_handler(RBAN_HANDLER)
dispatcher.add_handler(RUNBAN_HANDLER)
