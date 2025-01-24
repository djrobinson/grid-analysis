from datetime import datetime
import pandas as pd
import io
import requests
from .spp_scraper import BaseSPPScraper

class DAConstraintsScraper(BaseSPPScraper):
    def __init__(self):
        # https://portal.spp.org/file-browser-api/download/da-binding-constraints?path=%2F2025%2F01%2FBy_Day%2FDA-BC-202501010100.csv
        super().__init__("https://portal.spp.org/file-browser-api/download/da-binding-constraints")
    
    def _build_url(self, date: datetime, type: str = "day") -> str:
        """Build URL for constraints data"""
        print(date.strftime('%Y%m%d%H%M'))
        # https://portal.spp.org/file-browser-api/download/da-binding-constraints?path=/2024/12/By_Day/DA-BC-202412010100.csv
        # https://portal.spp.org/file-browser-api/download/da-binding-constraints?path=/2024/12/By_Day/01/DA-BC-202412010100.csv
        path = f"/{date.year}/{date.month:02d}/By_Day/DA-BC-{date.strftime('%Y%m%d')}0100.csv"
        return f"{self.base_url}?path={path}"
    

    def _process_response(self, response: requests.Response) -> pd.DataFrame:
        """Process the constraints CSV response"""
        df = pd.read_csv(io.StringIO(response.content.decode('utf-8')))
        # Add any specific constraints data processing here
        return df 