import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import os
import secrets

import collection_stats as cS
from providers import get_providers
import database as db

class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        parsed_url = urlparse(self.path)
        try:
            if parsed_url.path == "/health":
                if not self.verify_api_key():
                    return
                self.send_json(200, {})
            else:
                self.send_json(404, {"error": "Not found"})
                return
        except Exception as e:
            print(f"Internal server error: {e}")
            self.send_json(500, {"error": "Internal server error"})
            return

    def do_POST(self):
        parsed_url = urlparse(self.path)

        try:
            if parsed_url.path == "/stats":
                if not self.verify_api_key():
                    return
                collections, collection_errors = self.handle_stats(parsed_url)
            elif parsed_url.path == "/stats/all":
                if not self.verify_api_key():
                    return
                collections, collection_errors = self.handle_stats_all()
            else:
                self.send_json(404, {"error": "Not found"})
                return

            if not collections:
                self.send_json(404, {
                    "error": "No matching collections",
                    "collection_errors": collection_errors
                })
                return

            providers = get_providers()

            collections_stats, collection_errors2 , terminologies_stats= cS.calc_stats_for_collections(providers, collections)
            collection_errors = collection_errors + collection_errors2

            if not collections_stats:
                self.send_json(500, {
                    "error": "No collections without errors available for db insertion.",
                    "collection_errors": collection_errors

                })
                return

            print("Inserting calculated statistics into database...")
            with db.get_connection() as conn:
                db.insert_collection_stats(collections_stats, conn)
                db.insert_terminology_stats(terminologies_stats, conn)

            # print("Terminology statistics:")
            # print(terminologies_stats)

            print("Collection statistics:")
            print(collections_stats)

            print("Collection errors:")
            print(collection_errors)

            self.send_success_message(collection_errors)

        except Exception as e:
            print(f"Internal server error: {e}")
            self.send_json(500, {"error": "Internal server error"})
            return

    def handle_stats_all(self):
        collections, collection_errors = cS.create_selected_collection_list(include_all=True)
        return collections, collection_errors

    def handle_stats(self, parsed_url):
        params = parse_qs(parsed_url.query)
        collection_ids = params.get("collection", [])
        collections, collection_errors = cS.create_selected_collection_list(collection_ids)
        return collections, collection_errors

    def send_success_message(self, collection_errors):
        if collection_errors:
            self.send_json(200, {
                "message": "Successfully inserted collection and terminology statistics into DB."
                           " For some collections no statistics could be generated.",
                "collection_errors": collection_errors
            })
        else:
            self.send_json(200, {
                "message": "Successfully inserted collection and terminology statistics into DB."
                           " For all collections statistics could be generated.",
                "collection_errors": []
            })

    def send_json(self, status_code, data):
        response = json.dumps(data).encode("utf-8")

        self.send_response(status_code)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()

        self.wfile.write(response)

    def verify_api_key(self):
        expected_key = os.getenv("STATISTICS_SERVICE_PORTAL_KEY")
        provided_key = self.headers.get("X-Portal-Key", None)
        if provided_key is None:
            self.send_json(401, {"error": "'X-Portal-Key' header not provided"})
            return False
        if not secrets.compare_digest(expected_key, provided_key):
            self.send_json(401, {"error": "'X-Portal-Key' header invalid"})
            return False
        return True


server = HTTPServer(("0.0.0.0", 8000), Handler)

print("Server running on port 8000...")
server.serve_forever()
