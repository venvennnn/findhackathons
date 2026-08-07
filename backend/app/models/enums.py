from enum import Enum


class SkillLevel(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class DomainCategory(str, Enum):
    web_dev = "web-dev"
    mobile = "mobile"
    nlp = "nlp"
    cv = "cv"
    tabular = "tabular"
    web3 = "web3"
    hardware = "hardware"
    game_dev = "game-dev"
    other = "other"


class ConfidenceLevel(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class SourcePlatform(str, Enum):
    kaggle = "kaggle"
    devpost = "devpost"
    devfolio = "devfolio"
    unstop = "unstop"
    other = "other"