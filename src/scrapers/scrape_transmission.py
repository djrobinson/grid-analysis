import requests
import json
import pandas as pd
from pathlib import Path
from typing import List, Dict
import logging
from src.scrapers.spp_scraper import BaseSPPScraper

class TransmissionScraper(BaseSPPScraper):
    def __init__(self):
        super().__init__("https://services1.arcgis.com/Hp6G80Pky0om7QvQ/arcgis/rest/services/Transmission_Lines/FeatureServer/0/query")
        
    def _build_url(self, offset: int) -> str:
        """Build URL with the correct offset parameter"""
        base_params = {
            'where': '1=1',
            'outFields': 'ID,INFERRED,NAICS_CODE,NAICS_DESC,OWNER,SOURCE,SOURCEDATE,STATUS,SUB_1,SUB_2,TYPE,VAL_DATE,VAL_METHOD,VOLTAGE,VOLT_CLASS,OBJECTID,GlobalID',
            'returnGeometry': 'true',
            'f': 'geojson',
            'resultOffset': str(offset)
        }
        
        params = '&'.join([f"{k}={v}" for k, v in base_params.items()])
        return f"{self.base_url}?{params}"

    def _process_response(self, response: requests.Response) -> List[Dict]:
        """Process the GeoJSON response"""
        data = response.json()
        return data.get('features', [])

    def fetch_all_transmission_data(self) -> dict:
        """Fetch all transmission line data and return as merged GeoJSON"""
        offset = 0
        # Initialize GeoJSON structure
        merged_geojson = {
            "type": "FeatureCollection",
            "features": []
        }
        
        while True:
            url = self._build_url(offset)
            self.logger.info(f"Fetching data with offset {offset}")
            
            try:
                response = requests.get(url)
                response.raise_for_status()
                data = response.json()
                
                features = data.get('features', [])
                print('features')
                print(len(features))
                if not features:
                    break
                    
                merged_geojson['features'].extend(features)
                
                # Check if we've reached the end
                if not data.get('properties', {}).get('exceededTransferLimit', False):
                    break
                    
                offset += 2000
                
            except requests.RequestException as e:
                self.logger.error(f"Error fetching data: {e}")
                break
                
        return merged_geojson

def main():
    scraper = TransmissionScraper()
    geojson_data = scraper.fetch_all_transmission_data()
    
    if geojson_data['features']:
        # Save as GeoJSON
        output_path = Path("src/data/transmission_lines.geojson")
        with open(output_path, 'w') as f:
            json.dump(geojson_data, f, indent=2)
        print(f"Saved {len(geojson_data['features'])} transmission line features to {output_path}")
    else:
        print("No data was retrieved")

if __name__ == "__main__":
    main()

