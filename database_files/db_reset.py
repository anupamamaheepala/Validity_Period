'''
db_reset.py file is as follows:

    Purpose: This script resets and imports data into MongoDB collections from JSON files.
    Created Date: 
    Created By: Amupama(anupamamaheepala999@gmail.com)
    Last Modified Date: 
    Modified By: Amupama(anupamamaheepala999@gmail.com)     
    Version: Python 3.12
    Dependencies: pymongo, json, os, bson
    Notes:
'''

import pymongo
import json
import os
from bson import ObjectId

# MongoDB connection details
client = pymongo.MongoClient('mongodb+srv://drs:drs123@drsfunction.cbyqkvd.mongodb.net/?retryWrites=true&w=majority&appName=DRSfunction')
db = client['Validity_Period']

# List of collections to reset
collections = [
    'Case_details'
]

# Directory containing JSON files
json_dir = r'database_files'

# List of corresponding JSON file names
json_files = [
    os.path.join(json_dir, 'Case_details.json')
]

# Function to reset collections and insert data from JSON files
def reset_and_import_data():
    for collection_name, json_file in zip(collections, json_files):
        # Delete all documents from the collection
        collection = db[collection_name]
        collection.delete_many({})

        # Load data from the JSON file
        with open(json_file, 'r') as file:
            data = json.load(file)

        # Convert $oid fields to ObjectId
        def convert_oid(document):
            if isinstance(document, dict):
                for key, value in document.items():
                    if key == "_id" and "$oid" in value:
                        document[key] = ObjectId(value["$oid"])
                    else:
                        convert_oid(value)
            elif isinstance(document, list):
                for item in document:
                    convert_oid(item)

        convert_oid(data)

        # Insert data into the collection
        if isinstance(data, list):  # Assuming data is a list of documents
            collection.insert_many(data)
        else:  # If data is a single document
            collection.insert_one(data)
        print(f"Data imported into {collection_name} from {json_file}")

# Run the function
reset_and_import_data()
