from pydantic import BaseModel, Field


class TelegramChat(BaseModel):
    id: int


class TelegramVoice(BaseModel):
    file_id: str


class TelegramPhoto(BaseModel):
    file_id: str
    width: int
    height: int


class TelegramUser(BaseModel):
    id: int
    is_bot: bool
    first_name: str
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None


class TelegramMessage(BaseModel):
    chat: TelegramChat
    from_user: TelegramUser | None = Field(None, alias="from")
    date: int | None = None
    voice: TelegramVoice | None = None
    text: str | None = None
    photo: list[TelegramPhoto] | None = None
    caption: str | None = None


class TelegramUpdate(BaseModel):
    """
    Modela la estructura de una actualización entrante de un webhook de Telegram.
    Se enfoca específicamente en capturar mensajes de voz.
    """

    update_id: int
    message: TelegramMessage | None = None
