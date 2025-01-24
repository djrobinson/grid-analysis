from datetime import datetime
import pandas as pd
import io
import requests
from .spp_scraper import BaseSPPScraper

class RTConstraintsScraper(BaseSPPScraper):
    def __init__(self):
        super().__init__("https://portal.spp.org/file-browser-api/download/rtbm-binding-constraints")
    
    def _build_url(self, date: datetime, type: str = "day") -> str:
        """Build URL for constraints data"""
        print(date.strftime('%Y%m%d%H%M'))
        if type == "day":
            # https://portal.spp.org/file-browser-api/download/rtbm-binding-constraints?path=%2F2025%2F01%2FBy_Day%2FRTBM-DAILY-BC-20250103.csv
            path = f"/{date.year}/{date.month:02d}/By_Day/RTBM-DAILY-BC-{date.strftime('%Y%m%d')}.csv"
        else:
            path = f"/{date.year}/{date.month:02d}/By_Interval/{date.day:02d}/RTBM-BC-{date.strftime('%Y%m%d%H%M')}.csv"
        return f"{self.base_url}?path={path}"
    

    def _process_response(self, response: requests.Response) -> pd.DataFrame:
        """Process the constraints CSV response"""
        df = pd.read_csv(io.StringIO(response.content.decode('utf-8')))
        # Add any specific constraints data processing here
        return df 