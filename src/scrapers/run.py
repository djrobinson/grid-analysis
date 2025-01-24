from datetime import datetime, timedelta
import pandas as pd
from .spp_rtlmp_scraper import RTBMLMPScraper
from .spp_rt_constraints_scraper import RTConstraintsScraper
from .spp_da_constraints_scraper import DAConstraintsScraper
def scrape_day_data(date: datetime):
    # Fetch LMP data for the whole day
    # lmp_scraper = RTBMLMPScraper()
    # lmp_data = lmp_scraper.scrape_intervals_for_day(date)
    # lmp_scraper.save_data(lmp_data, date, "rtbm_lmp")

    # Fetch constraints data for the whole day
    # constraints_scraper = RTConstraintsScraper()
    # constraints_data = constraints_scraper.scrape_intervals_for_day(date)
    # constraints_scraper.save_data(constraints_data, date, "constraints")

    # Loop over all days in January 2025 through today
    start_date = datetime(2024, 1, 1)
    end_date = datetime.now() - timedelta(days=1)

    rt_constraints_scraper = RTConstraintsScraper()
    rt_constraints_data = rt_constraints_scraper.scrape_days_in_range(start_date, end_date)
    rt_constraints_scraper.save_data(rt_constraints_data, date, "rt_constraints")

    da_constraints_scraper = DAConstraintsScraper()
    da_constraints_data = da_constraints_scraper.scrape_days_in_range(start_date, end_date)
    da_constraints_scraper.save_data(da_constraints_data, date, "da_constraints")


if __name__ == "__main__":
    # Example: Scrape data for a specific day
    date = datetime(2025, 1, 1)  # Replace with desired date
    scrape_day_data(date)