from enum import Enum
from pydantic import BaseModel
from typing import List
from datetime import datetime


class StockLine(BaseModel):
    Date : datetime
    Open : float
    High : float
    Low : float
    Close : float
    Volume : int
    OpenInt : int

class StockData(BaseModel):
    data : List[StockLine]
    
class FrequencyEnum(Enum):
    daily="daily"
    weekly="weekly"
    monthly="monthly"
    yearly="yearly"
    