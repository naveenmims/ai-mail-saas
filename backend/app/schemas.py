from pydantic import BaseModel

class OrganizationCreate(BaseModel):
    name: str
class UserCreate(BaseModel):
    org_id: int
    email: str
    password: str
    role: str = "owner"
class LoginRequest(BaseModel):
    email: str
    password: str
class EmailAccountCreate(BaseModel):
    label: str = "Primary"
    email: str
    imap_host: str
    imap_port: int = 993
    imap_username: str
    imap_password: str
    sendgrid_api_key: str
    from_name: str = "AI Mail SaaS"

class EmailAccountOut(BaseModel):
    id: int
    org_id: int
    label: str
    email: str
    imap_host: str
    imap_port: int
    imap_username: str
    from_name: str
