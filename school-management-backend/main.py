import os
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import JSON, Boolean, DateTime, Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


def _parse_origins() -> list[str]:
    raw = os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,https://dev-sms.klopterz.in",
    )
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./sms_dev.db",
)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-dev-secret")
ACCESS_TOKEN_EXPIRES_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRES_MINUTES", "60"))
REFRESH_TOKEN_EXPIRES_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRES_DAYS", "14"))

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    first_name: Mapped[str] = mapped_column(String(100), default="System")
    last_name: Mapped[str] = mapped_column(String(100), default="Admin")
    phone: Mapped[str] = mapped_column(String(30), default="")
    role: Mapped[str] = mapped_column(String(50), default="SUPER_ADMIN")
    plan: Mapped[str] = mapped_column(String(50), default="standard")
    school_id: Mapped[int] = mapped_column(Integer, default=1)
    school_code: Mapped[str] = mapped_column(String(100), default="SMS001")
    school_name: Mapped[str] = mapped_column(String(255), default="Edusphere School")
    skid: Mapped[str] = mapped_column(String(100), default="SMS001")
    school_user_id: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ResourceRecord(Base):
    __tablename__ = "resource_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resource: Mapped[str] = mapped_column(String(100), index=True)
    skid: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


engine_kwargs = {"future": True}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")


def _unauthorized(detail: str = "Invalid authentication credentials") -> HTTPException:
    return HTTPException(status_code=401, detail=detail)


def decode_bearer_token(authorization: str | None) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise _unauthorized("Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
    except JWTError as exc:
        raise _unauthorized("Invalid token") from exc


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_bearer_token(authorization)
    if payload.get("type") != "access":
        raise _unauthorized("Invalid access token")
    user_id = payload.get("sub")
    if not user_id:
        raise _unauthorized()
    user = db.get(User, int(user_id))
    if not user or not user.is_active:
        raise _unauthorized("User not found or inactive")
    return user


def role_obj_for(role_code: str) -> dict[str, Any]:
    return {
        "id": 1,
        "role_code": role_code,
        "role_name": role_code.replace("_", " ").title(),
        "is_active": True,
        "is_system_role": role_code in {"SUPER_ADMIN", "SCHOOL_ADMIN"},
        "school_id": 1,
        "permissions": ["*"],
    }


def current_year_payload() -> dict[str, Any]:
    return {
        "id": 1,
        "year_name": "2026-2027",
        "start_date": "2026-04-01",
        "end_date": "2027-03-31",
        "is_active": True,
        "is_current": True,
    }


def auth_user_payload(user: User) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    current_year = current_year_payload()
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "name": f"{user.first_name} {user.last_name}".strip(),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": f"{user.first_name} {user.last_name}".strip(),
        "phone": user.phone,
        "role": user.role,
        "is_active": user.is_active,
        "plan": user.plan,
        "school_id": user.school_id,
        "school_code": user.school_code,
        "school_name": user.school_name,
        "school_logo": "",
        "school_address": "",
        "school_phone": "",
        "school_email": "",
        "skid": user.skid,
        "school_user_id": user.school_user_id,
        "role_obj": role_obj_for(user.role),
        "academicYear": current_year["id"],
        "academic_year": current_year["id"],
        "current_academic_year": current_year,
        "academic_years": [current_year],
        "created_at": user.created_at.isoformat() if user.created_at else now,
        "updated_at": user.updated_at.isoformat() if user.updated_at else now,
        "last_login": user.last_login.isoformat() if user.last_login else now,
    }


def ok_response(
    *,
    data: Any = None,
    code: int = 200,
    message: str = "Success",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "code": code,
        "status": "success",
        "message": message,
        "data": data if data is not None else {},
    }
    if extra:
        payload.update(extra)
    return payload


def get_records(db: Session, resource: str, skid: str | None = None) -> list[ResourceRecord]:
    stmt = select(ResourceRecord).where(ResourceRecord.resource == resource)
    if skid:
        stmt = stmt.where(ResourceRecord.skid == skid)
    return list(db.scalars(stmt))


def create_record(
    db: Session,
    resource: str,
    payload: dict[str, Any],
    skid: str | None = None,
) -> ResourceRecord:
    record = ResourceRecord(resource=resource, skid=skid, payload=payload)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def update_record(db: Session, record_id: int, payload: dict[str, Any]) -> ResourceRecord:
    record = db.get(ResourceRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    record.payload = {**record.payload, **payload}
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def record_to_dict(record: ResourceRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "resource": record.resource,
        "skid": record.skid,
        "is_active": record.is_active,
        **(record.payload or {}),
    }


def resource_alias(resource: str) -> str:
    aliases = {
        "attendance": "attendance",
        "announcements": "announcements",
        "marks": "marks",
        "users": "users",
        "parents": "parents",
        "teachers": "teachers",
        "students": "students",
        "classes": "classes",
        "subjects": "subjects",
        "roles": "roles",
        "rooms": "rooms",
        "seating": "seating",
        "syllabus": "syllabus",
        "fees": "fees",
        "timetable": "timetable",
        "assignments": "assignments",
        "staff": "staff",
        "institutions": "institutions",
        "exams": "exams",
        "progress": "progress",
        "progress-cards": "progress_cards",
    }
    return aliases.get(resource, resource)


def list_response_payload(
    *,
    resource: str,
    items: list[dict[str, Any]],
    page: int = 1,
    limit: int | None = None,
) -> dict[str, Any]:
    total = len(items)
    safe_limit = limit if limit and limit > 0 else (total if total > 0 else 1)
    total_pages = max((total + safe_limit - 1) // safe_limit, 1)
    alias = resource_alias(resource)
    return ok_response(
        data=items,
        extra={
            alias: items,
            "total": total,
            "page": page,
            "limit": safe_limit,
            "totalPages": total_pages,
            "meta": {
                "total": total,
                "page": page,
                "limit": safe_limit,
                "totalPages": total_pages,
            },
        },
    )


class LoginRequest(BaseModel):
    identifier: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    password: str
    password_confirmation: str


app = FastAPI(title="School Management System API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        exists = db.scalar(select(User).where(User.username == "admin"))
        if not exists:
            db.add(
                User(
                    username="admin",
                    email="admin@school.com",
                    password_hash=get_password_hash("admin123"),
                    first_name="Super",
                    last_name="Admin",
                    role="SUPER_ADMIN",
                    school_name="Edusphere School",
                    school_code="EDU001",
                    skid="EDU001",
                )
            )
            db.commit()
    finally:
        db.close()


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "databaseConfigured": bool(DATABASE_URL)}


@app.get("/api/health")
def api_health() -> dict[str, Any]:
    return health()


@app.post("/api/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    stmt = select(User).where(
        (User.username == payload.identifier) | (User.email == payload.identifier)
    )
    user = db.scalar(stmt)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username/email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is inactive")

    user.last_login = datetime.now(UTC)
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "access_token": create_token(
            str(user.id), "access", timedelta(minutes=ACCESS_TOKEN_EXPIRES_MINUTES)
        ),
        "refresh_token": create_token(
            str(user.id), "refresh", timedelta(days=REFRESH_TOKEN_EXPIRES_DAYS)
        ),
        "message": "Login successful",
        "user": auth_user_payload(user),
    }


@app.post("/api/auth/logout")
def logout(_: User = Depends(get_current_user)) -> dict[str, Any]:
    return {"success": True, "message": "Logout successful"}


@app.post("/api/auth/refresh")
def refresh_token(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    payload = decode_bearer_token(authorization)
    if payload.get("type") != "refresh":
        raise _unauthorized("Invalid refresh token")
    user = db.get(User, int(payload.get("sub", 0)))
    if not user or not user.is_active:
        raise _unauthorized("User not found or inactive")
    return {
        "access_token": create_token(
            str(user.id), "access", timedelta(minutes=ACCESS_TOKEN_EXPIRES_MINUTES)
        ),
        "refresh_token": create_token(
            str(user.id), "refresh", timedelta(days=REFRESH_TOKEN_EXPIRES_DAYS)
        ),
        "message": "Token refreshed successfully",
    }


@app.post("/api/auth/forgot-password")
def forgot_password(_: ForgotPasswordRequest) -> dict[str, Any]:
    return {"success": True, "message": "Password reset link sent if account exists"}


@app.post("/api/auth/reset-password")
def reset_password(_: ResetPasswordRequest) -> dict[str, Any]:
    return {"success": True, "message": "Password has been reset successfully"}


@app.post("/api/auth/signup")
def signup(payload: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, Any]:
    email = payload.get("email")
    username = payload.get("username") or email
    password = payload.get("password")
    if not email or not username or not password:
        raise HTTPException(status_code=400, detail="email, username, and password are required")

    exists = db.scalar(select(User).where((User.email == email) | (User.username == username)))
    if exists:
        raise HTTPException(status_code=409, detail="User already exists")

    first_name = payload.get("first_name") or payload.get("name") or "User"
    last_name = payload.get("last_name") or ""
    role = payload.get("role") or "SCHOOL_ADMIN"

    user = User(
        username=username,
        email=email,
        password_hash=get_password_hash(password),
        first_name=first_name,
        last_name=last_name,
        role=role,
        school_name=payload.get("school_name", "Edusphere School"),
        school_code=payload.get("school_code", "EDU001"),
        skid=payload.get("skid", "EDU001"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "access_token": create_token(
            str(user.id), "access", timedelta(minutes=ACCESS_TOKEN_EXPIRES_MINUTES)
        ),
        "refresh_token": create_token(
            str(user.id), "refresh", timedelta(days=REFRESH_TOKEN_EXPIRES_DAYS)
        ),
        "message": "Signup successful",
        "user": auth_user_payload(user),
    }


@app.get("/api/institutions")
@app.get("/api/users")
@app.get("/api/students")
@app.get("/api/teachers")
@app.get("/api/classes")
@app.get("/api/subjects")
@app.get("/api/attendance")
@app.get("/api/exams")
@app.get("/api/marks")
@app.get("/api/fees")
@app.get("/api/timetable")
@app.get("/api/progress-cards")
def list_resources(request: Request, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    resource = request.url.path.split("/")[-1]
    records = [record_to_dict(r) for r in get_records(db, resource)]
    page = int(request.query_params.get("page", 1))
    limit = int(request.query_params.get("limit", 20))
    return list_response_payload(resource=resource, items=records, page=page, limit=limit)


@app.post("/api/institutions")
@app.post("/api/users")
@app.post("/api/students")
@app.post("/api/teachers")
@app.post("/api/classes")
@app.post("/api/subjects")
@app.post("/api/attendance")
@app.post("/api/exams")
@app.post("/api/marks")
@app.post("/api/fees")
@app.post("/api/timetable")
@app.post("/api/progress-cards")
def create_resources(
    request: Request, payload: dict[str, Any], db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    resource = request.url.path.split("/")[-1]
    record = create_record(db, resource, payload)
    return ok_response(data=record_to_dict(record), message=f"{resource} created")


@app.get("/api/institutions/{item_id}")
@app.get("/api/users/{item_id}")
@app.get("/api/students/{item_id}")
@app.get("/api/teachers/{item_id}")
@app.get("/api/classes/{item_id}")
@app.get("/api/subjects/{item_id}")
@app.get("/api/attendance/{item_id}")
@app.get("/api/exams/{item_id}")
@app.get("/api/marks/{item_id}")
@app.get("/api/fees/{item_id}")
@app.get("/api/timetable/{item_id}")
@app.get("/api/progress-cards/{item_id}")
def get_resource_item(
    request: Request, item_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    resource = request.url.path.split("/")[-2]
    record = db.get(ResourceRecord, item_id)
    if not record or record.resource != resource:
        raise HTTPException(status_code=404, detail="Item not found")
    item = record_to_dict(record)
    extra = {}
    if resource == "teachers":
        extra["teacher_data"] = item
    if resource == "students":
        extra["student"] = item
    if resource == "classes":
        extra["class"] = item
    if resource == "users":
        extra["user"] = item
    return ok_response(data=item, extra=extra)


@app.get("/api/classes/list/{skid}")
def list_classes_by_school(skid: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    classes = [record_to_dict(r) for r in get_records(db, "classes", skid)]
    if not classes:
        classes = [record_to_dict(r) for r in get_records(db, "classes")]
    return ok_response(data=classes)


@app.get("/api/classes/sections/{skid}/{class_id}")
def list_sections_by_class(
    skid: str,
    class_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    sections = [
        record_to_dict(r)
        for r in get_records(db, "sections", skid)
        if int((r.payload or {}).get("class_id", class_id)) == class_id
    ]
    if not sections:
        sections = [{"id": 1, "name": "A", "class_id": class_id, "skid": skid}]
    return ok_response(data=sections)


@app.put("/api/institutions/{item_id}")
@app.put("/api/users/{item_id}")
@app.put("/api/students/{item_id}")
@app.put("/api/teachers/{item_id}")
@app.put("/api/classes/{item_id}")
@app.put("/api/subjects/{item_id}")
@app.put("/api/attendance/{item_id}")
@app.put("/api/exams/{item_id}")
@app.put("/api/marks/{item_id}")
@app.put("/api/fees/{item_id}")
@app.put("/api/timetable/{item_id}")
@app.put("/api/progress-cards/{item_id}")
def update_resource_item(
    item_id: int, payload: dict[str, Any], db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    record = update_record(db, item_id, payload)
    item = record_to_dict(record)
    extra = {}
    if record.resource == "users":
        extra["user"] = item
    if record.resource == "students":
        extra["student"] = item
    if record.resource == "teachers":
        extra["teacher_data"] = item
    if record.resource == "classes":
        extra["class"] = item
    return ok_response(data=item, message="Updated successfully", extra=extra)


@app.delete("/api/institutions/{item_id}")
@app.delete("/api/users/{item_id}")
@app.delete("/api/students/{item_id}")
@app.delete("/api/teachers/{item_id}")
@app.delete("/api/classes/{item_id}")
@app.delete("/api/subjects/{item_id}")
@app.delete("/api/attendance/{item_id}")
@app.delete("/api/exams/{item_id}")
@app.delete("/api/marks/{item_id}")
@app.delete("/api/fees/{item_id}")
@app.delete("/api/timetable/{item_id}")
@app.delete("/api/progress-cards/{item_id}")
def delete_resource_item(item_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    record = db.get(ResourceRecord, item_id)
    if not record:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(record)
    db.commit()
    return ok_response(message="Deleted successfully")


@app.get("/api/super-admin/stats")
def super_admin_stats(_: User = Depends(get_current_user)):
    return ok_response(
        data={
            "total_schools": 1,
            "active_schools": 1,
            "total_users": 1,
            "active_users": 1,
        }
    )


@app.get("/api/schoolAdminDashboard/stats/{skid}")
@app.get("/api/schoolAdminDashboard/attendance-overview/{skid}")
@app.get("/api/schoolAdminDashboard/finance-summary/{skid}")
@app.get("/api/schoolAdminDashboard/breakdown/monthly/{skid}")
@app.get("/api/schoolAdminDashboard/timetable/{skid}")
def school_admin_dashboard(skid: str, _: User = Depends(get_current_user)):
    return ok_response(data={"skid": skid, "summary": {}})


@app.get("/api/teacherDashboard/students/teacher/count/{skid}/{teacher_id}")
@app.get("/api/teacherDashboard/attendance/absentees/count/{skid}/{academic_year_id}/{date}")
@app.get("/api/teacherDashboard/timetable/teacher/{skid}/{teacher_id}/{date}")
@app.get("/api/teacherDashboard/timetable/teacher/week/{skid}/{teacher_id}")
def teacher_dashboard(
    skid: str,
    teacher_id: int,
    _: User = Depends(get_current_user),
):
    return ok_response(data={"skid": skid, "teacher_id": teacher_id, "items": []})


@app.get("/api/timeTable/student/{skid}/{student_id}/{date}")
def student_day_timetable(skid: str, student_id: int, date: str, _: User = Depends(get_current_user)):
    return ok_response(data={"skid": skid, "student_id": student_id, "date": date, "slots": []})


@app.get("/api/educator/dashboard")
@app.get("/api/learner/dashboard")
@app.get("/api/guardian/dashboard")
def legacy_dashboards(_: User = Depends(get_current_user)):
    return ok_response(data={"stats": {}})


@app.get("/api/announcements/list/{skid}")
def list_announcements(skid: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    records = [record_to_dict(r) for r in get_records(db, "announcements", skid)]
    return list_response_payload(resource="announcements", items=records)


@app.post("/api/announcements/create/{skid}")
def create_announcement(
    skid: str, payload: dict[str, Any], db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    record = create_record(db, "announcements", payload, skid=skid)
    return ok_response(
        code=201,
        data=record_to_dict(record),
        message="Announcement created",
    )


@app.get("/api/academic-years")
def list_academic_years(_: User = Depends(get_current_user)):
    year = current_year_payload()
    return ok_response(data=[year])


@app.post("/api/academic-years/create/{skid}")
def create_academic_year(skid: str, payload: dict[str, Any], _: User = Depends(get_current_user)):
    year = {
        "id": int(datetime.now(UTC).timestamp()),
        "year_name": payload.get("year_name", "New Academic Year"),
        "start_date": payload.get("start_date", "2026-04-01"),
        "end_date": payload.get("end_date", "2027-03-31"),
        "is_active": True,
        "is_current": False,
        "skid": skid,
    }
    return ok_response(data=year, message="Academic year created")


@app.put("/api/academic-years/update/{skid}/{year_id}")
def update_academic_year(
    skid: str, year_id: str, payload: dict[str, Any], _: User = Depends(get_current_user)
):
    return ok_response(data={"id": year_id, "skid": skid, **payload}, message="Academic year updated")


@app.patch("/api/academic-years/patch/{skid}/{year_id}/set-current")
def set_current_academic_year(skid: str, year_id: str, _: User = Depends(get_current_user)):
    return ok_response(
        data={"id": year_id, "skid": skid, "is_current": True},
        message="Current academic year updated",
    )


@app.post("/api/staff/create/{skid}")
def create_staff(skid: str, payload: dict[str, Any], db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    record = create_record(db, "staff", payload, skid=skid)
    return ok_response(data=record_to_dict(record), message="Staff created")


@app.get("/api/staff/list/{skid}")
def list_staff(skid: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    records = [record_to_dict(r) for r in get_records(db, "staff", skid)]
    return ok_response(data=records)


@app.post("/api/bus-scan/scan/{skid}")
@app.post("/api/bus-scan/scan-qr/{skid}")
def bus_scan(skid: str, payload: dict[str, Any], _: User = Depends(get_current_user)):
    return ok_response(data={"skid": skid, "scan": payload}, message="Scan recorded")


@app.get("/api/bus-scan/today/{skid}")
@app.get("/api/bus-scan/status/{skid}")
def bus_scan_today(skid: str, _: User = Depends(get_current_user)):
    return ok_response(data={"skid": skid, "records": []})


@app.get("/api/bus-scan/student/{skid}/{student_user_id}")
def bus_scan_student_history(skid: str, student_user_id: int, _: User = Depends(get_current_user)):
    return ok_response(data={"skid": skid, "student_user_id": student_user_id, "records": []})


@app.get("/api/bus-scan/search-students/{skid}")
def bus_scan_search_students(skid: str, _: User = Depends(get_current_user)):
    return ok_response(data={"skid": skid, "students": []})


@app.get("/api/assignments/teacher-classes")
def assignment_teacher_classes(_: User = Depends(get_current_user)):
    return ok_response(data=[])


@app.post("/api/assignments/create")
def assignment_create(payload: dict[str, Any], db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    record = create_record(db, "assignments", payload)
    return ok_response(data=record_to_dict(record), message="Assignment created")


@app.put("/api/assignments/update/{assignment_id}")
def assignment_update(
    assignment_id: int, payload: dict[str, Any], db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    record = update_record(db, assignment_id, payload)
    return ok_response(data=record_to_dict(record), message="Assignment updated")


@app.get("/api/assignments/list")
def assignment_list(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    records = [record_to_dict(r) for r in get_records(db, "assignments")]
    return ok_response(data=records)


@app.get("/api/assignments/{assignment_id}")
def assignment_get(assignment_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    record = db.get(ResourceRecord, assignment_id)
    if not record or record.resource != "assignments":
        raise HTTPException(status_code=404, detail="Assignment not found")
    return ok_response(data=record_to_dict(record))


@app.put("/api/assignments/{assignment_id}/submissions")
def assignment_update_submissions(
    assignment_id: int, payload: dict[str, Any], db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    record = update_record(db, assignment_id, {"submissions": payload})
    return ok_response(data=record_to_dict(record), message="Submissions updated")


@app.delete("/api/assignments/{assignment_id}")
def assignment_delete(assignment_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    record = db.get(ResourceRecord, assignment_id)
    if not record or record.resource != "assignments":
        raise HTTPException(status_code=404, detail="Assignment not found")
    db.delete(record)
    db.commit()
    return ok_response(message="Assignment deleted")


@app.get("/api/school/list")
def school_list(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    records = [record_to_dict(r) for r in get_records(db, "school")]
    return list_response_payload(resource="school", items=records)


@app.get("/api/school/{school_id}")
def school_get(school_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    record = db.get(ResourceRecord, school_id)
    if not record or record.resource != "school":
        raise HTTPException(status_code=404, detail="School not found")
    return ok_response(data=record_to_dict(record), extra={"school": record_to_dict(record)})


@app.post("/api/school/create")
def school_create(payload: dict[str, Any], db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    record = create_record(db, "school", payload)
    return ok_response(data={"school": record_to_dict(record)}, message="School created")


@app.put("/api/school/update/{school_id}")
def school_update(
    school_id: int, payload: dict[str, Any], db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    record = update_record(db, school_id, payload)
    return ok_response(data={"school": record_to_dict(record)}, message="School updated")


@app.delete("/api/school/delete/{school_id}")
def school_delete(school_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    record = db.get(ResourceRecord, school_id)
    if not record or record.resource != "school":
        raise HTTPException(status_code=404, detail="School not found")
    db.delete(record)
    db.commit()
    return ok_response(message="School deleted")


@app.patch("/api/school/activate/{school_id}")
@app.patch("/api/school/deactivate/{school_id}")
def school_toggle_status(
    school_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    record = db.get(ResourceRecord, school_id)
    if not record or record.resource != "school":
        raise HTTPException(status_code=404, detail="School not found")
    record.is_active = "deactivate" not in str(request.url.path)
    db.add(record)
    db.commit()
    return ok_response(message="School status updated")


@app.get("/api/school/list/school-admins")
def school_admin_list(_: User = Depends(get_current_user)):
    return ok_response(data=[])


@app.patch("/api/school/school-admin/change-password/{admin_id}")
def school_admin_change_password(admin_id: int, _: dict[str, Any], __: User = Depends(get_current_user)):
    return ok_response(data={"admin_id": admin_id}, message="Password updated")


@app.get("/api/users/schoolAdmin/{skid}/{admin_id}")
def get_school_admin(skid: str, admin_id: int, _: User = Depends(get_current_user)):
    return ok_response(
        extra={
            "user": {
                "id": admin_id,
                "skid": skid,
                "username": "school_admin",
                "email": "admin@school.com",
                "role": "SCHOOL_ADMIN",
            }
        }
    )


@app.post("/api/users/create")
def create_user_endpoint(
    payload: dict[str, Any], db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    record = create_record(db, "users", payload)
    return ok_response(extra={"user": record_to_dict(record)}, message="User created")


@app.put("/api/users/update/{user_id}")
def update_user_endpoint(
    user_id: int, payload: dict[str, Any], db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    record = update_record(db, user_id, payload)
    return ok_response(extra={"user": record_to_dict(record)}, message="User updated")


@app.get("/api/users/super-admins")
def list_super_admins(_: User = Depends(get_current_user)):
    return ok_response(data=[{"id": 1, "username": "admin", "role": "SUPER_ADMIN"}])


@app.post("/api/users/create-super-admin")
def create_super_admin(payload: dict[str, Any], _: User = Depends(get_current_user)):
    return ok_response(extra={"user": payload}, message="Super admin created")


@app.get("/api/school/dashboard/stats")
def school_dashboard_stats(_: User = Depends(get_current_user)):
    return ok_response(
        data={
            "total_institutions": 1,
            "total_users": 1,
            "total_students": 0,
            "total_educators": 0,
            "active_institutions": 1,
            "inactive_institutions": 0,
            "system_health": 100,
            "last_updated": datetime.now(UTC).isoformat(),
        }
    )


@app.get("/api/dashboard/administrator/stats")
def dashboard_admin_stats(_: User = Depends(get_current_user)):
    return {
        "total_students": 0,
        "total_educators": 0,
        "total_cohorts": 0,
        "total_courses": 0,
        "total_users": 1,
        "active_users": 1,
        "inactive_users": 0,
        "fees_collected": 0,
        "pending_fees": 0,
        "attendance_percentage": 0,
        "last_updated": datetime.now(UTC).isoformat(),
    }


@app.get("/api/dashboard/educator/stats")
def dashboard_educator_stats(_: User = Depends(get_current_user)):
    return {
        "assigned_cohorts": 0,
        "total_students": 0,
        "total_courses": 0,
        "pending_assignments": 0,
        "attendance_marked": 0,
        "total_marks_entered": 0,
        "last_updated": datetime.now(UTC).isoformat(),
    }


@app.get("/api/dashboard/learner/stats")
def dashboard_learner_stats(_: User = Depends(get_current_user)):
    return {
        "enrolled_cohorts": 0,
        "total_courses": 0,
        "pending_assignments": 0,
        "completed_assessments": 0,
        "overall_grade": "N/A",
        "attendance_percentage": 0,
        "last_updated": datetime.now(UTC).isoformat(),
    }


@app.get("/api/dashboard/guardian/stats")
def dashboard_guardian_stats(_: User = Depends(get_current_user)):
    return {
        "total_children": 0,
        "overall_attendance": 0,
        "overall_performance": "N/A",
        "pending_fees": 0,
        "recent_communications": 0,
        "last_updated": datetime.now(UTC).isoformat(),
    }


@app.get("/api/dashboard/activities")
def dashboard_activities(limit: int = 10, _: User = Depends(get_current_user)):
    return []


@app.get("/api/dashboard/chart-data")
def dashboard_chart_data(period: str = "weekly", _: User = Depends(get_current_user)):
    return {"period": period, "labels": [], "datasets": []}


@app.api_route("/api/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def api_fallback(
    full_path: str,
    request: Request,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    parts = [part for part in full_path.split("/") if part]
    if not parts:
        return ok_response(data={})

    resource = parts[0]
    page = int(request.query_params.get("page", 1))
    limit = int(request.query_params.get("limit", 20))
    skid = next((p for p in parts if p and p.isupper() and len(p) >= 4), None)

    if request.method == "GET":
        if resource == "teachers" and "subjects" in parts:
            return ok_response(data=[], extra={"subject_ids": []})
        is_list_request = (
            len(parts) == 1
            or any(
                token in parts
                for token in {
                    "list",
                    "today",
                    "status",
                    "search-students",
                    "teacher-classes",
                    "week",
                    "students",
                    "sections",
                }
            )
            or resource in {"dashboard", "schoolAdminDashboard", "teacherDashboard"}
        )
        if is_list_request:
            records = [record_to_dict(r) for r in get_records(db, resource, skid)]
            if resource == "bus-scan":
                return ok_response(data={"records": records, "students": []})
            if resource in {"dashboard", "schoolAdminDashboard", "teacherDashboard"}:
                return ok_response(data={"stats": {}, "items": [], "count": len(records)})
            if resource == "classes" and "sections" in parts:
                return ok_response(data=records)
            if resource == "classes" and "students" in parts:
                return ok_response(data={"data": records})
            return list_response_payload(resource=resource, items=records, page=page, limit=limit)

        maybe_id = next((p for p in reversed(parts) if p.isdigit()), None)
        if maybe_id:
            record = db.get(ResourceRecord, int(maybe_id))
            if record:
                item = record_to_dict(record)
                extra = {}
                if resource == "teachers":
                    extra["teacher_data"] = item
                if resource == "students":
                    extra["student"] = item
                if resource == "school":
                    extra["school"] = item
                if resource == "users":
                    extra["user"] = item
                return ok_response(data=item, extra=extra)
        return ok_response(data={})

    body: dict[str, Any] = {}
    try:
        body = await request.json()
        if not isinstance(body, dict):
            body = {"value": body}
    except Exception:
        body = {}

    if request.method == "DELETE":
        maybe_id = next((p for p in reversed(parts) if p.isdigit()), None)
        if maybe_id:
            record = db.get(ResourceRecord, int(maybe_id))
            if record:
                db.delete(record)
                db.commit()
        return ok_response(message="Deleted successfully")

    if request.method in {"PUT", "PATCH"}:
        maybe_id = next((p for p in reversed(parts) if p.isdigit()), None)
        if maybe_id:
            existing = db.get(ResourceRecord, int(maybe_id))
            if existing:
                updated = update_record(db, int(maybe_id), body)
            else:
                updated = create_record(db, resource, body, skid=skid)
            item = record_to_dict(updated)
            extra = {}
            if resource == "users":
                extra["user"] = item
            if resource == "school":
                extra["school"] = item
            return ok_response(data=item, extra=extra, message="Updated successfully")
        return ok_response(data=body, message="Updated successfully")

    create_code = 200
    if resource == "announcements" and "create" in parts:
        create_code = 201
    if resource == "timeTable" and ("save-draft" in parts or "create" in parts):
        create_code = 201
    if resource == "syllabus" and "assign-teacher" in parts:
        create_code = 201

    record = create_record(db, resource, body, skid=skid)
    item = record_to_dict(record)
    extra: dict[str, Any] = {}
    if resource == "users":
        extra["user"] = item
    if resource == "school":
        extra["school"] = item
    if resource == "teachers":
        extra["teacher_data"] = item
    if resource == "students":
        extra["student"] = item
    if resource == "subjects" and "teacher" in parts:
        extra["subject_ids"] = body.get("subject_ids", [])
    return ok_response(code=create_code, data=item, extra=extra, message="Created successfully")
