from datetime import datetime
import pandas as pd
import requests
from io import StringIO
from .spp_scraper import BaseSPPScraper

class RTBMLMPScraper(BaseSPPScraper):
    def __init__(self):
        super().__init__("https://portal.spp.org/file-browser-api/download/rtbm-lmp-by-location")

    def _build_url(self, date: datetime) -> str:
        """Build URL for RTBM LMP data"""
        path = f"/{date.year}/{date.month:02d}/By_Interval/{date.day:02d}/RTBM-LMP-SL-{date.strftime('%Y%m%d%H%M')}.csv"
        return f"{self.base_url}?path={path}"

    def _process_response(self, response: requests.Response) -> pd.DataFrame:
        """Process the RTBM LMP CSV response"""
        # Convert bytes to string and create StringIO object
        content = StringIO(response.content.decode('utf-8'))
        df = pd.read_csv(content)
        
        # Convert timestamp columns to datetime
        if 'Interval' in df.columns:
            df['Interval'] = pd.to_datetime(df['Interval'])
        if 'GMTIntervalEnd' in df.columns:
            df['GMTIntervalEnd'] = pd.to_datetime(df['GMTIntervalEnd'])
        return df

    def fetch_latest_lmps(self) -> pd.DataFrame:
        """Fetch the most recent RTBM LMP data"""
        current_time = datetime.now()
        # Round down to nearest 5 minutes since SPP updates every 5 minutes
        current_time = current_time.replace(minute=(current_time.minute // 5) * 5, second=0, microsecond=0)
        return self.fetch_data(current_time)