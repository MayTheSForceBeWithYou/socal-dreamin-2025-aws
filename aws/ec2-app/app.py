#!/usr/bin/env python3
"""
Simple Salesforce LoginEventStream to OpenSearch streamer for EC2
"""
import os
import sys
import time
import logging
from datetime import datetime, timedelta
from config import Config
from salesforce_client import SalesforceClient
from opensearch_client import OpenSearchClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/salesforce-streamer/salesforce-streamer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LoginEventStreamer:
    def __init__(self):
        try:
            self.config = Config()
            self.sf_client = SalesforceClient(self.config)
            self.os_client = OpenSearchClient(self.config)
            self.last_poll_time = datetime.utcnow() - timedelta(minutes=5)
        except Exception as e:
            logger.error(f"Failed to initialize LoginEventStreamer: {e}")
            raise
        
    def run(self):
        """Main processing loop"""
        logger.info(f"Starting Salesforce LoginEvent streamer...")
        logger.info(f"Polling interval: {self.config.poll_interval_seconds} seconds")
        logger.info(f"OpenSearch endpoint: {self.config.opensearch_endpoint}")
        
        # Test connections on startup
        if not self.sf_client.test_connection():
            logger.error("Failed to connect to Salesforce. Exiting.")
            sys.exit(1)
            
        if not self.os_client.test_connection():
            logger.error("Failed to connect to OpenSearch. Exiting.")
            sys.exit(1)
        
        while True:
            try:
                self.process_events()
                time.sleep(self.config.poll_interval_seconds)
                
            except KeyboardInterrupt:
                logger.info("Received shutdown signal")
                break
            except Exception as e:
                logger.error(f"Error in processing loop: {e}", exc_info=True)
                time.sleep(30)  # Wait before retrying on error
    
    def process_events(self):
        """Process a single batch of events"""
        end_time = datetime.utcnow()
        start_time = self.last_poll_time
        
        sf_start = start_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        sf_end = end_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        
        logger.debug(f"Polling for events from {sf_start} to {sf_end}")
        
        # Fetch events from Salesforce
        events = self.sf_client.get_login_events(sf_start, sf_end)
        
        if events:
            # Index to OpenSearch
            success = self.os_client.bulk_index_events(events)
            if success:
                logger.info(f"Successfully processed {len(events)} login events")
            else:
                logger.error(f"Failed to index {len(events)} events")
        else:
            logger.debug("No new events found")
        
        self.last_poll_time = end_time

if __name__ == "__main__":
    try:
        logger.info("Starting Salesforce LoginEvent Streamer application...")
        streamer = LoginEventStreamer()
        streamer.run()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please check your environment variables and configuration")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
