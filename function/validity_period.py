from datetime import datetime, timedelta, timezone
from utils.logger import SingletonLogger
from utils.connectionMongo import MongoDBConnectionSingleton
from bson import ObjectId

class ValidityPeriodMonitor:
    def __init__(self):
        self.logger = SingletonLogger.get_logger('appLogger')
        self.db_logger = SingletonLogger.get_logger('dbLogger')
        self.validity_period = timedelta(days=84)  # 3 months = 28 days * 3
        self.alert_period = timedelta(days=3)  # 3 days before expiration

    def get_active_drc(self, drc_list):
        """Select the last active DRC from the list based on drc_status."""
        try:
            self.logger.debug(f"Checking DRC list: {drc_list}")
            active_drcs = [drc for drc in drc_list if drc.get('drc_status') == 'Active']
            self.logger.debug(f"Active DRCs after filtering: {active_drcs}")
            if not active_drcs:
                raise ValueError("No active DRC found.")
            active_drc = max(active_drcs, key=lambda x: x.get('order_id'))
            self.logger.debug(f"Selected active DRC: {active_drc}")
            return active_drc
        except Exception as e:
            self.logger.error(f"Error selecting active DRC: {e}")
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
                        drc_list = case.get('drc', [])
                        self.logger.debug(f"Processing case {case['case_id']} with DRC list: {drc_list}")
                        active_drc = self.get_active_drc(drc_list)
                        
                        if not active_drc:
                            self.logger.warning(f"No active DRC for case {case['case_id']}. Skipping.")
                            continue
                        
                        expire_dtm = active_drc.get('expire_dtm', {}).get('$date')
                        if not expire_dtm:
                            self.logger.warning(f"No expire_dtm for DRC {active_drc['drc_id']} in case {case['case_id']}. Skipping.")
                            continue
                        
                        # Parse expire_dtm as offset-aware
                        expire_date = datetime.fromisoformat(expire_dtm.replace('Z', '+00:00'))
                        time_to_expiry = expire_date - current_date
                        self.logger.debug(f"Case {case['case_id']}: expire_date={expire_date}, current_date={current_date}, time_to_expiry={time_to_expiry}")
                        
                        # Check for 3-day alert
                        if self.alert_period >= time_to_expiry > timedelta(0):
                            self.logger.info(f"Sending 3-day alert for case {case['case_id']} (expires {expire_date})")
                            collection.update_one(
                                {"_id": case['_id'], "drc.order_id": active_drc['order_id']},
                                {
                                    "$set": {
                                        "drc.$.status": "Last Alert Received",
                                        "drc.$.current_status": None,
                                        "updatedAt": current_date
                                    }
                                }
                            )
                            self.db_logger.info(f"Updated DRC {active_drc['drc_id']} in case {case['case_id']} to Last Alert Received")
                        
                        # Check for expiration
                        elif time_to_expiry <= timedelta(0):
                            self.logger.info(f"Case {case['case_id']} expired. Directing to Letter of Demand.")
                            collection.update_one(
                                {"_id": case['_id'], "drc.order_id": active_drc['order_id']},
                                {
                                    "$set": {
                                        "drc.$.status": "Expired",
                                        "drc.$.current_status": "Direct to Letter of Demand",
                                        "updatedAt": current_date
                                    }
                                }
                            )
                            self.db_logger.info(f"Updated DRC {active_drc['drc_id']} in case {case['case_id']} to Expired, Direct to Letter of Demand")
                    
                    except Exception as e:
                        self.logger.error(f"Error processing case {case.get('case_id', 'Unknown')}: {e}")
                        continue
                
        except Exception as e:
            self.logger.error(f"Error in validity period check: {e}")