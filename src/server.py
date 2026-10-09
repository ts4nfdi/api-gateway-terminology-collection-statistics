import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import collectionStats as cS

class Handler(BaseHTTPRequestHandler):

    def do_POST(self):
        parsed_url = urlparse(self.path)
        try:
            if parsed_url.path == "/stats":
                collections, collection_errors = self.handle_stats(parsed_url)
            elif parsed_url.path == "/stats/all":
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

            providers = cS.get_providers()

            collections_stats, collection_errors2 = cS.calculate_stats_for_collections(providers, collections)
            collection_errors = collection_errors + collection_errors2

            if not collections_stats:
                self.send_json(500, {
                    "error": "No collections without errors available for db insertion.",
                    "collection_errors": collection_errors

                })
                return
            cS.write_to_db(collections_stats)
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
                "message": "Successfully inserted collection stats into DB."
                           " For some collections no statistics could be generated.",
                "collection_errors": collection_errors
            })
        else:
            self.send_json(200, {
                "message": "Successfully inserted collection stats into DB."
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

server = HTTPServer(("0.0.0.0", 8000), Handler)

print("Server running on port 8000...")
server.serve_forever()
