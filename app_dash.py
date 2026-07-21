"""
db.py — وحدة الاتصال بقاعدة بيانات Neon (PostgreSQL)
تُستخدم من قبل app_dash.py لإدارة المستخدمين وسجل عمليات حساب التكلفة.

الإعداد المطلوب في .streamlit/secrets.toml على Streamlit Cloud:

    DATABASE_URL = "postgresql://user:password@host/dbname?sslmode=require"

    [users]
    admin = "your_password_here"
"""

import json
from datetime import datetime

import psycopg2
import psycopg2.extras
import streamlit as st


def _get_conn():
    """يفتح اتصالاً جديداً بقاعدة بيانات Neon باستخدام رابط الاتصال من secrets."""
    dsn = st.secrets["DATABASE_URL"]
    return psycopg2.connect(dsn, sslmode="require")


def init_db():
    """ينشئ الجداول المطلوبة إن لم تكن موجودة (يُستدعى مرة واحدة عند بدء التشغيل)."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS app_users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS calculations (
                    id SERIAL PRIMARY KEY,
                    username TEXT NOT NULL,
                    total_length DOUBLE PRECISION NOT NULL,
                    total_cost DOUBLE PRECISION NOT NULL,
                    segments_count INTEGER NOT NULL,
                    segments_json TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW()
                );
            """)
        conn.commit()


def verify_user_db(username, password):
    """يتحقق من اسم المستخدم وكلمة المرور من جدول app_users في قاعدة البيانات."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT password FROM app_users WHERE username = %s",
                (username,),
            )
            row = cur.fetchone()
            return bool(row) and row[0] == password


def save_calculation(username, total_length, total_cost, segments):
    """يحفظ نتيجة عملية حساب تكلفة جديدة مرتبطة بالمستخدم الحالي."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO calculations
                    (username, total_length, total_cost, segments_count, segments_json)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    username,
                    total_length,
                    total_cost,
                    len(segments),
                    json.dumps(segments, ensure_ascii=False, default=str),
                ),
            )
        conn.commit()


def get_user_calculations(username, limit=100):
    """يرجع آخر العمليات المحفوظة لمستخدم معيّن، الأحدث أولاً."""
    with _get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, total_length, total_cost, segments_count, created_at
                FROM calculations
                WHERE username = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (username, limit),
            )
            return cur.fetchall()


def delete_calculation(calc_id, username):
    """يحذف عملية حساب محددة (يتحقق من أنها تخص نفس المستخدم قبل الحذف)."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM calculations WHERE id = %s AND username = %s",
                (calc_id, username),
            )
        conn.commit()
