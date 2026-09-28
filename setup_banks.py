"""Run once after filling .env. No real prospect data is created."""
import os
from dotenv import load_dotenv
from hindsight_client import Hindsight
from core import DEALS, bank_id
load_dotenv()
if __name__ == '__main__':
    with Hindsight(base_url=os.environ['HINDSIGHT_BASE_URL'], api_key=os.environ['HINDSIGHT_API_KEY'], timeout=90) as client:
        for deal, name in DEALS.items():
            client.create_bank(bank_id=bank_id(deal), name=name)
            print('Bank ready:', bank_id(deal))
