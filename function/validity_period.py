'''
validity_period.py file is as follows:

    Purpose: This script monitors the validity period of DRCs in MongoDB and updates their status.
    Created Date: 
    Created By: Amupama(anupamamaheepala999@gmail.com)
    Last Modified Date: 
    Modified By: Amupama(anupamamaheepala999@gmail.com)     
    Version: Python 3.12
    Dependencies: pymongo, json, os, bson
    Notes:
'''


from datetime import datetime, timedelta, timezone
from utils.logger import SingletonLogger
from utils.connectionMongo import MongoDBConnectionSingleton
from bson import ObjectId

class ValidityPeriodMonitor:
    def __init__(self):
        self.logger = SingletonLogger.get_logger('appLogger')
        self.db_logger = SingletonLogger.get_logger('dbLogger')
        self.validity_period = timedelta(days=84)  # 3 months
        self.alert_period = timedelta(days=3)      # 3-day alert window

    def get_active_drc(self, drc_list, case_id):
        """Select the last active DRC from the list based on order_id."""
        try:
            if not isinstance(drc_list, list):
                self.logger.warning(f"Invalid DRC list structure for case {case_id}. Expected a list.")
                return None

            self.logger.debug(f"Checking DRC list: {drc_list}")
            active_drcs = []

            for drc in drc_list:
                if not isinstance(drc, dict):
                    self.logger.warning(f"Invalid DRC entry (not a dict) in case {case_id}: {drc}")
                    continue

                if drc.get('drc_status') == 'Active':
                    order_id = drc.get('order_id')
                    if not isinstance(order_id, (int, float)):
                        self.logger.warning(f"Missing or invalid order_id in DRC {drc.get('drc_id')} for case {case_id}")
                        continue
                    active_drcs.append(drc)

            self.logger.debug(f"Active DRCs after filtering: {active_drcs}")
            if not active_drcs:
                raise ValueError(f"No valid active DRC found for case {case_id}.")

            active_drc = max(active_drcs, key=lambda x: x.get('order_id'))
            self.logger.debug(f"Selected active DRC: {active_drc}")
            return active_drc
        except Exception as e:
            self.logger.error(f"Error selecting active DRC for case {case_id}: {e}")
            return None

    def check_validity_and_alert(self):
        """Check validity period and update DRC status fields."""
        try:
            with MongoDBConnectionSingleton() as mongo_db:
                if mongo_db is None:
                    raise ValueError("No active MongoDB connection.")
                
                collection = mongo_db['Case_details']
                cases = collection.find({"drc.drc_status": "Active"})
                
                current_date = datetime.now(timezone.utc)  # Offset-aware UTC datetime
                
                for case in cases:
                    try:
                        case_id = case.get('case_id', 'Unknown Case ID')
                        drc_list = case.get('drc', [])

                        if not isinstance(drc_list, list):
                            self.logger.warning(f"Invalid DRC array in case {case_id}, expected a list. Skipping.")
                            continue

                        self.logger.debug(f"Processing case {case_id} with DRC list: {drc_list}")
                        active_drc = self.get_active_drc(drc_list, case_id)
                        
                        if not active_drc:
                            self.logger.warning(f"No active DRC for case {case_id}. Skipping.")
                            continue
                        
                        drc_id = active_drc.get('drc_id')
                        order_id = active_drc.get('order_id')

                        if not drc_id:
                            self.logger.warning(f"Missing drc_id for active DRC in case {case_id}. Skipping.")
                            continue
                        if not isinstance(order_id, (int, float)):
                            self.logger.warning(f"Missing or invalid order_id for DRC {drc_id} in case {case_id}. Skipping.")
                            continue

                        expire_dtm = active_drc.get('expire_dtm', {}).get('$date')
                        if not expire_dtm or not isinstance(expire_dtm, str):
                            self.logger.warning(f"Missing or invalid expire_dtm for DRC {drc_id} in case {case_id}. Skipping.")
                            continue
                        
                        # Parse expire_dtm as offset-aware datetime
                        try:
                            expire_date = datetime.fromisoformat(expire_dtm.replace('Z', '+00:00'))
                        except ValueError as ve:
                            self.logger.error(f"Failed to parse expire_dtm '{expire_dtm}' for DRC {drc_id} in case {case_id}: {ve}")
                            continue

                        time_to_expiry = expire_date - current_date
                        self.logger.debug(f"Case {case_id}: expire_date={expire_date}, current_date={current_date}, time_to_expiry={time_to_expiry}")
                        
                        # Check for 3-day alert
                        if self.alert_period >= time_to_expiry > timedelta(0):
                            self.logger.info(f"Sending 3-day alert for case {case_id} (expires {expire_date})")
                            result = collection.update_one(
                                {"_id": case['_id'], "drc.order_id": active_drc['order_id']},
                                {
                                    "$set": {
                                        "drc.$.status": "Last Alert Received",
                                        "drc.$.current_status": None,
                                        "updatedAt": current_date
                                    }
                                }
                            )
                            self.db_logger.info(f"Updated DRC {drc_id} in case {case_id} to Last Alert Received. Modified count: {result.modified_count}")
                        
                        # Check for expiration
                        elif time_to_expiry <= timedelta(0):
                            self.logger.info(f"Case {case_id} expired. Directing to Letter of Demand.")
                            result = collection.update_one(
                                {"_id": case['_id'], "drc.order_id": active_drc['order_id']},
                                {
                                    "$set": {
                                        "drc.$.status": "Expired",
                                        "drc.$.current_status": "Direct to Letter of Demand",
                                        "updatedAt": current_date
                                    }
                                }
                            )
                            self.db_logger.info(f"Updated DRC {drc_id} in case {case_id} to Expired, Direct to Letter of Demand. Modified count: {result.modified_count}")
                    
                    except Exception as e:
                        case_id = case.get('case_id', 'Unknown')
                        self.logger.error(f"Error processing case {case_id}: {e}", exc_info=True)
                        continue
                
        except Exception as e:
            self.logger.error(f"Error in validity period check: {e}", exc_info=True)