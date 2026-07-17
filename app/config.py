"""Configuration settings for the Smart Blood Donor Finder backend."""

from dotenv import load_dotenv
import os

load_dotenv()

PROJECT_NAME = "Smart Blood Donor Finder"
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
