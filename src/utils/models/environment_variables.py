from pydantic_settings import BaseSettings

from utils.variables import DEFAULT_ENVIRONMENT_NAME


class EnvironmentVariables(BaseSettings):
    environment_name: str = DEFAULT_ENVIRONMENT_NAME
