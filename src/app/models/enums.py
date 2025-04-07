# models/enums.py
from enum import Enum

class ReportType(str, Enum):
    SLIDE = "Slide"
    BLOCK = "Block"
    SPECIMEN = "Specimen"
    CASE = "Case"
