from pydantic import BaseModel


class GmailCreds(BaseModel):
    email: str
    password: str
